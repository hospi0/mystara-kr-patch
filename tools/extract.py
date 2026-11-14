# -*- coding: utf-8 -*-
"""미스타라(SOM) 본편 글 추출 1차 — EBOOT.elf 세그먼트 0 에서 BE 16비트 글 코드 덩어리를 찾아 work/text/scan.tsv 로.
글 코드 = tools/codetable.table() (+공백 1800). 제어 워드는 {XXXX} 로 둔다. (2026-11-12)
  덩어리: 짝수 오프셋에서 «아는 글자» 연속 ≥ MINRUN, 사이 제어 워드 ≤ 4 개면 한 덩어리로 이음."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import codetable
SEG0 = (0, 0x1402668)
MINRUN = 3

def scan(e, t):
    n = (SEG0[1] - SEG0[0]) // 2
    words = [int.from_bytes(e[SEG0[0] + 2 * i:SEG0[0] + 2 * i + 2], 'big') for i in range(n)]
    isch = [w in t for w in words]
    out = []; i = 0
    while i < n:
        if not isch[i]: i += 1; continue
        j = i
        while j < n and isch[j]: j += 1
        if j - i >= MINRUN:
            # 앞뒤로 제어 워드 몇 개 끼고 이어지는 글자 덩어리 합치기
            st, en = i, j
            while True:
                k = en; gap = 0
                while k < n and not isch[k] and gap < 4: k += 1; gap += 1
                m = k
                while m < n and isch[m]: m += 1
                if k < n and isch[k] and m - k >= 1 and gap <= 4: en = m
                else: break
            out.append((SEG0[0] + st * 2, words[st:en]))
            i = en
        else:
            i = j
    return out

def render(ws, t):
    return ''.join(t[w] if w in t else '{%04X}' % w for w in ws)

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    t = codetable.table()
    e = open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read()
    res = scan(e, t)
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'text', 'scan.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('off\tn\ttext\n')
        for off, ws in res: w.write('%06X\t%d\t%s\n' % (off, len(ws), render(ws, t)))
    print('덩어리', len(res), '· 글자 워드', sum(len(ws) for _, ws in res))
