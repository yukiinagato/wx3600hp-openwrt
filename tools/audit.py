#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Check tracked publication inputs, never private/out/work directories."""
import re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
paths=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
if not any(paths):
    paths=[str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file() and
           not any(x in p.relative_to(ROOT).parts for x in ['.git','work','out','private','__pycache__'])]
errors=[]
for path in paths:
    if not path:continue
    p=ROOT/path
    if any(x in Path(path).parts for x in ['private','work','out','full-backup','ssh-runtime']):errors.append(path+': private/build directory tracked')
    if p.suffix in ['.ko','.bin','.dtb','.itb','.ubi','.ubifs','.squashfs','.ipk']:errors.append(path+': binary/backup artifact tracked')
    data=p.read_bytes()
    for pattern in [rb'-----BEGIN (?:OPENSSH|RSA|EC|DSA)? ?PRIVATE KEY-----',
                    rb'ssh-ed25519 AAAA[0-9A-Za-z+/]{40,}']:
        # The audit's own patterns are test rules, not actual secret material.
        if p.name!='audit.py' and re.search(pattern,data):errors.append(path+': sensitive/private identifier pattern')
    if len(data)>1024*1024:errors.append(path+': unexpectedly large source file')
if errors:raise SystemExit('\n'.join(errors))
print('Publication audit passed:',len([p for p in paths if p]),'source/document files')
