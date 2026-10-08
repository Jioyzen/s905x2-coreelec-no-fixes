#!/bin/sh
# CoreELEC NO RTL8822CS override; normal ABI checks, with native fallback.
set -u
MODULE=/storage/.config/wifi-drivers/88x2cs-5.15.196.ko
SDIO_DEV=
for dev in /sys/bus/sdio/devices/*; do
    if grep -qs '^SDIO_ID=024C:C822$' "$dev/uevent"; then SDIO_DEV=$dev; break; fi
done
if [ -z "$SDIO_DEV" ]; then
    echo 'RTL8822CS not found; native driver retained'
    modprobe rtw_8822cs 2>/dev/null || true
    exit 0
fi
if [ "$(basename "$(readlink "$SDIO_DEV/driver" 2>/dev/null)")" = rtl88x2cs ]; then
    echo 'RTL8822CS vendor driver already bound'
    exit 0
fi
modprobe -r rtw_8822cs 2>/dev/null || true
modprobe cfg80211
if [ "$(uname -r)" = 5.15.196 ] && [ -r "$MODULE" ]; then
    if insmod "$MODULE" rtw_power_mgnt=0 rtw_ips_mode=0 rtw_en_napi=1 rtw_en_gro=1; then
        if [ "$(basename "$(readlink "$SDIO_DEV/driver" 2>/dev/null)")" = rtl88x2cs ]; then
            echo 'RTL8822CS vendor driver active: NAPI/GRO enabled, power saving off'
            exit 0
        fi
        rmmod 88x2cs 2>/dev/null || true
    fi
fi
echo 'Vendor driver unavailable or rejected; falling back to native rtw88'
modprobe rtw_8822cs
