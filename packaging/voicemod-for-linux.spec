Name:           voicemod-for-linux
Version:        0.7.0
Release:        1%{?dist}
Summary:        Independent real-time voice effects for Fedora
License:        MIT
URL:            https://github.com/FAKERH0G/voicemod-for-linux
Source0:        %{name}-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  python3-devel
Requires:       python3
Requires:       python3-gobject
Requires:       python3-numpy
Requires:       python3-sounddevice
Requires:       portaudio
Requires:       libayatana-appindicator-gtk3
Requires:       gtk4
Requires:       gstreamer1
Requires:       gstreamer1-plugins-good
Requires:       gstreamer1-plugins-bad-free
Requires:       pipewire-pulseaudio

%description
VoiceFX is an unofficial, independent voice changer and audio soundboard for
Fedora. It provides a GTK desktop interface and a command-line audio processor
that can route effects to a PipeWire virtual microphone. It is not affiliated
with Voicemod or its owners.

%prep
%autosetup -n %{name}

%build

%install
install -d %{buildroot}%{python3_sitelib}/voicemod_for_linux
install -pm0644 src/voicemod_for_linux/__init__.py \
    %{buildroot}%{python3_sitelib}/voicemod_for_linux/__init__.py
install -pm0644 src/voicemod_for_linux/cli.py \
    %{buildroot}%{python3_sitelib}/voicemod_for_linux/cli.py
install -pm0644 src/voicemod_for_linux/effects.py \
    %{buildroot}%{python3_sitelib}/voicemod_for_linux/effects.py
install -pm0644 src/voicemod_for_linux/gui.py \
    %{buildroot}%{python3_sitelib}/voicemod_for_linux/gui.py
install -pm0644 src/voicemod_for_linux/pipewire.py \
    %{buildroot}%{python3_sitelib}/voicemod_for_linux/pipewire.py
install -pm0644 src/voicemod_for_linux/soundboard.py \
    %{buildroot}%{python3_sitelib}/voicemod_for_linux/soundboard.py
install -pm0644 src/voicemod_for_linux/tray.py \
    %{buildroot}%{python3_sitelib}/voicemod_for_linux/tray.py
install -Dpm0755 packaging/voicefx-app %{buildroot}%{_bindir}/voicefx-app
install -Dpm0755 packaging/voicemod-for-linux \
    %{buildroot}%{_bindir}/voicemod-for-linux
install -Dpm0644 desktop/voicefx.desktop \
    %{buildroot}%{_datadir}/applications/voicefx.desktop
install -Dpm0644 assets/voicefx.svg \
    %{buildroot}%{_datadir}/icons/hicolor/scalable/apps/voicefx.svg

%files
%license LICENSE
%doc README.md
%{_bindir}/voicefx-app
%{_bindir}/voicemod-for-linux
%{python3_sitelib}/voicemod_for_linux/
%{_datadir}/applications/voicefx.desktop
%{_datadir}/icons/hicolor/scalable/apps/voicefx.svg

%changelog
* Fri Oct 23 2026 FAKERH0G <236636419+FAKERH0G@users.noreply.github.com> - 0.7.0-1
- Add tray menu and avoid routing virtual monitor devices as microphone input
* Fri Oct 23 2026 FAKERH0G <236636419+FAKERH0G@users.noreply.github.com> - 0.6.0-1
- Fix microphone and output backend selection and allow background operation
* Fri Oct 23 2026 FAKERH0G <236636419+FAKERH0G@users.noreply.github.com> - 0.5.0-1
- Route active call-app mic streams and decode common audio formats
