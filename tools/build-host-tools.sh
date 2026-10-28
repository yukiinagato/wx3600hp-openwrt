#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
set -eu
repo=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
out=${1:-"$repo/out/tools"}
cc=${CC:-aarch64-linux-gnu-gcc}
objcopy=${OBJCOPY:-aarch64-linux-gnu-objcopy}
mkdir -p "$out"
for name in ram_loader write_system2 boot_choice_linux wxboot_guard phy_mmd panel; do
 "$cc" -Os -static -fno-pie -no-pie "$repo/src/$name.c" -o "$out/$name"
done
"$cc" -Os -ffreestanding -fno-pic -fno-pie -fno-stack-protector -nostdlib -no-pie -Wl,--build-id=none -Wl,-T,"$repo/src/boot_choice_uboot.ld" "$repo/src/boot_choice_uboot.c" -o "$out/selector.elf"
"$objcopy" -O binary "$out/selector.elf" "$out/selector.bin"
mkimage -f "$repo/boot/helper.its" "$out/helper.itb"
python3 - "$out" <<'ENDPY'
import sys
from pathlib import Path
p=Path(sys.argv[1]);s=(p/'helper.itb').read_bytes();b=(p/'selector.bin').read_bytes()
assert len(s)<=0x8000 and len(b)<=0x8000
(p/'boothelper.bundle').write_bytes(s+b'\xff'*(0x8000-len(s))+b+b'\xff'*(0x8000-len(b)))
ENDPY
