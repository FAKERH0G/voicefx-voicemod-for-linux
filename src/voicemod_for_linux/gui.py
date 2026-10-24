from __future__ import annotations

import sys
from pathlib import Path

import gi
import numpy as np
import sounddevice as sd

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib, Gtk

from .effects import EFFECTS, EffectProcessor
from .pipewire import PipeWireRouting
from .soundboard import Soundboard


SAMPLE_RATE = 48000
BLOCK_SIZE = 256


class VoiceFxWindow(Gtk.ApplicationWindow):
    def __init__(self, application: Gtk.Application) -> None:
        super().__init__(application=application, title="VoiceFX")
        self.set_default_size(960, 680)
        self._stream: sd.Stream | None = None
        self._processor: EffectProcessor | None = None
        self._soundboard = Soundboard(sample_rate=SAMPLE_RATE)
        self._routing = PipeWireRouting()
        self._routing_error: str | None = None
        try:
            self._routing.ensure_virtual_microphone()
        except RuntimeError as error:
            self._routing_error = str(error)
        self._inputs = self._devices("max_input_channels")
        self._outputs = self._devices("max_output_channels")
        self._effect_buttons: dict[str, Gtk.ToggleButton] = {}
        self._sound_rows: Gtk.ListBox | None = None
        self._sound_states: tuple[tuple[str, bool, bool], ...] = ()

        shell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        shell.add_css_class("voicefx-window")
        self.set_child(shell)

        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar.set_size_request(210, -1)
        sidebar.set_margin_top(24)
        sidebar.set_margin_bottom(20)
        sidebar.set_margin_start(16)
        sidebar.set_margin_end(16)
        sidebar.add_css_class("voicefx-sidebar")
        shell.append(sidebar)

        brand = Gtk.Label(label="VoiceFX")
        brand.add_css_class("title-1")
        brand.set_xalign(0)
        sidebar.append(brand)
        tagline = Gtk.Label(label="Live voice studio")
        tagline.add_css_class("dim-label")
        tagline.set_xalign(0)
        sidebar.append(tagline)

        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar.append(separator)

        voice_page_button = Gtk.ToggleButton(label="Voice Changer")
        soundboard_page_button = Gtk.ToggleButton(label="Soundboard")
        soundboard_page_button.set_group(voice_page_button)
        voice_page_button.add_css_class("voicefx-nav")
        soundboard_page_button.add_css_class("voicefx-nav")
        voice_page_button.set_active(True)
        sidebar.append(voice_page_button)
        sidebar.append(soundboard_page_button)

        sidebar_spacer = Gtk.Box()
        sidebar_spacer.set_vexpand(True)
        sidebar.append(sidebar_spacer)
        sidebar_note = Gtk.Label(label="Fedora · PipeWire")
        sidebar_note.set_xalign(0)
        sidebar_note.add_css_class("dim-label")
        sidebar.append(sidebar_note)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main.set_hexpand(True)
        shell.append(main)

        header = Gtk.HeaderBar()
        header.set_title_widget(Gtk.Label(label="VoiceFX"))
        self.set_titlebar(header)

        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        stack.set_hexpand(True)
        stack.set_vexpand(True)
        main.append(stack)
        stack.add_named(self._build_voice_page(), "voice")
        stack.add_named(self._build_soundboard_page(), "soundboard")
        voice_page_button.connect("toggled", self._show_page, stack, "voice")
        soundboard_page_button.connect("toggled", self._show_page, stack, "soundboard")
        GLib.timeout_add(300, self._update_soundboard_rows)
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
    def _show_page(
        button: Gtk.ToggleButton, stack: Gtk.Stack, page: str
    ) -> None:
        if button.get_active():
            stack.set_visible_child_name(page)

    @staticmethod
    def _heading(title: str, description: str) -> Gtk.Box:
        block = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        heading = Gtk.Label(label=title)
        heading.add_css_class("title-1")
        heading.set_xalign(0)
        block.append(heading)
        subtitle = Gtk.Label(label=description)
        subtitle.set_xalign(0)
        subtitle.set_wrap(True)
        subtitle.add_css_class("dim-label")
        block.append(subtitle)
        return block

    def _build_voice_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_margin_top(28)
        page.set_margin_bottom(28)
        page.set_margin_start(32)
        page.set_margin_end(32)
        page.append(
            self._heading(
                "Voice Changer",
                "Choose an effect and route your live microphone to your calling apps.",
            )
        )

        devices = Gtk.Grid(column_spacing=16, row_spacing=8)
        self._input_dropdown = self._device_dropdown(self._inputs, default_index=0)
        self._output_dropdown = self._device_dropdown(self._outputs, default_index=1)
        self._attach_labeled(devices, "Microphone", self._input_dropdown, 0)
        self._attach_labeled(devices, "Virtual output", self._output_dropdown, 1)
        page.append(self._card(devices))

        effects_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        effects_title = Gtk.Label(label="Voice effects")
        effects_title.add_css_class("title-2")
        effects_title.set_xalign(0)
        effects_box.append(effects_title)
        effects_subtitle = Gtk.Label(label="Switch effects live while your mic is running.")
        effects_subtitle.set_xalign(0)
        effects_subtitle.add_css_class("dim-label")
        effects_box.append(effects_subtitle)
        effect_grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        first: Gtk.ToggleButton | None = None
        for index, effect in enumerate(EFFECTS):
            button = Gtk.ToggleButton(label=effect.capitalize())
            if first is None:
                first = button
                button.set_active(True)
            else:
                button.set_group(first)
            button.set_hexpand(True)
            button.set_size_request(-1, 52)
            button.add_css_class("voicefx-effect")
            button.connect("toggled", self._select_effect, effect)
            effect_grid.attach(button, index % 2, index // 2, 1, 1)
            self._effect_buttons[effect] = button
        effects_box.append(effect_grid)
        page.append(self._card(effects_box))

        self._start_button = Gtk.Button(label="Start voice effects")
        self._start_button.add_css_class("suggested-action")
        self._start_button.set_size_request(-1, 44)
        self._start_button.connect("clicked", self._toggle_stream)
        page.append(self._start_button)

        self._monitor_toggle = Gtk.CheckButton(label="Hear processed voice in my headphones")
        self._monitor_toggle.set_active(True)
        self._monitor_toggle.connect("toggled", self._toggle_monitor)
        page.append(self._monitor_toggle)
        monitor_note = Gtk.Label(
            label="Headphones recommended while monitoring to prevent microphone feedback."
        )
        monitor_note.set_xalign(0)
        monitor_note.add_css_class("caption")
        monitor_note.add_css_class("dim-label")
        page.append(monitor_note)

        self._status = Gtk.Label(
            label=self._routing_error
            or "Ready · processed audio routes to VoiceFX Microphone"
        )
        self._status.set_xalign(0)
        self._status.set_wrap(True)
        self._status.add_css_class("dim-label")
        page.append(self._status)
        return page

    def _build_soundboard_page(self) -> Gtk.Widget:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_top(28)
        page.set_margin_bottom(28)
        page.set_margin_start(32)
        page.set_margin_end(32)
        page.append(
            self._heading(
                "Soundboard",
                "Load WAV clips and play them into the same virtual microphone as your voice.",
            )
        )

        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        add_button = Gtk.Button(label="Add WAV sounds")
        add_button.add_css_class("suggested-action")
        add_button.connect("clicked", self._choose_sounds)
        toolbar.append(add_button)
        self._soundboard_status = Gtk.Label(
            label="Supports mono or stereo PCM WAV files."
        )
        self._soundboard_status.set_xalign(0)
        self._soundboard_status.add_css_class("dim-label")
        toolbar.append(self._soundboard_status)
        page.append(toolbar)

        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._sound_rows = Gtk.ListBox()
        self._sound_rows.set_selection_mode(Gtk.SelectionMode.NONE)
        scroller.set_child(self._sound_rows)
        page.append(scroller)
        return page

    @staticmethod
    def _card(child: Gtk.Widget) -> Gtk.Frame:
        frame = Gtk.Frame()
        frame.add_css_class("voicefx-card")
        child.set_margin_top(16)
        child.set_margin_bottom(16)
        child.set_margin_start(16)
        child.set_margin_end(16)
        frame.set_child(child)
        return frame

    def _device_dropdown(
        self,
        devices: list[tuple[int | None, str]],
        default_index: int,
    ) -> Gtk.DropDown:
        dropdown = Gtk.DropDown.new_from_strings([name for _, name in devices])
        if default_index == 1:
            for index, (_, name) in enumerate(devices):
                if "voicefx_output" in name.lower() or "voicefx output" in name.lower():
                    dropdown.set_selected(index)
                    break
        if sd.default.device is not None:
            default_id = sd.default.device[default_index]
            for index, (device_id, _) in enumerate(devices):
                if default_index == 1 and dropdown.get_selected() != 0:
                    break
                if device_id == default_id:
                    dropdown.set_selected(index)
                    break
        dropdown.set_hexpand(True)
        return dropdown

    @staticmethod
    def _attach_labeled(
        grid: Gtk.Grid, label_text: str, control: Gtk.Widget, row: int
    ) -> None:
        label = Gtk.Label(label=label_text)
        label.set_xalign(0)
        grid.attach(label, 0, row, 1, 1)
        grid.attach(control, 1, row, 1, 1)

    def _select_effect(self, button: Gtk.ToggleButton, effect: str) -> None:
        if not button.get_active():
            return
        if self._processor is not None:
            self._processor.set_effect(effect)
            self._status.set_text(f"Running {effect} effect.")

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

        try:
            input_device = self._selected_device(self._input_dropdown, self._inputs)
            output_device = self._selected_device(self._output_dropdown, self._outputs)
            input_settings = sd.query_devices(input_device, "input")
            output_settings = sd.query_devices(output_device, "output")
            if input_settings["max_input_channels"] < 1:
                raise ValueError("The selected microphone does not provide an input channel.")
            if output_settings["max_output_channels"] < 1:
                raise ValueError("The selected output device does not accept audio.")
            if output_device is None or "voicefx" not in str(output_settings["name"]).lower():
                raise ValueError(
                    "Select the VoiceFX_Output virtual device so your calling app can receive the processed mic."
                )
            output_channels = min(2, int(output_settings["max_output_channels"]))
            effect = next(
                (
                    name
                    for name, button in self._effect_buttons.items()
                    if button.get_active()
                ),
                "clean",
            )
            processor = EffectProcessor(effect, sample_rate=SAMPLE_RATE, channels=1)

            def callback(indata, outdata, _frames, _time_info, status) -> None:
                if status:
                    print(f"Audio stream status: {status}", file=sys.stderr)
                voice = processor.process(indata)
                cue = self._soundboard.mix(len(indata))
                mixed = np.clip(voice + cue, -1.0, 1.0)
                outdata[:] = mixed if outdata.shape[1] == 1 else mixed.repeat(
                    outdata.shape[1], axis=1
                )

            stream = sd.Stream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                device=(input_device, output_device),
                channels=(1, output_channels),
                dtype="float32",
                callback=callback,
            )
            stream.start()
        except (sd.PortAudioError, RuntimeError, ValueError) as error:
            self._status.set_text(f"Could not start audio: {error}")
            return

        self._processor = processor
        self._stream = stream
        self._start_button.set_label("Stop voice effects")
        monitor_error = None
        if self._monitor_toggle.get_active():
            try:
                self._routing.start_monitor()
            except RuntimeError as error:
                monitor_error = str(error)
                self._monitor_toggle.set_active(False)
        self._status.set_text(f"Running {effect} effect · select VoiceFX_Microphone in your call app.")
        if monitor_error:
            self._status.set_text(f"Voice changer is running; headphone monitoring failed: {monitor_error}")

    def _toggle_monitor(self, button: Gtk.CheckButton) -> None:
        if self._stream is None:
            return
        try:
            if button.get_active():
                self._routing.start_monitor()
                self._status.set_text("Headphone monitoring is on. Use headphones to avoid feedback.")
            else:
                self._routing.stop_monitor()
                self._status.set_text("Headphone monitoring is off.")
        except RuntimeError as error:
            button.set_active(False)
            self._status.set_text(f"Could not change headphone monitoring: {error}")

    def _stop_stream(self) -> None:
        stream = self._stream
        if stream is not None:
            self._stream = None
            self._processor = None
            try:
                stream.stop()
            finally:
                stream.close()
            self._start_button.set_label("Start voice effects")
            self._status.set_text("Stopped")

    def _choose_sounds(self, _button: Gtk.Button) -> None:
        chooser = Gtk.FileChooserNative(
            title="Add soundboard WAV files",
            parent=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="_Add",
            cancel_label="_Cancel",
        )
        chooser.set_select_multiple(True)
        file_filter = Gtk.FileFilter()
        file_filter.set_name("WAV audio")
        file_filter.add_mime_type("audio/wav")
        file_filter.add_pattern("*.wav")
        file_filter.add_pattern("*.WAV")
        chooser.add_filter(file_filter)
        chooser.connect("response", self._on_files_chosen)
        chooser.show()

    def _on_files_chosen(self, chooser: Gtk.FileChooserNative, response: int) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            files = chooser.get_files()
            errors: list[str] = []
            for index in range(files.get_n_items()):
                file = files.get_item(index)
                path = file.get_path()
                if path is None:
                    errors.append("Could not read a local sound file.")
                    continue
                try:
                    self._soundboard.add_file(path)
                except ValueError as error:
                    errors.append(f"{Path(path).name}: {error}")
            self._refresh_sound_rows()
            if errors:
                self._soundboard_status.set_text(" · ".join(errors))
            elif files.get_n_items():
                self._soundboard_status.set_text(
                    f"Loaded {files.get_n_items()} WAV sound(s). Start voice effects to play them into calls."
                )
        chooser.destroy()

    def _refresh_sound_rows(self) -> None:
        if self._sound_rows is None:
            return
        sounds = self._soundboard.list_sounds()
        self._sound_states = tuple(
            (name, playing, looping) for name, _, playing, looping in sounds
        )
        child = self._sound_rows.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self._sound_rows.remove(child)
            child = next_child
        for name, path, playing, looping in sounds:
            row = Gtk.ListBoxRow()
            content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            content.set_margin_top(8)
            content.set_margin_bottom(8)
            content.set_margin_start(10)
            content.set_margin_end(10)
            label = Gtk.Label(label=name)
            label.set_tooltip_text(str(path))
            label.set_xalign(0)
            label.set_hexpand(True)
            content.append(label)
            play = Gtk.Button(label="Play")
            play.connect("clicked", self._play_sound, name)
            content.append(play)
            stop = Gtk.Button(label="Stop")
            stop.connect("clicked", self._stop_sound, name)
            content.append(stop)
            loop = Gtk.CheckButton(label="Loop")
            loop.set_active(looping)
            loop.connect("toggled", self._set_sound_loop, name)
            content.append(loop)
            if playing:
                label.set_text(f"{name} · playing")
            row.set_child(content)
            self._sound_rows.append(row)

    def _update_soundboard_rows(self) -> bool:
        sounds = self._soundboard.list_sounds()
        states = tuple((name, playing, looping) for name, _, playing, looping in sounds)
        if states != self._sound_states:
            self._refresh_sound_rows()
        return True

    def _play_sound(self, _button: Gtk.Button, name: str) -> None:
        try:
            self._soundboard.play(name)
            self._refresh_sound_rows()
            if self._stream is None:
                self._soundboard_status.set_text(
                    "Sound loaded. Start voice effects to route playback to the virtual microphone."
                )
        except ValueError as error:
            self._soundboard_status.set_text(str(error))

    def _stop_sound(self, _button: Gtk.Button, name: str) -> None:
        self._soundboard.stop(name)
        self._refresh_sound_rows()

    def _set_sound_loop(self, button: Gtk.CheckButton, name: str) -> None:
        self._soundboard.set_looping(name, button.get_active())

    def _on_close(self, _window: Gtk.ApplicationWindow) -> bool:
        self._stop_stream()
        errors = self._routing.close()
        if errors:
            print(
                f"Could not clean up PipeWire routing: {'; '.join(errors)}",
                file=sys.stderr,
            )
        return False


def main() -> int:
    def activate(application: Gtk.Application) -> None:
        provider = Gtk.CssProvider()
        provider.load_from_data(
            b"""
            .voicefx-window {
                background: #050a14;
                color: #eff6ff;
            }
            .voicefx-sidebar {
                background: #080f1e;
                border-right: 1px solid #123264;
            }
            .voicefx-card {
                background: #0b1730;
                border: 1px solid #164a91;
                border-radius: 16px;
            }
            .voicefx-nav {
                min-height: 40px;
                padding: 8px 12px;
                border-radius: 10px;
                background: transparent;
            }
            .voicefx-nav:checked {
                background: #123d78;
                color: #c4e2ff;
            }
            .voicefx-effect {
                min-height: 64px;
                border-radius: 12px;
                background: #102448;
            }
            .voicefx-effect:checked {
                background: #0878e8;
                color: white;
            }
            """
        )
        display = Gdk.Display.get_default()
        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        VoiceFxWindow(application).present()

    application = Gtk.Application(application_id="io.github.fakerh0g.VoiceFX")
    application.connect("activate", activate)
    return application.run(None)
