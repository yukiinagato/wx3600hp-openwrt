#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Read logical flash partitions over verified SSH, with length and remote SHA256 checks.

Optional raw physical MAIN data uses ECC, includes bad blocks, and NEVER requests OOB.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host',required=True);p.add_argument('--port',type=int,default=22)
    p.add_argument('--identity',type=Path,required=True);p.add_argument('--known-hosts',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--include-physical',action='store_true')
    a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.:%-]+',a.host) or a.host.startswith('-'): raise SystemExit('Invalid host')
    a.out.mkdir(mode=0o700,parents=True,exist_ok=False)
    ssh=['ssh','-p',str(a.port),'-i',str(a.identity.resolve()),'-o','BatchMode=yes','-o','IdentitiesOnly=yes',
         '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile='+str(a.known_hosts.resolve()),'root@'+a.host]
    def read(cmd): return subprocess.check_output(ssh+[cmd],timeout=60)
    table=read('cat /proc/mtd');(a.out/'proc-mtd.txt').write_bytes(table)
    entries=re.findall(rb'mtd(\d+): ([0-9a-f]+) ([0-9a-f]+) "([^"]+)"',table)
    if not entries: raise SystemExit('No MTD table')
    manifest=[]
    def dump(name,command,size,remote_hash=None):
        target=a.out/name
        with target.open('xb') as out:
            r=subprocess.run(ssh+[command],stdout=out,stderr=subprocess.PIPE,timeout=600,check=True)
        target.chmod(0o600)
        if target.stat().st_size!=size: raise SystemExit('Incorrect backup length: '+name)
        with target.open('rb') as stream: sha=hashlib.file_digest(stream,'sha256').hexdigest()
        if remote_hash and sha!=read(remote_hash).split()[0].decode():
            raise SystemExit('Hash changed/mismatched: '+name+'; keep incomplete backup private and retry into a new directory')
        manifest.append({'file':name,'bytes':size,'sha256':sha})
        (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print('Verified',name,size,'bytes')
    if a.include_physical:
        item=next((e for e in entries if e[0]==b'0'),None)
        if item is None or int(item[1],16)!=0x8000000: raise SystemExit('Not the tested 128 MiB stock physical MTD0')
        cmd='/opt/nec-ssh/ld-musl-aarch64.so.1 --library-path /opt/nec-ssh /opt/nec-ssh/nanddump --omitoob --bb=dumpbad /dev/mtd0'
        dump('physical-ecc-main.bin',cmd,0x8000000)
        # Independent second ECC read, streamed and hashed on the host.
        digest=hashlib.sha256();proc=subprocess.Popen(ssh+[cmd],stdout=subprocess.PIPE)
        while block:=proc.stdout.read(1024*1024): digest.update(block)
        if proc.wait()!=0 or digest.hexdigest()!=manifest[-1]['sha256']: raise SystemExit('Second physical read differs')
    for n,size,erase,label in entries:
        n=int(n);size=int(size,16)
        if n==0: continue
        name=re.sub(r'[^A-Za-z0-9_-]','_',label.decode())
        dump('mtd%d-%s.bin'%(n,name),'dd if=/dev/mtd%dro bs=131072'%n,size,'sha256sum /dev/mtd%dro'%n)
    for name,cmd in [('running.dtb','cat /sys/firmware/fdt'),('kernel.config.gz','cat /proc/config.gz'),
                     ('cmdline.txt','cat /proc/cmdline'),('mounts.txt','cat /proc/mounts'),('dmesg.txt','dmesg')]:
        (a.out/name).write_bytes(read(cmd))
    (a.out/'COMPLETE').write_text('Individually verified partitions; not an atomic whole-device snapshot. No OOB backup.\n')
    print('Backup complete. Keep two private copies outside this repository. No erase/write issued.')
if __name__=='__main__': main()
