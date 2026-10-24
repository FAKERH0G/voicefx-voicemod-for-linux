# Voicemod for Linux

![VoiceFX icon](assets/voicefx.svg)

An unofficial, independent voice-effects prototype for Fedora Linux. It is not
a port of Voicemod, does not include Voicemod code or assets, and is not
affiliated with Voicemod or its owners.

The prototype processes a microphone in real time and sends the result to a
PipeWire virtual microphone. It currently includes clean, robot, radio, and
echo effects. It is a small command-line starting point, not a feature-complete
replacement for Voicemod.

## Fedora setup

Install the system audio and Python tools:

```sh
sudo dnf install pipewire pipewire-pulseaudio pipewire-utils portaudio python3 python3-pip
```

Create a virtual output and microphone for this login session:

```sh
pactl load-module module-null-sink sink_name=voicechanger_out sink_properties=device.description=VoiceChanger_Output
pactl load-module module-remap-source source_name=voicechanger_mic master=voicechanger_out.monitor source_properties=device.description=VoiceChanger_Microphone
```

Install the app in a virtual environment:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install .
```

List audio devices and note the device IDs:

```sh
voicemod-for-linux --list-devices
```

Run the effect with your physical microphone as input and the virtual output as
output. Replace the IDs with the ones shown on your machine:

```sh
voicemod-for-linux --input INPUT_ID --output OUTPUT_ID --effect robot
```

Replace `INPUT_ID` and `OUTPUT_ID` with the numeric IDs reported on your
machine; select the `VoiceChanger_Output` device for output.

In Discord, a game, or another calling app, select **VoiceChanger_Microphone**
as the microphone. Use `--effect clean`, `robot`, `radio`, or `echo` to choose
an effect. Press Ctrl+C to stop processing.

The repository includes an original VoiceFX icon at `assets/voicefx.svg` and a
desktop launcher at `desktop/voicefx.desktop`. To install them for your user:

```sh
install -Dm644 assets/voicefx.svg ~/.local/share/icons/hicolor/scalable/apps/voicefx.svg
install -Dm644 desktop/voicefx.desktop ~/.local/share/applications/voicefx.desktop
```

The launcher uses the default input/output devices; use the terminal command
above when you need to select device IDs explicitly.

The virtual devices created with `pactl load-module` last until the audio
service restarts or the modules are unloaded. You can remove them with
`pactl unload-module MODULE_ID`, using the IDs printed by `pactl`.

## Requirements and limitations

- Fedora with PipeWire and its PulseAudio compatibility service.
- Python, NumPy, and PortAudio (provided by the Python dependencies and Fedora
  packages above).
- The icon is original project artwork, not Voicemod branding. This prototype
  has no graphical interface, soundboard, effect editor, or
  automatic device discovery. Audio routing and device IDs are configured by
  the user.

## Development

```sh
python -m pip install -e '.[test]'
python -m unittest discover -s tests
```

## License

MIT. The name Voicemod is used only to describe the intended use case; all
trademarks belong to their respective owners.
