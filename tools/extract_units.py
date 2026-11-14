# -*- coding: utf-8 -*-
r"""미스타라(SOM) 본편 번역 단위 추출 (2026-11-13) — 포인터 기준, 누락 0 검산.
  세그먼트 0: VA = 파일 오프셋 + 0x10000. 글 포인터 = 2정렬 32비트 VA.
  토큰: 0000 끝 · FFFF x y 줄바꿈(x = −글자수×16, 빌더가 다시 계산) · FFFE n 색 · 7000~700F 이름 매크로.
  단위 = 겹치는 문자열을 합친 «덩어리»(시작~0000). 덩어리 안쪽을 가리키는 포인터 자리는 {＊} 로 표시
         (번역에서도 같은 뜻 자리에 {＊} 를 둬야 함).
  머리 = 글 앞 날 워드(아이템 메시지의 x·y 등, 2개까지) — TSV 에 안 내보내고 빌더가 그대로 씀.
  표기: 줄바꿈 ／ · 색 {c18} 꼴 · 매크로 {N0} 꼴 · 빈 문자열은 내보내지 않음.
  출력: work/text/units.tsv(전체·위치·머리·줄 y·포인터) · work/text/tsv/mys_NNN.tsv(18KB, 번호·위치·JP·KO, 같은 글 합침)
  python tools/extract_units.py"""
import os, sys, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import codetable
END = 0x1402668
VA = 0x10000
SPLIT = 18 * 1024
JPR = lambda w: 0x1E00 <= w < 0x1EC0 or 0x1D40 <= w < 0x1D52 or 0x2000 <= w < 0x2200

def W(e, o): return struct.unpack_from('>H', e, o)[0]

def parse(e, t, a):
    """→ (머리 워드들, 토큰들, 끝) 또는 None. 토큰: ('ch',w) ('nl',x,y) ('c',n) ('m',w)."""
    o = a; head = []
    if W(e, o) == 0 and W(e, o + 4) != 0xFFFE:
        return 'empty'
    while len(head) < 2 and W(e, o) not in t and W(e, o) not in (0xFFFF, 0xFFFE) and not 0x7000 <= W(e, o) < 0x7010             and not 0x1800 <= W(e, o) < 0x2000:
        head.append(W(e, o)); o += 2
    toks = []
    while o < END and len(toks) < 800:
        w = W(e, o)
        if w == 0: return head, toks, o + 2
        if w == 0xFFFF: toks.append(('nl', W(e, o + 2), W(e, o + 4), o)); o += 6; continue
        if w == 0xFFFE: toks.append(('c', W(e, o + 2), o)); o += 4; continue
        if 0x7000 <= w < 0x7010: toks.append(('m', w, o)); o += 2; continue
        if w in t: toks.append(('ch', w, o)); o += 2; continue
        if 0x1800 <= w < 0x2000: toks.append(('g', w, o)); o += 2; continue   # 코드표 밖 글자칸(아이콘·괴물 문자) — 그대로 보존
        return None                                    # 모르는 워드 → 글 아님
    return None

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    t = codetable.table(); t[0x1800] = '　'
    e = open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read()
    refs = collections.defaultdict(list)
    for o in range(0, END - 3, 2):
        v = struct.unpack_from('>I', e, o)[0] - VA
        if 0 <= v < END and not v & 1: refs[v].append(o)
    good = {}; weak = {}; empty = []
    for a in refs:
        r = parse(e, t, a)
        if r is None: continue
        if r == 'empty': empty.append(a); continue
        head, toks, end = r
        chs = [x[1] for x in toks if x[0] == 'ch']
        if not chs or not any(JPR(w) or w == 0x1EC1 or 0x1ED0 <= w < 0x1F00 for w in chs): continue
        if sum(1 for x in toks if x[0] == 'g') > len(chs) // 2: continue      # 코드표 밖 칸 투성이 = 그림 데이터
        (good if len(chs) >= 2 and any(JPR(w) for w in chs) else weak)[a] = r
    # 한 글자 등 약한 후보 = 참조 자리 바로 옆(±4·±8)에 확실한 글의 참조가 있을 때만
    refpos = {o for a in good for o in refs[a]}
    for _ in range(3):
        add = [a for a in weak if any(o + d in refpos for o in refs[a] for d in (-8, -4, 4, 8))]
        for a in add:
            good[a] = weak.pop(a); refpos |= set(refs[a])
    emp_ok = [a for a in empty if any(o + d in refpos for o in refs[a] for d in (-8, -4, 4, 8))]
    # 덩어리: 같은 끝을 공유하는 문자열 = 하나(가장 앞 시작), 나머지는 안쪽 포인터
    byend = collections.defaultdict(list)
    for a, (head, toks, end) in good.items(): byend[end].append(a)
    units = []
    # 안쪽 포인터 검증: 참조 자리 옆(±4~±0x14)에 «덩어리 시작»을 가리키는 포인터가 있어야 진짜(좌표표 등 우연 일치 제거)
    ustart = {min(st) for st in byend.values()}
    def ptr_at(o):
        if o < 0 or o + 4 > END: return None
        return struct.unpack_from('>I', e, o)[0] - VA
    def trusted(s):
        # 같은 표 안이라 보고: 옆 4칸(±4·±8) 중 둘 이상이 덩어리 시작을 가리키거나, 레코드 간격(±0x14) 양쪽이 다 가리킬 때
        for o in refs[s]:
            if sum(ptr_at(o + d) in ustart for d in (-8, -4, 4, 8)) >= 2: return True
            if ptr_at(o - 0x14) in ustart and ptr_at(o + 0x14) in ustart: return True
        return False
    dropped = 0; notterm = []
    for end, starts in byend.items():
        starts.sort()
        # 앞 워드가 0000 이 아니고 옆 포인터 검증도 안 되는 시작(이름 입력 문자표에 붙은 가짜 시작 등)은 버림
        while len(starts) > 1 and W(e, starts[0] - 2) != 0 and not trusted(starts[0]):
            dropped += 1; starts.pop(0)
        a0 = starts[0]
        head, toks, _ = good[a0]
        if a0 not in ustart: toks = [x for x in toks if x[-1] >= a0]
        body0 = a0 + 2 * len(head)
        inner = [s for s in starts[1:] if trusted(s)]
        dropped += len(starts) - 1 - len(inner)
        if W(e, a0 - 2) != 0: notterm.append(a0)
        # 안쪽 포인터가 토큰 경계/머리에 맞는지
        units.append(dict(start=a0, end=end, head=head, toks=toks, inner=inner,
                          refs=sum(len(refs[s]) for s in starts), ref0=refs[a0][0], body=body0))
    units.sort(key=lambda u: u['start'])
    # 렌더
    def render(u):
        marks = set()
        for s in u['inner']:
            hd = good[s][0]; marks.add(s + 2 * len(hd))
        out = []; ys = []
        pos = [x[-1] for x in u['toks']]
        for x in u['toks']:
            if x[-1] in marks: out.append('{＊}'); marks.discard(x[-1])
            if x[0] == 'ch': out.append(t[x[1]])
            elif x[0] == 'nl': out.append('／'); ys.append('%X' % x[2])
            elif x[0] == 'c': out.append('{c%02X}' % x[1])
            elif x[0] == 'g': out.append('{%04X}' % x[1])
            else: out.append('{N%X}' % (x[1] & 0xF))
        return ''.join(out), ys, marks
    bad_inner = 0
    os.makedirs(os.path.join(ROOT, 'work', 'text', 'tsv'), exist_ok=True)
    rows = []
    with open(os.path.join(ROOT, 'work', 'text', 'units.tsv'), 'w', encoding='utf-8', newline='\n') as w:
        w.write('off\tend\thead\tys\tinner\tnref\tref0\ttext\n')
        for u in units:
            txt, ys, left = render(u)
            if left: bad_inner += 1; print('⚠안쪽 포인터가 토큰 경계 아님 %06X %s' % (u['start'], [hex(x) for x in left]))
            u['txt'] = txt
            w.write('%06X\t%06X\t%s\t%s\t%s\t%d\t%06X\t%s\n' % (u['start'], u['end'], ','.join('%04X' % h for h in u['head']),
                    ','.join(ys), ','.join('%06X' % s for s in u['inner']), u['refs'], u['ref0'], txt))
    # 같은 글 합치기 → TSV
    uniq = collections.OrderedDict()
    for u in units: uniq.setdefault(u['txt'], []).append(u['start'])
    lines = []
    for i, (txt, offs) in enumerate(uniq.items(), 1):
        lines.append('%05d\tEB:%06X(×%d)\t%s\t\n' % (i, offs[0], len(offs), txt))
    head = '번호\t위치\tJP\tKO\n'
    chunks = []; cur = []; size = len(head.encode())
    for ln in lines:
        n = len(ln.encode('utf-8'))
        if cur and size + n > SPLIT: chunks.append(cur); cur = []; size = len(head.encode())
        cur.append(ln); size += n
    if cur: chunks.append(cur)
    d = os.path.join(ROOT, 'work', 'text', 'tsv')
    for f in os.listdir(d):
        if f.startswith('mys_'): os.remove(os.path.join(d, f))
    for i, c in enumerate(chunks, 1):
        open(os.path.join(d, 'mys_%03d.tsv' % i), 'w', encoding='utf-8', newline='\n').write(head + ''.join(c))
    # 검산: 본문 구역(0x6D0000~0x750000)·0x8F0000~0x8FFFFF 안 가나 워드가 덩어리 밖에 있으면 보고
    cov = set()
    for u in units:
        cov.update(range(u['start'], u['end'], 2))
    for a in emp_ok: cov.add(a)
    miss = []
    for lo, hi in ((0x6D0000, 0x750000), (0x8F0000, 0x900000)):
        o = lo
        while o < hi:
            if 0x1E00 <= W(e, o) < 0x1EC0 and o not in cov:
                s = o
                while o < hi and W(e, o) in t and o not in cov: o += 2
                if (o - s) // 2 >= 3: miss.append((s, o))
            o += 2
    nch = sum(sum(1 for x in u['toks'] if x[0] == 'ch') for u in units)
    print('덩어리 %d (안쪽 포인터 %d) · 빈 문자열 %d · 같은 글 합친 뒤 %d줄 · TSV %d개 · 글자 %d' %
          (len(units), sum(len(u['inner']) for u in units), len(emp_ok), len(uniq), len(chunks), nch))
    print('버린 우연 포인터 %d · 앞 워드가 0000 아닌 시작 %d' % (dropped, len(notterm)))
    for a in notterm[:30]: print('  시작 %06X 앞 %04X  %s' % (a, W(e, a - 2), next(u['txt'] for u in units if u['start'] == a)[:40]))
    print('덮이지 않은 가나 3자+ 덩어리 %d' % len(miss))
    for s, o in miss:
        print('  %06X %s' % (s, ''.join(t.get(W(e, p), '?') for p in range(s, min(o, s + 60), 2))))

if __name__ == '__main__':
    main()
