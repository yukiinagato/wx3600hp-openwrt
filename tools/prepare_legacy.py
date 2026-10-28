#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Download NEC GPL source, verify SHA256, prepare the matched legacy kernel source."""
import argparse,hashlib,inspect,json,re,shutil,subprocess,tarfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def extract_verified(t,dest,members=None):
    # Only called on the SHA256-verified NEC archive or its contained kernel tar.
    options={'filter':'data'} if 'filter' in inspect.signature(t.extractall).parameters else {}
    t.extractall(dest,members=members,**options)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=Path)
    p.add_argument('--out',type=Path,default=ROOT/'work/legacy-kernel');a=p.parse_args()
    if a.out.exists(): raise SystemExit('Output already exists; refusing overwrite')
    lock=json.loads((ROOT/'sources.lock.json').read_text())['nec_gpl']
    archive=a.archive or ROOT/'work/WX3600HP_source.tar.gz';archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists(): urllib.request.urlretrieve(lock['url'],archive)
    with archive.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest!=lock['sha256']: raise SystemExit('NEC GPL source checksum mismatch')
    vendor=ROOT/'work/nec-gpl';vendor.mkdir(parents=True,exist_ok=True)
    # The verified archive is large; extract only the Linux source/patch directory.
    with tarfile.open(archive) as t:
        members=[m for m in t if m.name.lstrip('./').startswith('linux-4.4.198/')]
        extract_verified(t,vendor,members)
    base=vendor/'linux-4.4.198'
    a.out.mkdir(parents=True)
    with tarfile.open(base/'linux-4.4.198.tar.xz') as t:
        # Kernel tar contains linux-4.4.198/ at top level.
        extract_verified(t,a.out.parent/'legacy-unpack')
    unpack=a.out.parent/'legacy-unpack/linux-4.4.198'
    a.out.rmdir();shutil.move(str(unpack),str(a.out))
    for group in ['generic','mediatek']:
        folder=base/group
        if (folder/'setting').exists(): shutil.copytree(folder/'setting',a.out,dirs_exist_ok=True)
        for patch in sorted(folder.iterdir()):
            if patch.suffix not in ['.patch','.path']: continue
            command=['patch','--batch','-p1','-i',str(patch.resolve())]
            check=subprocess.run(command+['--forward','--dry-run'],cwd=a.out,capture_output=True)
            if check.returncode:
                reverse=subprocess.run(command+['--reverse','--dry-run'],cwd=a.out,capture_output=True)
                if reverse.returncode: raise SystemExit('Vendor patch does not apply: '+patch.name)
            else: subprocess.run(command+['--forward'],cwd=a.out,check=True,stdout=subprocess.DEVNULL)
    # Old dtc defines yylloc in both lexer and parser; GCC 10+ defaults to -fno-common.
    for name in ['dtc-lexer.l','dtc-lexer.lex.c','dtc-lexer.lex.c_shipped']:
        lexer=a.out/'scripts/dtc'/name
        if lexer.is_file():
            text=lexer.read_text()
            lexer.write_text(re.sub(r'^YYLTYPE yylloc;$','extern YYLTYPE yylloc;',text,flags=re.M))
    shutil.copyfile(ROOT/'legacy/stock-4.4.198.config',a.out/'.config')
    print('Legacy source prepared. Compare its config with YOUR saved /proc/config.gz before building/loading.')
if __name__=='__main__': main()
