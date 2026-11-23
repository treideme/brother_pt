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

Render one or more lines of text to a bitmap sized to the tape.

The rendering engine is FreeType with monochrome (1-bit) hinting and HarfBuzz
shaping (see ``brother_pt/font.py``, contributed by Joshua Wise). Monochrome
hinting produces crisp glyph edges on a 1-bit thermal print head, which looks
noticeably better than greyscale-antialiased text once thresholded for the
printer.

Fonts are selected through fontconfig: ``font_path`` may be either a path to a
``.ttf``/``.otf`` file or a fontconfig pattern such as
``"Helsinki Narrow:style=Bold"``. When no font is given a stock fontconfig
default (``"sans-serif"``) is used, so the command works on a plain Linux box
with no special fonts installed.

The result is an ``L`` image (black text ``0`` on white ``255``), which is the
polarity the raster path inks correctly.
"""

import os

from PIL import ImageOps

from .font import Font

DEFAULT_SPACING = 4  # px of white between stacked lines

# A fontconfig pattern that resolves to a usable font on a stock Linux box.
DEFAULT_FONT_PATTERN = "sans-serif"


def _make_font(size, font_path):
    """Build a :class:`~brother_pt.font.Font` at ``size`` px.

    ``font_path`` is used as a font file when it names an existing file, and as
    a fontconfig pattern otherwise. ``None`` falls back to a stock default
    pattern that always resolves.
    """
    if font_path and os.path.exists(font_path):
        return Font(filename=font_path, size=size)
    return Font(pattern=font_path or DEFAULT_FONT_PATTERN, size=size)


def _stack_height(lines, font, spacing):
    """Total ink height of ``lines`` stacked with ``spacing`` px between them."""
    total = sum(font.text_dimensions(line)[1] for line in lines)
    return total + spacing * (len(lines) - 1)


def _fit_font_size(lines, height, font_path, spacing):
    """The largest font size whose stacked lines fit within ``height`` px."""
    best = 1
    for size in range(4, height + 1):
        if _stack_height(lines, _make_font(size, font_path), spacing) <= height:
            best = size
        else:
            break
    return best


def render_text_label(lines, height, *, font_path=None, font_size=None, spacing=DEFAULT_SPACING):
    """Render ``lines`` into an ``L`` image exactly ``height`` px tall.

    The image is black text (``0``) on a white (``255``) background, which is
    the polarity the raster path inks correctly.

    ``font_size`` defaults to the largest size that fits the tape height; pass a
    value to force one. ``font_path`` selects the typeface: it may be a path to
    a ``.ttf``/``.otf`` file, or a fontconfig pattern (for example
    ``"Helsinki Narrow:style=Bold"``). Without it a stock fontconfig default is
    used, so the command works with no font files installed.

    Raises ``ValueError`` if there is no text or the geometry is impossible.
    """
    lines = list(lines)
    if not lines or all(line == "" for line in lines):
        raise ValueError("no text to print")
    if height < 1:
        raise ValueError("tape height must be positive")

    if font_size is None:
        font_size = _fit_font_size(lines, height, font_path, spacing)
    font = _make_font(font_size, font_path)

    bitmap = font.render_texts(
        lines, height=height, vcenter=True, hcenter=False, spacing=spacing
    )

    # ``bitmap.pixels`` is a "1"-mode image where 1 == ink. Convert to the
    # required polarity: ink -> 0 (black), background -> 255 (white).
    return ImageOps.invert(bitmap.pixels.convert("L"))
