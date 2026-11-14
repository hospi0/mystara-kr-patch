# -*- coding: utf-8 -*-
r"""1.00 ELF(work/bin/EBOOT.elf) ↔ 1.02 ELF(work/v102/dec/EBOOT.elf) 바이트 대응 지도 (2026-11-14).
  같은 바이트가 이어지는 구간 (1.00 시작, 끝, 1.02 − 1.00 차이) 목록 → work/v102/map.json
  python tools/v102_map.py [시작 끝]..."""
import os, sys, json
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = lambda *p: os.path.join(ROOT, *p)
A = R('work', 'bin', 'EBOOT.elf'); B = R('work', 'v102', 'dec', 'EBOOT.elf')
K = 24


_IDX = None
def index(b):
    """1.02 의 짝수 자리 16 B 해시 → 정렬 색인(numpy)"""
    global _IDX
    if _IDX is None:
        import numpy as np
        u = np.frombuffer(b[:len(b) // 16 * 16], np.uint8)
        hs = []; pos = []
        for sh in range(0, 16, 2):                                   # 자리 = 16k + sh
            v = u[sh:sh + (len(u) - 16) // 16 * 16].reshape(-1, 16)
            w = v.view('>u8').reshape(-1, 2)
            hs.append(w[:, 0] * np.uint64(0x9E3779B97F4A7C15) + w[:, 1]); pos.append(np.arange(len(w), dtype=np.int64) * 16 + sh)
        h = np.concatenate(hs); p = np.concatenate(pos); od = np.argsort(h, kind='stable')
        _IDX = (h[od], p[od])
    return _IDX
def find1(a, b, o):
    """1.00 의 o 자리 16 B 가 1.02 에 «딱 한 곳»이면 그 자리, 아니면 −1"""
    import numpy as np
    h, p = index(b); key = a[o:o + 16]
    w = np.frombuffer(key, '>u8'); q = w[0] * np.uint64(0x9E3779B97F4A7C15) + w[1]
    i = int(np.searchsorted(h, q)); c = []
    while i < len(h) and h[i] == q and len(c) < 3:
        if b[int(p[i]):int(p[i]) + 16] == key: c.append(int(p[i]))
        i += 1
    return c[0] if len(c) == 1 else -1


def build(a, b, s, e, log=print):
    segs = []; o = s; last = None
    while o < e:
        key = a[o:o + K]
        if len(set(key)) < 6: o += 2; continue                      # 0 채움 등 특징 없는 곳은 건너뜀(뒤에서 이웃 구간에 붙임)
        p = -1
        if last is not None and b[o + last:o + last + K] == key: p = o + last
        if p < 0:
            p = find1(a, b, o)
            if p >= 0 and b[p:p + K] != key: p = -1
        if p < 0: o += 2; continue
        d = p - o
        x = o                                                        # 앞으로 늘림
        while x > s and x + d > 0 and a[x - 1] == b[x - 1 + d] and not (segs and x <= segs[-1][1]): x -= 1
        y = o + K
        while y < e and y + d < len(b) and a[y] == b[y + d]: y += 1
        segs.append([x, y, d]); last = d; o = y
    return segs


def lookup(segs, o):
    for x, y, d in segs:
        if x <= o < y: return o + d
    return None


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    a = open(A, 'rb').read(); b = open(B, 'rb').read()
    rng = [(int(sys.argv[i], 16), int(sys.argv[i + 1], 16)) for i in range(1, len(sys.argv) - 1, 2)] or [(0x0A0000, 0x760000), (0x8F0000, 0x900000), (0x1290000, 0x12A0000), (0x1490000, 0x14E0000)]
    allsegs = []
    for s, e in rng:
        segs = build(a, b, s, e); allsegs += segs
        cov = sum(y - x for x, y, d in segs)
        print('%07X~%07X: 구간 %d · 덮은 바이트 %d / %d (%.1f%%)' % (s, e, len(segs), cov, e - s, 100 * cov / (e - s)))
        # 틈 요약(큰 것만)
        prev = s
        for x, y, d in segs + [[e, e, 0]]:
            if x - prev >= 0x400:
                z = a[prev:x].count(0)
                print('   틈 %07X~%07X (%d B, 0 바이트 %d%%)' % (prev, x, x - prev, 100 * z // (x - prev)))
            prev = y
        ds = []
        for x, y, d in segs:
            if not ds or ds[-1][2] != d: ds.append([x, y, d])
            else: ds[-1][1] = y
        print('   차이값 묶음 %d: %s' % (len(ds), ' '.join('%07X~%07X:%+X' % (x, y, d) for x, y, d in ds[:60])))
    json.dump(allsegs, open(R('work', 'v102', 'map.json'), 'w'))
