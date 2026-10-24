import unittest

import numpy as np

from voicemod_for_linux.effects import EFFECTS, EffectProcessor


class EffectProcessorTests(unittest.TestCase):
    def test_all_effects_preserve_shape_and_finite_samples(self):
        audio = np.full((128, 1), 0.1, dtype=np.float32)
        for effect in EFFECTS:
            with self.subTest(effect=effect):
                output = EffectProcessor(effect, sample_rate=48000, channels=1).process(audio)
                self.assertEqual(output.shape, audio.shape)
                self.assertTrue(np.isfinite(output).all())

    def test_clean_effect_does_not_modify_input(self):
        audio = np.array([[0.1], [-0.2]], dtype=np.float32)
        output = EffectProcessor("clean", 48000, 1).process(audio)
        np.testing.assert_array_equal(output, audio)
        self.assertIsNot(output, audio)

    def test_echo_carries_audio_across_calls(self):
        processor = EffectProcessor("echo", sample_rate=10, channels=1)
        first = np.zeros((5, 1), dtype=np.float32)
        first[0, 0] = 0.5
        output = processor.process(first)
        self.assertGreater(float(output[2, 0]), 0.0)

    def test_invalid_effect_and_channel_shape_are_rejected(self):
        with self.assertRaises(ValueError):
            EffectProcessor("unknown", 48000, 1)
        with self.assertRaises(ValueError):
            EffectProcessor("clean", 48000, 1).process(np.zeros((8, 2), dtype=np.float32))


if __name__ == "__main__":
    unittest.main()
