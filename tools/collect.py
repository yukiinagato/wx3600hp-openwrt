#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
import argparse, hashlib, json, shutil
from pathlib import Path
from cpio import ram_cpio
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);base=a.source/'bin/targets/mediatek/mt7622';report={}
for suffix,name in [('Image','Image'),('ram.dtb','ram.dtb'),('ro.dtb','ro.dtb'),('install.dtb','install.dtb'),('flash.dtb','flash.dtb'),('squashfs-rootfs.bin','rootfs.squashfs')]:
    found=list(base.glob('*nec_aterm-wx3600hp-'+suffix))
    if len(found)!=1: raise SystemExit('Missing/ambiguous artifact: '+suffix)
    shutil.copyfile(found[0],a.out/name)
cpio=list(base.glob('*rootfs.cpio.gz'))
if len(cpio)!=1: raise SystemExit('Missing/ambiguous rootfs.cpio.gz')
(a.out/'initrd.cpio.gz').write_bytes(ram_cpio(cpio[0].read_bytes(),(a.source/'target/linux/generic/other-files/init').read_bytes()))
for f in a.out.iterdir():
    if f.is_file(): report[f.name]={'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
(a.out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
print('Collected components (not installable without personalization):',a.out)
