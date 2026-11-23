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
import warnings

from PIL import ImageOps

from .font import Font

DEFAULT_SPACING = 4  # px of white between stacked lines

# A fontconfig pattern that resolves to a usable font on a stock Linux box.
DEFAULT_FONT_PATTERN = "sans-serif"

# Smallest size the auto-fit will choose; below this, text is illegible on tape.
MIN_FONT_SIZE = 4

# Suffixes that mark a --font argument as a font file rather than a fontconfig
# pattern (patterns like "Helsinki Narrow:style=Bold" carry none of these).
_FONT_FILE_SUFFIXES = (".ttf", ".otf", ".ttc", ".otc")


def _looks_like_font_path(s):
    """True if ``s`` is meant as a font file path rather than a fontconfig pattern."""
    return "/" in s or "\\" in s or s.lower().endswith(_FONT_FILE_SUFFIXES)


def _fontconfig_available():
    try:
        import fontconfig  # noqa: F401
        return True
    except ImportError:
        return False


# Stock OS fonts to fall back on for the default when fontconfig is not
# installed (e.g. Windows, where fontconfig-py has no wheel). An explicit
# --font path always takes precedence over these.
_OS_DEFAULT_FONTS = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\segoeui.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _default_font_file():
    for path in _OS_DEFAULT_FONTS:
        if os.path.exists(path):
            return path
    return None


def _make_font(size, font_path):
    """Build a :class:`~brother_pt.font.Font` at ``size`` px.

    ``font_path`` is used as a font file when it names an existing file, and as
    a fontconfig pattern otherwise. ``None`` uses fontconfig's ``sans-serif``
    where fontconfig is available, otherwise a stock OS font -- so the command
    still works on platforms without fontconfig (e.g. Windows).
    """
    if font_path and os.path.exists(font_path):
        return Font(filename=font_path, size=size)
    if font_path:
        if _looks_like_font_path(font_path):
            # A path-like argument that does not exist: fail loudly instead of
            # silently handing it to fontconfig, which would match some default
            # font and print in the wrong typeface.
            raise FileNotFoundError("font file not found: %s" % font_path)
        return Font(pattern=font_path, size=size)  # a fontconfig pattern
    if _fontconfig_available():
        return Font(pattern=DEFAULT_FONT_PATTERN, size=size)
    path = _default_font_file()
    if path:
        return Font(filename=path, size=size)
    raise ValueError(
        "no default font available without fontconfig; pass --font with a "
        '.ttf/.otf path, or install "brother_pt[fontconfig]" on Linux'
    )


def _stack_height(lines, font, spacing):
    """Total ink height of ``lines`` stacked with ``spacing`` px between them."""
    total = sum(font.text_dimensions(line)[1] for line in lines)
    return total + spacing * (len(lines) - 1)


def _fit_font_size(lines, height, font_path, spacing):
    """The largest font size whose stacked lines fit within ``height`` px.

    Raises ``ValueError`` if even the smallest legible size does not fit, rather
    than returning a size that renders an unreadable one-pixel sliver.
    """
    best = None
    for size in range(MIN_FONT_SIZE, height + 1):
        if _stack_height(lines, _make_font(size, font_path), spacing) <= height:
            best = size
        else:
            break
    if best is None:
        raise ValueError(
            "text does not fit in %d px of tape height; use fewer lines, "
            "shorter text, or a wider tape" % height
        )
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
    if font_size is not None and font_size < 1:
        raise ValueError("font size must be positive")

    explicit_size = font_size is not None
    if font_size is None:
        font_size = _fit_font_size(lines, height, font_path, spacing)
    font = _make_font(font_size, font_path)

    if explicit_size:
        stack = _stack_height(lines, font, spacing)
        if stack > height:
            warnings.warn(
                "text is %d px tall but the tape is only %d px; it will be clipped"
                % (stack, height), stacklevel=2)

    bitmap = font.render_texts(
        lines, height=height, vcenter=True, hcenter=False, spacing=spacing
    )

    # ``bitmap.pixels`` is a "1"-mode image where 1 == ink. Convert to the
    # required polarity: ink -> 0 (black), background -> 255 (white).
    return ImageOps.invert(bitmap.pixels.convert("L"))
