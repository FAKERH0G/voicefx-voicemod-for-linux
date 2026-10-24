from __future__ import annotations

import argparse
import sys
import time

import sounddevice as sd

from .effects import EFFECTS, EffectProcessor


def _device_id(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("Device must be an integer ID from --list-devices") from None


def _list_devices() -> None:
    for index, device in enumerate(sd.query_devices()):
        print(
            f"{index}: {device['name']} "
            f"(inputs: {device['max_input_channels']}, "
            f"outputs: {device['max_output_channels']})"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Real-time voice effects for PipeWire")
    parser.add_argument("--input", type=_device_id, help="Input audio device ID")
    parser.add_argument("--output", type=_device_id, help="Output audio device ID")
    parser.add_argument("--effect", choices=EFFECTS, default="clean")
    parser.add_argument("--sample-rate", type=int, default=48000)
    parser.add_argument("--block-size", type=int, default=256)
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args()

    if args.list_devices:
        _list_devices()
        return 0

    processor = EffectProcessor(args.effect, args.sample_rate, channels=1)

    def callback(indata, outdata, frames, time_info, status) -> None:
        if status:
            print(f"Audio stream status: {status}", file=sys.stderr)
        outdata[:] = processor.process(indata)

    print(f"Starting {args.effect} effect. Press Ctrl+C to stop.", file=sys.stderr)
    with sd.Stream(
        samplerate=args.sample_rate,
        blocksize=args.block_size,
        device=(args.input, args.output),
        channels=1,
        dtype="float32",
        callback=callback,
    ):
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return 0


if __name__ == "__main__":
    raise SystemExit(main())
