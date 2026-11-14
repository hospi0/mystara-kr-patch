# -*- coding: utf-8 -*-
r"""이름 입력 돌판: 일본판(가나 6x10 + 버튼) → 영문판(FBNeo ddsoma 원본 화소) 새김 글자·버튼을 일본판 칸 배치로 (2026-11-13).
  입력: work/ring/nameent_clean.png(일본판 RPCS3, 필터 끔) · work/ring/fbneo_name.png(FBNeo 384x224, 색값 일본판과 같음)
        work/ring/grid_map2.json(일본판 화면 8x8 칸 → dd21x 타일·반전, 투명 무시 색 대응으로 찾음)
  1) 돌판 = 두 판 화소가 같으면 그대로, 가나 자리 = 영문판 화소, 둘 다 글자 = 이웃 돌판
  2) 영문 글자(경계 상자 중심 = 가나 칸 중심) · 버튼(SPACE·NAME·R/B·END 통째) 붙임
  3) 화면 색 → 돌판 팔레트 번호(대응 타일들에서 모음) → 칸 타일에 써 넣음(유일 대응 칸만, 빈칸은 좌우 연속 번호로 메움)
  python tools/name_grid_gfx.py [dd21x 입력 출력] → 미리보기 work/ring/preview/name_grid_fb7.png"""
import os, sys, json
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = lambda *p: os.path.join(ROOT, *p)
JP_ROWS = [62, 86, 109, 132, 157, 179]; JP_COLS = [59, 81, 102, 123, 145, 184, 207, 228, 250, 271]
EN_ROWS = [60, 85, 111, 136]; EN_COLS = [62 + 25 * k for k in range(11)]
EN = {}
for k, ch in enumerate('ABCDEFGHIJK'): EN[ch] = (0, k)
for k, ch in enumerate('LMNOPQRSTUV'): EN[ch] = (1, k)
for k, ch in enumerate('WXYZ?!&-'): EN[ch] = (2, k)
for k, ch in enumerate('1234567890'): EN[ch] = (3, k)
LAYOUT = ['ABCDE01234', 'FGHIJ56789', 'KLMNO.&_-!', 'PQRST.&_-!', 'UVWXY    ?', 'Z         ']
# 버튼: 영문판 상자(x0,y0,x1,y1) → 일본판 버튼 자리 왼위(5x2칸 = 40x16)
EN_BTN = [(128, 160, 166, 175), (176, 160, 212, 175), (224, 160, 260, 175), (270, 160, 307, 175)]
JP_BTN = [(312, 80), (312, 104), (312, 128), (312, 152)]
def native(path, rpcs3):
    a = np.array(Image.open(path).convert('RGB')).astype(np.int64)
    if rpcs3: a = np.array([[a[int(72 + (y + 0.5) * 576 / 224), 256 + 2 * x] for x in range(384)] for y in range(224)])
    return (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
def boxmask(shape, centers, r=8):
    m = np.zeros(shape, bool)
    for cx, cy in centers: m[cy - r:cy + r + 1, cx - r:cx + r + 1] = True
    return m
BRIGHT = {0xeeeeff, 0xffffff, 0xddddee, 0xccccdd, 0xbbbbcc}
ORANGE = {0xffaa00: 0xffffff, 0xff8800: 0xeeeeff, 0xff6600: 0xddddee, 0xff5500: 0xccccdd}   # 커서 글자색 → 흰 새김색
def bbox(K, cx, cy, r=10, pad=2):
    """칸 중심 둘레 밝은 획(흰·커서 주황) 중 «중심 6px 안에 닿는 덩어리»(3px 틈까지 이음)의 경계 상자 + pad"""
    sub = K[cy - r:cy + r + 1, cx - r:cx + r + 1]
    m = np.isin(sub, list(BRIGHT | set(ORANGE)))
    n = 2 * r + 1; lab = np.zeros((n, n), int); k = 0
    for y, x in zip(*np.nonzero(m)):
        if lab[y, x]: continue
        k += 1; st = [(y, x)]; lab[y, x] = k
        while st:
            a, b = st.pop()
            for dy in range(-3, 4):
                for dx in range(-3, 4):
                    yy, xx = a + dy, b + dx
                    if 0 <= yy < n and 0 <= xx < n and m[yy, xx] and not lab[yy, xx]: lab[yy, xx] = k; st.append((yy, xx))
    keep = set(int(v) for v in np.unique(lab[r - 6:r + 7, r - 6:r + 7]) if v)
    ys, xs = np.nonzero(np.isin(lab, list(keep)))
    if not len(ys): return None
    return (cx - r + xs.min() - pad, cy - r + ys.min() - pad, cx - r + xs.max() + pad + 1, cy - r + ys.max() + pad + 1)
LETTER = BRIGHT | set(ORANGE) | {0x111122, 0x111133, 0x112244, 0x222233, 0x550000}
def main():
    J = native(R('work', 'ring', 'nameent_clean.png'), True); F = native(R('work', 'ring', 'fbneo_name.png'), False)
    jr = np.zeros(J.shape, bool); er = np.zeros(J.shape, bool)
    jb = {}; eb = {}
    for r, y in enumerate(JP_ROWS):
        for c, x in enumerate(JP_COLS):
            bb = bbox(J, x, y)
            if bb: jb[r, c] = bb; jr[bb[1]:bb[3], bb[0]:bb[2]] = True
    for ch, (r, k) in EN.items():
        bb = bbox(F, EN_COLS[k], EN_ROWS[r])
        if bb: eb[ch] = bb; er[bb[1]:bb[3], bb[0]:bb[2]] = True
    btn = np.zeros(J.shape, bool)
    for x0, y0, x1, y1 in EN_BTN: btn[y0 - 2:y1 + 2, x0 - 2:x1 + 2] = True   # 영문 버튼 자리 = 영문판 화소 못 씀
    btn[156:177, 55:122] = True                                                  # 영문판 Ⅰ Ⅱ Ⅲ 줄
    # 1) 깨끗한 돌판: 가나 상자 = 영문판 화소(그 자리에 영문 글자 없으면), 둘 다면 가장 가까운 깨끗한 화소
    clean = J.copy(); take = jr & ~er & ~btn; clean[take] = F[take]
    both = jr & (er | btn)
    for y, x in zip(*np.nonzero(both)):
        jv, fv = int(J[y, x]), int(F[y, x])
        if not btn[y, x] and (jv == fv or (jv in LETTER) != (fv in LETTER)):
            clean[y, x] = fv if jv in LETTER else jv; both[y, x] = False
    if both.any():                                    # 두 판 다 글자인 화소 = 둘레 돌판으로 메움(inpaint) → 돌판에 있는 색으로 맞춤
        import cv2
        img = np.stack([(clean >> 16) & 255, (clean >> 8) & 255, clean & 255], -1).astype(np.uint8)
        fill = cv2.inpaint(img, both.astype(np.uint8), 3, cv2.INPAINT_TELEA).astype(np.int64)
        stone = np.unique(J[60:190, 60:300][~jr[60:190, 60:300]])
        sr = np.stack([(stone >> 16) & 255, (stone >> 8) & 255, stone & 255], -1)
        for y, x in zip(*np.nonzero(both)):
            d = ((sr - fill[y, x]) ** 2).sum(1); clean[y, x] = stone[d.argmin()]
    out = clean.copy()
    # 2) 영문 글자: 상자 안에서 돌판과 다른 화소만, 상자 중심 = 가나 상자 중심(없으면 칸 중심)
    for r, row in enumerate(LAYOUT):
        for c, ch in enumerate(row):
            if ch == '.' and '!' in eb:                      # 。 = 영문 «!» 아래 점
                x0, y0, x1, y1 = eb['!']; y0 = y1 - 5
                ox = JP_COLS[c] - (x0 + x1) // 2; oy = JP_ROWS[r] + 8 - y1
                for y in range(y0, y1):
                    for x in range(x0, x1):
                        if F[y, x] != clean[y, x]: out[y + oy, x + ox] = F[y, x]
                continue
            if ch not in eb: continue
            x0, y0, x1, y1 = eb[ch]
            if (r, c) in jb: tx0, ty0, tx1, ty1 = jb[r, c]; tcx, tcy = (tx0 + tx1) // 2, (ty0 + ty1) // 2
            else: tcx, tcy = JP_COLS[c], JP_ROWS[r]
            ox, oy = tcx - (x0 + x1) // 2, tcy - (y0 + y1) // 2
            for y in range(y0, y1):
                for x in range(x0, x1):
                    v = int(F[y, x])
                    if v == int(clean[y, x]): continue
                    if v in ORANGE: v = ORANGE[v]
                    elif ch == 'A' and v not in BRIGHT and v not in (0x111133, 0x111122, 0x112244, 0x222233, 0x550000): continue
                    if v == 0x550000: v = 0x111122
                    out[y + oy, x + ox] = v
    # 3) 버튼(통째): 영문판 상자 안 돌판과 다른 화소
    for (x0, y0, x1, y1), (jx, jy) in zip(EN_BTN, JP_BTN):
        w, h = x1 - x0, y1 - y0
        ox, oy = jx + (40 - w) // 2 - x0, jy + (16 - h) // 2 - y0
        for y in range(y0, y1):
            for x in range(x0, x1):
                if F[y, x] != J[y, x]: out[y + oy, x + ox] = F[y, x]
    np.save(R('work', 'ring', 'name_grid_rgb.npy'), out)
    rgb = lambda k: np.stack([(k >> 16) & 255, (k >> 8) & 255, k & 255], -1).astype(np.uint8)
    a = np.hstack([rgb(J), np.zeros((224, 4, 3), np.uint8), rgb(out)])[44:196, 36:]
    Image.fromarray(a).resize((a.shape[1] * 3, a.shape[0] * 3), 0).save(R('work', 'ring', 'preview', 'name_grid_fb7.png'))
    if len(sys.argv) > 2: write_tiles(J, out, sys.argv[1], sys.argv[2])
def write_tiles(J, out, src, dst):
    m = json.load(open(R('work', 'ring', 'grid_map2.json')))
    raw = bytearray(open(src, 'rb').read())
    p = np.empty(len(raw) * 2, np.uint8); a = np.frombuffer(bytes(raw), np.uint8); p[0::2] = a & 15; p[1::2] = a >> 4
    T8 = p.reshape(-1, 16, 8)
    flip = {'n': lambda t: t, 'x': lambda t: t[:, ::-1], 'y': lambda t: t[::-1, :], 'xy': lambda t: t[::-1, ::-1]}
    pal = {}
    for k, v in m.items():
        if len(v) != 1: continue
        x, y = map(int, k.split(',')); t, fl = v[0]
        tt = flip[fl](T8[t, :8]); w = J[y:y + 8, x:x + 8]
        for i, c in zip(tt.reshape(-1), w.reshape(-1)):
            if i != 15: pal.setdefault(int(c), int(i))
    changed = 0; miss = 0
    for k, v in m.items():
        x, y = map(int, k.split(','))
        if (out[y:y + 8, x:x + 8] == J[y:y + 8, x:x + 8]).all(): continue
        if len(v) != 1: miss += 1; continue
        t, fl = v[0]
        tt = flip[fl](T8[t, :8]).copy(); w = out[y:y + 8, x:x + 8]
        for yy in range(8):
            for xx in range(8):
                c = int(w[yy, xx])
                if tt[yy, xx] == 15 and c == int(J[y + yy, x + xx]): continue
                if c in pal: tt[yy, xx] = pal[c]
        tt = flip[fl](tt)
        o = t * 64; nib = tt.reshape(-1)
        raw[o:o + 32] = bytes((nib[0::2] & 15) | ((nib[1::2] & 15) << 4)); changed += 1
    open(dst, 'wb').write(raw); print('타일 바꿈', changed, '대응 없어 못 바꾼 칸', miss)
if __name__ == '__main__':
    main()
