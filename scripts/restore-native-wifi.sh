#!/bin/sh
set -eu
systemctl disable wifi-vendor.service || true
rm -f /storage/.config/modprobe.d/90-s905x2-rtl8822cs.conf
rmmod 88x2cs 2>/dev/null || true
modprobe rtw_8822cs
echo 'Native rtw88 restored. SDR104 DTB and HDMI fixes retained.'
