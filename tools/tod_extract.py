# -*- coding: utf-8 -*-
r"""타워 오브 둠(TOD) 글 추출 (2026-11-13).
  글 = EBOOT.elf 세그먼트 0(VA = 파일 오프셋 + 0x10000) 안 큰 끝 16비트. 4040 = 끝 · 2F2F = 줄바꿈.
  ① 큰 글꼴(16x16) 문장 — tools/tod_codetable.table(). 문장 시작을 가리키는 것:
     · 본문 대사: 0x2211E0 레코드 표(5워드 = 표 기준 16비트 오프셋·시간·?·?·0)
     · 가게 대사: 0x2E8F4C 16비트 오프셋 배열(표 기준)
     · 그 밖: 32비트 VA 포인터
     → 셋 다 없는 문자열도 4040 다음부터 문장으로 잡고(누락 방지) «포인터» 칸에 «-» 로 적는다.
     머리 = 앞 0000·포인터 표 조각 건너뛴 뒤, 첫 7워드 안에 0010/000C 가 있으면 거기까지, 없으면 첫 1워드.
  ② 작은 글꼴(8x8) 아이템 이름 — 0x246920~0x246D8C, 포인터 표 0x246838. tod_codetable.table8().
  표기: ／ 줄바꿈 · {XXXX} 코드표 밖 워드(아이콘·HP 칸 등 그대로) · 이름 입력 문자표(가나 한 자씩 ／)는 번역 안 함 → 빼고 보고.
  출력: work/text/tod_units.tsv · work/text/tsv/tod_NNN.tsv(18KB, 번호·위치·JP·KO, 같은 글 합침)
  검산: 0x200000~0x320000 안 큰 글꼴 가나 3자+ 덩어리가 문장 밖에 있으면 보고.
  python tools/tod_extract.py"""
import os, sys, struct, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import tod_codetable as tc
END = 0x1402668
VA = 0x10000
LO, HI = 0x200000, 0x320000
SPLIT = 18 * 1024
ITEM_LO, ITEM_HI = 0x246920, 0x246D8C
MAIN_TAB, MAIN_N = 0x2211E0, None        # 5워드 레코드
SHOP_TAB = 0x2E8F4C
SMALL_TABS = [(0x220990, 9)]        # 표 자리 기준 16비트 오프셋(«あそこだ‼» 등)
FRAG = [(0x30CE0C, 0x30CE52)]        # 레벨업 메시지 조각(は·ＬＥＶＥＬ·になり·ＨＰの·ＭＡＸ·が·上がった。) — 조각마다 머리 1워드
EXCLUDE = {0x30CC56: '이름 입력 글자판(가나 전부 나열)'}


def W(e, o): return struct.unpack_from('>H', e, o)[0]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    T = tc.table(); T8 = tc.table8()
    e = open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read()
    kana16 = {c for c in range(0x100, 0x3F0, 2) if c % 32 < 16}
    # ── 문장 시작 후보(가리키는 것)
    ptr = collections.defaultdict(list)
    for o in range(0, END - 3, 2):
        v = struct.unpack_from('>I', e, o)[0] - VA
        if LO <= v < HI and not v & 1: ptr[v].append('VA@%06X' % o)
    # 본문 레코드 표(장면 번호 순, 빈 칸 = 0) — 표 끝 = 가장 작은 오프셋 자리
    def table(base, stride):
        out = []; i = 0; lim = 0x4000
        while i * stride < lim:                      # 표 끝 = 지금까지 본 가장 작은 오프셋 자리
            off = W(e, base + i * stride)
            if off:
                lim = min(lim, off); out.append((base + i * stride, off))
            i += 1
        return out
    t1 = table(MAIN_TAB, 10); t2 = table(SHOP_TAB, 2)
    for o, off in t1: ptr[MAIN_TAB + off].append('T1@%06X' % o)
    for o, off in t2: ptr[SHOP_TAB + off].append('T2@%06X' % o)
    for base, n in SMALL_TABS:
        for i in range(n): ptr[base + W(e, base + 2 * i)].append('T3@%06X' % (base + 2 * i))
    n_main, n_shop = len(t1), len(t2)
    # ── 문장 시작 후보 = 4040 다음 자리 + 가리켜지는 자리 → 같은 끝(다음 4040)끼리 묶어 하나 고름
    ends = [a for a in range(LO, HI, 2) if W(e, a) == 0x4040]
    import bisect
    zrun = {x for x in range(LO + 4, HI, 2) if W(e, x - 2) == 0 and W(e, x - 4) == 0 and W(e, x) != 0}   # 0000 두 개 뒤
    cands = set(x + 2 for x in ends) | {v for v in ptr if LO <= v < HI} | zrun
    group = collections.defaultdict(list)
    for c in cands:
        k = bisect.bisect_left(ends, c)
        if k < len(ends): group[ends[k]].append(c)
    def parse_at(a, b, pointed):
        if b - a < 4 or b - a > 0x1000 or ITEM_LO <= a < ITEM_HI: return None
        ws = [W(e, x) for x in range(a, b, 2)]
        st = 0
        if not pointed:                               # 가리킴 없음: 앞 0000·VA 포인터 표 조각 건너뛰기
            while st < len(ws) and ws[st] == 0: st += 1
            while st + 1 < len(ws) and 0x20 <= ws[st] < 0x34 and ws[st + 1] % 2 == 0: st += 2
        body = ws[st:]
        hd = 1
        for k in range(min(7, len(body))):
            if body[k] in (0x0010, 0x000C):
                hd = k + 1
                if hd < len(body) and body[k] == 0x000C and body[hd] == 0x0010: hd += 1
                break
        head, txt = body[:hd], body[hd:]
        # FFFF n… = 대기·줄 위치 제어(뒤따르는 작은 수 워드까지 한 덩어리) / 코드표 밖 3워드 이상 연속 = 다른 글(8x8 영문 등) → 거기서 끝
        toks = []; i = 0
        while i < len(txt):
            w = txt[i]
            if w == 0xFFFF:
                j = i + 1
                while j < len(txt) and txt[j] < 0x40: j += 1
                toks.append(('w', txt[i + 1:j])); i = j; continue
            if w not in T and w != 0x2F2F and all(x not in T and x != 0xFFFF for x in txt[i:i + 3]) and i + 3 <= len(txt):
                break
            toks.append(('c', w)); i += 1
        cut = i
        txt = [w for k, w in toks if k == 'c']
        chars = [w for w in txt if w in T and w != 0x2323]
        unk = [w for w in txt if w not in T and w != 0x2F2F]
        if len(chars) < 1 or not any(w in kana16 or w >= 0x600 for w in chars): return None
        if len(unk) * 3 > len(txt): return None
        s = ''.join(('{w' + '.'.join('%X' % x for x in v) + '}') if k == 'w' else '／' if v == 0x2F2F else T.get(v, '{%04X}' % v) for k, v in toks)
        start = a + 2 * st
        if start in EXCLUDE: return ('skip', start, EXCLUDE[start])
        parts = s.split('／')
        if len(parts) >= 4 and all(len(p) <= 1 or p.startswith('{') for p in parts): return ('skip', start, s)
        if not pointed and (sum(1 for w in txt if w in kana16) < 2 or len(chars) < 4): return None
        if not pointed and any(w not in T and w != 0x2F2F for w in txt) and '{053B}' not in s: return None   # 가리킴 없는데 코드표 밖 = 그림 자료
        if len(chars) < 2 and not any(r[0] == 'T' for r in ptr.get(a, [])): return None              # 한 글자 = 표가 가리킬 때만
        if not any(r[0] == 'T' for r in ptr.get(a, [])) and len(chars) < 8 and any(w not in T and w != 0x2F2F for w in txt): return None   # VA 우연 일치 + 코드표 밖
        endo = b + 2 if cut >= len(body) - hd else start + 2 * (hd + cut)
        return ('ok', dict(kind='16', start=start, body=start + 2 * hd, end=endo, head=head, txt=s,
                           refs=ptr.get(start, []) + ptr.get(start + 2 * hd, [])))
    units = []; skipped = []
    for b, cs in sorted(group.items()):
        cs.sort()
        seg0 = cs[0]
        def ok_pt(c):                                 # 표(T1·T2)는 그대로, VA 는 덩어리 첫머리 근처나 포인터 표 조각 뒤일 때만
            if any(r[0] == 'T' for r in ptr[c]): return True
            pre = [W(e, x) for x in range(seg0, c, 2)]
            return c - seg0 <= 16 or any(0x20 <= pre[j] < 0x34 and pre[j + 1] % 2 == 0 and pre[j + 1] > 0x40 for j in range(max(0, len(pre) - 12), len(pre) - 1))   # 바로 앞(12워드 안)에 VA 포인터 표
        pts = [c for c in cs if c in ptr and ok_pt(c) and b - c <= 0x1000]
        tp = [c for c in pts if any(r[0] == 'T' for r in ptr[c])]
        order = tp + [c for c in pts if c not in tp] + [c for c in cs if c not in pts]
        for a in order:                               # 앞에서부터 «글로 읽히는» 첫 시작
            r = parse_at(a, b, a in pts)
            if r == 'skip' or r is None: continue
            if r[0] == 'skip': skipped.append(r[1:]); break
            units.append(r[1]); break

    # ── 조각 구역: 4040 사이 하나하나(머리 1워드)
    for lo, hi in FRAG:
        units[:] = [u for u in units if not (lo <= u['start'] < hi)]
        a = lo
        while a < hi:
            b = a
            while W(e, b) != 0x4040: b += 2
            txt = [W(e, x) for x in range(a + 2, b, 2)]
            units.append(dict(kind='16', start=a, body=a + 2, end=b + 2, head=[W(e, a)], refs=['FRAG'],
                              txt=''.join(T.get(w, '{%04X}' % w) for w in txt)))
            a = b + 2
    # ── 8x8 아이템 이름
    a = ITEM_LO; s0 = a; cur = []
    while a < ITEM_HI:
        w = W(e, a); a += 2
        if w == 0x4040:
            units.append(dict(kind='8', start=s0, body=s0, end=a, head=[], txt=''.join(cur), refs=ptr.get(s0, [])))
            s0 = a; cur = []
        else: cur.append(T8.get(w, '{%04X}' % w))
    units.sort(key=lambda u: u['start'])
    # ── 쓰기
    d = os.path.join(ROOT, 'work', 'text'); os.makedirs(os.path.join(d, 'tsv'), exist_ok=True)
    with open(os.path.join(d, 'tod_units.tsv'), 'w', encoding='utf-8', newline='\n') as f:
        f.write('off\tend\tkind\thead\trefs\ttext\n')
        for u in units:
            f.write('%06X\t%06X\t%s\t%s\t%s\t%s\n' % (u['start'], u['end'], u['kind'], ','.join('%04X' % h for h in u['head']),
                                                  ','.join(u['refs'][:3]) or '-', u['txt']))
    uniq = collections.OrderedDict()
    for u in units:
        if u['txt'].strip(): uniq.setdefault(u['txt'], []).append(u['start'])
    lines = ['%05d\tTD:%06X(×%d)\t%s\t\n' % (i, offs[0], len(offs), txt) for i, (txt, offs) in enumerate(uniq.items(), 1)]
    head = '번호\t위치\tJP\tKO\n'
    chunks = []; cur = []; size = len(head.encode())
    for ln in lines:
        n = len(ln.encode('utf-8'))
        if cur and size + n > SPLIT: chunks.append(cur); cur = []; size = len(head.encode())
        cur.append(ln); size += n
    if cur: chunks.append(cur)
    for fn in os.listdir(os.path.join(d, 'tsv')):
        if fn.startswith('tod_'): os.remove(os.path.join(d, 'tsv', fn))
    for i, c in enumerate(chunks, 1):
        open(os.path.join(d, 'tsv', 'tod_%03d.tsv' % i), 'w', encoding='utf-8', newline='\n').write(head + ''.join(c))
    # ── 검산
    cov = set()
    for u in units: cov.update(range(u['start'], u['end'], 2))
    for s, _ in skipped: cov.add(s)
    miss = []; o = LO
    while o < HI:
        if W(e, o) in kana16 and W(e, o) < 0x280 and o not in cov:
            s = o
            while o < HI and (W(e, o) in T or W(e, o) == 0x2F2F) and o not in cov: o += 2
            if sum(1 for x in range(s, o, 2) if W(e, x) in kana16) >= 3: miss.append((s, o))
        o += 2
    nch = sum(len(u['txt'].replace('／', '')) for u in units)
    nopt = [u for u in units if not u['refs']]
    print('문장 %d (큰 글꼴 %d · 아이템 %d) · 같은 글 합친 뒤 %d줄 · TSV %d개 · 글자 약 %d' %
          (len(units), sum(u['kind'] == '16' for u in units), sum(u['kind'] == '8' for u in units), len(uniq), len(chunks), nch))
    print('본문 레코드 표 %d개 · 가게 오프셋 표 %d개 · 가리키는 것 못 찾은 문장 %d' % (n_main, n_shop, len(nopt)))
    for u in nopt[:40]: print('  가리킴 없음 %06X %s' % (u['start'], u['txt'][:30]))
    print('뺀 것(이름 입력 문자표 등) %d' % len(skipped))
    for s, t in skipped: print('  %06X %s' % (s, t[:50]))
    print('덮이지 않은 큰 글꼴 가나 덩어리 %d' % len(miss))
    for s, o in miss: print('  %06X~%06X' % (s, o))


if __name__ == '__main__':
    main()
