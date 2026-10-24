Name:           voicemod-for-linux
Version:        0.2.0
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
Requires:       gtk4
Requires:       pipewire-pulseaudio

%description
VoiceFX is an unofficial, independent voice-effects application for Fedora.
It provides a GTK desktop interface and a command-line audio processor that
can route effects to a PipeWire virtual microphone. It is not affiliated with
Voicemod or its owners.

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
* Fri Oct 23 2026 FAKERH0G <236636419+FAKERH0G@users.noreply.github.com> - 0.2.0-1
- Add GTK desktop app and Fedora RPM packaging
