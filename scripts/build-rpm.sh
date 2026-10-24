#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
command -v rpmbuild >/dev/null || {
    printf 'rpmbuild is required; install it with: sudo dnf install rpm-build\n' >&2
    exit 1
}

"$root/scripts/prepare-rpm-sources.sh"
mkdir -p "$root/rpmbuild/BUILD" "$root/rpmbuild/BUILDROOT" \
    "$root/rpmbuild/RPMS" "$root/rpmbuild/SPECS" "$root/rpmbuild/SRPMS"
rpmbuild -bb \
    --define "_topdir $root/rpmbuild" \
    "$root/packaging/voicemod-for-linux.spec"
printf 'RPM packages are available under %s/rpmbuild/RPMS\n' "$root"
