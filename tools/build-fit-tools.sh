#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
set -eu
repo=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
archive="$repo/work/WX3600HP_source.tar.gz"
[ -f "$archive" ] || { echo 'First run tools/prepare_legacy.py to fetch/verify the NEC GPL archive'; exit 1; }
python3 - "$repo" "$archive" <<'ENDPY'
import sys,json,hashlib
from pathlib import Path
r=Path(sys.argv[1]);p=Path(sys.argv[2])
with p.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest==json.loads((r/'sources.lock.json').read_text())['nec_gpl']['sha256'],'GPL archive checksum mismatch'
ENDPY
mkdir -p "$repo/work/nec-gpl" "$repo/work/fit-tools"
[ -d "$repo/work/nec-gpl/Uboot-upstream" ] || tar -xzf "$archive" -C "$repo/work/nec-gpl" ./Uboot-upstream
make -C "$repo/work/nec-gpl/Uboot-upstream" O="$repo/work/fit-tools" tools-only_defconfig
make -C "$repo/work/nec-gpl/Uboot-upstream" O="$repo/work/fit-tools" -j"${JOBS:-4}" tools-only
[ -x "$repo/work/fit-tools/tools/fit_check_sign" ]
