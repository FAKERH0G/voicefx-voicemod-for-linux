from __future__ import annotations

import sys

import gi
import sounddevice as sd

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from .effects import EFFECTS, EffectProcessor


class VoiceFxWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="VoiceFX")
        self.set_default_size(560, 440)
        self._stream: sd.Stream | None = None
        self._inputs = self._devices("max_input_channels")
        self._outputs = self._devices("max_output_channels")

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        self.set_child(content)

        heading = Gtk.Label(label="VoiceFX")
        heading.add_css_class("title-1")
        heading.set_xalign(0)
        content.append(heading)

        description = Gtk.Label(
            label="Choose your microphone, a virtual output, and a voice effect."
        )
        description.set_xalign(0)
        description.set_wrap(True)
        description.add_css_class("dim-label")
        content.append(description)

        self._input_dropdown = self._device_dropdown(content, "Microphone", self._inputs)
        self._output_dropdown = self._device_dropdown(content, "Virtual output", self._outputs)
        self._effect_dropdown = Gtk.DropDown.new_from_strings(
            [effect.capitalize() for effect in EFFECTS]
        )
        self._add_row(content, "Effect", self._effect_dropdown)

        self._start_button = Gtk.Button(label="Start voice effects")
        self._start_button.add_css_class("suggested-action")
        self._start_button.connect("clicked", self._toggle_stream)
        content.append(self._start_button)

        self._status = Gtk.Label(label="Ready")
        self._status.set_xalign(0)
        self._status.set_wrap(True)
        self._status.add_css_class("dim-label")
        content.append(self._status)

        note = Gtk.Label(
            label="For calls, select VoiceChanger_Microphone as your microphone. "
            "Create the PipeWire virtual devices using the setup instructions in the README."
        )
        note.set_xalign(0)
        note.set_wrap(True)
        note.add_css_class("caption")
        note.add_css_class("dim-label")
        content.append(note)

        self.connect("close-request", self._on_close)

    @staticmethod
    def _devices(channel_field: str) -> list[tuple[int | None, str]]:
        devices: list[tuple[int | None, str]] = [(None, "System default")]
        devices.extend(
            (index, str(device["name"]))
            for index, device in enumerate(sd.query_devices())
            if device[channel_field] > 0
        )
        return devices

    @staticmethod
    def _add_row(parent: Gtk.Box, title: str, control: Gtk.Widget) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        label = Gtk.Label(label=title)
        label.set_xalign(0)
        label.add_css_class("heading")
        row.append(label)
        row.append(control)
        parent.append(row)

    def _device_dropdown(
        self, parent: Gtk.Box, title: str, devices: list[tuple[int | None, str]]
    ) -> Gtk.DropDown:
        dropdown = Gtk.DropDown.new_from_strings([name for _, name in devices])
        default_id = (
            sd.default.device[0 if title == "Microphone" else 1]
            if sd.default.device is not None
            else None
        )
        for index, (device_id, _) in enumerate(devices):
            if device_id == default_id:
                dropdown.set_selected(index)
                break
        self._add_row(parent, title, dropdown)
        return dropdown

    @staticmethod
    def _selected_device(
        dropdown: Gtk.DropDown, devices: list[tuple[int | None, str]]
    ) -> int | None:
        selected = dropdown.get_selected()
        if selected >= len(devices):
            raise ValueError("Select a valid audio device.")
        return devices[selected][0]

    def _toggle_stream(self, _button: Gtk.Button) -> None:
        if self._stream is not None:
            self._stop_stream()
            return

        input_device = self._selected_device(self._input_dropdown, self._inputs)
        output_device = self._selected_device(self._output_dropdown, self._outputs)
        effect = EFFECTS[self._effect_dropdown.get_selected()]
        processor = EffectProcessor(effect, sample_rate=48000, channels=1)

        def callback(indata, outdata, _frames, _time_info, status) -> None:
            if status:
                print(f"Audio stream status: {status}", file=sys.stderr)
            outdata[:] = processor.process(indata)

        stream = None
        try:
            stream = sd.Stream(
                samplerate=48000,
                blocksize=256,
                device=(input_device, output_device),
                channels=1,
                dtype="float32",
                callback=callback,
            )
            stream.start()
        except (sd.PortAudioError, RuntimeError, ValueError) as error:
            if stream is not None:
                stream.close()
            self._status.set_text(f"Could not start audio: {error}")
            return

        self._stream = stream
        self._start_button.set_label("Stop voice effects")
        self._status.set_text(f"Running {effect} effect.")

    def _stop_stream(self) -> None:
        if self._stream is None:
            return
        self._stream.stop()
        self._stream.close()
        self._stream = None
        self._start_button.set_label("Start voice effects")
        self._status.set_text("Stopped")

    def _on_close(self, _window: Gtk.ApplicationWindow) -> bool:
        self._stop_stream()
        return False


def main() -> int:
    application = Gtk.Application(application_id="io.github.fakerh0g.VoiceFX")
    application.connect("activate", lambda app: VoiceFxWindow(app).present())
    return application.run(None)
