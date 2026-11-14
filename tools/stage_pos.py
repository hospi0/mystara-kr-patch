# -*- coding: utf-8 -*-
r"""무대 제목 타일의 상대 x 위치를 «대사 글꼴(dd21x) 글자 모양 대조»로 구함 — 스테이트·스샷 없이 (2026-11-13).
  제목 타일 = 흰 잉크(0). 타일마다 제목 글자 하나(또는 둘 조각)의 어느 부분인지 찾아 «글자 번호, 글자 안 x 오프셋»을 얻는다.
  글자 원점 간격은 한 타일에 두 글자가 걸친 경우나 블록(가로 이어짐)으로 구한다."""
import os, sys, struct, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import ps3gfx, poc_build as P
g22 = open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd22.bin'), 'rb').read()
g21 = open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd21x.bin'), 'rb').read()
JM = P.jp_map()
def font_ink(ch):
    return ps3gfx.tile(g21, JM[ch]) == 0
def tile_ink(t):
    return ps3gfx.tile(g22, t) == 0
def match(ink, chars):
    """타일 잉크를 설명하는 (글자 번호, dx, dy) 목록 — dx = 글자 원점이 타일 왼쪽에서 떨어진 거리"""
    res = []
    rem = ink.copy()
    while rem.sum() > 2:
        best = None
        for i, ch in enumerate(chars):
            if ch not in JM: continue
            G = font_ink(ch)
            for dy in range(-4, 5):
                for dx in range(-15, 16):
                    S = np.zeros((16, 16), bool)
                    ys, xs = np.nonzero(G); ys2 = ys + dy; xs2 = xs + dx
                    k = (ys2 >= 0) & (ys2 < 16) & (xs2 >= 0) & (xs2 < 16)
                    if k.sum() < 3: continue
                    S[ys2[k], xs2[k]] = True
                    if (S & ~ink).sum() > 0: continue
                    sc = (S & rem).sum()
                    if best is None or sc > best[0]: best = (sc, i, dx, dy, S)
        if best is None or best[0] < 3: break
        res.append((best[1], best[2], best[3])); rem &= ~best[4]
    return res, int(rem.sum())
if __name__ == '__main__':
    t0 = int(sys.argv[1], 16); n = int(sys.argv[2]); chars = sys.argv[3]
    for t in range(t0, t0 + n):
        r, left = match(tile_ink(t), chars)
        print('%X' % t, [(chars[i], dx, dy) for i, dx, dy in r], '남은', left)

TITLES = {0x511664: 'ブロークンランドの北の山々', 0x511694: 'トリンタン村へ', 0x5116C8: '重戦車・ジャガーノート',
          0x5116EC: '激流・ベスビア川を下れ！', 0x511728: '激流・ベスビア川を下れ！', 0x511760: 'アエングモアの森・上空',
          0x511780: '腐海と呼ばれる森', 0x5117A4: '情報を求めてーアインスンの街ー', 0x5117E8: 'エルフー木々のかけ橋ー',
          0x51182C: '攻防！大樹の大要塞', 0x511864: '魔獣が住む森', 0x511884: '迷いの森',
          0x5118C0: 'ノームの村を助けろ！！', 0x5118E8: '精霊・ラファエルの洞窟の異変', 0x511920: '隠された財宝', 0x511930: '灼熱！溶岩界',
          0x51195C: 'ロスト・ワールド', 0x511990: 'ドワーフの隠し地下通路', 0x5119B4: '浮遊城ー侵入ー',
          0x5119F0: '浮遊城ー決戦Ⅰー', 0x511A1C: '浮遊城ー闘技場Ⅰー', 0x511A58: '浮遊城ー決戦Ⅱー',
          0x511A84: '浮遊城ー闘技場Ⅱー', 0x511AAC: '浮遊城ー最上階の扉へー'}
def blocks_at(e, o):
    W = lambda a: struct.unpack('>H', e[a:a + 2])[0]; out = []
    while 0x6000 <= W(o) < 0x7000 and (W(o + 2) & 0xFF) < 0x20:
        a = W(o + 2); out.append((o, W(o), (a >> 8 & 15) + 1, (a >> 12) + 1)); o += 4
    return out
def analyze(e, o, chars):
    """→ 묶음 목록: dict(tiles=[(블록 기록 자리, 블록 안 번호 i, j, 타일, x, y)], chars={글자 번호: 원점 x}, span)"""
    occ = []                                     # 타일 쓰임 하나하나
    for bo, t, nx, ny in blocks_at(e, o):
        for j in range(ny):
            for i in range(nx): occ.append(dict(bo=bo, i=i, j=j, t=t + i + 16 * j, nx=nx, ny=ny))
    for k, oc in enumerate(occ):
        oc['m'], oc['left'] = match(tile_ink(oc['t']), chars)
    # 합집합: 노드 = ('o',k) 타일 쓰임 / ('c',i) 글자 — 값 = x 좌표
    par = {}; off = {}
    def find(a):
        if par.setdefault(a, a) == a: off.setdefault(a, 0); return a
        r = find(par[a]); off[a] = off[a] + off[par[a]]; par[a] = r; return r
    def union(a, b, d):                           # x(b) = x(a) + d
        ra, rb = find(a), find(b)
        if ra == rb:
            if off[b] - off[a] != d: print('  어긋남', a, b, d, off[b] - off[a])
            return
        par[rb] = ra; off[rb] = off[a] + d - off[b]
    for k, oc in enumerate(occ):
        find(('o', k))
        for ci, dx, dy in oc['m']: union(('o', k), ('c', ci), dx)
    # 같은 블록 안 이웃 타일 = +16
    for k, oc in enumerate(occ):
        for k2, oc2 in enumerate(occ):
            if oc2['bo'] == oc['bo'] and oc2['j'] == oc['j'] and oc2['i'] == oc['i'] + 1: union(('o', k), ('o', k2), 16)
    comps = {}
    for k, oc in enumerate(occ):
        if not oc['m']: continue                  # STAGE 작은 글자 타일 등
        r = find(('o', k)); comps.setdefault(r, dict(tiles=[], chars={}))['tiles'].append((k, off[('o', k)]))
    for i in range(len(chars)):
        if ('c', i) in par:
            r = find(('c', i))
            if r in comps: comps[r]['chars'][i] = off[('c', i)]
    out = []
    for r, c in comps.items():
        xs = [x for k, x in c['tiles']]; base = min(xs)
        c['tiles'] = [(k, x - base) for k, x in c['tiles']]; c['chars'] = {i: x - base for i, x in c['chars'].items()}
        c['span'] = max(xs) - base + 16; out.append(c)
    out.sort(key=lambda c: min(c['chars']) if c['chars'] else 99)
    return occ, out
def report():
    e = open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read()
    for o, chars in TITLES.items():
        occ, comps = analyze(e, o, chars)
        bad = [('%X' % oc['t'], oc['left']) for oc in occ if oc['m'] and oc['left']]
        print('%X %s' % (o, chars), '설명 안 된 잉크' if bad else '', bad)
        for c in comps:
            s = ''.join(chars[i] for i in sorted(c['chars']))
            print('    묶음 폭 %3d  글자 %s  원점 %s  타일 %d' % (c['span'], s, [c['chars'][i] for i in sorted(c['chars'])], len(c['tiles'])))

def is_stage_row(t):
    a = ps3gfx.tile(g22, t); ys = np.nonzero((a != 15).any(1))[0]
    return len(ys) > 0 and ys.max() <= 7
def groups(e, o, chars):
    """제목 줄 타일 쓰임을 «붙어 있는 묶음»으로 → [dict(occ=[(쓰임번호, x)], w, ink=(x0,x1))] 기록 순서"""
    occ = []
    for bo, t, nx, ny in blocks_at(e, o):
        for j in range(ny):
            for i in range(nx):
                tt = t + i + 16 * j
                if is_stage_row(tt): continue
                occ.append(dict(bo=bo, i=i, j=j, t=tt, k=len(occ)))
    for oc in occ: oc['m'], oc['left'] = match(tile_ink(oc['t']), chars)
    par = list(range(len(occ))); off = [0] * len(occ)
    def find(a):
        if par[a] == a: return a
        r = find(par[a]); off[a] += off[par[a]]; par[a] = r; return r
    def union(a, b, d):
        ra, rb = find(a), find(b)
        if ra != rb: par[rb] = ra; off[rb] = off[a] + d - off[b]
    for a, oc in enumerate(occ):
        for b in range(a + 1, len(occ)):
            ob = occ[b]
            if ob['bo'] == oc['bo'] and ob['j'] == oc['j'] and ob['i'] == oc['i'] + 1: union(a, b, 16)
        if a + 1 < len(occ):                      # 글자가 다음 타일로 넘어감: 같은 글자 dx 차이 16
            ob = occ[a + 1]
            if any(c1 == c2 and d1 > 0 and d2 == d1 - 16 for c1, d1, _ in oc['m'] for c2, d2, _ in ob['m']): union(a, a + 1, 16)
    out = {}
    for a in range(len(occ)): out.setdefault(find(a), []).append(a)
    res = []
    for r, ks in out.items():
        xs = {k: off[k] for k in ks}; find(r); base = min(xs.values())
        ink = np.zeros((16, max(xs.values()) - base + 16), bool)
        for k in ks:
            x = xs[k] - base; ink[:, x:x + 16] |= tile_ink(occ[k]['t']) | (ps3gfx.tile(g22, occ[k]['t']) == 14)
        cols = np.nonzero(ink.any(0))[0]
        res.append(dict(occ=[(k, xs[k] - base) for k in sorted(ks)], w=ink.shape[1], ink=(int(cols.min()), int(cols.max()) + 1) if len(cols) else (0, 0),
                        jp=''.join(sorted({chars[c] for k in ks for c, _, _ in occ[k]['m']}, key=chars.index))))
    res.sort(key=lambda g: g['occ'][0][0])
    return occ, res
def report2():
    e = open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read()
    for o, chars in TITLES.items():
        occ, gs = groups(e, o, chars)
        print('%X %s  제목 타일 %d' % (o, chars, len(occ)))
        print('    ' + ' | '.join('%s(폭%d 잉크%d-%d)' % (g['jp'] or '?', g['w'], g['ink'][0], g['ink'][1]) for g in gs))
