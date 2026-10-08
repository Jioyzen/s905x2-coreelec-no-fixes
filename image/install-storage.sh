#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# The optional paths also allow offline verification without touching /storage.
set -eu
PAYLOAD_DIR=${1:-/flash/s905x2-fixes}
STORAGE_DIR=${2:-/storage}
MARKER="$STORAGE_DIR/.s905x2-no-fixes-v1-installed"

# CoreELEC's stock resize reformats storage and rejects pre-existing .config.
# Do nothing until its automatic resize/reboot has completed.
if [ -e "$STORAGE_DIR/.please_resize_me" ] || [ -e "$MARKER" ] ||
   [ -e "$STORAGE_DIR/.s905x2-no-fixes-disabled" ]; then
    exit 0
fi

cd "$PAYLOAD_DIR"
# The stock initramfs has md5sum but no sha256sum/chmod/ln applets.
# SHA256 is supplied for the complete image and payload for external checks.
md5sum -c payload.md5
STAGING_DIR="$STORAGE_DIR/.s905x2-no-fixes-staging"
mkdir -p "$STAGING_DIR"
trap 'rm -rf "$STAGING_DIR"' EXIT
tar -xzf storage.tar.gz -C "$STAGING_DIR"
(cd "$STAGING_DIR" && md5sum -c "$PAYLOAD_DIR/storage-files.md5")

mkdir -p "$STORAGE_DIR/.config/wifi-drivers" \
    "$STORAGE_DIR/.config/modprobe.d" \
    "$STORAGE_DIR/.config/system.d/multi-user.target.wants"
# Preserve the executable bits and the enable symlink stored in the archive.
cp -a "$STAGING_DIR/.config/." "$STORAGE_DIR/.config/"
echo 's905x2-no-fixes-v1' > "$MARKER"
sync
echo 'S905X2 fixes: wireless driver installed and service enabled before systemd startup'
