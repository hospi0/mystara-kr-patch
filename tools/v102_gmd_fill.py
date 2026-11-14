# -*- coding: utf-8 -*-
r"""1.02 GMD 번역표 채우기 (2026-11-14).
  work/v102/common102_ko.tsv(1.02 646줄, 1.00 번역 재사용분 채워짐)에
  ① 무대 이름 = work/gui/tex_ko.tsv(챕터 그림 번역)에서 같은 원문(전각 숫자·F 정규화), «STAGE x 이름» 은 앞머리 그대로 + 이름 번역
  ② 손 번역 = work/v102/new102_ko.tsv(원문\t한글) — 원문이 같은 줄 전부
  → work/v102/common102_ko.tsv 덮어씀(번역 칸만), 남은 일본어 줄 수 출력
  python tools/v102_gmd_fill.py"""
import os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = lambda *p: os.path.join(ROOT, *p)
JP = re.compile('[ぁ-んァ-ヶ一-龥々]')
def nz(s):
    s = s.translate(str.maketrans('０１２３４５６７８９ＡＢＦ！', '0123456789ABF!'))
    s = re.sub(r'(?<=[ァ-ヶ])ー', 'ー', s)                                  # 장음은 그대로
    return re.sub(r'(?<![ァ-ヶ])ー', '－', s).replace('―', '－').replace('　', ' ').replace('－1F', '1F').strip()
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    tex = {}
    for ln in open(R('work', 'gui', 'tex_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 4 and c[3]: tex.setdefault(nz(c[2]), c[3])          # 열 = 텍스처·상자 번호·원문·한글
    tex = {k.replace('－', ''): v for k, v in tex.items()} | tex
    hand = {}
    p = R('work', 'v102', 'new102_ko.tsv')
    if os.path.exists(p):
        for ln in open(p, encoding='utf-8').read().split('\n'):
            if '\t' in ln and not ln.startswith('#'):
                a, b = ln.split('\t', 1); hand[a] = b
    rows = [l.rstrip('\n').split('\t') for l in open(R('work', 'v102', 'common102_ko.tsv'), encoding='utf-8')]
    n_tex = n_hand = 0; left = []
    for r in rows[1:]:
        while len(r) < 3: r.append('')
        src = r[1]
        if src in hand: r[2] = hand[src]; n_hand += 1; continue
        if r[2]: continue
        m = re.match(r'^(STAGE [0-9]+(?:-[0-9A-Z]+)? )(.*)$', src)
        key = nz(m.group(2) if m else src)
        v = tex.get(key) or tex.get(key.replace('－', ''))
        if v: r[2] = (m.group(1) if m else '') + v; n_tex += 1; continue
        if JP.search(src): left.append((r[0], src))
    open(R('work', 'v102', 'common102_ko.tsv'), 'w', encoding='utf-8').write('\n'.join('\t'.join(r) for r in rows) + '\n')
    print('무대 이름 채움 %d · 손 번역 %d · 남은 일본어 줄 %d' % (n_tex, n_hand, len(left)))
    for no, s in left: print(no, s)
if __name__ == '__main__':
    main()
