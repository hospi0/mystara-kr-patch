# -*- coding: utf-8 -*-
r"""MT 프레임워크 PS3 ARC v8(«\0CRA», 큰 끝) 풀기·묶기 (2026-11-14 gui.arc).
  머리 8 B(magic·ver u16·수 u16) + 항목 80 B(이름 64 · 형식 해시 · 압축 크기 · 풀린 크기×8(하위 3비트 플래그) · 오프셋), 데이터 = zlib.
  entries(path) → [(이름, 해시, 데이터 bytes, 플래그)] · pack(src, dst, {이름: 새 데이터})"""
import struct, zlib
def entries(path):
    b = open(path, 'rb').read(); n = struct.unpack('>H', b[6:8])[0]; out = []
    for i in range(n):
        e = b[8 + i * 80:8 + i * 80 + 80]; name = e[:64].split(b'\0')[0].decode()
        th, cs, ds, off = struct.unpack('>IIII', e[64:80])
        raw = b[off:off + cs]
        try: data = zlib.decompress(raw)
        except zlib.error: data = raw                       # 압축 안 된 항목
        out.append((name, th, data, ds & 0xFF000000))
    return out
def pack(src, dst, repl):
    b = open(src, 'rb').read(); n = struct.unpack('>H', b[6:8])[0]
    hdr = bytearray(b[:8 + n * 80]); first = min(struct.unpack('>I', b[8 + i * 80 + 76:8 + i * 80 + 80])[0] for i in range(n))
    body = bytearray(); base = first
    pad = b[8 + n * 80:first]
    for i in range(n):
        e = 8 + i * 80; name = hdr[e:e + 64].split(b'\0')[0].decode()
        th, cs, ds, off = struct.unpack('>IIII', hdr[e + 64:e + 80])
        if name in repl:
            raw = repl[name]; c = zlib.compressobj(6, zlib.DEFLATED, 14); comp = c.compress(raw) + c.flush(); ds = (len(raw) << 3) | (ds & 7)   # 풀린 크기 = 크기×8(하위 3비트 플래그) · 창 16KB(원본 머리 6881) — 2026-11-14 로고 안 나옴 고침
        else: comp = b[off:off + cs]
        o = base + len(body); body += comp
        struct.pack_into('>IIII', hdr, e + 64, th, len(comp), ds, o)
    open(dst, 'wb').write(bytes(hdr) + pad + bytes(body))
