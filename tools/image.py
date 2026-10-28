# SPDX-License-Identifier: GPL-2.0-only
"""Bounded System2 image format and CRC helpers; no hardware access."""
import hashlib,struct,zlib
from fdt import FDT,Node
SIZE=0x2000000
REGIONS={'carrier':(0,0x280000),'rootfs':(0x280000,0xa80000),
         'kernel':(0xd00000,0xbc0000),'selector':(0x18c0000,0x40000),
         'dtb':(0x1900000,0x10000),'helper':(0x1910000,0x10000),'ubi':(0x1920000,0x6e0000)}
def bootseq(data):
    if len(data)!=0x40000: raise ValueError('bootseq must be 256 KiB')
    records=[]
    for offset in (0x10,0x40):
        r=data[offset:offset+48]
        if r[:4]!=b'WUDI' or struct.unpack_from('<I',r,4)[0]!=48:
            raise ValueError('Unrecognized bootseq record layout')
        kc,ks,rc,rs,rn=struct.unpack_from('>5I',r,8)
        if rs!=0x280000 or not 0<ks<=0x280000 or not 0<rn<=0xa80000:
            raise ValueError('Unsupported CRC windows')
        records.append(dict(kernel_crc=kc,kernel_size=ks,rootfs_crc=rc,rootfs_start=rs,rootfs_size=rn,
                            version=r[32:48].split(b'\0',1)[0].decode('ascii')))
    return records

def force_crc(data,target):
    if len(data)<4: raise ValueError('CRC correction needs four padding bytes')
    data=bytearray(data);data[-4:]=b'\0'*4;base=zlib.crc32(data);basis={}
    # Only vary four trailing bytes. Their independence is checked, not assumed.
    for bit in range(32):
        sample=bytearray(data);sample[-4+bit//8]^=1<<(bit%8)
        value=zlib.crc32(sample)^base;mask=1<<bit
        while value:
            n=value.bit_length()-1
            if n not in basis: basis[n]=(value,mask);break
            value^=basis[n][0];mask^=basis[n][1]
    if len(basis)!=32: raise ValueError('Singular CRC correction matrix')
    value=target^base;mask=0
    while value:
        n=value.bit_length()-1;value^=basis[n][0];mask^=basis[n][1]
    data[-4:]=mask.to_bytes(4,'little')
    if zlib.crc32(data)!=target: raise ValueError('CRC correction failed')
    return data

def carrier(stock):
    f=FDT(stock);images=f.node('/images');configs=f.node('/configurations')
    if any(n.name=='script@0' for n in images.children): raise ValueError('Stock already modified')
    images.child('script@1')
    if not any(b'script@1\0'==n.props.get('loadables') for n in configs.children):
        raise ValueError('Not the tested stock FIT configuration')
    if not any('signature' in n.name for n in configs.walk()): raise ValueError('No signed configuration')
    if any('data-offset' in n.props or 'data-position' in n.props for n in images.children):
        raise ValueError('External FIT data unsupported')
    script=b'setenv wxfetch nmbm nmbm0 read 45000000 5910000 10000\nsetenv wxsource source 45000000:script\nrun wxfetch wxsource;run boot_system1\n'
    n=Node('script@0',{'description':b'WX3600HP OpenWrt boot entry\0','type':b'script\0',
        'arch':b'arm64\0','os':b'linux\0','compression':b'none\0','data':script})
    n.children=[Node('hash@1',{'algo':b'crc32\0','value':struct.pack('>I',zlib.crc32(script))}),
                Node('hash@2',{'algo':b'sha1\0','value':hashlib.sha1(script).digest()})]
    images.children.insert(0,n)
    return f.encode()

def selection(choice=0,sequence=1):
    r=struct.pack('<5I',0x57425833,1,sequence,choice,choice^0xffffffff)
    r+=struct.pack('<I',zlib.crc32(r))
    return r+b'\xff'*(0x40000-len(r))

def validate_parts(parts):
    f=FDT(parts['dtb'])
    if b'nec,aterm-wx3600hp\0' not in f.root.props.get('compatible',b''):
        raise ValueError('Not a WX3600HP flash DTB')
    if any(k.startswith('linux,initrd-') for k in f.node('/chosen').props):
        raise ValueError('RAM DTB cannot be used for flash boot')
    labels={}
    for n in f.root.walk():
        if 'nec,read-only-probe' in n.props: raise ValueError('Read-only probe DTB cannot boot writable flash')
        if 'label' in n.props and 'reg' in n.props and len(n.props['reg'])==8:
            labels[n.props['label'].rstrip(b'\0').decode()]=(struct.unpack('>2I',n.props['reg']),n.props)
    expected={'boot-carrier':(0x4000000,0x280000),'rootfs':(0x4280000,0xa80000),
              'openwrt-kernel':(0x4d00000,0xbc0000),'boot-selection':(0x58c0000,0x40000),
              'openwrt-boot-data':(0x5900000,0x20000),'ubi':(0x5920000,0x6e0000)}
    for name,region in expected.items():
        if name not in labels or labels[name][0]!=region: raise ValueError('Unexpected flash DT partition: '+name)
        ro='read-only' in labels[name][1]
        if ro!=(name not in ['boot-selection','ubi']): raise ValueError('Unexpected partition access: '+name)
    radios=[n for n in f.root.walk() if n.props.get('compatible')==b'mediatek,mt76\0']
    if len(radios)!=2 or any(len(n.props.get('mediatek,eeprom-data',b''))!=0xe00 or n.props.get('status')!=b'okay\0' for n in radios):
        raise ValueError('Both radios need this device\'s calibration before packaging')
    helper=parts['helper']
    if len(helper)!=0x10000 or helper[0x8000:0x8004] in [b'\0'*4,b'\xff'*4]:
        raise ValueError('Missing boothelper/selector bundle')
    h=FDT(helper)
    h.node('/images/script@1')
    if parts['ubi'][:4]!=b'UBI#': raise ValueError('Not an UBI image')

def assemble(stock,seq,parts):
    if len(stock)!=SIZE: raise ValueError('Stock System2 must be exactly 32 MiB')
    b=bootseq(seq)[1]
    if seq[15]!=1: raise ValueError('Stock System2 must be selected in the tested bootseq layout')
    if b['version']!='1.5.3': raise ValueError('Only stock 1.5.3 tested')
    for name,start,length in [('kernel',0,b['kernel_size']),('rootfs',0x280000,b['rootfs_size'])]:
        if zlib.crc32(stock[start:start+length])!=b[name+'_crc']:
            raise ValueError('Original '+name+' CRC does not match bootseq')
    validate_parts(parts)
    parts=dict(parts);parts['carrier']=carrier(stock);parts['selector']=selection()
    if parts['rootfs'][:4]!=b'hsqs': raise ValueError('Not SquashFS')
    if parts['kernel'][56:60]!=b'ARM\x64': raise ValueError('Not a raw ARM64 Image')
    if struct.unpack_from('<Q',parts['kernel'],8)[0]!=0: raise ValueError('Flash booti expects text_offset=0')
    squashsize=struct.unpack_from('<Q',parts['rootfs'],40)[0]
    if not 96<=squashsize<=len(parts['rootfs']): raise ValueError('Invalid SquashFS used length')
    parts['rootfs']=parts['rootfs'][:squashsize]
    if len(parts['carrier'])>b['kernel_size']-4 or squashsize>b['rootfs_size']-4:
        raise ValueError('No safe CRC padding outside FIT/SquashFS data')
    image=bytearray(b'\xff'*SIZE)
    for name,data in parts.items():
        offset,limit=REGIONS[name]
        if len(data)>limit: raise ValueError(name+' exceeds its reserved region')
        image[offset:offset+len(data)]=data
    ks=b['kernel_size'];rs=b['rootfs_size'];image[:ks]=force_crc(image[:ks],b['kernel_crc'])
    image[0x280000:0x280000+rs]=force_crc(image[0x280000:0x280000+rs],b['rootfs_crc'])
    return bytes(image)
