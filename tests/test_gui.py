import unittest

from voicemod_for_linux.gui import _resolve_voicefx_output


class VoiceFxOutputSelectionTests(unittest.TestCase):
    def test_system_default_falls_back_to_virtual_output(self):
        devices = [
            (None, "System default"),
            (4, "Headphones"),
            (17, "VoiceFX_Output"),
        ]
        self.assertEqual(
            _resolve_voicefx_output(devices, 0),
            (2, (17, "VoiceFX_Output")),
        )

    def test_physical_output_falls_back_to_virtual_output(self):
        devices = [(None, "System default"), (4, "Headphones"), (17, "VoiceFX_Output")]
        self.assertEqual(
            _resolve_voicefx_output(devices, 1),
            (2, (17, "VoiceFX_Output")),
        )

    def test_voicefx_output_selection_is_preserved(self):
        devices = [(None, "System default"), (17, "VoiceFX_Output")]
        self.assertEqual(
            _resolve_voicefx_output(devices, 1),
            (1, (17, "VoiceFX_Output")),
        )

    def test_missing_virtual_output_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, "VoiceFX_Output is unavailable"):
            _resolve_voicefx_output(
                [(None, "System default"), (4, "Headphones")], 0
            )


if __name__ == "__main__":
    unittest.main()
