# -*- coding: utf-8 -*-
"""모르는 인코딩 문자열 찾기: «같은 글자 = 같은 코드, 다른 글자 = 다른 코드»(동형) — 1바이트·2바이트(BE) numpy 검색. (2026-11-12 미스타라)
  python tools/isosearch.py 파일 [--swap] [--range a:b] 문장 …"""
import sys
import numpy as np
def check(vals, s, pat):
    seen = {}; inv = {}
    for k, p in enumerate(pat):
        v = int(vals[s + k])
        if seen.setdefault(p, v) != v or inv.setdefault(v, p) != p: return False
    return True
def search(arr, text, maxhit=20):
    m = {}; pat = [m.setdefault(c, len(m)) for c in text]; n = len(pat)
    eq = [(i, j) for i in range(n) for j in range(i + 1, n) if pat[i] == pat[j]]
    N = len(arr) - n
    if not eq: return []
    mask = np.ones(N, bool)
    for i, j in eq: mask &= arr[i:i + N] == arr[j:j + N]
    # 서로 다른 글자 몇 쌍(이웃)으로 더 거름
    for k in range(n - 1):
        if pat[k] != pat[k + 1]: mask &= arr[k:k + N] != arr[k + 1:k + 1 + N]
    out = []
    for s in np.nonzero(mask)[0]:
        if check(arr, s, pat): out.append((int(s), [int(arr[s + k]) for k in range(n)]))
        if len(out) >= maxhit: break
    return out
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    f = sys.argv[1]; args = sys.argv[2:]
    sw = '--swap' in args; rg = next((a for a in args if a.startswith('--range')), None)
    args = [a for a in args if not a.startswith('--')]
    b = open(f, 'rb').read()
    if rg: a_, b_ = [int(x, 16) for x in rg.split('=')[1].split(':')]; b = b[a_:b_]
    if sw: b = bytes(b[i ^ 1] for i in range(len(b) - 1))
    u8 = np.frombuffer(b, np.uint8)
    for t in args:
        for off, codes in search(u8, t): print('8bit', hex(off), t, ' '.join('%02X' % c for c in codes))
        for par in (0, 1):
            u16 = np.frombuffer(b[par:len(b) - ((len(b) - par) % 2)], '>u2')
            for off, codes in search(u16, t): print('16bit', hex(par + off * 2), t, ' '.join('%04X' % c for c in codes))
