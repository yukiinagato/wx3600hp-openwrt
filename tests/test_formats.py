# SPDX-License-Identifier: GPL-2.0-only
import gzip,random,struct,sys,unittest,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from fdt import FDT,Node
from image import bootseq,force_crc,carrier,selection,REGIONS,SIZE
from personalize import personalize
from stock_config import enable,decode,crypt
from cpio import ram_cpio

def tree(root):
    f=FDT.__new__(FDT);f.root=root;f.strings=b'original-property\0';f.reserve=b'\0'*16;f.bootcpu=0
    return f.encode()

def seq():
    b=bytearray(b'\xff'*0x40000);b[15]=1
    for offset,version in [(0x10,b'1.3.7'),(0x40,b'1.5.3')]:
        r=b'WUDI'+struct.pack('<I',48)+struct.pack('>5I',1,0x1000,2,0x280000,0x4000)+b'\0'*4+version.ljust(16,b'\0')
        b[offset:offset+48]=r
    return bytes(b)

class Formats(unittest.TestCase):
    def test_crc_padding(self):
        rng=random.Random(813)
        for n in [4,9,128,8192]:
            original=rng.randbytes(n);target=rng.getrandbits(32);out=force_crc(original,target)
            self.assertEqual(out[:-4],original[:-4]);self.assertEqual(zlib.crc32(out),target)
    def test_bootseq(self):
        self.assertEqual(bootseq(seq())[1]['version'],'1.5.3')
        b=bytearray(seq());b[0x40]=0
        with self.assertRaises(ValueError):bootseq(b)
        with self.assertRaises(ValueError):bootseq(seq()[:-1])
    def test_region_geometry(self):
        entries=sorted(REGIONS.values())
        self.assertEqual(entries[0][0],0)
        for (offset,size),(nextoffset,_) in zip(entries,entries[1:]):self.assertEqual(offset+size,nextoffset)
        self.assertEqual(sum(size for _,size in entries),SIZE)
    def test_selector_crc(self):
        b=selection(1,0xffffffff);self.assertEqual(len(b),0x40000)
        self.assertEqual(struct.unpack_from('<I',b,20)[0],zlib.crc32(b[:20]))
        self.assertEqual(b[24:],b'\xff'*(len(b)-24))
    def test_fdt_roundtrip(self):
        b=tree(Node('',{'original-property':b'abc\0'},[Node('child',{'foo':b'12345'})]))
        f=FDT(b);f.root.props['extra']=b'value'
        out=f.encode();g=FDT(out)
        self.assertEqual(g.strings[:len(f.strings)],f.strings)
        self.assertEqual(g.node('/child').props,{'foo':b'12345'})
        with self.assertRaises(ValueError):FDT(out[:-1])
    def test_carrier_preserves_original(self):
        old=Node('script@1',{'type':b'script\0','data':b'original'})
        root=Node('',{},[Node('images',{},[old]),Node('configurations',{},[
            Node('config@1',{'loadables':b'script@1\0'},[Node('signature',{'value':b'synthetic signature'})])])])
        original=tree(root);out=carrier(original);f=FDT(out)
        self.assertEqual(f.node('/images').children[0].name,'script@0')
        self.assertEqual(f.node('/images/script@1').props,old.props)
        self.assertEqual(f.node('/configurations/config@1/signature').props['value'],b'synthetic signature')
        self.assertTrue(f.strings.startswith(FDT(original).strings))
        with self.assertRaises(ValueError):carrier(out)
    def test_personalization(self):
        root=Node('',{'compatible':b'nec,aterm-wx3600hp\0'},[
            Node('chosen',{'bootargs':b'console=ttyS0\0'}),
            Node('mac',{'compatible':b'mediatek,eth-mac\0','reg':struct.pack('>I',0)}),
            Node('radio',{'compatible':b'mediatek,mt76\0','ieee80211-freq-limit':struct.pack('>2I',2400000,2500000)})])
        factory=bytearray(b'\xff'*0x100000);factory[:2]=bytes.fromhex('1579');factory[0x7fff4:0x7fffa]=bytes.fromhex('020000000001')
        f=FDT(personalize(tree(root),factory,12345,True))
        self.assertEqual(f.node('/mac').props['local-mac-address'],bytes.fromhex('020000000001'))
        self.assertEqual(f.node('/radio').props['mediatek,eeprom-data'],factory[:0xe00])
        self.assertIn(b'maxcpus=1',f.node('/chosen').props['bootargs'])
        self.assertEqual(struct.unpack('>Q',f.node('/chosen').props['linux,initrd-end'])[0],0x52000000+12345)
        with self.assertRaises(ValueError):personalize(tree(root),factory[:1024])
    def test_config_roundtrip(self):
        # Synthetic format fixture; no vendor encryption parameters or real config.
        key=b'1'*64;iv=b'2'*32;cgi=b'fixture\0'+key+b'\0'+iv+b'\0'
        body=b'F'*16+b"uci set system.example='synthetic'\nuci commit\n"
        original=body+format(zlib.crc32(body),'08x').encode()+b'\n'
        encrypted=crypt(original,key,iv);modified=enable(encrypted,cgi)
        plain,_,_=decode(modified,cgi)
        self.assertTrue(plain.startswith(body));self.assertIn(b'TELNETS_ENABLED 1',plain)
        with self.assertRaises(ValueError):enable(encrypted[:-1],cgi)
    def test_ram_init(self):
        def entry(name,content,mode):
            n=name+b'\0';fields=[1,mode,0,0,1,0,len(content),0,0,0,0,len(n),0]
            b=b'070701'+b''.join(format(x,'08x').encode() for x in fields)+n
            b+=b'\0'*((-len(b))%4);b+=content;b+=b'\0'*((-len(b))%4);return b
        cpio=entry(b'etc/example',b'keep',0o100644)+entry(b'TRAILER!!!',b'',0)
        result=gzip.decompress(ram_cpio(gzip.compress(cpio),b'export INITRAMFS=1\n'))
        self.assertIn(b'etc/example',result);self.assertIn(b'keep',result)
        self.assertIn(b'export INITRAMFS=1',result);self.assertEqual(result.count(b'TRAILER!!!'),1)
if __name__=='__main__':unittest.main()
