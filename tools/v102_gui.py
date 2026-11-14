# -*- coding: utf-8 -*-
r"""1.02 업데이트용 바깥 메뉴(GMD·글꼴·gui.arc) 빌드 (2026-11-14).
  원본 = work/v102/plain(1.02 hdd0 파일 SFH 벗긴 것, tools/sfh.py) · 번역 = work/v102/common102_ko.tsv(tools/v102_gmd_fill.py)
  출력 = work/v102/build/hdd0/USRDIR/nativePS3/… (SFH 로 다시 싼 것 = 그대로 dev_hdd0\game\BLJM61055 에 덮음)
  python tools/v102_gui.py"""
import os, sys, re
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import gmd, gui_font, sfh, mtarc
R = lambda *p: os.path.join(ROOT, *p)
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？：；:;～~])[ 　]+(?!<ICON)')
PLAIN = R('work', 'v102', 'plain'); OUT = R('work', 'v102', 'build', 'hdd0', 'USRDIR', 'nativePS3')
def put(rel, data):
    p = os.path.join(OUT, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
    w = sfh.wrap(data); assert sfh.unwrap(w) == data
    open(p, 'wb').write(w); return p
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    src = R('work', 'v102', 'common102_ko.tsv'); tmp = R('work', 'v102', 'common102_ko.built.tsv')
    rows = [l.rstrip('\n').split('\t') for l in open(src, encoding='utf-8')]
    out = [rows[0]]
    for r in rows[1:]:
        if len(r) > 2 and r[2]: r = r[:2] + [PUNCT_SP.sub(lambda m: m.group(1), r[2])]
        out.append(r)
    open(tmp, 'w', encoding='utf-8').write('\n'.join('\t'.join(r) for r in out) + '\n')
    texts = gmd.load_tsv(tmp)
    jp = [i for i, t in enumerate(texts) if re.search('[ぁ-んァ-ヶ一-龥]', t)]
    g = gmd.build(os.path.join(PLAIN, 'GUI', 'message', 'common_jpn.gmd'), texts)
    put(os.path.join('GUI', 'message', 'common_jpn.gmd'), g)
    import tempfile, shutil
    td = tempfile.mkdtemp()
    try:
        extra = ('게임 데이터가 손상되었습니다.게임을 끝내고 Dungeons & Dragons ―미스타라 영웅전기―의 게임 데이터를 삭제해 주세요.'
                 'Dungeons & Dragons® ―미스타라 영웅전기―에서 Tower of Doom을 함께 플레이할까요?'
                 '연령 제한으로 이 애플리케이션에서는 PlayStation®Network를 사용하는 기능을 이용할 수 없습니다.'
                 '계정에 이 애플리케이션의 채팅과 게임 안 이름 입력 기능을 이용할 권한이 없습니다.'
                 'Shadow over Mystara를 함께 플레이할까요?-미스타라 영웅전기-에서 함께함')   # v102_port 가 1.02 EBOOT 에 직접 쓰는 UI 6줄
        need, ns = gui_font.build([tmp, R('work', 'gui', 'eboot_ui.tsv')], td, src=os.path.join(PLAIN, 'GUI'), extra=extra)
        for f in ('Font.gfd', 'Font_00_ID.tex'):
            put(os.path.join('GUI', 'font', f), open(os.path.join(td, f), 'rb').read())
    finally:
        shutil.rmtree(td, True)
    print('GMD %d줄(일본어 남은 줄 %d) · 글꼴 새 글자 %d(빈 한자 칸 %d 중)' % (len(texts), len(jp), len(need), ns))
    # gui.arc = 1.02 원본 + 1.00 빌드가 바꾼 항목(타이틀 로고 logo_ID·sub_ID — 1.02 원본에서도 1.00 원본과 같은 바이트일 때만)
    o = {n: d for n, th, d, fl in mtarc.entries(R('work', 'orig', 'arc', 'gui.arc'))}
    k = {n: d for n, th, d, fl in mtarc.entries(R('work', 'build', 'arc', 'gui.arc'))}
    v = {n: d for n, th, d, fl in mtarc.entries(os.path.join(PLAIN, 'arc', 'gui.arc'))}
    repl = {}
    for n in o:
        if k[n] != o[n]:
            assert v.get(n) == o[n], ('1.02 에서 바뀐 항목', n); repl[n] = k[n]
    td = tempfile.mkdtemp()
    try:
        # 1.02 에 새로 생긴 그림 글자(tools/v102_tex.py): 업데이트 내역 2장·난이도 «전부» → gui.arc · 온라인 일시정지 메뉴 → options/setting2_LIN
        import v102_tex
        tex, tlog = v102_tex.make(td)
        for n_, d_ in tex.items():
            if n_.startswith('options/'): put(n_, d_)
            else: assert n_ in v and n_ not in repl; repl[n_] = d_
        print('그림 글자: ' + ' · '.join(tlog))
        t = os.path.join(td, 'gui.arc'); mtarc.pack(os.path.join(PLAIN, 'arc', 'gui.arc'), t, repl)
        chk = {n: d for n, th, d, fl in mtarc.entries(t)}
        assert all(chk[n] == (repl.get(n, v[n])) for n in v) and len(chk) == len(v)
        put(os.path.join('arc', 'gui.arc'), open(t, 'rb').read())
    finally:
        shutil.rmtree(td, True)
    print('gui.arc 항목 %d · 바꾼 항목 %s' % (len(v), sorted(repl)))
if __name__ == '__main__':
    main()
