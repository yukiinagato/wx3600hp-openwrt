# SPDX-License-Identifier: GPL-2.0-only
"""Small FDT v17 reader/writer. Preserves existing property names' string offsets.

Only inline-data FIT is supported. No hardware access; rejects malformed trees.
"""
import struct
from dataclasses import dataclass, field
@dataclass
class Node:
    name: str
    props: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    def child(self, name):
        return next(n for n in self.children if n.name == name)
    def walk(self):
        yield self
        for n in self.children: yield from n.walk()
class FDT:
    def __init__(self, data):
        if len(data)<40: raise ValueError('Truncated FDT')
        h=struct.unpack_from('>10I',data)
        magic,total,off,strings,reserve,version,last,self.bootcpu,nstrings,nstruct=h
        if magic!=0xd00dfeed or version!=17 or last>17 or total>len(data):
            raise ValueError('Unsupported FDT header')
        if off+nstruct>total or strings+nstrings>total or reserve<40:
            raise ValueError('FDT bounds')
        end=reserve
        while end+16<=total:
            a,b=struct.unpack_from('>QQ',data,end);end+=16
            if a==b==0: break
        else: raise ValueError('No reservation terminator')
        self.reserve=data[reserve:end];self.strings=data[strings:strings+nstrings]
        self.root=None;stack=[];pos=off;limit=off+nstruct
        while pos+4<=limit:
            token=struct.unpack_from('>I',data,pos)[0];pos+=4
            if token==1:
                z=data.index(0,pos,limit);name=data[pos:z].decode('ascii');pos=(z+4)&~3
                n=Node(name)
                if stack: stack[-1].children.append(n)
                elif self.root is not None: raise ValueError('Multiple roots')
                else: self.root=n
                stack.append(n)
            elif token==2:
                if not stack: raise ValueError('Unbalanced end node')
                stack.pop()
            elif token==3:
                if not stack or pos+8>limit: raise ValueError('Invalid property')
                size,nameoff=struct.unpack_from('>II',data,pos);pos+=8
                if pos+size>limit or nameoff>=len(self.strings): raise ValueError('Property bounds')
                name=self.strings[nameoff:self.strings.index(0,nameoff)].decode('ascii')
                if name in stack[-1].props: raise ValueError('Duplicate property')
                stack[-1].props[name]=data[pos:pos+size];pos=(pos+size+3)&~3
            elif token==4: pass
            elif token==9:
                if stack or self.root is None: raise ValueError('Unbalanced tree')
                break
            else: raise ValueError('Invalid FDT token')
        else: raise ValueError('Missing FDT end token')
    def node(self,path):
        n=self.root
        for part in path.strip('/').split('/'):
            if part: n=n.child(part)
        return n
    def encode(self):
        strings=bytearray(self.strings);offsets={};pos=0
        while pos<len(strings):
            z=strings.index(0,pos);offsets.setdefault(strings[pos:z].decode('ascii'),pos);pos=z+1
        def word(v): return struct.pack('>I',v)
        def pad(b): return b+b'\0'*((-len(b))%4)
        def emit(n):
            b=word(1)+pad(n.name.encode()+b'\0')
            for k,v in n.props.items():
                if k not in offsets:
                    offsets[k]=len(strings);strings.extend(k.encode()+b'\0')
                b+=word(3)+word(len(v))+word(offsets[k])+pad(v)
            for c in n.children: b+=emit(c)
            return b+word(2)
        structure=emit(self.root)+word(9);ro=40;so=(ro+len(self.reserve)+7)&~7;st=so+len(structure)
        total=st+len(strings)
        header=struct.pack('>10I',0xd00dfeed,total,so,st,ro,17,16,self.bootcpu,len(strings),len(structure))
        return header+self.reserve+b'\0'*(so-ro-len(self.reserve))+structure+strings
