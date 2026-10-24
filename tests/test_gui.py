import unittest
from unittest.mock import patch

from voicemod_for_linux.gui import _resolve_input_device, _resolve_voicefx_output


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

    @patch("voicemod_for_linux.gui.sd.query_devices")
    def test_input_is_mapped_to_matching_device_on_output_backend(self, query):
        devices = [
            {"name": "USB Mic ALSA", "hostapi": 0, "max_input_channels": 1},
            {"name": "USB Mic Mono", "hostapi": 2, "max_input_channels": 1},
            {"name": "VoiceFX_Microphone", "hostapi": 2, "max_input_channels": 2},
        ]

        def query_device(device=None, kind=None):
            if device is None:
                return devices
            if device == 0 and kind == "input":
                return devices[0]
            if device == 3 and kind == "output":
                return {"name": "VoiceFX_Output", "hostapi": 2, "max_output_channels": 2}
            raise AssertionError((device, kind))

        query.side_effect = query_device
        self.assertEqual(_resolve_input_device(0, 3), 1)

    @patch("voicemod_for_linux.gui.sd.query_devices")
    def test_default_input_uses_physical_device_on_output_backend(self, query):
        devices = [
            {"name": "default", "hostapi": 0, "max_input_channels": 128},
            {"name": "USB Microphone Mono", "hostapi": 2, "max_input_channels": 1},
            {"name": "VoiceFX_Microphone", "hostapi": 2, "max_input_channels": 2},
        ]

        def query_device(device=None, kind=None):
            if device is None:
                return devices
            if device == 3 and kind == "output":
                return {"name": "VoiceFX_Output", "hostapi": 2, "max_output_channels": 2}
            raise AssertionError((device, kind))

        query.side_effect = query_device
        self.assertEqual(_resolve_input_device(None, 3), 1)


if __name__ == "__main__":
    unittest.main()
