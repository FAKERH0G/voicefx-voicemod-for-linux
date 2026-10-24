from __future__ import annotations

import threading
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


MAX_CLIP_SECONDS = 300


def load_wav(path: str | Path, sample_rate: int) -> np.ndarray:
    """Load and convert a PCM WAV sound to mono float audio at sample_rate."""
    if sample_rate <= 0:
        raise ValueError("Sample rate must be positive")

    try:
        with wave.open(str(path), "rb") as source:
            channels = source.getnchannels()
            source_rate = source.getframerate()
            sample_width = source.getsampwidth()
            frame_count = source.getnframes()
            if source.getcomptype() != "NONE":
                raise ValueError("Only uncompressed PCM WAV sounds are supported")
            if channels not in (1, 2):
                raise ValueError("WAV sounds must be mono or stereo")
            if sample_width not in (1, 2, 3, 4):
                raise ValueError("WAV sounds must use 8-, 16-, 24-, or 32-bit PCM")
            if source_rate <= 0 or frame_count <= 0:
                raise ValueError("WAV sound has no audio frames")
            if frame_count > source_rate * MAX_CLIP_SECONDS:
                raise ValueError(f"WAV sounds must be {MAX_CLIP_SECONDS // 60} minutes or shorter")
            raw = source.readframes(frame_count)
    except (wave.Error, OSError) as error:
        raise ValueError(f"Could not read WAV sound: {error}") from error

    if sample_width == 1:
        audio = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sample_width == 2:
        audio = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    elif sample_width == 3:
        bytes_ = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        samples = bytes_[:, 0] | (bytes_[:, 1] << 8) | (bytes_[:, 2] << 16)
        samples = (samples ^ 0x800000) - 0x800000
        audio = samples.astype(np.float32) / 8388608.0
    else:
        audio = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0

    audio = audio.reshape(-1, channels)
    if channels == 2:
        audio = audio.mean(axis=1, keepdims=True)
    if source_rate != sample_rate:
        target_frames = max(1, round(len(audio) * sample_rate / source_rate))
        old_positions = np.arange(len(audio), dtype=np.float64)
        new_positions = np.arange(target_frames, dtype=np.float64) * source_rate / sample_rate
        audio = np.interp(new_positions, old_positions, audio[:, 0]).astype(np.float32)[:, None]
    return audio


@dataclass
class Sound:
    name: str
    path: Path
    audio: np.ndarray
    position: int = 0
    playing: bool = False
    looping: bool = False


class Soundboard:
    def __init__(self, sample_rate: int, channels: int = 1) -> None:
        if sample_rate <= 0 or channels <= 0:
            raise ValueError("Sample rate and channel count must be positive")
        self.sample_rate = sample_rate
        self.channels = channels
        self._sounds: list[Sound] = []
        self._lock = threading.Lock()

    def add_file(self, path: str | Path) -> str:
        file_path = Path(path).expanduser()
        if not file_path.is_file():
            raise ValueError(f"Sound file does not exist: {file_path}")
        audio = load_wav(file_path, self.sample_rate)
        base_name = file_path.stem or file_path.name
        with self._lock:
            name = base_name
            suffix = 2
            existing = {sound.name for sound in self._sounds}
            while name in existing:
                name = f"{base_name} ({suffix})"
                suffix += 1
            self._sounds.append(Sound(name, file_path, audio))
        return name

    def list_sounds(self) -> list[tuple[str, Path, bool, bool]]:
        with self._lock:
            return [
                (sound.name, sound.path, sound.playing, sound.looping)
                for sound in self._sounds
            ]

    def play(self, name: str) -> None:
        with self._lock:
            sound = self._get(name)
            sound.position = 0
            sound.playing = True

    def stop(self, name: str) -> None:
        with self._lock:
            sound = self._get(name)
            sound.playing = False
            sound.position = 0

    def set_looping(self, name: str, looping: bool) -> None:
        with self._lock:
            self._get(name).looping = looping

    def mix(self, frames: int) -> np.ndarray:
        if frames < 0:
            raise ValueError("Frame count cannot be negative")
        mixed = np.zeros((frames, self.channels), dtype=np.float32)
        with self._lock:
            for sound in self._sounds:
                if not sound.playing:
                    continue
                produced = 0
                while produced < frames and sound.playing:
                    remaining = len(sound.audio) - sound.position
                    if remaining == 0:
                        if sound.looping:
                            sound.position = 0
                            remaining = len(sound.audio)
                        else:
                            sound.playing = False
                            break
                    count = min(frames - produced, remaining)
                    mixed[produced : produced + count] += sound.audio[
                        sound.position : sound.position + count
                    ]
                    sound.position += count
                    produced += count
                    if sound.position == len(sound.audio) and sound.looping:
                        sound.position = 0
                    elif sound.position == len(sound.audio):
                        sound.playing = False
        return np.clip(mixed, -1.0, 1.0)

    def _get(self, name: str) -> Sound:
        for sound in self._sounds:
            if sound.name == name:
                return sound
        raise ValueError(f"Sound not found: {name}")
