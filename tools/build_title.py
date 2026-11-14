# -*- coding: utf-8 -*-
r"""타이틀 로고 gui.arc 빌드 (2026-11-14): logo_ID = work/title_export/logo_ko.png(title_logo.py) · sub_ID = 하스피 흰 로고 그대로.
  → work/build/arc/gui.arc · 검산 = 묶은 arc 다시 풀어 디코드 → work/title_export/check_*.png"""
import os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); import texio, mtarc
ROOT = os.path.dirname(HERE); R = lambda *p: os.path.join(ROOT, *p)
BS = chr(92); TD = R('work', 'title_export')
def main():
    srcs = {'logo_ID': R('work', 'title_export', 'logo_ko.png'), 'sub_ID': R('my files', '작업', 'white_logo_same_diagonal_clean_transparent.png')}
    repl = {}
    for k, p in srcs.items():
        rgba = np.array(Image.open(p).convert('RGBA'))
        o = os.path.join(TD, k + '.tex'); n = os.path.join(TD, k + '_ko.tex')
        texio.save(o, n, rgba); repl['GUI' + BS + 'title' + BS + k] = open(n, 'rb').read()
    os.makedirs(R('work', 'build', 'arc'), exist_ok=True); dst = R('work', 'build', 'arc', 'gui.arc')
    mtarc.pack(R('work', 'orig', 'arc', 'gui.arc'), dst, repl)
    a = {nm: d for nm, th, d, fl in mtarc.entries(dst)}; b = {nm: d for nm, th, d, fl in mtarc.entries(R('work', 'orig', 'arc', 'gui.arc'))}
    diff = [nm for nm in b if a[nm] != b[nm]]; print('바뀐 항목', diff, '항목 수', len(a), len(b))
    for k in srcs:
        t = os.path.join(TD, 'check_%s.tex' % k); open(t, 'wb').write(a['GUI' + BS + 'title' + BS + k])
        img, info = texio.load(t); Image.fromarray(img).save(os.path.join(TD, 'check_%s.png' % k)); print(k, info)
if __name__ == '__main__':
    main()
