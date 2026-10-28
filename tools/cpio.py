# SPDX-License-Identifier: GPL-2.0-only
"""Preserve newc entries and add the upstream RAM /init before its trailer."""
import gzip

def ram_cpio(data,init):
    raw=gzip.decompress(data);pos=0;parts=[];ino=1
    while pos+110<=len(raw):
        start=pos;h=raw[pos:pos+110];pos+=110
        if h[:6] not in [b'070701',b'070702']: raise ValueError('Not newc cpio')
        fields=[int(h[6+i*8:14+i*8],16) for i in range(13)]
        size=fields[6];ns=fields[11]
        if not 1<=ns<=4096 or pos+ns>len(raw): raise ValueError('CPIO name bounds')
        name=raw[pos:pos+ns-1];pos=(pos+ns+3)&~3
        if pos+size>len(raw): raise ValueError('CPIO data bounds')
        pos=(pos+size+3)&~3
        if name==b'TRAILER!!!': break
        if name not in [b'init',b'./init']: parts.append(raw[start:pos])
        ino=max(ino,fields[0]+1)
    else: raise ValueError('No cpio trailer')
    def entry(name,mode,content,number):
        name=name+b'\0';fields=[number,mode,0,0,1,0,len(content),0,0,0,0,len(name),0]
        out=b'070701'+b''.join(format(n,'08x').encode() for n in fields)+name
        out+=b'\0'*((-len(out))%4);out+=content;out+=b'\0'*((-len(out))%4)
        return out
    parts.extend([entry(b'init',0o100755,init,ino),entry(b'TRAILER!!!',0,b'',ino+1)])
    result=b''.join(parts);result+=b'\0'*((-len(result))%512)
    return gzip.compress(result,mtime=0)
