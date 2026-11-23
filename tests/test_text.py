"""Tests for the text label renderer and the ``text`` CLI command."""

import argparse
import os
import tempfile
import unittest

from brother_pt.text import render_text_label


class RenderTextLabel(unittest.TestCase):
    def test_single_line_fills_tape_height(self):
        img = render_text_label(["hello"], 50)
        self.assertEqual(img.mode, "L")
        self.assertEqual(img.height, 50)
        self.assertGreater(img.width, 0)

    def test_polarity_is_black_text_on_white(self):
        # The raster path inks dark pixels, so text must be 0 (black) on 255.
        lo, hi = render_text_label(["AB"], 50).getextrema()
        self.assertEqual(lo, 0)  # ink present
        self.assertEqual(hi, 255)  # background present

    def test_multiple_lines_stack_and_keep_height(self):
        img = render_text_label(["line one", "line two"], 50)
        self.assertEqual(img.height, 50)

    def test_width_is_the_widest_line(self):
        one = render_text_label(["i"], 50, font_size=20)
        many = render_text_label(["i", "wwwwwwww"], 50, font_size=20)
        self.assertGreater(many.width, one.width)

    def test_auto_fit_keeps_height_for_long_text(self):
        img = render_text_label(["a fairly long single line of text"], 50)
        self.assertEqual(img.height, 50)

    def test_explicit_font_size_is_honoured(self):
        small = render_text_label(["Mg"], 50, font_size=10)
        big = render_text_label(["Mg"], 50, font_size=30)
        self.assertGreater(big.width, small.width)

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            render_text_label([], 50)

    def test_all_blank_lines_raise(self):
        with self.assertRaises(ValueError):
            render_text_label(["", ""], 50)

    def test_nonpositive_height_raises(self):
        with self.assertRaises(ValueError):
            render_text_label(["x"], 0)

    def test_too_small_to_fit_raises(self):
        # Many lines on a tiny tape must raise, not render a 1px sliver.
        with self.assertRaises(ValueError):
            render_text_label(["a", "b", "c", "d", "e"], 8)

    def test_nonpositive_font_size_raises(self):
        with self.assertRaises(ValueError):
            render_text_label(["Hi"], 50, font_size=0)

    def test_missing_font_file_raises(self):
        # A path-like --font that does not exist must error, not silently fall
        # back to a default font.
        with self.assertRaises(FileNotFoundError):
            render_text_label(["Hi"], 50, font_path="/tmp/not-a-real-font.ttf")
        with self.assertRaises(FileNotFoundError):
            render_text_label(["Hi"], 50, font_path="also-missing.otf")

    def test_oversize_font_size_warns_about_clipping(self):
        with self.assertWarns(UserWarning):
            render_text_label(["Hi"], 50, font_size=200)

    def test_pattern_without_fontconfig_raises_importerror(self):
        # On a host without fontconfig (e.g. Windows), a font *pattern* must
        # raise a clear ImportError rather than something do_text won't catch.
        import sys
        from unittest import mock
        with mock.patch.dict(sys.modules, {"fontconfig": None}):
            with self.assertRaises(ImportError):
                render_text_label(["Hi"], 50, font_path="Some Pattern Name")


class DoTextOffline(unittest.TestCase):
    """The ``--tape-mm`` + ``--output`` path renders without a printer."""

    def _args(self, **over):
        base = dict(
            printer=None, text=["brave-river"], font=None, size=None,
            spacing=4, margin=0, no_cut=False, tape_mm=9, output=None,
        )
        base.update(over)
        return argparse.Namespace(**base)

    def test_output_writes_png_without_a_printer(self):
        from brother_pt.__main__ import do_text

        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "label.png")
            rc = do_text(self._args(output=out))
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(out))

    def test_tape_mm_without_output_is_an_error(self):
        from brother_pt.__main__ import do_text

        self.assertEqual(do_text(self._args(output=None)), 1)

    def test_empty_text_is_an_error(self):
        from brother_pt.__main__ import do_text

        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "label.png")
            self.assertEqual(do_text(self._args(text=[""], output=out)), 1)


if __name__ == "__main__":
    unittest.main()
