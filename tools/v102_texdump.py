# -*- coding: utf-8 -*-
r"""1.02 에 새로 생기거나 바뀐 그림(gui.arc 새 항목·바뀐 항목, options/setting2_LIN) → work/v102/tex/*.png (2026-11-14)"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import mtarc, texio
from PIL import Image
R = lambda *p: os.path.join(ROOT, *p)
BS = chr(92)
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    o = {n: d for n, th, d, fl in mtarc.entries(R('work', 'orig', 'arc', 'gui.arc'))}
    od = R('work', 'v102', 'tex'); os.makedirs(od, exist_ok=True)
    for n, th, d, fl in mtarc.entries(R('work', 'v102', 'plain', 'arc', 'gui.arc')):
        if d[:4] != b'\0XET': continue
        if n in o and o[n] == d: continue
        p = os.path.join(od, n.replace(BS, '_') + '.tex'); open(p, 'wb').write(d)
        try:
            img, info = texio.load(p); Image.fromarray(img).save(p[:-4] + '.png'); print(n, '새' if n not in o else '바뀜', info)
        except Exception as e:
            print(n, '못 읽음', e)
    p = R('work', 'v102', 'plain', 'options', 'setting2_LIN.tex')
    img, info = texio.load(p); Image.fromarray(img).save(os.path.join(od, 'options_setting2_LIN.png')); print('options/setting2_LIN', info)
if __name__ == '__main__':
    main()
