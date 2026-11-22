"""Unit tests for the image-to-raster pipeline. No printer required."""
import unittest

from PIL import Image

from brother_pt import raster
from brother_pt.cmd import MediaWidthToTapeMargin


class CompressBuffer(unittest.TestCase):
    def test_eight_bytes_pack_into_one(self):
        buf = bytearray([0xFF, 0, 0xFF, 0, 0, 0, 0, 0])  # 1010 0000
        self.assertEqual(bytes(raster.compress_buffer(buf)), b"\xa0")

    def test_pads_non_multiple_of_eight(self):
        # Three bytes is not a whole pin-byte; it must pad, not IndexError.
        self.assertEqual(bytes(raster.compress_buffer(bytearray([0xFF, 0, 0xFF]))), b"\xa0")

    def test_all_set(self):
        self.assertEqual(bytes(raster.compress_buffer(bytearray([1] * 8))), b"\xff")


class LumaCutoff(unittest.TestCase):
    def test_none_is_pure_white(self):
        self.assertEqual(raster._luma_cutoff(None), 0xFF)

    def test_percentages(self):
        self.assertEqual(raster._luma_cutoff(0), 0)
        self.assertEqual(raster._luma_cutoff(100), 0xFF)
        self.assertEqual(raster._luma_cutoff(50), 128)

    def test_clamps_out_of_range(self):
        self.assertEqual(raster._luma_cutoff(-10), 0)
        self.assertEqual(raster._luma_cutoff(250), 0xFF)


class SelectRasterChannel(unittest.TestCase):
    def test_mode_1_passthrough(self):
        img = Image.new("1", (2, 2), 1)
        self.assertIs(raster.select_raster_channel(img), img)

    def test_L_inks_non_white_by_default(self):
        self.assertEqual(raster.select_raster_channel(Image.new("L", (1, 1), 254)).getpixel((0, 0)), 0xFF)

    def test_L_pure_white_is_background(self):
        self.assertEqual(raster.select_raster_channel(Image.new("L", (1, 1), 255)).getpixel((0, 0)), 0)

    def test_L_threshold_splits_at_cutoff(self):
        bg = raster.select_raster_channel(Image.new("L", (1, 1), 200), threshold=50)
        ink = raster.select_raster_channel(Image.new("L", (1, 1), 100), threshold=50)
        self.assertEqual(bg.getpixel((0, 0)), 0)
        self.assertEqual(ink.getpixel((0, 0)), 0xFF)

    def test_rgb_black_is_ink(self):
        self.assertEqual(raster.select_raster_channel(Image.new("RGB", (1, 1), (0, 0, 0))).getpixel((0, 0)), 0xFF)

    def test_unsupported_mode_raises(self):
        with self.assertRaises(AttributeError):
            raster.select_raster_channel(Image.new("CMYK", (1, 1)))

    def test_rgba_uses_alpha(self):
        img = Image.new("RGBA", (2, 1), (0, 0, 0, 0))
        img.putpixel((0, 0), (255, 255, 255, 255))  # opaque -> ink
        out = raster.select_raster_channel(img)
        self.assertEqual(out.getpixel((0, 0)), 0xFF)  # opaque prints
        self.assertEqual(out.getpixel((1, 0)), 0)  # transparent does not


class PrepareImage(unittest.TestCase):
    def test_threshold_is_passed_through(self):
        h = MediaWidthToTapeMargin.to_print_width(9)
        img = Image.new("L", (4, h), 200)  # light gray
        # With a 90% cutoff (229) the light gray is ink; with 10% (25) it is not.
        self.assertEqual(raster.prepare_image(img.copy(), 9, threshold=90).getpixel((0, 0)), 0xFF)
        self.assertEqual(raster.prepare_image(img.copy(), 9, threshold=10).getpixel((0, 0)), 0)

    def test_rejects_image_that_does_not_fit(self):
        with self.assertRaises(AttributeError):
            raster.prepare_image(Image.new("L", (80, 80)), 9)


class MakeFit(unittest.TestCase):
    def setUp(self):
        self.h = MediaWidthToTapeMargin.to_print_width(9)  # 50

    def test_exact_height_passes_through(self):
        img = Image.new("L", (80, self.h))
        self.assertIs(raster.make_fit(img, 9), img)

    def test_rotates_when_width_matches_tape(self):
        out = raster.make_fit(Image.new("L", (self.h, 80)), 9)
        self.assertIsNotNone(out)
        self.assertEqual(out.height, self.h)

    def test_none_when_neither_dimension_matches(self):
        self.assertIsNone(raster.make_fit(Image.new("L", (80, 80)), 9))


class RasterImage(unittest.TestCase):
    def test_output_length_is_16_bytes_per_column(self):
        h = MediaWidthToTapeMargin.to_print_width(9)
        prepared = raster.select_raster_channel(Image.new("1", (4, h), 1))
        self.assertEqual(len(raster.raster_image(prepared, 9)), 4 * 16)


class HasTransparency(unittest.TestCase):
    def test_rgb_has_none(self):
        self.assertFalse(raster.has_transparency(Image.new("RGB", (1, 1))))

    def test_rgba_info_flag(self):
        img = Image.new("RGBA", (1, 1))
        img.info["transparency"] = 0
        self.assertTrue(raster.has_transparency(img))


if __name__ == "__main__":
    unittest.main()
