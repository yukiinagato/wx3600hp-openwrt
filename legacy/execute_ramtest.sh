#!/bin/sh
# The payload is already verified in /tmp. No firmware write is performed.
set -u
cd /tmp/wx-ramboot || exit 1
sync
for p in / /tmp/usercfg1 /tmp/usercfg2 /nvram /nvram_data /overlay; do
 if ! mount -o remount,ro "$p"; then
  echo "Cannot remount $p read-only; refusing transition"
  exit 1
 fi
done
cat /proc/mounts
./ram_loader Image board.dtb initrd.cpio.gz --execute
result=$?
echo "Handoff returned $result; restoring original mounts and services"
./ram_loader --unload
for p in /overlay /tmp/usercfg1 /tmp/usercfg2 /nvram /nvram_data /; do
 mount -o remount,rw "$p"
done
if [ -f stopped-pids ]; then
 while read pid; do kill -CONT "$pid" 2>/dev/null || true; done < stopped-pids
fi
dmesg | tail -45
exit "$result"
