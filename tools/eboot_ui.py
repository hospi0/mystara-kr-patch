# -*- coding: utf-8 -*-
r"""EBOOT 안 UTF-8 시스템 문구(저장·트로피·설치 데이터 오류 등, 0x12934D0~) 한글 제자리 쓰기 (2026-11-14).
  work/gui/eboot_ui.tsv(번호 = 파일 오프셋 16진, \n 이스케이프). 예산 = 다음 0 아닌 바이트 전까지(원래 문자열 + NUL 채움).
  문장부호 뒤 공백 지움(규칙). apply(e) → 쓴 줄 수. 글꼴 = tools/gui_font(build_gui 가 이 TSV 도 넘김)."""
import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TSV = os.path.join(ROOT, 'work', 'gui', 'eboot_ui.tsv')
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？：；:;～~])[ 　]+')
def rows():
    out = []
    for ln in open(TSV, encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 3 and c[2]:
            ko = PUNCT_SP.sub(lambda m: m.group(1), c[2].replace('\\n', '\n'))
            out.append((int(c[0], 16), c[1].replace('\\n', '\n'), ko))
    return out
def apply(e, log=print):
    n = 0
    for off, jp, ko in rows():
        cur = bytes(e[off:off + len(jp.encode('utf-8'))]).decode('utf-8', 'replace')
        assert cur == jp, ('원문 다름 %X' % off, cur[:20])
        end = off + len(jp.encode('utf-8'))
        while end < len(e) and e[end] == 0: end += 1
        raw = ko.encode('utf-8')
        if len(raw) + 1 > end - off: log('⛔UI 문구 넘침 %X %d>%d' % (off, len(raw) + 1, end - off)); continue
        e[off:end] = raw + b'\0' * (end - off - len(raw)); n += 1
    log('EBOOT UI 문구 %d줄' % n)
    return n
