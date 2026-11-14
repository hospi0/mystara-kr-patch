# -*- coding: utf-8 -*-
r"""화면 8x8 칸 ↔ dd21x 8x8 타일 빠른 대응: 색 번호를 «처음 나온 순서»로 다시 매긴 모양 서명으로 해시 비교 (2026-11-13 이름 돌판)."""
import numpy as np
def sig(a):
    a = np.asarray(a).reshape(-1); m = {}; out = []
    for v in a.tolist():
        if v not in m: m[v] = len(m)
        out.append(m[v])
    return bytes(out)
def tiles8(path, lo, hi):
    raw = np.frombuffer(open(path, 'rb').read(), np.uint8)
    p = np.empty(raw.size * 2, np.uint8); p[0::2] = raw & 15; p[1::2] = raw >> 4
    T = p.reshape(-1, 16, 8)[:, :8]
    return T[lo:hi]
def index(T, lo):
    d = {}
    for i, t in enumerate(T):
        if (t == 15).any(): continue                    # 돌판 칸은 불투명
        for fl, tt in (('n', t), ('x', t[:, ::-1]), ('y', t[::-1]), ('xy', t[::-1, ::-1])):
            d.setdefault(sig(tt), []).append((lo + i, fl))
    return d
def match_screen(K, d, x0, y0, nx, ny):
    """K = 화면 색 키(정수) 배열 → {(cx,cy): [(타일, 반전)…]}"""
    out = {}
    for j in range(ny):
        for i in range(nx):
            x, y = x0 + 8 * i, y0 + 8 * j
            out[x, y] = d.get(sig(K[y:y + 8, x:x + 8]), [])
    return out
