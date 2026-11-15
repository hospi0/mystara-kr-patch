# -*- coding: utf-8 -*-
r"""TOD 열쇠 HUD «カギ=01» → «열쇠=01» (2026-11-15, 하스피 «열쇠은»)
  · dd11x 8x8 칸(64 B 중 앞 32 B): 0x27C3·0x27C4 = カ·ギ(화면 쓰는 줄, 앞 0x27C1·C2 = 열쇠 그림, 0x27C5 = «=»)
    같은 꼴 다른 벌 0x2780·0x2781, 0x27B1·0x27B2 (영문 KEY 줄 0x27E0~ 은 그대로).
  · 원본 꼴 = 획 색(0 또는 2) 0~6행 + 8방향 1px 테두리 E, 바탕 F. 글꼴 = 갈무리7(한글 7줄).
  python tools/key_hud.py               → 미리보기 work/report1115/key_hud_preview_<n>.png (원본 위, 한글 아래)
  apply(dd11x bytearray, log)"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
from bdf import Font

SETS = [0x2780, 0x27B1, 0x27C3]   # 두 칸씩(カ·ギ)
TEXT = '열쇠'


def t8(g, k):
    b = np.frombuffer(bytes(g[k * 64:k * 64 + 32]), np.uint8); p = np.empty(64, np.uint8); p[0::2] = b & 15; p[1::2] = b >> 4
    return p.reshape(8, 8)


def put8(g, k, a):
    f = a.reshape(-1).astype(np.uint8); g[k * 64:k * 64 + 32] = bytes((f[0::2] & 15) | ((f[1::2] & 15) << 4))


def render(stroke):
    f = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf')
    ref, _ = f.draw('가'); top = min(y for _, y in ref)
    ink = np.zeros((8, 16), bool); x0 = 0
    for ch in TEXT:
        pts, w = f.draw(ch)
        xs = [p[0] for p in pts]; dx = 8 * TEXT.index(ch) + max(0, (7 - (max(xs) - min(xs) + 1)) // 2) + 1 - min(xs)
        for x, y in pts:
            yy = y - top
            if 0 <= yy <= 6 and 0 <= x + dx < 16: ink[yy, x + dx] = True
    ol = np.zeros_like(ink)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            sh = np.roll(np.roll(ink, dy, 0), dx, 1)
            if dy == 1: sh[0, :] = False
            if dy == -1: sh[-1, :] = False
            if dx == 1: sh[:, 0] = False
            if dx == -1: sh[:, -1] = False
            ol |= sh
    a = np.full((8, 16), 15, np.uint8); a[ol & ~ink] = 14; a[ink] = stroke
    return a


def apply(g, log=print):
    for base in SETS:
        o = np.hstack([t8(g, base), t8(g, base + 1)])
        stroke = int([v for v in o.ravel() if v not in (14, 15)][0])
        a = render(stroke)
        put8(g, base, a[:, :8]); put8(g, base + 1, a[:, 8:])
    log('열쇠 HUD «%s=» %d벌' % (TEXT, len(SETS)))


def preview():
    from PIL import Image
    g0 = open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd11x.bin'), 'rb').read()
    g = bytearray(g0); apply(g, lambda *_: None)
    pal = {0: (68, 170, 255), 2: (68, 170, 255), 14: (17, 17, 17), 15: (68, 68, 51)}
    def rgb(a):
        o = np.zeros(a.shape + (3,), np.uint8); o[:] = (120, 120, 120)
        for v, c in pal.items(): o[a == v] = c
        return o
    rows = []
    for base in SETS:
        for src in (g0, g):
            rows.append(rgb(np.hstack([t8(src, base - 2), t8(src, base - 1), t8(src, base), t8(src, base + 1), t8(src, base + 2)])))
        rows.append(np.zeros((3, 40, 3), np.uint8))
    im = Image.fromarray(np.vstack(rows)).resize((40 * 10, sum(r.shape[0] for r in rows) * 10), Image.NEAREST)
    n = 1
    while os.path.exists(os.path.join(ROOT, 'work', 'report1115', 'key_hud_preview_%d.png' % n)): n += 1
    p = os.path.join(ROOT, 'work', 'report1115', 'key_hud_preview_%d.png' % n); im.save(p); print(p)


if __name__ == '__main__':
    preview()
