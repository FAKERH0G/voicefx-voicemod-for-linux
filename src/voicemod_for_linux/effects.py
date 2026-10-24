from __future__ import annotations

import numpy as np


EFFECTS = ("clean", "robot", "radio", "echo")


class EffectProcessor:
    def __init__(self, effect: str, sample_rate: int, channels: int) -> None:
        if effect not in EFFECTS:
            raise ValueError(f"Unknown effect {effect!r}; choose from {', '.join(EFFECTS)}")
        if sample_rate <= 0 or channels <= 0:
            raise ValueError("Sample rate and channel count must be positive")

        self.effect = effect
        self.sample_rate = sample_rate
        self.channels = channels
        self._phase = 0.0
        self._echo = np.zeros((max(1, int(sample_rate * 0.24)), channels), dtype=np.float32)
        self._echo_position = 0

    def process(self, audio: np.ndarray) -> np.ndarray:
        if audio.ndim != 2 or audio.shape[1] != self.channels:
            raise ValueError(f"Expected audio with {self.channels} channel(s)")

        if self.effect == "clean":
            return audio.copy()
        if self.effect == "robot":
            frames = audio.shape[0]
            phase = self._phase + (
                2.0 * np.pi * 35.0 * np.arange(frames, dtype=np.float64) / self.sample_rate
            )
            carrier = np.sin(phase).astype(np.float32)[:, np.newaxis]
            if frames:
                self._phase = float(
                    (phase[-1] + 2.0 * np.pi * 35.0 / self.sample_rate) % (2.0 * np.pi)
                )
            return audio * (0.2 + 0.8 * carrier)
        if self.effect == "radio":
            clipped = np.clip(audio * 3.0, -1.0, 1.0)
            return np.round(clipped * 16.0) / 16.0
        return self._process_echo(audio)

    def _process_echo(self, audio: np.ndarray) -> np.ndarray:
        output = np.empty_like(audio)
        offset = 0
        while offset < audio.shape[0]:
            count = min(audio.shape[0] - offset, self._echo.shape[0] - self._echo_position)
            end = offset + count
            echo_end = self._echo_position + count
            delayed = self._echo[self._echo_position : echo_end].copy()
            chunk = audio[offset:end]
            self._echo[self._echo_position : echo_end] = chunk + delayed * 0.35
            output[offset:end] = chunk + delayed * 0.55
            self._echo_position = echo_end % self._echo.shape[0]
            offset = end
        return np.clip(output, -1.0, 1.0)
