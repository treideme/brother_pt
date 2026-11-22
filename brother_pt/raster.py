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
from PIL import Image
from .cmd import MediaWidthToTapeMargin, PRINT_HEAD_PINS


def make_fit(image: Image, media_width: int):
    expected_height = MediaWidthToTapeMargin.to_print_width(media_width)
    if image.height != expected_height:
        if image.width != expected_height:
            return None
        else:
            return image.transpose(Image.ROTATE_90)
    return image


def has_transparency(img):
    if img.info.get("transparency", None) is not None:
        return True
    if img.mode == "P":
        transparent = img.info.get("transparency", -1)
        # getcolors() returns None when the image has more distinct colors than
        # its (default 256) limit; a palette image never does, but guard anyway.
        for _, index in (img.getcolors() or []):
            if index == transparent:
                return True
    return False


def _luma_cutoff(threshold):
    """Luminance below which a pixel prints as ink.

    ``threshold`` is a percentage in [0, 100]; ``None`` keeps the original
    behaviour of inking every pixel that is not pure white.
    """
    if threshold is None:
        return 0xFF  # ink if luminance < 255, i.e. anything not pure white
    return round(max(0.0, min(100.0, threshold)) / 100.0 * 0xFF)


def select_raster_channel(image: Image, threshold: float = None):
    # Special handling for paletized images
    if image.mode == 'P':
        if has_transparency(image):
            image = image.convert('RGBA')
        else:
            image = image.convert('RGB')

    cutoff = _luma_cutoff(threshold)
    if image.mode == '1':
        # BW
        return image
    elif image.mode == 'L':
        # Darker than the cutoff is ink; everything else is background.
        return image.point(lambda x: 0xFF if x < cutoff else 0)
    elif image.mode == 'RGB':
        return image.convert('L').point(lambda x: 0xFF if x < cutoff else 0)
    elif image.mode == 'RGBA':
        # Use alpha, any transparency is not printed
        return image.split()[-1].point(lambda x: 0xFF if x > 0 else 0)
    else:
        raise AttributeError("Unsupported color space for printing: "+image.mode)


def compress_buffer(buffer: bytearray):
    # Pack 8 bytes (one per pin, non-zero = ink) into one bit-per-pin byte. A
    # valid raster is a whole number of 128-pin columns and so already a
    # multiple of 8; pad defensively rather than IndexError on a stray input.
    if len(buffer) % 8:
        buffer = bytearray(buffer) + bytearray(8 - len(buffer) % 8)
    bits = bytearray()
    for i in range(0, len(buffer), 8):
        byte = 0
        for j in range(0, 8):
            if buffer[i + j] > 0:
                byte |= (1 << (7 - j))
        bits.append(byte)
    return bits


def prepare_image(image: Image, media_width: int, threshold: float = None):
    width, height = image.width, image.height
    image = make_fit(image, media_width)
    # Image doesn't fit the tape width
    if image is None:
        expected_height = MediaWidthToTapeMargin.to_print_width(media_width)
        raise AttributeError("At least one dimension needs to fit the tape width: %i vs (%i, %i)" %
                             (expected_height, width, height))

    return select_raster_channel(image, threshold)


def raster_image(prepared_image: Image, media_width: int):
    # Print buffer
    buffer = bytearray()

    # Compose raster template
    for column in range(prepared_image.width):
        # Leading margin of print head
        buffer += b'\x00'*MediaWidthToTapeMargin.margin[media_width]

        # printable raster
        for row in range(prepared_image.height):
            buffer += b'\xFF' if prepared_image.getpixel((column, row)) else b'\00'

        # Trailing margin of print head
        buffer += b'\x00' * MediaWidthToTapeMargin.margin[media_width]

    return compress_buffer(buffer)
