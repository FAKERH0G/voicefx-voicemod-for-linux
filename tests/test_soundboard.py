import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from voicemod_for_linux.soundboard import Soundboard, load_wav


def write_wav(path: Path, samples: np.ndarray, sample_rate: int, channels: int) -> None:
    pcm = np.clip(samples, -1.0, 1.0)
    pcm = (pcm * 32767).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(pcm.tobytes())


class SoundboardTests(unittest.TestCase):
    def test_load_wav_converts_stereo_and_resamples(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stereo.wav"
            write_wav(path, np.array([[0.5, 0.5], [-0.5, -0.5], [0.25, 0.25], [0, 0]]), 4, 2)
            audio = load_wav(path, sample_rate=2)
        self.assertEqual(audio.shape, (2, 1))
        self.assertAlmostEqual(float(audio[0, 0]), 0.5, places=3)
        self.assertAlmostEqual(float(audio[1, 0]), 0.25, places=3)

    def test_play_stop_loop_and_mix(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            write_wav(path, np.full((3, 1), 0.5, dtype=np.float32), 48000, 1)
            board = Soundboard(sample_rate=48000)
            name = board.add_file(path)

            board.play(name)
            first = board.mix(2)
            np.testing.assert_allclose(first[:, 0], [0.5, 0.5], atol=0.001)
            self.assertTrue(board.list_sounds()[0][2])

            tail = board.mix(2)
            self.assertAlmostEqual(float(tail[0, 0]), 0.5, places=3)
            self.assertAlmostEqual(float(tail[1, 0]), 0.0, places=3)
            self.assertFalse(board.list_sounds()[0][2])

            board.set_looping(name, True)
            board.play(name)
            repeated = board.mix(5)
            self.assertTrue(np.all(repeated[:, 0] > 0.49))
            board.stop(name)
            self.assertFalse(board.list_sounds()[0][2])

    def test_duplicate_names_are_unique_and_unknown_sounds_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "tone.wav"
            write_wav(path, np.zeros((2, 1), dtype=np.float32), 48000, 1)
            board = Soundboard(sample_rate=48000)
            self.assertEqual(board.add_file(path), "tone")
            self.assertEqual(board.add_file(path), "tone (2)")
            with self.assertRaises(ValueError):
                board.play("missing")

    def test_invalid_wav_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "not-audio.wav"
            path.write_text("not audio")
            with self.assertRaises(ValueError):
                load_wav(path, sample_rate=48000)


if __name__ == "__main__":
    unittest.main()
