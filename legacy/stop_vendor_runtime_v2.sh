#!/bin/sh
# Runtime-only quiescence. Do not unload the vendor Wi-Fi module: its netdev teardown leaks a reference.
set -u
: > /tmp/wx-ramboot/stopped-pids
for name in nmmgr netifd udhcpc network_refresh.sh phy_reset.sh; do
 for pid in $(pidof "$name" 2>/dev/null); do
  kill -STOP "$pid" && echo "$pid" >> /tmp/wx-ramboot/stopped-pids
 done
done
/etc/init.d/fwdd stop
killall wapp wifi_notify 2>/dev/null || true
for d in /sys/class/net/*; do
 name=${d##*/}
 case "$name" in ra[0-9]*|rai[0-9]*|rae[0-9]*|rax[0-9]*|apcli[0-9]*|apclii[0-9]*)
  echo "Closing wireless interface $name"
  ifconfig "$name" down || exit 1
 esac
done
for retry in 1 2 3 4 5; do
 [ "$(cat /sys/module/mtfwd/refcnt 2>/dev/null)" = 0 ] && break
 sleep 1
done
for m in mt_whnat mtfwd; do
 if [ -d "/sys/module/$m" ]; then rmmod "$m" || exit 1; fi
done
if [ -e /sys/bus/platform/drivers/mediatek_soc_hnat/1b100000.hnat ]; then
 printf '%s' '1b100000.hnat' > /sys/bus/platform/drivers/mediatek_soc_hnat/unbind || exit 1
fi
for d in /sys/class/net/ra* /sys/class/net/apcli*; do
 [ -e "$d/flags" ] || continue
 echo "${d##*/} flags=$(cat "$d/flags")"
done
echo VENDOR_DMA_QUIESCENCE_PREPARED
