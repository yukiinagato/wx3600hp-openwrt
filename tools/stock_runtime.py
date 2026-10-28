#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Fetch checksum-locked public packages and build a private stock SSH runtime."""
import argparse,hashlib,io,json,os,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--public-key',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path);a=p.parse_args()
    pub=a.public_key.read_bytes().strip()
    if not pub.startswith(b'ssh-ed25519 ') or b'PRIVATE KEY' in pub or b'\n' in pub:
        raise SystemExit('Supply your own single-line ED25519 PUBLIC key')
    files={};wanted={'dropbear':'usr/sbin/dropbear','libc':'lib/libc.so','nand-utils':'usr/sbin/nanddump','libgcc1':'lib/libgcc_s.so.1'}
    for dep in json.loads((ROOT/'sources.lock.json').read_text())['stock_runtime']:
        data=urllib.request.urlopen(dep['url'],timeout=30).read(4000001)
        if hashlib.sha256(data).hexdigest()!=dep['sha256']: raise SystemExit('Package checksum mismatch')
        with tarfile.open(fileobj=io.BytesIO(data)) as outer:
            member=next(x for x in outer if x.name.lstrip('./')=='data.tar.gz')
            payload=outer.extractfile(member).read()
        with tarfile.open(fileobj=io.BytesIO(payload)) as inner:
            path=wanted[dep['package']]
            member=next(x for x in inner if x.name.lstrip('./')==path)
            if not member.isfile(): raise SystemExit('Unexpected package member')
            files['ld-musl-aarch64.so.1' if dep['package']=='libc' else Path(path).name]=inner.extractfile(member).read()
    files['authorized_keys']=pub+b'\n'
    files['install-stock-ssh.sh']=(ROOT/'legacy/install-stock-ssh.sh').read_bytes()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    with tarfile.open(a.out,'w:gz') as out:
        for name,data in files.items():
            info=tarfile.TarInfo('wx-stock-runtime/'+name);info.size=len(data);info.mode=0o600 if name=='authorized_keys' else 0o700
            out.addfile(info,io.BytesIO(data))
    a.out.chmod(0o600)
    print('Private runtime archive prepared. Contains your public key; no generated/shared private key.')
if __name__=='__main__': main()
