#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Create an EMPTY small UBIFS/UBI overlay image, never use this on an existing MTD.
set -eu
out=${1:?Usage: make-ubi.sh output.ubi}
[ ! -e "$out" ] || { echo 'Output already exists'; exit 1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT HUP INT TERM
mkdir -p "$tmp/root/upper" "$tmp/root/work"
mkfs.ubifs -m 2048 -e 126976 -c 32 -x zlib -r "$tmp/root" -o "$tmp/root.ubifs"
cat >"$tmp/ubi.ini" <<EOF
[rootfs_data]
mode=ubi
image=$tmp/root.ubifs
vol_id=0
vol_type=dynamic
vol_name=rootfs_data
vol_flags=autoresize
EOF
ubinize -m 2048 -p 128KiB -s 2048 -o "$out" "$tmp/ubi.ini"
