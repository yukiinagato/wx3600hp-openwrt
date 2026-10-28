#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
set -eu
repo=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
source_dir=${OPENWRT_SOURCE:-"$repo/work/openwrt"}
[ -f "$source_dir/.wx3600hp-overlay" ] || python3 "$repo/tools/prepare.py" --source "$source_dir"
cd "$source_dir"
./scripts/feeds update -a
./scripts/feeds install luci luci-ssl luci-i18n-base-zh-cn luci-app-upnp luci-app-usteer luci-app-ddns luci-app-wol iperf3
[ -f .config ] || cp "$repo/configs/seed.config" .config
make defconfig
[ "${1:-}" != --menuconfig ] || make menuconfig
make download -j"${JOBS:-4}"
make -j"${JOBS:-4}" V=s
python3 "$repo/tools/collect.py" --source "$source_dir" --out "$repo/out/components"
