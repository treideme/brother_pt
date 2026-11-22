"""Tests for the printer model registry."""

import unittest

from brother_pt.cmd import SUPPORTED_MODELS, UNSUPPORTED_MODELS, ModelFlag


class ModelRegistry(unittest.TestCase):
    def test_keeps_the_original_three(self):
        for pid, name in [(0x2060, "PT-E550W"), (0x2062, "PT-P750W"), (0x20AF, "PT-P710BT")]:
            self.assertIn(pid, SUPPORTED_MODELS)
            self.assertEqual(SUPPORTED_MODELS[pid][0], name)

    def test_supported_entries_are_well_formed(self):
        for pid, (name, flags) in SUPPORTED_MODELS.items():
            self.assertIsInstance(pid, int)
            self.assertTrue(name.startswith("PT-"), name)
            self.assertIsInstance(flags, ModelFlag)

    def test_supported_and_unsupported_do_not_overlap(self):
        self.assertEqual(set(SUPPORTED_MODELS) & set(UNSUPPORTED_MODELS), set())

    def test_plite_decoys_are_not_supported(self):
        # These product ids are the printer in P-Lite mass-storage mode and must
        # never be driven as raster.
        for pid in (0x2030, 0x2064, 0x2065):
            self.assertIn(pid, UNSUPPORTED_MODELS)
            self.assertNotIn(pid, SUPPORTED_MODELS)

    def test_360dpi_heads_are_not_claimed_as_supported(self):
        for pid in (0x2083, 0x2085, 0x2086, 0x20C7):
            self.assertIn(pid, UNSUPPORTED_MODELS)
            self.assertNotIn(pid, SUPPORTED_MODELS)

    def test_unsupported_entries_have_a_reason(self):
        for name, reason in UNSUPPORTED_MODELS.values():
            self.assertTrue(name)
            self.assertTrue(reason)

    def test_added_models_present(self):
        # A few of the broad-support additions.
        for pid in (0x205F, 0x205E, 0x2061, 0x2074):
            self.assertIn(pid, SUPPORTED_MODELS)


if __name__ == "__main__":
    unittest.main()
