"""Unit tests for the raster command builders. No printer required."""
import unittest

from brother_pt import cmd


class CommandBuilders(unittest.TestCase):
    def test_initialize(self):
        self.assertEqual(cmd.initialize(), b"\x1b\x40")

    def test_invalidate_is_100_nulls(self):
        self.assertEqual(cmd.invalidate(), b"\x00" * 100)

    def test_enter_dynamic_command_mode(self):
        self.assertEqual(cmd.enter_dynamic_command_mode(), b"\x1b\x69\x61\x01")

    def test_print_information_encodes_width_and_length(self):
        data = b"\x00" * 32  # len >> 4 == 2
        out = cmd.print_information(data, 9)
        self.assertTrue(out.startswith(b"\x1b\x69\x7a\x84\x00\x09\x00"))
        self.assertEqual(out[7:11], (len(data) >> 4).to_bytes(4, "little"))
        self.assertEqual(out[-2:], b"\x00\x00")

    def test_set_mode_default_is_auto_cut(self):
        self.assertEqual(cmd.set_mode(), b"\x1b\x69\x4d\x40")

    def test_set_mode_no_cut(self):
        self.assertEqual(cmd.set_mode(cmd.Mode(0)), b"\x1b\x69\x4d\x00")

    def test_margin_amount_little_endian(self):
        self.assertEqual(cmd.margin_amount(0), b"\x1b\x69\x64\x00\x00")
        self.assertEqual(cmd.margin_amount(14), b"\x1b\x69\x64" + (14).to_bytes(2, "little"))

    def test_print_with_feeding(self):
        self.assertEqual(cmd.print_with_feeding(), b"\x1a")


class TapeGeometry(unittest.TestCase):
    def test_to_print_width_9mm(self):
        self.assertEqual(cmd.MediaWidthToTapeMargin.to_print_width(9), 128 - 39 * 2)  # 50

    def test_every_width_fills_the_head(self):
        # margin + printable + margin must equal the 128-pin head for every tape.
        for width, margin in cmd.MediaWidthToTapeMargin.margin.items():
            printable = cmd.MediaWidthToTapeMargin.to_print_width(width)
            self.assertEqual(margin + printable + margin, cmd.PRINT_HEAD_PINS)


class GenRasterCommands(unittest.TestCase):
    def test_blank_line_becomes_zero_command(self):
        blank = b"\x00" * cmd.LINE_LENGTH_BYTES
        self.assertEqual(cmd.gen_raster_commands(blank), [b"\x5a"])

    def test_nonblank_line_uses_raster_command(self):
        line = b"\xff" + b"\x00" * (cmd.LINE_LENGTH_BYTES - 1)
        out = cmd.gen_raster_commands(line)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith(b"\x47"))

    def test_two_lines_two_commands(self):
        self.assertEqual(len(cmd.gen_raster_commands(b"\x00" * (cmd.LINE_LENGTH_BYTES * 2))), 2)


if __name__ == "__main__":
    unittest.main()
