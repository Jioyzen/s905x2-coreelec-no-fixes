#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Sourced by the unchanged CoreELEC initramfs; retain its normal mount operation.
if mount_part "$disk" "/storage" "rw,noatime"; then
    # A failed seed must not prevent normal boot or native wireless loading.
    if ! sh /flash/s905x2-fixes/install-storage.sh; then
        echo 'S905X2 fixes: storage setup failed; check payload and retry next boot' >&2
    fi
fi
