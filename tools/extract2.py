# -*- coding: utf-8 -*-
"""미스타라(SOM) 본편 글 추출 2차 — «포인터 기준» (2026-11-13).
  세그먼트 0: VA = 파일 오프셋 + 0x10000. 글 포인터 = 2정렬 32비트 VA 값(표·장면 레코드 안).
  토큰: FFFF x y = 줄바꿈(x = -(그 줄 글자 수×16), y = 줄 간격) · FFFE n = 머리 명령(색·크기?) · 0000 = 끝
        (글자가 하나라도 나온 뒤의 0000 만 끝 — 머리 x·y 의 0 은 머리로 둠).
  검산: 본문 구역 안 «글자 워드»가 어떤 문자열에도 안 들어가면 목록으로 찍는다(누락 0 이어야).
  python tools/extract2.py  →  work/text/strings.tsv"""
import os, sys, struct, collections, bisect
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import codetable
END = 0x1402668
LO, HI = 0x6D7000, 0x741000          # 본문 구역
VA = 0x10000

def words(e, o):
    return struct.unpack_from('>H', e, o)[0]

def parse(e, t, a, limit=END):
    """a 부터 토큰 목록 [(종류, 오프셋, 워드들)] 과 끝 오프셋(0000 다음)."""
    toks = []; o = a; seen = False
    while o < limit:
        w = words(e, o)
        if w == 0xFFFF:
            toks.append(('nl', o, [w, words(e, o + 2), words(e, o + 4)])); o += 6; continue
        if w == 0xFFFE:
            toks.append(('cmd', o, [w, words(e, o + 2)])); o += 4; continue
        if w == 0 and seen:
            return toks, o + 2
        if w in t:
            seen = True; toks.append(('ch', o, [w]))
        else:
            toks.append(('raw', o, [w]))
        o += 2
        if len(toks) > 600 or o - a > 4000: break
    return toks, None

def render(toks, t):
    out = []
    for k, o, ws in toks:
        if k == 'ch': out.append(t[ws[0]])
        elif k == 'nl': out.append('{n:%04X,%04X}' % (ws[1], ws[2]))
        elif k == 'cmd': out.append('{c:%04X}' % ws[1])
        else: out.append('{%04X}' % ws[0])
    return ''.join(out)

def collect(e):
    refs = collections.defaultdict(list)
    for o in range(0, END - 3, 2):
        v = struct.unpack_from('>I', e, o)[0] - VA
        if 0 <= v < END and not v & 1: refs[v].append(o)
    return refs

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t = codetable.table(); t[0x1800] = '　'
    e = open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read()
    refs = collect(e)
    strs = []
    for a in sorted(refs):
        toks, end = parse(e, t, a)
        if end is None: continue
        nch = sum(1 for k, *_ in toks if k == 'ch')
        nraw = sum(1 for k, *_ in toks if k == 'raw')
        jp = sum(1 for k, o, ws in toks if k == 'ch' and (0x1E00 <= ws[0] < 0x1EC0 or 0x1D40 <= ws[0] < 0x1D52 or 0x2000 <= ws[0] < 0x2200))
        if nch < 2 or jp < 1 or nraw > nch: continue
        strs.append((a, end, toks))
    # 다른 문자열 «안쪽»을 가리키는 것(접미 공유)은 따로 표시
    starts = [s[0] for s in strs]
    cov = bytearray(HI - LO)
    for a, b, _ in strs:
        for o in range(max(a, LO), min(b, HI)): cov[o - LO] = 1
    miss = []
    for o in range(LO, HI, 2):
        if words(e, o) in t and words(e, o) != 0x1800 and not cov[o - LO]: miss.append(o)
    # 누락 묶기
    runs = []
    for o in miss:
        if runs and o - runs[-1][1] <= 8: runs[-1][1] = o
        else: runs.append([o, o])
    os.makedirs(os.path.join(ROOT, 'work', 'text'), exist_ok=True)
    with open(os.path.join(ROOT, 'work', 'text', 'strings.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('off\tend\tnref\tref0\ttext\n')
        for a, b, toks in strs:
            w.write('%06X\t%06X\t%d\t%06X\t%s\n' % (a, b, len(refs[a]), refs[a][0], render(toks, t)))
    print('문자열', len(strs), '· 덮지 못한 글자 워드', len(miss), '· 덩어리', len(runs))
    for a, b in runs[:40]:
        toks, _ = parse(e, t, a, a + 80)
        print('  %06X-%06X %s' % (a, b, render(toks, t)[:60]))
    return strs

if __name__ == '__main__':
    main()
