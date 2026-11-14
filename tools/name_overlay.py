# -*- coding: utf-8 -*-
r"""이름 입력 돌판 = 바탕 돌층(일·영 같음) + 글자층(dd21x 8x8 반투명 타일: 일본 0x2983~0x2B9B, 영문 0x2B9F~0x2D5D) (2026-11-14).
  화면 8x8 칸마다 글자층 타일 대응: 불투명 화소의 «번호→색»이 일관되고 불투명 화소가 가장 많은 후보.
  python tools/name_overlay.py map → work/ring/ovl_JP.json · ovl_EN.json"""
import os, sys, json
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = lambda *p: os.path.join(ROOT, *p)
RANGE = {'JP': (0x2983, 0x2B9C), 'EN': (0x2B9C, 0x2D5E)}
def T8(path=None):
    raw = np.frombuffer(open(path or R('work', 'orig', 'game_data', 'dd21x.bin'), 'rb').read(), np.uint8)
    p = np.empty(raw.size * 2, np.uint8); p[0::2] = raw & 15; p[1::2] = raw >> 4
    return p.reshape(-1, 16, 8)[:, :8]
def screen(which):
    if which == 'JP':
        a = np.array(Image.open(R('work', 'ring', 'nameent_clean.png')).convert('RGB')).astype(np.int64)
        a = np.array([[a[int(72 + (y + 0.5) * 576 / 224), 256 + 2 * x] for x in range(384)] for y in range(224)])
    else:
        a = np.array(Image.open(R('work', 'ring', 'fbneo_name.png')).convert('RGB')).astype(np.int64)
    return (a[..., 0] << 16) | (a[..., 1] << 8) | a[..., 2]
FL = {'n': lambda t: t, 'x': lambda t: t[:, ::-1], 'y': lambda t: t[::-1], 'xy': lambda t: t[::-1, ::-1]}
def fits(tt, w):
    op = tt != 15
    if op.sum() < 3: return -1
    f = {}
    for i, c in zip(tt[op].tolist(), w[op].tolist()):
        if f.setdefault(i, c) != c: return -1
    return int(op.sum())
def build_map(which):
    T = T8(); K = screen(which); lo, hi = RANGE[which]; res = {}
    cand = [(t, fl, FL[fl](T[t])) for t in range(lo, hi) for fl in FL]
    for y in range(40, 200, 8):
        for x in range(32, 320, 8):
            w = K[y:y + 8, x:x + 8]; sc = []
            for t, fl, tt in cand:
                s = fits(tt, w)
                if s > 0: sc.append((s, t, fl))
            sc.sort(reverse=True)
            res['%d,%d' % (x, y)] = sc[:4]
    json.dump(res, open(R('work', 'ring', 'ovl_%s.json' % which), 'w'))
    top = [v for v in res.values() if v]
    clear = sum(1 for v in top if len(v) == 1 or v[0][0] > v[1][0])
    print(which, '후보 있는 칸', len(top), '1등이 단독', clear)
if __name__ == '__main__':
    build_map(sys.argv[2] if len(sys.argv) > 2 else 'EN')

def palette_of(which):
    """불투명 40화소 넘는 단독 1등 칸들에서 «번호→색» 투표 → 전역 팔레트"""
    m = json.load(open(R('work', 'ring', 'ovl_%s.json' % which))); T = T8(); K = screen(which)
    votes = {}
    for k, v in m.items():
        if not v or v[0][0] < 40 or (len(v) > 1 and v[1][0] == v[0][0]): continue
        x, y = map(int, k.split(',')); s, t, fl = v[0]; tt = FL[fl](T[t]); w = K[y:y + 8, x:x + 8]
        for i, c in zip(tt.reshape(-1).tolist(), w.reshape(-1).tolist()):
            if i != 15: votes.setdefault(i, {}).setdefault(c, 0); votes[i][c] += 1
    return {i: max(d, key=d.get) for i, d in votes.items()}, votes
def remap(which):
    pal, votes = palette_of(which)
    T = T8(); K = screen(which); lo, hi = RANGE[which]; res = {}
    cand = [(t, fl, FL[fl](T[t])) for t in range(lo, hi) for fl in FL]
    P = np.full(16, -1, np.int64)
    for i, c in pal.items(): P[i] = c
    for y in range(40, 200, 8):
        for x in range(32, 320, 8):
            w = K[y:y + 8, x:x + 8]; sc = []
            for t, fl, tt in cand:
                op = tt != 15
                if op.sum() == 0: continue
                if (P[tt[op]] == w[op]).all(): sc.append((int(op.sum()), t, fl))
            sc.sort(reverse=True); res['%d,%d' % (x, y)] = sc[:6]
    json.dump(res, open(R('work', 'ring', 'ovl2_%s.json' % which), 'w'))
    top = [v for v in res.values() if v]
    print(which, '팔레트', {i: '%06x' % c for i, c in sorted(pal.items())})
    print(which, '후보 있는 칸', len(top), '1등 단독', sum(1 for v in top if len(v) == 1 or v[0][0] > v[1][0]))

BASE = {0: 0x112233, 2: 0x333344, 3: 0x334455, 4: 0x445566, 5: 0x556666, 7: 0xccddee, 8: 0x111122, 9: 0x555566,
        10: 0xbbbbcc, 11: 0xccccdd, 12: 0xddddee, 13: 0xeeeeff, 14: 0xffffff}
PALS = {'A': {**BASE, 1: 0x222233, 6: 0x667777}, 'B': {**BASE, 1: 0x223344, 6: 0xbbccdd},
        'C': {**BASE, 1: 0x222233, 6: 0x667777, 8: 0x550000, 9: 0x990000, 10: 0xff3300, 11: 0xff5500, 12: 0xff6600, 13: 0xff8800, 14: 0xffaa00}}   # C = 커서(그 칸 팔레트만 바뀜)
def remap2(which):
    T = T8(); K = screen(which); lo, hi = RANGE[which]; res = {}
    cand = [(t, fl, FL[fl](T[t])) for t in range(lo, hi) for fl in FL]
    PP = {}
    for n, d in PALS.items():
        P = np.full(16, -1, np.int64)
        for i, c in d.items(): P[i] = c
        PP[n] = P
    for y in range(16, 200, 8):
        for x in range(32, 368, 8):
            w = K[y:y + 8, x:x + 8]; sc = []
            for t, fl, tt in cand:
                op = tt != 15
                if op.sum() == 0: continue
                for n, P in PP.items():
                    if (P[tt[op]] == w[op]).all(): sc.append((int(op.sum()), t, fl, n)); break
            sc.sort(reverse=True); res['%d,%d' % (x, y)] = sc[:6]
    json.dump(res, open(R('work', 'ring', 'ovl3_%s.json' % which), 'w'))
    top = [v for v in res.values() if v]
    print(which, '후보 있는 칸', len(top), '1등 단독', sum(1 for v in top if len(v) == 1 or v[0][0] > v[1][0]))

def overlay_img(which, path=None):
    """대응표대로 글자층만 다시 그림 → (색 번호 화면, 팔레트 이름 화면) — 투명 = 15"""
    m = json.load(open(R('work', 'ring', 'ovl3_%s.json' % which))); T = T8(path)
    idx = np.full((224, 384), 15, np.uint8); pn = np.full((224, 384), '', object)
    for k, v in m.items():
        if not v: continue
        x, y = map(int, k.split(',')); s, t, fl, n = v[0]
        idx[y:y + 8, x:x + 8] = FL[fl](T[t]); pn[y:y + 8, x:x + 8] = n
    return idx, pn
def show(which):
    idx, pn = overlay_img(which); K = screen(which)
    rgb = np.zeros((224, 384, 3), np.uint8); rgb[:] = (200, 60, 200)
    for n, d in PALS.items():
        for i, c in d.items():
            sel = (idx == i) & (pn == n); rgb[sel] = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
    scr = np.stack([(K >> 16) & 255, (K >> 8) & 255, K & 255], -1).astype(np.uint8)
    a = np.hstack([scr, np.zeros((224, 4, 3), np.uint8), rgb])[40:200]
    Image.fromarray(a).resize((a.shape[1] * 2, a.shape[0] * 2), 0).save(R('work', 'ring', 'preview', 'ovl_%s.png' % which))

def full_map(which, xr=(32, 320), idr=None):
    """기준점(확실한 1등, 반전 없음, 번호 증가 유지) 사이를 «래스터 순서 = 번호 순서»로 동적 계획 배정 → {(x,y): 타일}"""
    m = json.load(open(R('work', 'ring', 'ovl3_%s.json' % which))); T = T8(); K = screen(which)
    cells = [(x, y) for y in range(16, 200, 8) for x in range(xr[0], xr[1], 8)]
    lo, hi = idr or RANGE[which]
    anc = []
    for i, (x, y) in enumerate(cells):
        v = m['%d,%d' % (x, y)]
        if v and v[0][0] >= 6 and v[0][2] == 'n' and lo <= v[0][1] < hi and (len(v) == 1 or v[0][0] > v[1][0]): anc.append((i, v[0][1]))
    # 번호가 증가하는 가장 긴 부분열(LIS)만 기준점으로
    import bisect
    best = []; prev = [-1] * len(anc); tails = []; tidx = []
    for k, (i, t) in enumerate(anc):
        p = bisect.bisect_left(tails, t)
        if p == len(tails): tails.append(t); tidx.append(k)
        else: tails[p] = t; tidx[p] = k
        prev[k] = tidx[p - 1] if p else -1
    k = tidx[-1]; seq = []
    while k >= 0: seq.append(anc[k]); k = prev[k]
    seq.reverse()
    out = {cells[i]: t for i, t in seq}
    def fit_any(t, c):
        x, y = c; w = K[y:y + 8, x:x + 8]; return N_fit(T[t], w)
    bounds = [(-1, lo - 1)] + seq + [(len(cells), hi)]
    unres = 0
    for (i0, t0), (i1, t1) in zip(bounds, bounds[1:]):
        ids = list(range(t0 + 1, t1)); cs = list(range(i0 + 1, i1))
        if not ids: continue
        if len(ids) > len(cs): unres += len(ids) - len(cs); ids = ids[:len(cs)]
        # DP: ids 를 cs 에 순서대로 배정(모두 배정), 점수 = 맞는 불투명 화소 수, 안 맞으면 불가
        n, k2 = len(cs), len(ids)
        NEG = -10 ** 9
        S = [[NEG] * (k2 + 1) for _ in range(n + 1)]; S[0][0] = 0; ch = {}
        sc = {(a, b): fit_any(ids[b], cells[cs[a]]) for a in range(n) for b in range(k2)}
        for a in range(n):
            for b in range(k2 + 1):
                if S[a][b] == NEG: continue
                if S[a][b] > S[a + 1][b]: S[a + 1][b] = S[a][b]; ch[a + 1, b] = (a, b, None)
                if b < k2 and sc[a, b] >= 0 and S[a][b] + sc[a, b] > S[a + 1][b + 1]:
                    S[a + 1][b + 1] = S[a][b] + sc[a, b]; ch[a + 1, b + 1] = (a, b, ids[b])
        if S[n][k2] == NEG: unres += k2; continue
        a, b = n, k2
        while a > 0:
            pa, pb, t = ch[a, b]
            if t is not None: out[cells[cs[pa]]] = t
            a, b = pa, pb
    print(which, '기준점', len(seq), '배정', len(out), '못 정한 번호', unres)
    return out
def N_fit(tt, w):
    op = tt != 15; f = {}
    for i, c in zip(tt[op].tolist(), w[op].tolist()):
        if f.setdefault(i, c) != c: return -1
    return int(op.sum())

# ---- 합성 ----
JP_ROWS = [62, 86, 109, 132, 157, 179]; JP_COLS = [59, 81, 102, 123, 145, 184, 207, 228, 250, 271]
EN_ROWS = [60, 85, 111, 136]; EN_COLS = [62 + 25 * k for k in range(11)]
EN = {}
for k, ch in enumerate('ABCDEFGHIJK'): EN[ch] = (0, k)
for k, ch in enumerate('LMNOPQRSTUV'): EN[ch] = (1, k)
for k, ch in enumerate('WXYZ?!&-'): EN[ch] = (2, k)
for k, ch in enumerate('1234567890'): EN[ch] = (3, k)
LAYOUT = ['ABCDE01234', 'FGHIJ56789', 'KLMNO.&_-!', 'PQRST.&_-!', 'UVWXY    ?', 'Z         ']
GRID_X = (48, 296); GRID_Y = (48, 192)          # 가나 글자층을 비울 범위(버튼 x≥304 제외)
BLOCKS = {'JP': [((32, 256), (0x2983, 0x2B2D)), ((256, 368), (0x2B2D, 0x2B9C))], 'EN': [((32, 256), (0x2B9C, 0x2CFD)), ((256, 368), (0x2CFD, 0x2D5E))]}
EXTRA = {'JP': {(248, 184): 0x2B1C}, 'EN': {}}      # 순서 배정이 놓친 칸(번호 0x2B1C~ 는 블록1 꼬리, ヨ 아래 끝)
def layer(which, path=None):
    mp = {tuple(map(int, k.split(','))): v for k, v in json.load(open(R('work', 'ring', 'ovlfull_%s.json' % which))).items()}
    mp.update(EXTRA[which])
    T = T8(path); img = np.full((224, 384), 15, np.uint8)
    for (x, y), t in mp.items(): img[y:y + 8, x:x + 8] = T[t]
    return mp, img
def bbox_op(img, cx, cy, r=12):
    sub = img[cy - r:cy + r + 1, cx - r:cx + r + 1]; ys, xs = np.nonzero(sub != 15)
    if not len(ys): return None
    return cx - r + xs.min(), cy - r + ys.min(), cx - r + xs.max() + 1, cy - r + ys.max() + 1
def compose():
    mj, J = layer('JP'); E = layer_en_direct()
    new = J.copy(); new[GRID_Y[0]:GRID_Y[1], GRID_X[0]:GRID_X[1]] = 15
    has = np.zeros((224, 384), bool)
    for (x, y) in mj: has[y:y + 8, x:x + 8] = True
    clipped = []
    for r, row in enumerate(LAYOUT):
        for c, ch in enumerate(row):
            jb = bbox_op(J, JP_COLS[c], JP_ROWS[r], 11)
            jx, jy = ((jb[0] + jb[2]) // 2, (jb[1] + jb[3]) // 2) if jb else (JP_COLS[c], JP_ROWS[r])
            src = '!' if ch == '.' else ch
            if src not in EN: continue
            er, ek = EN[src]; b = bbox_op(E, EN_COLS[ek], EN_ROWS[er], 12)
            if not b: clipped.append((ch, '영문 글자 없음')); continue
            x0, y0, x1, y1 = b
            if ch == '.':                                       # 。 = «!» 맨 아래 밝은 덩어리(+음영 1px)
                sub = E[y0:y1, x0:x1]; rows = np.nonzero(((sub >= 10) & (sub != 15)).any(1))[0]
                gap = [r_ for r_ in range(rows.min(), rows.max()) if r_ not in set(rows.tolist())]
                y0 = y0 + (max(gap) + 1 if gap else rows.max() - 1) - 1
            sub = E[y0:y1, x0:x1]; sx = np.nonzero((sub >= 10) & (sub != 15))[1]
            scx = x0 + (sx.min() + sx.max() + 1) // 2 if len(sx) else (x0 + x1) // 2
            jsub = J[jy - 11:jy + 12, JP_COLS[c] - 11:JP_COLS[c] + 12]; jx_ = np.nonzero((jsub >= 10) & (jsub != 15))[1]
            jcx = JP_COLS[c] - 11 + (jx_.min() + jx_.max() + 1) // 2 if len(jx_) else jx
            ox0 = jcx - scx; oy0 = JP_ROWS[r] - EN_ROWS[er]
            if ch == '.': oy0 = JP_ROWS[r] + 7 - y1
            px = [(y, x, E[y, x]) for y in range(y0, y1) for x in range(x0, x1) if E[y, x] != 15]
            best = None
            for dy in ((-3, -2, -1, 0, 1, 2, 3) if ch == 'A' else (0,)):
                for dx in (range(-7, 8) if ch == 'A' else range(-2, 3)):
                    cost = sum((20 if v >= 10 else 1) for y, x, v in px if not has[y + oy0 + dy, x + ox0 + dx]) + 10 * abs(dx) + 10 * abs(dy)
                    if best is None or cost < best[0]: best = (cost, dx, dy)
            ox, oy = ox0 + best[1], oy0 + best[2]
            n = 0; nb = 0
            for y, x, v in px:
                X, Y = x + ox, y + oy
                if not has[Y, X]: n += 1; nb += v >= 10; continue
                new[Y, X] = v
            if n: clipped.append((ch, n, '획 %d' % nb, (best[1], best[2])))
    return mj, J, new, clipped
def preview(J, new):
    """바탕 돌 = 일본판 화면에서 일본 글자층이 투명한 화소 / 아니면 영문판 화면(영문 글자층 투명) / 둘 다 아니면 이웃"""
    KJ = screen('JP'); KE = screen('EN'); E = layer_en_direct()
    base = KJ.copy(); hole = J != 15
    enbad = np.zeros_like(hole); enbad[150:180, 40:320] = True; enbad[40:80, 40:80] = True   # 영문 버튼·Ⅰ~Ⅲ·커서 A
    ok = hole & (E == 15) & ~enbad
    base[ok] = KE[ok]
    both = hole & ~ok
    both[40:80, 40:80] |= (KJ[40:80, 40:80] != KE[40:80, 40:80])                              # 커서 빛 둘레도 메움
    import cv2
    img = np.stack([(base >> 16) & 255, (base >> 8) & 255, base & 255], -1).astype(np.uint8)
    fill = cv2.inpaint(img, both.astype(np.uint8), 3, cv2.INPAINT_TELEA).astype(np.int64)
    base[both] = (fill[..., 0] << 16 | fill[..., 1] << 8 | fill[..., 2])[both]
    pal = PALS['A']; out = base.copy(); g = np.zeros_like(new, bool); g[GRID_Y[0]:GRID_Y[1], GRID_X[0]:GRID_X[1]] = True
    out[g] = base[g]
    for i, c in pal.items(): out[(new == i) & g] = c
    out[~g] = KJ[~g]
    rgb = lambda k: np.stack([(k >> 16) & 255, (k >> 8) & 255, k & 255], -1).astype(np.uint8)
    a = np.hstack([rgb(KJ), np.zeros((224, 4, 3), np.uint8), rgb(out)])[44:196, 36:]
    Image.fromarray(a).resize((a.shape[1] * 3, a.shape[0] * 3), 0).save(R('work', 'ring', 'preview', 'name_grid_v2.png'))
    return int(both.sum())

def layer_en_direct():
    """영문 글자층: 칸마다 엄격 맞춤 1등(팔레트 A/B) — 없으면(커서 칸) 팔레트 무관 맞춤 최대 불투명"""
    m = json.load(open(R('work', 'ring', 'ovl3_EN.json'))); T = T8(); K = screen('EN')
    full = json.load(open(R('work', 'ring', 'ovlfull_EN.json')))
    img = np.full((224, 384), 15, np.uint8); lo, hi = RANGE['EN']
    for y in range(16, 200, 8):
        for x in range(32, 368, 8):
            v = m.get('%d,%d' % (x, y), [])
            inA = 40 <= x <= 72 and 40 <= y <= 80                       # 커서 A 둘레 = 래스터 순서 배정 결과(커서 스프라이트가 덮어 화면 대조 불가)
            if v and v[0][0] >= 3: img[y:y + 8, x:x + 8] = FL[v[0][2]](T[v[0][1]]); continue
            if not inA: continue
            t = full.get('%d,%d' % (x, y))
            if t is not None: img[y:y + 8, x:x + 8] = T[t]
    return img

def write(src, dst):
    """dd21x 글자층 타일에 새 글자판을 써 넣음(가나 칸 범위만) → 바꾼 타일 수"""
    mj, J, new, cl = compose()
    up = R('work', 'ring', 'tablet_user_layer.npy')            # 하스피가 그린 돌판 그대로(2026-11-14) — ⚠24x24 커서 사각형 가정으로 옮긴 판은 실기에서 커서가 옆 글자로 번져 되돌림
    if os.path.exists(up):
        u = np.load(up); g = np.zeros_like(new, bool); g[GRID_Y[0]:GRID_Y[1], GRID_X[0]:GRID_X[1]] = True
        new = np.where(g, u, new); cl = []
    raw = bytearray(open(src, 'rb').read()); n = 0
    BTN = set()
    for a, b in ((0x2B3D, 0x2B42), (0x2B45, 0x2B4A), (0x2B57, 0x2B5C), (0x2B62, 0x2B67), (0x2B6E, 0x2B73), (0x2B76, 0x2B7B), (0x2B85, 0x2B8A), (0x2B8E, 0x2B93)):
        BTN |= set(range(a, b))
    for (x, y), t in mj.items():
        if not (GRID_X[0] <= x < GRID_X[1] and GRID_Y[0] <= y < GRID_Y[1]): continue
        assert t not in BTN, ('버튼 타일과 겹침', hex(t))
        tt = new[y:y + 8, x:x + 8].astype(np.uint8).reshape(-1)
        o = t * 64                                     # 칸 = 64 B(앞 32 B 가 8x8 그림) — 2026-11-14 ×32 로 잘못 써서 돌판 안 바뀌고 다른 칸 덮었던 것 고침
        old = bytes(raw[o:o + 32])
        raw[o:o + 32] = bytes((tt[0::2] & 15) | ((tt[1::2] & 15) << 4))
        n += old != bytes(raw[o:o + 32])
    open(dst, 'wb').write(raw)
    return n, cl
if __name__ == '__main__' and len(sys.argv) > 2 and sys.argv[1] == 'write':
    print(write(sys.argv[2], sys.argv[3]))
