"""
   Copyright 2022 Thomas Reidemeister

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""
import packbits
from enum import IntEnum, IntFlag

PRINT_HEAD_PINS = 128
USBID_BROTHER = 0x04f9
LINE_LENGTH_BYTES = 0x10
MINIMUM_TAPE_POINTS = 174 # 25.4 mm @ 180dpi
USB_OUT_EP_ID = 0x2
USB_IN_EP_ID = 0x81
USB_TRX_TIMEOUT_MS = 15000


class SupportedPrinterIDs(IntEnum):
    E550W = 0x2060
    P750W = 0x2062
    P710BT = 0x20af


STATUS_MESSAGE_LENGTH = 32


class StatusOffsets(IntEnum):
    ERROR_INFORMATION_1 = 8
    ERROR_INFORMATION_2 = 9
    MEDIA_WIDTH = 10
    MEDIA_TYPE = 11
    MODE = 15
    MEDIA_LENGTH = 17
    STATUS_TYPE = 18
    PHASE_TYPE = 19
    PHASE_NUMBER = 20
    NOTIFICATION_NUMBER = 22
    TAPE_COLOR_INFORMATION = 24
    TEXT_COLOR_INFORMATION = 25
    HARDWARE_SETTINGS = 26


class MediaWidthToTapeMargin:
    margin = {
        4: 52,  # 3.5mm
        6: 48,  # 6mm
        9: 39,  # 9mm
        12: 29, # 12mm
        18: 8,  # 19mm
        24: 0,  # 24mm
    }

    @staticmethod
    def to_print_width(tape_width: int):
        return PRINT_HEAD_PINS - MediaWidthToTapeMargin.margin[tape_width] * 2


class ErrorInformation1(IntFlag):
    NO_MEDIA = 0x01
    CUTTER_JAM = 0x04
    WEAK_BATTERIES = 0x08
    HIGH_VOLTAGE_ADAPTER = 0x40


class ErrorInformation2(IntFlag):
    WRONG_MEDIA = 0x01
    COVER_OPEN = 0x10
    OVERHEATING = 0x20


class MediaType(IntEnum):
    NO_MEDIA = 0x00
    LAMINATED_TAPE = 0x01
    NON_LAMINATED_TAPE = 0x03
    HEAT_SHRINK_TUBE = 0x11
    INCOMPATIBLE_TAPE = 0xFF


class Mode(IntFlag):
    AUTO_CUT = 0x40
    MIRROR_PRINTING = 0x80


class StatusType(IntEnum):
    REPLY_TO_STATUS_REQUEST = 0x00
    PRINTING_COMPLETED = 0x01
    ERROR_OCCURRED = 0x02
    TURNED_OFF = 0x04
    NOTIFICATION = 0x05
    PHASE_CHANGE = 0x06


class PhaseType(IntEnum):
    EDITING_STATE = 0x00
    PRINTING_STATE = 0x01


class PhaseNumberEditingState(IntEnum):
    EDITING_STATE = 0x0000
    FEED = 0x0001


class PhaseNumberPrintingState(IntEnum):
    PRINTING = 0x0000
    COVER_OPEN_WHILE_RECEIVING = 0x0014


class NotificationNumber(IntEnum):
    NOT_AVAILABLE = 0x00
    COVER_OPEN = 0x01
    COVER_CLOSED = 0x02


class TapeColor(IntEnum):
    WHITE = 0x01
    OTHER = 0x02
    CLEAR = 0x03
    RED = 0x04
    BLUE = 0x05
    YELLOW = 0x06
    GREEN = 0x07
    BLACK = 0x08
    CLEAR_WHITE_TEXT = 0x09
    MATTE_WHITE = 0x20
    MATTE_CLEAR = 0x21
    MATTE_SILVER = 0x22
    SATIN_GOLD = 0x23
    SATIN_SILVER = 0x24
    BLUE_D = 0x30
    RED_D = 0x31
    FLUORESCENT_ORANGE = 0x40
    FLUORESCENT_YELLOW = 0x41
    BERRY_PINK_S = 0x50
    LIGHT_GRAY_S = 0x51
    LIME_GREEN_S = 0x52
    YELLOW_F = 0x60
    PINK_F = 0x61
    BLUE_F = 0x62
    WHITE_HEAT_SHRINK_TUBE = 0x70
    WHITE_FLEX_ID = 0x90
    YELLOW_FLEX_ID = 0x91
    CLEANING = 0xF0
    STENCIL = 0xF1
    INCOMPATIBLE = 0xFF


class TextColor(IntEnum):
    WHITE = 0x01
    OTHER = 0x02
    RED = 0x04
    BLUE = 0x05
    BLACK = 0x08
    GOLD = 0x0A
    BLUE_F = 0x62
    CLEANING = 0xF0
    STENCIL = 0xF1
    INCOMPATIBLE = 0XFF


def invalidate():
    return b"\x00" * 100


def initialize():
    # send [1B 40]
    return b"\x1B\x40"


def enter_dynamic_command_mode():
    # set dynamic command mode to "raster mode" [1B 69 61 {01}]
    return b"\x1B\x69\x61\x01"


def enable_status_notification():
    # set automatic status notification mode to "notify" [1B 69 21 {00}]
    return b"\x1B\x69\x21\x00"


def print_information(data: bytes):
    # print to 24mm tape [1B 69 7A {84 00 18 00 <data length 4 bytes> 00 00}]
    return b"\x1B\x69\x7A\x84\x00\x18\x00" + \
           (len(data) >> 4).to_bytes(4, 'little') + \
           b"\x00\x00"


def set_mode(mode: Mode = Mode.AUTO_CUT):
    # set to auto-cut, no mirror printing [1B 69 4D {40}]
    return b"\x1B\x69\x4D" +\
        mode.to_bytes(1, "big")


def set_advanced_mode():
    # set print chaining off [1B 69 4B {08}]
    return b"\x1B\x69\x4B\x08"


def margin_amount(dots: int = 0):
    # set margin (feed) amount to 0 [1B 69 64 {00 00}]
    return b"\x1B\x69\x64"+dots.to_bytes(2, 'little')


def set_compression_mode():
    # set to TIFF compression [4D {02}]
    return b"\x4D\x02"


def gen_raster_commands(rasterized_image: bytes):
    raster_cmd = b'\x47'
    zero_cmd = b'\x5A'
    cmd_buffer = []
    # send all raster data lines
    for i in range(0, len(rasterized_image), LINE_LENGTH_BYTES):
        line = rasterized_image[i:i + LINE_LENGTH_BYTES]
        if line == b'\x00'*LINE_LENGTH_BYTES:
            cmd_buffer.append(zero_cmd)
        else:
            packed_line = packbits.encode(line)

            cmd = raster_cmd +\
                  len(packed_line).to_bytes(2, "little") +\
                  packed_line
            cmd_buffer.append(cmd)

    return cmd_buffer


def print_with_feeding():
    # print and feed [1A]
    return b"\x1A"


def status_information_request():
    # request status information [1B 69 53]
    return b"\x1B\x69\x53"
