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
import sys

import usb.core
import warnings

from .cmd import *
from .raster import *


def find_printers(serial=None):
    found_printers = []
    for product_id in SupportedPrinterIDs:
        dev = usb.core.find(idVendor=USBID_BROTHER, idProduct=product_id)
        if dev is not None:
            if serial is not None:
                if serial == dev.serial_number:
                    found_printers.append(dev)
                else:
                    continue
            else:
                found_printers.append(dev)

    return found_printers


class BrotherPt:
    def __init__(self, serial: str = None):
        printers = find_printers(serial)
        if len(printers) == 0:
            raise RuntimeError("No supported driver found")

        self._media_width = None
        self._media_type = None
        self._tape_color = None
        self._text_color = None

        self._dev = printers[0]
        self.__initialize()

    def __initialize(self):
        # libusb initialization, and bypass kernel drivers
        if self._dev.is_kernel_driver_active(0):
            self._dev.detach_kernel_driver(0)

        self._dev.set_configuration()
        self.update_status()

    def __write(self, data: bytes) -> int:
        length = 0
        while length < len(data):
            # chunk into packet size
            length += self._dev.write(USB_OUT_EP_ID, data[length:(length+0x40)], USB_TRX_TIMEOUT_MS)
            if length == 0:
                raise RuntimeError("IO timeout while writing to printer")
        return length

    def __read(self, length: int = 0x80) -> bytes:
        try:
            data = self._dev.read(USB_IN_EP_ID, length, USB_TRX_TIMEOUT_MS)
        except usb.core.USBError as e:
            raise RuntimeError("IO timeout while reading from printer")
        return data

    def update_status(self):
        self.__write(invalidate())
        self.__write(initialize())
        status_information = b''
        while len(status_information) == 0:
            self.__write(status_information_request())
            status_information = self.__read(STATUS_MESSAGE_LENGTH)

        self._media_width = status_information[StatusOffsets.MEDIA_WIDTH]
        self._media_type = MediaType(status_information[StatusOffsets.MEDIA_TYPE])
        self._tape_color = TapeColor(status_information[StatusOffsets.TAPE_COLOR_INFORMATION])
        self._text_color = TextColor(status_information[StatusOffsets.TEXT_COLOR_INFORMATION])

    @property
    def media_width(self) -> int:
        return self._media_width

    @property
    def media_type(self) -> MediaType:
        return self._media_type

    @property
    def tape_color(self) -> TapeColor:
        return self._tape_color

    @property
    def text_color(self) -> TextColor:
        return self._text_color

    def print_data(self, data:bytes, margin_px:int):
        self.__write(enter_dynamic_command_mode())
        self.__write(enable_status_notification())
        self.__write(print_information(data))
        self.__write(set_mode())
        self.__write(set_advanced_mode())
        self.__write(margin_amount(margin_px))
        self.__write(set_compression_mode())
        for cmd in gen_raster_commands(data):
            self.__write(cmd)
        self.__write(print_with_feeding())
        while True:
            res = self.__read()
            if len(res) > 0:
                if res[StatusOffsets.STATUS_TYPE] == StatusType.PRINTING_COMPLETED:
                    # absorb phase change message
                    self.__read()
                    break

    def print_image(self, image: Image, margin_px: int = 0):
        self.update_status()
        image = prepare_image(image, self.media_width)
        if (image.width + margin_px) < MINIMUM_TAPE_POINTS:
            warnings.warn("Image (%i) + cut margin (%i) is smaller than minimum tape width (%i) ... "
                          "cutting length will be extended" % (image.width, margin_px, MINIMUM_TAPE_POINTS))
        data = raster_image(image, self.media_width)
        self.print_data(data, margin_px)


if __name__ == '__main__':
    printer = BrotherPt()
    print("Media width: %dmm" % printer.media_width)
    print("Media type : %s" % printer.media_type.name)
    print("Tape color : %s" % printer.tape_color.name)
    print("Text color : %s" % printer.text_color.name)
    print()
    if len(sys.argv) != 2:
        print("%s <imagename>" % sys.argv[0], file=sys.stderr)
        sys.exit(1)
    image = Image.open(sys.argv[1])

    printer.print_image(image)
