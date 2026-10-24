from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class RecordingStream:
    index: int
    name: str
    source: str


class PipeWireRouting:
    def __init__(self) -> None:
        self._modules: list[str] = []
        self._monitor_module: str | None = None
        self._monitor_sink: str | None = None
        self._previous_default_source: str | None = None
        self._routed_streams: dict[int, str] = {}

    @staticmethod
    def _run(*args: str) -> str:
        try:
            result = subprocess.run(
                ["pactl", *args],
                check=True,
                capture_output=True,
                text=True,
                timeout=8,
            )
        except FileNotFoundError as error:
            raise RuntimeError("pactl is missing; install pipewire-pulseaudio.") from error
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("PipeWire did not respond to pactl in time.") from error
        except subprocess.CalledProcessError as error:
            detail = error.stderr.strip() or error.stdout.strip() or str(error)
            raise RuntimeError(f"PipeWire command failed: {detail}") from error
        return result.stdout.strip()

    @classmethod
    def _names(cls, kind: str) -> set[str]:
        result = cls._run("list", "short", kind)
        return {line.split("\t", 2)[1] for line in result.splitlines() if "\t" in line}

    @classmethod
    def _json_list(cls, kind: str) -> list[dict]:
        try:
            data = json.loads(cls._run("-f", "json", "list", kind))
        except json.JSONDecodeError as error:
            raise RuntimeError(f"Could not parse PipeWire {kind} list: {error}") from error
        if not isinstance(data, list):
            raise RuntimeError(f"PipeWire returned an invalid {kind} list.")
        return [item for item in data if isinstance(item, dict)]

    def ensure_virtual_microphone(self) -> None:
        sinks = self._names("sinks")
        if "voicefx_output" not in sinks:
            module_id = self._run(
                "load-module",
                "module-null-sink",
                "sink_name=voicefx_output",
                "sink_properties=device.description=VoiceFX_Output",
            )
            self._modules.append(module_id)
        sources = self._names("sources")
        if "voicefx_mic" not in sources:
            module_id = self._run(
                "load-module",
                "module-remap-source",
                "source_name=voicefx_mic",
                "master=voicefx_output.monitor",
                "source_properties=device.description=VoiceFX_Microphone",
            )
            self._modules.append(module_id)

    def set_default_source(self) -> None:
        if self._previous_default_source is None:
            self._previous_default_source = self._run("get-default-source")
        self._run("set-default-source", "voicefx_mic")

    def restore_default_source(self) -> None:
        previous = self._previous_default_source
        if previous is None:
            return
        current = self._run("get-default-source")
        if current == "voicefx_mic":
            self._run("set-default-source", previous)
        self._previous_default_source = None

    def recording_streams(self) -> list[RecordingStream]:
        sources = self._json_list("sources")
        source_names = {
            int(source["index"]): str(source["name"])
            for source in sources
            if "index" in source and "name" in source
        }
        streams: list[RecordingStream] = []
        for output in self._json_list("source-outputs"):
            properties = output.get("properties")
            if not isinstance(properties, dict):
                continue
            try:
                index = int(output["index"])
                source_index = int(output["source"])
            except (KeyError, TypeError, ValueError):
                continue
            source = source_names.get(source_index)
            if source is None:
                continue
            name = str(
                properties.get("application.name")
                or properties.get("application.process.binary")
                or properties.get("media.name")
                or f"Recording app {index}"
            )
            details = " ".join(
                str(properties.get(key, ""))
                for key in (
                    "application.name",
                    "application.process.binary",
                    "application.process.id",
                    "media.name",
                    "node.name",
                )
            ).lower()
            if "voicefx" in details:
                continue
            streams.append(RecordingStream(index, name, source))
        return streams

    def route_recording_stream(self, index: int) -> None:
        streams = {stream.index: stream for stream in self.recording_streams()}
        stream = streams.get(index)
        if stream is None:
            raise RuntimeError("That app's microphone stream is no longer active.")
        if stream.source == "voicefx_mic":
            return
        newly_routed = index not in self._routed_streams
        if index not in self._routed_streams:
            self._routed_streams[index] = stream.source
        try:
            self._run("move-source-output", str(index), "voicefx_mic")
        except RuntimeError:
            if newly_routed:
                self._routed_streams.pop(index, None)
            raise

    def restore_recording_stream(self, index: int) -> None:
        source = self._routed_streams.get(index)
        if source is None:
            return
        active_streams = {stream.index: stream for stream in self.recording_streams()}
        stream = active_streams.get(index)
        if stream is not None and stream.source == "voicefx_mic":
            self._run("move-source-output", str(index), source)
        self._routed_streams.pop(index, None)

    def restore_recording_streams(self) -> list[str]:
        errors: list[str] = []
        for index in list(self._routed_streams):
            try:
                self.restore_recording_stream(index)
            except RuntimeError as error:
                errors.append(str(error))
        return errors

    def is_stream_routed(self, index: int) -> bool:
        return index in self._routed_streams

    def start_monitor(self) -> None:
        if self._monitor_module is not None:
            return
        self.ensure_virtual_microphone()
        sink = self._run("get-default-sink")
        if not sink or sink == "voicefx_output":
            raise RuntimeError("Set your headphones as the system's default output first.")
        module_id = self._run(
            "load-module",
            "module-loopback",
            "source=voicefx_output.monitor",
            f"sink={sink}",
            "latency_msec=80",
        )
        self._monitor_sink = sink
        self._monitor_module = module_id
        self._modules.append(module_id)

    def stop_monitor(self) -> None:
        if self._monitor_module is None:
            return
        module_id = self._monitor_module
        self._run("unload-module", module_id)
        self._monitor_module = None
        self._monitor_sink = None
        self._modules.remove(module_id)

    def close(self) -> list[str]:
        errors = self.restore_recording_streams()
        try:
            self.restore_default_source()
        except RuntimeError as error:
            errors.append(str(error))
        for module_id in reversed(self._modules):
            try:
                self._run("unload-module", module_id)
            except RuntimeError as error:
                errors.append(str(error))
        self._modules.clear()
        self._monitor_module = None
        self._monitor_sink = None
        return errors
