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

Render one or more lines of text to a bitmap sized to the tape, using only
Pillow's bundled font support -- no FreeType, HarfBuzz, fontconfig or external
font files are required. The result is an ``L`` image (black text on white),
which is the polarity the raster path inks correctly.
"""

from PIL import Image, ImageDraw, ImageFont

DEFAULT_SPACING = 4  # px of white between stacked lines


def _load_font(size, font_path=None):
    if font_path:
        return ImageFont.truetype(font_path, size)
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10: the default font is a fixed size
        return ImageFont.load_default()


def _line_bbox(text, font):
    """(width, height, top) of one line, measured without drawing."""
    probe = ImageDraw.Draw(Image.new("L", (1, 1), 255))
    left, top, right, bottom = probe.textbbox((0, 0), text or " ", font=font)
    return right - left, bottom - top, top


def _stack_height(lines, font, spacing):
    total = sum(_line_bbox(line, font)[1] for line in lines)
    return total + spacing * (len(lines) - 1)


def _fit_font_size(lines, height, font_path, spacing):
    """The largest built-in font size whose stacked lines fit ``height`` px."""
    best = 1
    for size in range(4, height + 1):
        if _stack_height(lines, _load_font(size, font_path), spacing) <= height:
            best = size
        else:
            break
    return best


def render_text_label(lines, height, *, font_path=None, font_size=None, spacing=DEFAULT_SPACING):
    """Render ``lines`` into an ``L`` image exactly ``height`` px tall.

    ``font_size`` defaults to the largest size that fits the tape height; pass a
    value to force one. ``font_path`` selects a .ttf/.otf; without it Pillow's
    bundled font is used, so the command works with no font files installed.
    Raises ``ValueError`` if there is no text or the geometry is impossible.
    """
    lines = list(lines)
    if not lines or all(line == "" for line in lines):
        raise ValueError("no text to print")
    if height < 1:
        raise ValueError("tape height must be positive")

    if font_size is None:
        font_size = _fit_font_size(lines, height, font_path, spacing)
    font = _load_font(font_size, font_path)

    strips = []
    for line in lines:
        width, line_h, top = _line_bbox(line, font)
        strip = Image.new("L", (max(1, width + 2), max(1, line_h)), 255)
        ImageDraw.Draw(strip).text((1, -top), line, font=font, fill=0)
        strips.append(strip)

    total_h = sum(s.height for s in strips) + spacing * (len(strips) - 1)
    width = max(s.width for s in strips)
    canvas = Image.new("L", (width, height), 255)
    y = max(0, (height - total_h) // 2)
    for strip in strips:
        canvas.paste(strip, (0, y))
        y += strip.height + spacing
    return canvas
