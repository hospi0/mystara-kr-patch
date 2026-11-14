# -*- coding: utf-8 -*-
r"""함정 말풍선(dd22 16x16 0x4BC0~0x4BFF, 16칸×4줄 판) 일본어 글자 → 한글 (2026-11-13).
  말풍선 조합(스프라이트) 몰라도 되게: 일본어 글자가 있던 상자 안에서만 지우고 같은 상자 안에 한글. 테두리·«!»·영문판 말풍선은 그대로.
  글자 = 색 10(흰) 1px, 바탕 0. 글꼴 = 갈무리11 BDF.
  python tools/trap_balloons.py [dd22 입력] [출력] → work/ring/preview/trap.png(원본|한글)"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import ps3gfx
from bdf import Font
LO = 0x4BC0
# (지울 상자 x0,y0,x1,y1 판 좌표, 한글, 정렬) — 상자 = 원문 글자 범위 + 1px
BOXES = [((79, 9, 128, 22), '석화살', 'c80'),   # 게임 말풍선은 판 x 80~111 만 보임(«석화화살» → «석화호» 로 잘림, 2026-11-14) — 좁은 판 글꼴
         ((156, 9, 188, 22), '낙석', 'c'),
         ((65, 26, 80, 39), '불', 'c'),
         ((221, 27, 251, 38), '가스', 'c'),
         ((6, 34, 52, 47), '잠겨', 'l'),
         ((6, 49, 65, 60), '있다.', 'l'),
         ((79, 33, 107, 45), '', 'c'),            # «る。» 조각 — 비움(2줄째 «있다.» 로 대신)
         ((119, 40, 161, 53), '열렸다', 'c')]
def load(b):
    return np.vstack([np.hstack([ps3gfx.tile(b, LO + r * 16 + k) for k in range(16)]) for r in range(4)])
def store(b, cv):
    for r in range(4):
        for k in range(16): ps3gfx.put(b, LO + r * 16 + k, cv[r * 16:(r + 1) * 16, k * 16:(k + 1) * 16].copy())
def render(font, text):
    pts, w = font.draw(text)
    if not pts: return np.zeros((1, 1), bool)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    a = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for x, y in pts: a[y - min(ys), x - min(xs)] = True
    return a
def border_mask(cv):
    ink = cv == 10; bm = np.zeros_like(ink)
    for y in range(ink.shape[0]):
        x = 0
        while x < ink.shape[1]:
            if ink[y, x]:
                s_ = x
                while x < ink.shape[1] and ink[y, x]: x += 1
                if x - s_ >= 18: bm[y, s_:x] = True
            else: x += 1
    for x in range(ink.shape[1]):
        y = 0
        while y < ink.shape[0]:
            if ink[y, x]:
                s_ = y
                while y < ink.shape[0] and ink[y, x]: y += 1
                if y - s_ >= 18: bm[s_:y, x] = True
            else: y += 1
    return bm
def apply(b):
    cv = load(bytes(b)); font = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'); over = []
    bm = border_mask(cv)
    for (x0, y0, x1, y1), txt, al in BOXES:
        reg = cv[y0:y1, x0:x1]; keep = bm[y0:y1, x0:x1] | (reg == 15)
        reg[~keep] = 0                       # 글자·번짐 화소 전부 바탕(0)으로 — 테두리·투명은 그대로
        if not txt: continue
        f_ = Font(os.path.join(r'C:\claude\utils\font\Galmuri-v2.40.3', 'Galmuri11-Condensed.bdf')) if al == 'c80' else font
        a = render(f_, txt); h, w = a.shape
        if w > x1 - x0 or h > y1 - y0: over.append((txt, w, h, x1 - x0, y1 - y0))
        a = a[:y1 - y0, :x1 - x0]; h, w = a.shape
        ox = x0 + ((x1 - x0 - w) // 2 if al == 'c' else 1); oy = y0 + (y1 - y0 - h) // 2
        if al == 'c80': ox = 80 + (32 - w) // 2
        sub = cv[oy:oy + h, ox:ox + w]; sub[a & ~bm[oy:oy + h, ox:ox + w]] = 10
    store(b, cv); return over
def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd22.bin')
    b0 = open(src, 'rb').read(); b = bytearray(b0)
    over = apply(b); print('넘침', over)
    if len(sys.argv) > 2: open(sys.argv[2], 'wb').write(b)
    from PIL import Image
    pal = np.zeros((16, 3), np.uint8); pal[:] = (90, 90, 90); pal[10] = (255, 255, 255); pal[0] = (0, 0, 0); pal[15] = (40, 40, 90)
    a = np.vstack([pal[load(b0)], np.full((4, 256, 3), 200, np.uint8), pal[load(bytes(b))]])
    Image.fromarray(a).resize((256 * 4, a.shape[0] * 4), 0).save(os.path.join(ROOT, 'work', 'ring', 'preview', 'trap_v4.png'))
if __name__ == '__main__':
    main()
