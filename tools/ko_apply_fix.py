# -*- coding: utf-8 -*-
"""고친 번역 줄(work/text/ko/fixN.tsv = 접두·번호·한국어)을 work/text/ko/{mys,tod}_ko.tsv 에 번호로 덮어쓴다 (2026-11-13).
  python tools/ko_apply_fix.py work/text/ko/fix1.tsv"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
fix = {}
for ln in open(sys.argv[1], encoding='utf-8').read().split('\n'):
    if ln.strip():
        p, n, t = ln.split('\t', 2); fix.setdefault(p, {})[n] = t
for p, d in fix.items():
    f = os.path.join(ROOT, 'work', 'text', 'ko', p + '_ko.tsv')
    rows = open(f, encoding='utf-8').read().split('\n'); hit = 0
    for i, ln in enumerate(rows):
        if ln.strip():
            n = ln.split('\t', 1)[0]
            if n in d: rows[i] = n + '\t' + d[n]; hit += 1
    assert hit == len(d), (p, hit, len(d))
    open(f, 'w', encoding='utf-8', newline='\n').write('\n'.join(rows))
    print(p, '고친 줄', hit)
