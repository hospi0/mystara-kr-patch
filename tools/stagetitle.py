# -*- coding: utf-8 -*-
r"""SOM 무대 제목 스프라이트 레코드(EBOOT 0x511600~) 읽기·그리기 (2026-11-13).
  레코드 = 0002 · X · Y · 4000 · 0162 PPPP(32비트 VA) · [타일(16), 속성(16)]… — 속성 상위 바이트 = (세로 블록−1)<<4 | (가로 블록−1), 하위 = 색.
  타일 = dd22 16x16 번호(스프라이트 코드 − 0x9000). 블록은 차례로 가로로 이어 붙음(가정, 그림으로 확인).
  python tools/stagetitle.py → work/ring/stage_recs.json · work/ring/stage_recs.png"""
import os, sys, struct, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import ps3gfx
def parse(e, lo=0x511600, hi=0x512400):
    W = lambda o: struct.unpack('>H', e[o:o + 2])[0]
    recs = []; o = lo
    while o < hi:
        if W(o) == 0x0002 and W(o + 6) == 0x4000 and W(o + 8) == 0x0162:
            blocks = []; p = o + 12
            while 0x6000 <= W(p) < 0x7000 and (W(p + 2) & 0xFF) < 0x20:
                a = W(p + 2); blocks.append((W(p), (a >> 8 & 15) + 1, (a >> 12) + 1, a & 0xFF)); p += 4
            recs.append(dict(at=o, x=W(o + 2), y=W(o + 4), blocks=blocks)); o = p
        else: o += 2
    return recs
def block_img(g, t, nx, ny):
    a = np.zeros((16 * ny, 16 * nx), np.uint8)
    for j in range(ny):
        for i in range(nx): a[16 * j:16 * j + 16, 16 * i:16 * i + 16] = ps3gfx.tile(g, t + i + 16 * j)
    return a
def rec_img(g, r):
    parts = [block_img(g, t, nx, ny) for t, nx, ny, c in r['blocks']]
    H = max(p.shape[0] for p in parts)
    return np.hstack([np.pad(p, ((0, H - p.shape[0]), (0, 1)), constant_values=15) for p in parts])
def main():
    from PIL import Image, ImageDraw
    e = open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read()
    g = open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd22.bin'), 'rb').read()
    recs = [r for r in parse(e) if r['blocks']]
    json.dump(recs, open(os.path.join(ROOT, 'work', 'ring', 'stage_recs.json'), 'w'))
    pal = np.full(16, 90, np.uint8); pal[0] = 255; pal[14] = 20; pal[15] = 45
    imgs = [rec_img(g, r) for r in recs]
    s = 2; Wd = max(i.shape[1] for i in imgs) * s + 80
    H = sum(i.shape[0] * s + 6 for i in imgs)
    im = Image.new('L', (Wd, H), 25); d = ImageDraw.Draw(im); y = 0
    for k, (r, a) in enumerate(zip(recs, imgs)):
        d.text((2, y + 4), '%d %X' % (k, r['at']), fill=255)
        im.paste(Image.fromarray(pal[a]).resize((a.shape[1] * s, a.shape[0] * s), 0), (80, y)); y += a.shape[0] * s + 6
    im.save(os.path.join(ROOT, 'work', 'ring', 'stage_recs.png')); print(len(recs), im.size)
if __name__ == '__main__':
    main()
