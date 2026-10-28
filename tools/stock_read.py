#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Authenticated, bounded file read on OWN stock 1.5.3 unit. No config writes."""
import argparse,getpass,re,urllib.parse,urllib.request
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host',required=True);p.add_argument('--stock-version',required=True,choices=['1.5.3'])
    p.add_argument('--path',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if not a.path.startswith('/') or any(c in a.path for c in '?#\r\n'):
        raise SystemExit('Absolute file path required')
    base=a.host.rstrip('/');parsed=urllib.parse.urlsplit(base)
    if parsed.scheme not in ['http','https'] or not parsed.hostname or parsed.path or parsed.username:
        raise SystemExit('Use http://router-address with no path/embedded password')
    op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    page=base+'/page/login_main.html?return=index_contents.html'
    html=op.open(page,timeout=10).read().decode('euc_jp','replace')
    token=re.search(r'name="SESSION_ID" value="([^"]+)"',html)
    if not token: raise SystemExit('Unsupported login form')
    fields={'SESSION_ID':token.group(1),'dest':'','user':'admin','pass':getpass.getpass('Stock admin password: '),'return':''}
    r=op.open(urllib.request.Request(base+'/form/formLogin',data=urllib.parse.urlencode(fields).encode(),headers={'Referer':page,'Origin':base}),timeout=10)
    if not r.url.startswith(base+'/page/index_contents.html'): raise SystemExit('Authentication failed')
    request=urllib.request.Request(base+'/page/..'+urllib.parse.quote(a.path,safe='/'),headers={'Referer':r.url})
    with op.open(request,timeout=20) as result: data=result.read(32000001)
    if not data or len(data)>32000000 or data.startswith(b'stat error file:') or b'<title>NEC' in data[:2000]:
        raise SystemExit('File unavailable; nothing saved')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_bytes(data);a.out.chmod(0o600)
    print('Private file saved; do not publish it.')
if __name__=='__main__': main()
