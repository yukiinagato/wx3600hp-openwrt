#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Extract the unique fit_key-bearing U-Boot control FDT from OWN FIP backup."""
import argparse,struct
from pathlib import Path
from fdt import FDT
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fip',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();data=a.fip.read_bytes();matches=[];pos=0
while True:
    pos=data.find(bytes.fromhex('d00dfeed'),pos)
    if pos<0: break
    try:
        size=struct.unpack_from('>I',data,pos+4)[0]
        if not 40<=size<=0x20000: raise ValueError('bounds')
        candidate=data[pos:pos+size];f=FDT(candidate);key=f.node('/signature/key-fit_key')
        if key.props.get('required')==b'conf\0' and key.props.get('algo')==b'sha1,rsa2048\0':matches.append(candidate)
    except (ValueError,StopIteration,struct.error): pass
    pos+=4
if len(matches)!=1: raise SystemExit('Expected one matching stock control FDT; found '+str(len(matches)))
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(matches[0]);a.out.chmod(0o600)
print('Private control FDT extracted; use it for stock FIT verification.')
