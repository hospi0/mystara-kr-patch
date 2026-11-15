# -*- coding: utf-8 -*-
r"""TOD 상자 함정·열쇠 말풍선 한글 (2026-11-15, 하스피 FBNeo 대조로 찾음)
  · 그림 = dd10 16x16 타일(128 B, 4bpp 아래 니블 = 왼쪽). 조립 기록 = EBOOT 0x1675EC~0x168070 «2000 FFFF id (타일, 속성)…»
    속성: 가로 칸 (a>>8&15)+1 · 세로 칸 (a>>12)+1 · 0x20 좌우 뒤집기. 테두리 칸 8C21(세로)·8C30(모서리)은 공용이라 안 건드림.
  · «！» 칸 8C23·8C27 은 여러 말풍선이 같이 씀 → 그대로.
  · 꼴: 바탕 0 · 테두리·글자 A(10) · 번짐 1~5. 글자 칸 안 위·아래 테두리 줄(0행·31행)과 세로 테두리 열은 남기고 안쪽 비움 → 원래 글자 잉크 가운데에 갈무리11(1px).
  python tools/tod_balloons.py            → 미리보기 work/report1115/tod_balloons_<n>/ (원본 위·한글 아래)
  apply(dd10 bytearray, log)"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
from bdf import Font
GAL = r'C:\claude\utils\font\Galmuri-v2.40.3\%s.bdf'
INK, BG = 10, 0
# (이름, 화면 순서 칸 묶음[(시작 타일, 가로 칸)], 줄들, 글꼴)
BALLOONS = [
    ('석화', [(0x8C02, 2)], ['석화'], 'Galmuri11'),
    ('낙석', [(0x8C08, 3)], ['낙석'], 'Galmuri11'),
    ('불', [(0x8C0B, 1)], ['불'], 'Galmuri11'),
    ('화살', [(0x8C22, 1)], ['화살'], 'Galmuri11-Condensed'),
    ('가스', [(0x8C24, 3)], ['가스'], 'Galmuri11'),
    ('잠겨있다', [(0x8C01, 1), (0x87A0, 4), (0x93DB, 1)], ['열쇠가', '잠겨 있다.'], 'Galmuri11'),
]


def tile(g, k):
    a = np.frombuffer(bytes(g[k * 128:k * 128 + 128]), np.uint8); p = np.empty(256, np.uint8); p[0::2] = a & 15; p[1::2] = a >> 4
    return p.reshape(16, 16)


def put(g, k, img):
    f = img.reshape(-1).astype(np.uint8); g[k * 128:k * 128 + 128] = bytes((f[0::2] & 15) | ((f[1::2] & 15) << 4))


def strip(g, parts):
    return np.hstack([np.vstack([np.hstack([tile(g, b + i + 16 * j) for i in range(w)]) for j in range(2)]) for b, w in parts])


def render_line(text, font):
    f = Font(GAL % font)
    pts, w = f.draw(text)
    ref, _ = f.draw('가'); top = min(y for _, y in ref)
    xs = [p[0] for p in pts]; x0 = min(xs)
    W_ = max(xs) - x0 + 1
    a = np.zeros((12, W_), bool)
    for x, y in pts:
        yy = y - top
        if 0 <= yy < 12: a[yy, x - x0] = True
    return a


def build(g0, parts, lines, font):
    s = strip(g0, parts).copy(); H, W = s.shape
    inner = s[1:H - 1]
    vcols = [x for x in range(W) if (inner[:, x] == INK).all()]          # 세로 테두리 열
    ink = (s != BG); ink[0, :] = False; ink[H - 1, :] = False; ink[:, vcols] = False
    ys, xs = np.nonzero(ink)
    lo = (min(vcols) + 1) if vcols and min(vcols) < W // 2 else 0
    hi = (max(vcols)) if vcols and max(vcols) >= W // 2 else W
    keep = np.zeros_like(ink)                                            # 테두리 근처(세로 테두리 ±1 열, 위·아래 2줄)는 그대로
    keep[:2, :] = True; keep[H - 2:, :] = True
    for v in vcols: keep[:, max(0, v - 1):v + 2] = True
    s[ink & ~keep] = BG
    rs = [render_line(t, font) for t in lines]
    if len(rs) == 1:
        cy = (ys.min() + ys.max() + 1) // 2 if len(ys) else H // 2
        tops = [cy - 6]
    else:
        tops = [3, 17]
    cx = (xs.min() + xs.max() + 1) // 2 if len(xs) else (lo + hi) // 2
    over = []
    for r, ty in zip(rs, tops):
        h, w = r.shape
        room = (hi - lo) if not vcols else (hi - lo - 2)
        if w > room: over.append((w, room))
        x0 = (min(max(lo + (1 if vcols else 0), cx - w // 2), hi - (1 if vcols else 0) - w)) if len(rs) == 1 else lo + 2
        sub = s[ty:ty + h, x0:x0 + w]; sub[r[:sub.shape[0], :sub.shape[1]]] = INK
    return s, over


def apply(g, log=print):
    g0 = bytes(g); over = []
    for name, parts, lines, font in BALLOONS:
        s, o = build(g0, parts, lines, font)
        if o: over.append((name, o))
        x = 0
        for b, w in parts:
            for j in range(2):
                for i in range(w): put(g, b + i + 16 * j, s[16 * j:16 * j + 16, x + 16 * i:x + 16 * i + 16].copy())
            x += 16 * w
    log('TOD 말풍선 %d개 · 넘침 %s' % (len(BALLOONS), over))
    return over


def preview():
    from PIL import Image
    g0 = open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd10.bin'), 'rb').read()
    g = bytearray(g0); over = apply(g, print)
    n = 1
    while os.path.exists(os.path.join(ROOT, 'work', 'report1115', 'tod_balloons_%d' % n)): n += 1
    od = os.path.join(ROOT, 'work', 'report1115', 'tod_balloons_%d' % n); os.makedirs(od)
    lut = np.zeros((16, 3), np.uint8); lut[:] = (90, 90, 90); lut[0] = (17, 17, 17); lut[10] = (255, 238, 238)
    for k, c in zip((1, 2, 3, 4, 5), (60, 90, 120, 160, 200)): lut[k] = (c, c, c)
    rows = []
    for name, parts, lines, font in BALLOONS:
        a = strip(g0, parts); b = strip(g, parts)
        pad = lambda m: np.pad(m, ((0, 0), (0, 96 - m.shape[1])), constant_values=15) if m.shape[1] < 96 else m
        rows += [lut[pad(a)], lut[pad(b)], np.full((4, 96, 3), 40, np.uint8)]
    im = Image.fromarray(np.vstack(rows)).resize((96 * 5, sum(r.shape[0] for r in rows) * 5), Image.NEAREST)
    p = os.path.join(od, 'TOD말풍선_원본위_한글아래.png'); im.save(p); print(p)


if __name__ == '__main__':
    preview()
