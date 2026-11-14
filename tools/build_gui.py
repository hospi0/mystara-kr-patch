# -*- coding: utf-8 -*-
r"""바깥 화면(PS3 쪽) 한글 빌더 (2026-11-14).
  · GUI/message/common_jpn.gmd ← work/gui/common_ko.tsv (문장부호 뒤 공백 빌더에서 지움)
  · GUI/font/Font.gfd + Font_00_ID.tex ← 번역에 쓰인 한글·부호를 안 쓰는 한자 칸에 Noto Sans KR 로(tools/gui_font.py)
  출력 work/build/GUI/…  ·  python tools/build_gui.py"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import gmd, gui_font
R = lambda *p: os.path.join(ROOT, *p)
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？：；:;～~])[ 　]+(?!<ICON)')
def main():
    src = R('work', 'gui', 'common_ko.tsv'); tmp = R('work', 'gui', 'common_ko.built.tsv')
    rows = [l.rstrip('\n').split('\t') for l in open(src, encoding='utf-8')]
    out = [rows[0]]
    for r in rows[1:]:
        if len(r) > 2 and r[2]: r = r[:2] + [PUNCT_SP.sub(lambda m: m.group(1), r[2])]
        out.append(r)
    open(tmp, 'w', encoding='utf-8').write('\n'.join('\t'.join(r) for r in out) + '\n')
    od = R('work', 'build', 'GUI'); os.makedirs(os.path.join(od, 'message'), exist_ok=True)
    texts = gmd.load_tsv(tmp)
    open(os.path.join(od, 'message', 'common_jpn.gmd'), 'wb').write(gmd.build(R('work', 'orig', 'GUI', 'message', 'common_jpn.gmd'), texts))
    need, ns = gui_font.build([tmp, R('work', 'gui', 'eboot_ui.tsv')], os.path.join(od, 'font'))
    print('GMD %d줄 · 글꼴 새 글자 %d(한자 칸 %d 중)' % (len(texts), len(need), ns))

def build_all():
    main()
    import texlabel, warning_tex, copy_announce
    warning_tex.main(); copy_announce.main()
    os.makedirs(R('work', 'build', 'options'), exist_ok=True)
    for n in ('descripter0_LIN', 'setting1_LIN', 'record0_LIN', 'chpt_title0_LIN'):
        print(n, texlabel.build(n, R('work', 'build', 'options', n + '.tex')))
if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'all':
    build_all()
if __name__ == '__main__' and len(sys.argv) == 1:
    main()
