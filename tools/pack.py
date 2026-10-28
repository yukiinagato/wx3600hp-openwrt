#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Package OWN backup and build components. Requires independent stock FIT verification."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
from image import assemble

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['stock-system2','bootseq','kernel','rootfs','dtb','helper','ubi','control-dtb','fit-check-sign','out']:
        p.add_argument('--'+n,required=True,type=Path)
    a=p.parse_args()
    parts={n:getattr(a,n).read_bytes() for n in ['kernel','rootfs','dtb','helper','ubi']}
    image=assemble(a.stock_system2.read_bytes(),a.bootseq.read_bytes(),parts)
    with tempfile.TemporaryDirectory() as t:
        f=Path(t)/'carrier.itb';f.write_bytes(image[:0x280000])
        subprocess.run([str(a.fit_check_sign.resolve()),'-f',str(f),'-k',str(a.control_dtb.resolve())],check=True)
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(image);a.out.chmod(0o600)
    manifest={'size':len(image),'sha256':hashlib.sha256(image).hexdigest(),
              'stock_system2_sha256':hashlib.sha256(a.stock_system2.read_bytes()).hexdigest(),
              'notice':'Private device-specific image. Not OEM UI/sysupgrade format. No device writes performed.'}
    a.out.with_suffix('.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Signature verifier succeeded; private image and manifest written. No flash accessed.')
if __name__=='__main__': main()
