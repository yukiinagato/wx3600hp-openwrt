#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Inject OWN Factory calibration/MAC into a DTB, without touching a device."""
import argparse, struct
from pathlib import Path
from fdt import FDT

def personalize(data, factory, initrd=None, single_core=False):
    if len(factory)!=0x100000: raise ValueError('Factory must be the 1 MiB logical partition')
    mac=factory[0x7fff4:0x7fffa]
    if mac[0]&1 or mac==b'\0'*6 or mac==b'\xff'*6: raise ValueError('Invalid Factory base MAC')
    f=FDT(data)
    if b'nec,aterm-wx3600hp\0' not in f.root.props.get('compatible',b''):
        raise ValueError('Not our WX3600HP DTB')
    for n in f.root.walk():
        if n.props.get('compatible')==b'mediatek,eth-mac\0' and n.props.get('reg')==struct.pack('>I',0):
            n.props['local-mac-address']=mac
        if n.props.get('compatible')==b'mediatek,mt76\0':
            freq=struct.unpack('>2I',n.props['ieee80211-freq-limit'])[0]
            offset=0 if freq==2400000 else 0x5000 if freq==5000000 else None
            if offset is None: raise ValueError('Unknown radio band')
            eeprom=factory[offset:offset+0xe00]
            if eeprom[:2]!=bytes.fromhex('1579'): raise ValueError('Not MT7915 EEPROM')
            n.props['mediatek,eeprom-data']=eeprom
            n.props['status']=b'okay\0'
    chosen=f.node('/chosen')
    args=chosen.props.get('bootargs',b'').rstrip(b'\0').split()
    args=[x for x in args if not x.startswith(b'maxcpus=')]
    if single_core: args.append(b'maxcpus=1')
    chosen.props['bootargs']=b' '.join(args)+b'\0'
    if initrd is not None:
        if not 0<initrd<=0x4000000: raise ValueError('Initrd exceeds RAM loader reservation')
        chosen.props['linux,initrd-start']=struct.pack('>Q',0x52000000)
        chosen.props['linux,initrd-end']=struct.pack('>Q',0x52000000+initrd)
    else:
        chosen.props.pop('linux,initrd-start',None);chosen.props.pop('linux,initrd-end',None)
    result=f.encode()
    if len(result)>0x10000: raise ValueError('DTB exceeds 64 KiB reservation')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dtb',required=True,type=Path);p.add_argument('--factory',required=True,type=Path)
    p.add_argument('--single-core',action='store_true')
    p.add_argument('--initrd',type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    out=personalize(a.dtb.read_bytes(),a.factory.read_bytes(),a.initrd.stat().st_size if a.initrd else None,a.single_core)
    a.out.write_bytes(out);a.out.chmod(0o600)
    print('Private personalized DTB written. Do not upload it or share calibration data.')
if __name__=='__main__': main()
