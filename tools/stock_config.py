#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Prepare a Telnet-enable config from OWN stock 1.5.3 export and form CGI.

Offline only. Does not upload, reboot, expose firmware keys, or write flash.
"""
import argparse, re, subprocess, zlib
from pathlib import Path

def crypt(data,key,iv,decrypt=False):
    # Firmware passes ASCII strings as AES key/IV, not hex-decoded values.
    args=['openssl','enc','-aes-256-cbc','-K',key[:32].hex(),'-iv',iv[:16].hex()]
    if decrypt: args.append('-d')
    r=subprocess.run(args,input=data,capture_output=True)
    if r.returncode: raise ValueError('AES decode failed')
    return r.stdout

def check(data):
    if len(data)<26 or not re.fullmatch(rb'[0-9a-fA-F]{8}\n',data[-9:]): return False
    return zlib.crc32(data[:-9])==int(data[-9:-1],16) and b'uci ' in data[16:]

def decode(data,cgi):
    keys=set(re.findall(rb'(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])',cgi))
    ivs=set(re.findall(rb'(?<![0-9a-f])[0-9a-f]{32}(?![0-9a-f])',cgi))
    if len(keys)*len(ivs)>256: raise ValueError('Unsupported CGI: too many candidates')
    matches=[]
    for key in keys:
        for iv in ivs:
            try: plain=crypt(data,key,iv,True)
            except ValueError: continue
            if check(plain): matches.append((plain,key,iv))
    if len(matches)!=1: raise ValueError('Not the tested export format / ambiguous key candidates')
    return matches[0]

def enable(data,cgi):
    original,key,iv=decode(data,cgi)
    extra=b"\n/usr/sbin/productcfg_set TELNETS_ENABLED 1 >/tmp/wx-telnet-enable.log 2>&1\n/usr/sbin/productcfg TELNETS_ENABLED >>/tmp/wx-telnet-enable.log 2>&1\nsync\n"
    body=original[:-9]+extra
    modified=body+format(zlib.crc32(body),'08x').encode()+b'\n'
    subprocess.run(['sh','-n'],input=modified[16:-9],check=True)
    result=crypt(modified,key,iv)
    if decode(result,cgi)[0]!=modified: raise ValueError('Encryption round-trip failed')
    if not modified.startswith(original[:-9]): raise ValueError('Original commands changed')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stock-version',choices=['1.5.3'],required=True)
    p.add_argument('--export',dest='export_file',type=Path,required=True)
    p.add_argument('--form-cgi',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();out=enable(a.export_file.read_bytes(),a.form_cgi.read_bytes())
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(out);a.out.chmod(0o600)
    print('Prepared private config; CRC, shell syntax and AES round-trip passed. Original commands preserved.')
    print('Import it through your authenticated stock config-restore UI, then reboot. This changes configuration.')
if __name__=='__main__': main()
