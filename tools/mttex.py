# -*- coding: utf-8 -*-
r"""MT 프레임워크 PS3 .tex(«\0XET» v0x9A, 큰 끝) 읽기 → PNG (2026-11-13 미스타라 옵션 그림).
  w2: 밉 수 = &0x3F · 폭 = >>6 &0x1FFF · 높이 = >>19 · w3>>8&0xFF 형식: 0x27 = RGBA8(ARGB 순) · 0x17 = DXT5 · 0x13 = DXT1 · w4 = 데이터 오프셋.
  python tools/mttex.py 파일.tex 출력.png"""
import struct, sys, io
import numpy as np
from PIL import Image
def info(d):
    w1, w2, w3, off = struct.unpack('>IIII', d[4:20])
    return dict(mip=w2 & 0x3F, W=(w2 >> 6) & 0x1FFF, H=(w2 >> 19) & 0x1FFF, fmt=(w3 >> 8) & 0xFF, off=off)
def dds(W, H, fourcc, data):
    hdr = struct.pack('<4sIIIIIII44sIII4s20sI16s', b'DDS ', 124, 0x1007, H, W, len(data), 0, 1, b'\0' * 44,
                      32, 4, 0, fourcc, b'\0' * 20, 0x1000, b'\0' * 16)
    return Image.open(io.BytesIO(hdr + data)).convert('RGBA')
def load(path):
    d = open(path, 'rb').read(); i = info(d); W, H, o = i['W'], i['H'], i['off']
    if i['fmt'] == 0x27:
        a = np.frombuffer(d[o:o + W * H * 4], np.uint8).reshape(H, W, 4)
        return Image.fromarray(a[:, :, [1, 2, 3, 0]].copy(), 'RGBA'), i
    if i['fmt'] in (0x17, 0x18, 0x19):
        return Image.frombytes('RGBA', (W, H), d[o:o + W * H], 'bcn', 3), i
    if i['fmt'] == 0x13:
        return Image.frombytes('RGBA', (W, H), d[o:o + W * H // 2], 'bcn', 1), i
    raise SystemExit('형식 %X' % i['fmt'])
if __name__ == '__main__':
    im, i = load(sys.argv[1]); print(i)
    bg = Image.new('RGBA', im.size, (60, 60, 90, 255)); bg.alpha_composite(im); bg.convert('RGB').save(sys.argv[2])
