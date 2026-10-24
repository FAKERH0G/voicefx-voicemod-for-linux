# VoiceFX — Voicemod for Linux

<p align="center">
  <img src="assets/voicefx.svg" alt="VoiceFX app icon" width="220">
</p>

An unofficial, independent voice-effects prototype for Fedora Linux. It is not
a port of Voicemod, does not include Voicemod code or assets, and is not
affiliated with Voicemod or its owners.

VoiceFX provides a native GTK desktop app and a command-line processor for
real-time microphone effects. Switch between clean, robot, radio, and echo
effects while the mic is running, or play WAV clips from the built-in soundboard.
It is an independent project, not a port or feature-complete replacement for
Voicemod.

## Install the Fedora RPM

Install the Fedora 44 RPM from the
[latest release](https://github.com/FAKERH0G/voicemod-for-linux/releases/latest)
with DNF. DNF will install the app and resolve its dependencies:

```sh
sudo dnf install https://github.com/FAKERH0G/voicemod-for-linux/releases/download/v0.3.0/voicemod-for-linux-0.3.0-1.fc44.noarch.rpm
```

For a locally built RPM, install
`rpmbuild/RPMS/noarch/voicemod-for-linux-0.3.0-1.fc44.noarch.rpm` instead.

The RPM adds **VoiceFX** to the application grid and installs the
`voicemod-for-linux` command-line tool. It uses Fedora's packaged GTK, Python,
NumPy, and PortAudio bindings rather than bundling Python dependencies.

## Create a virtual microphone

VoiceFX processes audio from the selected microphone to the selected output.
To make the processed signal available as a microphone to Discord and other
apps, create PipeWire virtual devices for the current login:

```sh
pactl load-module module-null-sink sink_name=voicechanger_out sink_properties=device.description=VoiceChanger_Output
pactl load-module module-remap-source source_name=voicechanger_mic master=voicechanger_out.monitor source_properties=device.description=VoiceChanger_Microphone
```

Start **VoiceFX**, select your physical microphone and **VoiceChanger_Output**,
choose an effect, and click **Start voice effects**. In Discord or another
calling app, select **VoiceChanger_Microphone** as its input device.

The devices created with `pactl load-module` last until the audio service
restarts or their modules are unloaded. To remove them, run
`pactl unload-module MODULE_ID` with each module ID printed by `pactl`.

## Soundboard

Open **Soundboard**, choose **Add WAV sounds**, and select mono or stereo
uncompressed PCM WAV files (up to five minutes each). Start voice effects, then
use **Play**, **Stop**, and **Loop** on a sound. Clips are mixed with the
processed microphone and routed to the selected virtual output. Select
**VoiceChanger_Microphone** in your call app to hear both.

## Command line

List audio devices:

```sh
voicemod-for-linux --list-devices
```

Select devices by ID and start an effect:

```sh
voicemod-for-linux --input INPUT_ID --output OUTPUT_ID --effect robot
```

Replace the IDs with those reported on your machine. Effects are `clean`,
`robot`, `radio`, and `echo`. Press Ctrl+C to stop processing.

## Requirements and limitations

- Fedora Linux with PipeWire and its PulseAudio compatibility service.
- The soundboard currently supports uncompressed PCM WAV files. The app does
  not include an effect editor or advanced voice models. Its interface and icon
  are original project work, not Voicemod branding.

## Development

```sh
sudo dnf install gtk4 pipewire-pulseaudio python3-devel python3-gobject \
  python3-numpy python3-sounddevice rpm-build
PYTHONPATH=src python3 -m unittest discover -s tests
./scripts/build-rpm.sh
```

The RPM build script creates a Fedora-native RPM in
`rpmbuild/RPMS/noarch/`. Tagging a release `v*` also builds and attaches the RPM
to a GitHub release using the Fedora 44 CI workflow.

## License

MIT. The name Voicemod is used only to describe the intended use case; all
trademarks belong to their respective owners.
