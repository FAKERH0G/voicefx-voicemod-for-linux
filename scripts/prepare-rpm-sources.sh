#!/usr/bin/env bash
set -euo pipefail

root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
version="$(sed -n 's/^Version: *//p' "$root/packaging/voicemod-for-linux.spec" | head -n 1)"
if [[ ! "$version" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    printf 'Could not read a valid RPM version from the spec file\n' >&2
    exit 1
fi

out="${1:-$root/rpmbuild/SOURCES}"
mkdir -p "$out"
tar -czf "$out/voicemod-for-linux-$version.tar.gz" \
    --exclude=.git \
    --exclude=.venv \
    --exclude=__pycache__ \
    --exclude='*.egg-info' \
    --exclude=build \
    --exclude=rpmbuild \
    -C "$(dirname "$root")" "$(basename "$root")"
printf 'RPM source archive prepared in %s\n' "$out"
