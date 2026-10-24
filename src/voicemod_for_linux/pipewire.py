from __future__ import annotations

import subprocess


class PipeWireRouting:
    def __init__(self) -> None:
        self._modules: list[str] = []
        self._monitor_module: str | None = None
        self._monitor_sink: str | None = None

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
        errors: list[str] = []
        for module_id in reversed(self._modules):
            try:
                self._run("unload-module", module_id)
            except RuntimeError as error:
                errors.append(str(error))
        self._modules.clear()
        self._monitor_module = None
        self._monitor_sink = None
        return errors
