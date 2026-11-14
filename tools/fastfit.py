# -*- coding: utf-8 -*-
r"""화면 8x8 창 ↔ 타일 «팔레트 무관» 빠른 대조 (2026-11-14).
  타일마다 화소 p 의 «같은 색 번호 화소 비트마스크»를 미리 계산 → 창의 같은 색 마스크와 포함 관계로 판정(불투명 화소만)."""
import numpy as np
def tiles8(path):
    raw = np.frombuffer(open(path, 'rb').read(), np.uint8)
    p = np.empty(raw.size * 2, np.uint8); p[0::2] = raw & 15; p[1::2] = raw >> 4
    return p.reshape(-1, 64)
def tiles8_from16(path):
    """16x16 타일(128 B) → 4개 8x8(왼위·오위·왼아·오아) 순서로"""
    raw = np.frombuffer(open(path, 'rb').read(), np.uint8)
    p = np.empty(raw.size * 2, np.uint8); p[0::2] = raw & 15; p[1::2] = raw >> 4
    t = p.reshape(-1, 16, 16)
    q = np.stack([t[:, :8, :8], t[:, :8, 8:], t[:, 8:, :8], t[:, 8:, 8:]], 1)
    return q.reshape(-1, 64)
def masks(T):
    """(N,64) 색 번호 → (N,64) uint64 같은 번호 마스크(투명 15 는 0)"""
    N = len(T); M = np.zeros((N, 64), np.uint64)
    bits = (np.uint64(1) << np.arange(64, dtype=np.uint64))
    for p in range(64):
        eq = (T == T[:, p:p + 1]) & (T != 15)
        M[:, p] = (eq * bits).sum(1, dtype=np.uint64) if False else np.bitwise_or.reduce(np.where(eq, bits, np.uint64(0)), axis=1)
        M[T[:, p] == 15, p] = 0
    return M
def win_mask(w):
    w = np.asarray(w).reshape(-1); bits = (np.uint64(1) << np.arange(64, dtype=np.uint64))
    return np.array([np.bitwise_or.reduce(np.where(w == w[p], bits, np.uint64(0))) for p in range(64)], np.uint64)
def fit(M, T, w, minop=12, mincol=2):
    wm = win_mask(w); ok = np.ones(len(M), bool)
    for p in range(64): ok &= (M[:, p] & ~wm[p]) == 0
    op = (T != 15).sum(1)
    ok &= op >= minop
    idx = np.nonzero(ok)[0]
    # 색 2가지 이상(단색 우연 일치 제외)
    good = [i for i in idx if len(set(np.asarray(w).reshape(-1)[T[i] != 15].tolist())) >= mincol]
    return sorted(good, key=lambda i: -op[i])
