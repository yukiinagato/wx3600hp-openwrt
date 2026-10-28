#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Interactive local Telnet shell using the credential from OWN stock clix ELF.

Firmware-specific, unencrypted LAN recovery transport. No credential is printed.
"""
import argparse, select, socket, sys, time, uuid
class Telnet:
    def __init__(self, host):
        self.sock = socket.create_connection((host, 23), timeout=5)
        self.sock.settimeout(0.5)
        self.buffer = bytearray()
        self.raw = bytearray()

    def _receive(self):
        try:
            data = self.sock.recv(65536)
        except socket.timeout:
            return
        if not data:
            raise EOFError('Telnet connection closed')
        self.raw.extend(data)
        pos = 0
        while pos < len(self.raw):
            if self.raw[pos] != 255:
                self.buffer.append(self.raw[pos])
                pos += 1
                continue
            if pos + 1 >= len(self.raw):
                break
            cmd = self.raw[pos+1]
            if cmd == 255:
                self.buffer.append(255)
                pos += 2
            elif cmd in (251, 252, 253, 254):
                if pos + 2 >= len(self.raw):
                    break
                opt = self.raw[pos+2]
                if cmd == 251:
                    self.sock.sendall(bytes([255, 254, opt]))
                elif cmd == 253:
                    self.sock.sendall(bytes([255, 252, opt]))
                pos += 3
            elif cmd == 250:
                end = self.raw.find(b'\xff\xf0', pos+2)
                if end < 0:
                    break
                pos = end+2
            else:
                pos += 2
        del self.raw[:pos]

    def until(self, marker, timeout=12):
        limit = time.monotonic() + timeout
        while marker not in self.buffer:
            if time.monotonic() >= limit:
                raise TimeoutError('Expected prompt absent; last output: ' + repr(bytes(self.buffer[-400:])))
            self._receive()
        end = self.buffer.index(marker) + len(marker)
        result = bytes(self.buffer[:end])
        del self.buffer[:end]
        return result

    def send(self, value):
        self.sock.sendall(value.replace(b'\xff', b'\xff\xff'))

    def line(self, value):
        self.send(value + b'\r\n')

    def close(self):
        self.sock.close()

    def command(self, command, timeout=30):
        marker = ('NEC_DONE_' + uuid.uuid4().hex).encode()
        self.line(command.encode() + b"; printf '\\n" + marker + b":%s\\n' \"$?\"")
        data = self.until(b'\r\n' + marker + b':', timeout)
        status = self.until(b'\r\n', 5).strip()
        return data[:-len(marker)-3], int(status)


def main():
    from elftools.elf.elffile import ELFFile
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host',required=True);p.add_argument('--stock-version',choices=['1.5.3'],required=True)
    p.add_argument('--clix',required=True)
    a=p.parse_args()
    with open(a.clix,'rb') as stream:
        elf=ELFFile(stream);ro=elf.get_section_by_name('.rodata')
        offset=0x407feb-ro['sh_addr']
        if not 0<=offset<len(ro.data()): raise SystemExit('Unsupported clix ELF')
        credential=ro.data()[offset:].split(b'\0',1)[0]
        if not 1<=len(credential)<=128: raise SystemExit('Unsupported console credential')
    tn=Telnet(a.host)
    tn.until(b'aterm login: ');tn.line(b'root')
    tn.until(b'Please enter your password : ');tn.line(credential)
    tn.until(b'Command> ');tn.line(b'z_shell')
    print('Connected to own device shell. Commands run as root; Ctrl-D exits.')
    while True:
        readable,_,_=select.select([tn.sock,sys.stdin],[],[],1)
        if tn.sock in readable:
            tn._receive();sys.stdout.buffer.write(tn.buffer);sys.stdout.buffer.flush();tn.buffer.clear()
        if sys.stdin in readable:
            line=sys.stdin.buffer.readline()
            if not line: break
            tn.line(line.rstrip(b'\r\n'))
    tn.close()
if __name__=='__main__': main()
