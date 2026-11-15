# -*- coding: utf-8 -*-
r"""타워 오브 둠(TOD) 한글 빌더 (2026-11-14).
  입력: EBOOT(work/build/EBOOT.BIN = SOM 빌드 결과 위에 덧씀, 없으면 원본) · game_data/dd11x.bin(원본)
        work/text/tod_units.tsv(추출) · work/text/tsv_ko/tod_*.tsv(번역)
  · 글 = 큰 끝 16비트, 4040 끝 · 2F2F 줄바꿈 · FFFF n… 제어 · 머리 워드 그대로.
  · 한글 16x16 = 번역에 안 쓰는 한자·가나 칸(영문 이름판용 전각 영문·숫자·Ⅰ~Ⅴ·＆‼？ー 는 남김)에 갈무리11,
    글자 1(흰) + 오른쪽·아래 E 그림자, F 투명. 16x16 코드 c = 8x8 칸 c·c+1·c+16·c+17(칸 64 B, 앞 32 B 4bpp 아래 니블 왼쪽).
  · 제자리 → 넘치면 남는 자리(줄어든 꼬리·옮긴 자리)로. 참조 = 본문 표 0x2211E0(10 B 레코드 첫 워드, 표 기준) ·
    가게 표 0x2E8F4C(표 기준) · 0x220990 작은 표 · VA 포인터(글 구역 0x220000~0x320000 안만).
  · 8x8 아이템 이름 = 작은 가나 칸(0x580~·0x780~)에 han8 한글(획 0 + 테두리 E).
  · 이름 입력 = 영문 배치(격자 0x14A33E0, 글자 목록 0x30CC96 번호) · もどる/おわる(8x8) → 뒤로/완료.
  출력: work/build/EBOOT.BIN(덧씀) · work/build/dd11x.bin · work/build/report_tod.txt"""
import os, sys, re, struct, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools'); sys.path.insert(0, r'C:\claude\project\quovadis2-kr-patch\tools')
import tod_codetable as tc
from bdf import Font
R = lambda *p: os.path.join(ROOT, *p)
VA = 0x10000; END = 0x1402668
ZONE = (0x220000, 0x320000)                       # 글·포인터 구역(코드 구역 우연값 금지)
MAIN_TAB, SHOP_TAB, SMALL_TAB = 0x2211E0, 0x2E8F4C, 0x220990
GRID = 0x14A33E0
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？：；:;～~])[ 　]+')
W = lambda e, o: struct.unpack_from('>H', e, o)[0]
# 영문 이름판(목록 번호): Ａ=0x6E · ０=0x88 · Ⅰ=0x92 · ＆0x98 ‼0x99 ？0x9A ー0x9B · 빈칸 0x37
_A = [0x6E + i for i in range(26)]; _D = [0x88 + i for i in range(10)]; SP = 0x37
NAME_GRID = (_A[0:10] + _A[10:20] + _A[20:26] + [0x98, 0x99, 0x9A, 0x9B] + _D + [0x92, 0x93, 0x94, 0x95, 0x96] + [SP] * 5 + [SP] * 10)
def cells_of(c): return (c, c + 1, c + 16, c + 17)
def put8(g, n, a):
    nib = a.reshape(-1).astype(np.uint8); g[n * 64:n * 64 + 32] = bytes((nib[0::2] & 15) | ((nib[1::2] & 15) << 4))
def get8(g, n):
    b = np.frombuffer(bytes(g[n * 64:n * 64 + 32]), np.uint8); p = np.empty(64, np.uint8); p[0::2] = b & 15; p[1::2] = b >> 4
    return p.reshape(8, 8)
def put16(g, c, a):
    put8(g, c, a[:8, :8]); put8(g, c + 1, a[:8, 8:]); put8(g, c + 16, a[8:, :8]); put8(g, c + 17, a[8:, 8:])
def glyph16(font, ch):
    a = np.full((16, 16), 15, np.uint8); ink = np.zeros((16, 16), bool)
    if ch in '.,':
        if ch == '.': ink[12:14, 3:5] = True
        else: ink[12:14, 3:5] = True; ink[14, 3] = True
    elif ch == '…':
        for x in (2, 7, 12): ink[12:14, x:x + 2] = True
    else:
        pts, w = font.draw(ch)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        dx = (16 - (max(xs) - min(xs) + 1)) // 2 - min(xs); dy = 3 + (12 - (max(ys) - min(ys) + 1)) // 2 - min(ys)
        for x, y in pts:
            if 0 <= x + dx < 15 and 0 <= y + dy < 15: ink[y + dy, x + dx] = True
    sh = np.zeros_like(ink); sh[:, 1:] |= ink[:, :-1]; sh[1:, :] |= ink[:-1, :]; sh[1:, 1:] |= ink[:-1, :-1]
    a[sh & ~ink] = 14; a[ink] = 1
    return a
def glyph8(ch):
    import han8
    g, w = han8.glyph(ch); m = np.array(g, bool)[:8, :8]
    a = np.full((8, 8), 15, np.uint8); ol = np.zeros_like(m)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            s = np.zeros_like(m)
            ys, xs = np.nonzero(m); ys2, xs2 = ys + dy, xs + dx; k = (ys2 >= 0) & (ys2 < 8) & (xs2 >= 0) & (xs2 < 8)
            s[ys2[k], xs2[k]] = True; ol |= s
    a[ol & ~m] = 14; a[m] = 0
    return a
def load_ko():
    ko = {}
    for f in sorted(os.listdir(R('work', 'text', 'tsv_ko'))):
        if not f.startswith('tod_'): continue
        for ln in open(R('work', 'text', 'tsv_ko', f), encoding='utf-8').read().split('\n')[1:]:
            c = ln.split('\t')
            if len(c) >= 4 and c[3]: ko[c[2]] = PUNCT_SP.sub(lambda m: m.group(1), c[3])
    return ko
TOK = re.compile(r'\{w([0-9A-F.]+)\}|\{([0-9A-F]{4})\}|(／)|(.)', re.S)
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    T = tc.table(); T8 = tc.table8()
    RT = collections.defaultdict(list)
    for c, ch in sorted(T.items()): RT[ch].append(c)
    RT8 = {}
    for c, ch in sorted(T8.items()): RT8.setdefault(ch, c)
    src = R('work', 'build', 'EBOOT.BIN') if os.path.exists(R('work', 'build', 'EBOOT.BIN')) else R('work', 'bin', 'EBOOT.elf')
    e0 = open(R('work', 'bin', 'EBOOT.elf'), 'rb').read(); e = bytearray(open(src, 'rb').read()); e0_som = bytes(e)
    g = bytearray(open(R('work', 'orig', 'game_data', 'dd11x.bin'), 'rb').read())
    units = []
    for ln in open(R('work', 'text', 'tod_units.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) < 6: continue
        units.append(dict(start=int(c[0], 16), end=int(c[1], 16), kind=c[2], head=[int(h, 16) for h in c[3].split(',') if h], refs=c[4], jp=c[5]))
    ko = load_ko(); rep = []; log = lambda s: (rep.append(s), print(s))
    # 줄 폭 검사(2026-11-14 하스피 «얼굴 대화상자 칸 벗어남»): 창 머리 코드별 원문 최대 줄 길이 = 창 폭
    _st = lambda t: re.sub(r'\{[^}]*\}', '', t)
    _W = collections.defaultdict(int)
    for u in units:
        if u['kind'] == '16' and u['head']:
            for ln in _st(u['jp']).split('／'): _W[u['head'][0]] = max(_W[u['head'][0]], len(ln))
    _over = [(u['jp'][:12], ln) for u in units if u['kind'] == '16' and u['head'] and ko.get(u['jp'])
             for ln in _st(ko[u['jp']]).split('／') if len(ln) > _W[u['head'][0]]]
    log(('⛔줄 폭 넘침 %d %s' % (len(_over), _over[:10])) if _over else '줄 폭 넘침 0')
    # ── 글자 칸 배정
    used_ko = set()
    for u in units:
        k = ko.get(u['jp'])
        if k and u['kind'] == '16': used_ko |= set(re.sub(r'\{[^}]*\}', '', k))
    keep_ch = set('ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ０１２３４５６７８９ⅠⅡⅢⅣⅤ＆‼？ー　 ') | {ch for ch in used_ko if not ('가' <= ch <= '힣')}
    toks = set()
    for u in units: toks |= {int(m, 16) for m in re.findall(r'\{([0-9A-F]{4})\}', u['jp'])}
    t8cells = set(T8)
    pool = [c for c, ch in sorted(T.items()) if ch not in keep_ch and c not in toks and not (set(cells_of(c)) & t8cells) and not any(0xE00 <= x < 0x1000 for x in cells_of(c))
            and ('぀' <= ch <= 'ヿ' or '一' <= ch <= '鿿' or ch in 'Ⅵ Ⅶ Ⅷ Ⅸ Ⅹ、。．，／©＿‥')]
    need = sorted(ch for ch in used_ko if '가' <= ch <= '힣') + ['.', ','] + sorted(ch for ch in used_ko if ch not in RT and not ('가' <= ch <= '힣') and ch not in '.,／ ')
    if len(need) > len(pool):                         # 모자라면 한자 판 안 빈 16x16 자리(0x3A00~0x3FFF, 4칸 모두 투명) — TOD 스테이트 4개 scroll1 에서 안 쓰임 확인
        blank = lambda n: bytes(g[n * 64:n * 64 + 32]) == b'\xff' * 32
        extra = [c for c in range(0x3A00, 0x4000, 2) if c % 32 < 16 and c not in T and all(blank(x) for x in cells_of(c))]
        pool += extra[:len(need) - len(pool)]
        log('빈 자리 %d 칸 더 씀(0x3A00~)' % len(extra[:len(need) - (len(pool) - len(extra[:0]))]))
    log('한글 16x16 필요 %d · 칸 %d' % (len(need), len(pool)))
    if len(need) > len(pool): raise SystemExit('⛔칸 모자람 %d' % (len(need) - len(pool)))
    font = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'); slot = {}
    for ch, c in zip(need, pool): slot[ch] = c; put16(g, c, glyph16(font, ch))
    for c in RT.get('…', []): put16(g, c, glyph16(font, '…'))              # 한국식 바닥 말줄임표
    def code16(ch):
        if ch in slot: return slot[ch]
        if ch == ' ': return RT['　'][0]
        if ch in RT: return RT[ch][0]
        raise KeyError(ch)
    # 8x8
    used8 = set()
    for u in units:
        if u['kind'] == '8' and ko.get(u['jp']): used8 |= set(ko[u['jp']])
    for s_ in ('뒤로', '완료'): used8 |= set(s_)
    # ★랭킹 이름 = 작은 가타카나 칸 0x780 + 이름 번호(0~44) → 그 45칸은 영문 자리로 비워 둠(2026-11-15 랭킹 «치실이»).
    #   대신 원본에서 완전히 빈(그리고 8x8 글이 안 쓰는) 칸 0x5B0~0x7FF 를 더 씀.
    RANK8 = set(range(0x780, 0x780 + 45)) | {0x5BE, 0x5FF}   # 0x5BE·0x5FF = 원본 빈칸인데 랭킹 화면이 이름 뒤 채움·바탕으로 씀(스테이트 타일맵 실측, «륻» 2026-11-15)
    pool8 = [c for c, ch in sorted(T8.items()) if 0x580 <= c < 0x800 and '぀' <= ch <= 'ヿ' and c not in RANK8]
    pool8 += [c for c in range(0x5B0, 0x800) if c not in T8 and c not in RANK8 and bytes(g[c * 64:c * 64 + 32]) == b'\xff' * 32]
    need8 = sorted(ch for ch in used8 if '가' <= ch <= '힣')
    log('한글 8x8 필요 %d · 칸 %d' % (len(need8), len(pool8)))
    if len(need8) > len(pool8): raise SystemExit('⛔8x8 칸 모자람')
    slot8 = {}
    for ch, c in zip(need8, pool8): slot8[ch] = c; put8(g, c, glyph8(ch))
    # 랭킹 이름 영문: 0x780 + k ← 작은 글꼴 ASCII 칸(같은 그림체). k = 이름 번호(A~Z · & ! ? - · 0~9 · Ⅰ~Ⅴ→1~5)
    RANKCH = [chr(65 + i) for i in range(26)] + ['&', '!', '?', '-'] + [str(i) for i in range(10)] + ['1', '2', '3', '4', '5']
    for k, ch in enumerate(RANKCH): put8(g, 0x780 + k, get8(g0_11 := bytearray(open(R('work', 'orig', 'game_data', 'dd11x.bin'), 'rb').read()) if k == 0 else g0_11, ord(ch)))
    log('랭킹 이름 8x8 영문 %d칸(0x780~)' % len(RANKCH))
    def code8(ch):
        if ch in slot8: return slot8[ch]
        if ch in RT8: return RT8[ch]
        if ch.isdigit(): return RT8[chr(0xFF10 + int(ch))] if chr(0xFF10 + int(ch)) in RT8 else RT8[ch]
        raise KeyError(ch)
    def enc(text, kind):
        out = []
        for m in TOK.finditer(text):
            if m.group(1): out += [0xFFFF] + [int(x, 16) for x in m.group(1).split('.')]
            elif m.group(2): out.append(int(m.group(2), 16))
            elif m.group(3): out.append(0x2F2F)
            else: out.append(code16(m.group(4)) if kind == '16' else code8(m.group(4)))
        return out
    # ── 참조 찾기(원본 기준)
    def table(base, stride):                       # 추출기와 같음: 표 끝 = 지금까지 본 가장 작은 오프셋 자리
        out = []; i = 0; lim = 0x4000
        while i * stride < lim:
            off = W(e0, base + i * stride)
            if off: lim = min(lim, off); out.append((base + i * stride, base + off))
            i += 1
        return out
    TABS = [(o, t, MAIN_TAB) for o, t in table(MAIN_TAB, 10)] + [(o, t, SHOP_TAB) for o, t in table(SHOP_TAB, 2)] +            [(SMALL_TAB + 2 * i, SMALL_TAB + W(e0, SMALL_TAB + 2 * i), SMALL_TAB) for i in range(9)]
    tab_idx = collections.defaultdict(list)
    for o, t, base in TABS: tab_idx[t].append(('T', o, base))
    def refs_to(addr): return list(tab_idx.get(addr, []))
    va_idx = collections.defaultdict(list)
    for o in range(ZONE[0], ZONE[1] - 3, 2):
        v = struct.unpack_from('>I', e0, o)[0] - VA
        if ZONE[0] <= v < ZONE[1]: va_idx[v].append(o)
    # ── 넣기
    stats = collections.Counter(); holes = []; pending = []
    plan = []
    for u in units:
        k = ko.get(u['jp'])
        if not k: stats['번역 없음'] += 1; continue
        try: body = enc(k, u['kind'])
        except KeyError as x: log('⛔글자 없음 %06X %r' % (u['start'], x)); stats['오류'] += 1; continue
        words = u['head'] + body + [0x4040]
        raw = b''.join(struct.pack('>H', w) for w in words)
        cap = u['end'] - u['start']
        refs = []
        for addr, delta in ((u['start'], 0), (u['start'] + 2 * len(u['head']), 2 * len(u['head']))):
            for r in refs_to(addr): refs.append((r, delta))
            for o in va_idx.get(addr, []): refs.append((('V', o, 0), delta))
        plan.append((u, raw, cap, refs))
    # 문장 한가운데를 가리키는 VA 가 있으면 고정
    inner = set()
    for v, os_ in va_idx.items():
        for u, raw, cap, refs in plan:
            if u['start'] < v < u['start'] + cap and v != u['start'] + 2 * len(u['head']): inner.add(u['start'])
    movable = lambda u, refs: refs and all(r[0][0] in 'TV' for r in refs) and u['refs'] not in ('FRAG', '-') and u['start'] not in inner
    fixed = [(u, raw, cap, refs) for u, raw, cap, refs in plan if not movable(u, refs)]
    mov = [(u, raw, cap, refs) for u, raw, cap, refs in plan if movable(u, refs)]
    for u, raw, cap, refs in fixed:
        if len(raw) > cap: log('⛔넘침(고정) %06X %d>%d %s' % (u['start'], len(raw), cap, ko.get(u['jp'])[:20])); stats['넘침'] += 1; continue
        e[u['start']:u['start'] + len(raw)] = raw; e[u['start'] + len(raw):u['start'] + cap] = b'\0' * (cap - len(raw)); stats['제자리(고정)'] += 1
        # ★글 안쪽을 가리키는 VA(오프닝 쪽 포인터 표 0x244068~ 등) = «k번째 FFFF 제어 + d워드» → 새 글의 같은 자리로(2026-11-15 TOD 오프닝 2쪽 크래시)
        a0 = u['start']; ends = u['start'] + cap
        fo = [a for a in range(a0, ends, 2) if W(e0, a) == 0xFFFF]
        fn = [a for a in range(a0, a0 + len(raw), 2) if W(e, a) == 0xFFFF]
        for v, os_ in (va_idx.items() if not os.environ.get('NO_INNER') else []):
            if not (a0 < v < ends) or v == a0 + 2 * len(u['head']): continue
            k = max([i for i, f in enumerate(fo) if f <= v], default=None)
            if k is None or len(fo) != len(fn):
                log('  안쪽 포인터 못 맞춤 %06X → %06X (글 %06X, FFFF 원 %d 새 %d) %s' % (os_[0], v, a0, len(fo), len(fn), ko.get(u['jp'])[:16]))
                stats['안쪽 포인터 못 맞춤'] += 1; continue
            nv = fn[k] + (v - fo[k])
            for o in os_: struct.pack_into('>I', e, o, nv + VA)
            stats['안쪽 포인터'] += 1
    # 옮길 것들의 원래 자리 = 빈자리, 붙은 것끼리 합침
    sl = sorted([u['start'], u['start'] + cap] for u, raw, cap, refs in mov)
    for h in sl: e[h[0]:h[1]] = b'\0' * (h[1] - h[0])
    for h in sl:
        if holes and holes[-1][1] == h[0]: holes[-1][1] = h[1]
        else: holes.append(list(h))
    log('빈자리 %d 개 · 큰 것 %s' % (len(holes), sorted((h[1] - h[0] for h in holes), reverse=True)[:6]))
    mov.sort(key=lambda x: (not any(r[0][0] == 'T' for r in x[3]), -len(x[1])))   # 표로 묶인 것 먼저
    for u, raw, cap, refs in mov:
        def ok(h):
            if h[1] - h[0] < len(raw): return False
            for (kind, o, base), delta in refs:
                if kind == 'T' and not (0 < h[0] + delta - base < 0x8000): return False   # 표 오프셋은 부호 있는 16비트(0x8000 넘으면 음수 → 상점 멈춤, 2026-11-15)
            return True
        fit = [h for h in holes if ok(h)]
        if not fit: log('⛔자리 없음 %06X %d B' % (u['start'], len(raw))); stats['넘침'] += 1; continue
        h = min(fit, key=lambda h: h[1] - h[0]); pos = h[0]
        e[pos:pos + len(raw)] = raw; h[0] += len(raw)
        if pos != u['start']:
            for (kind, o, base), delta in refs:
                if kind == 'T': struct.pack_into('>H', e, o, pos + delta - base)
                else: struct.pack_into('>I', e, o, pos + delta + VA)
            stats['옮김'] += 1; stats['포인터'] += len(refs)
        else: stats['제자리'] += 1
    # 검산: 참조를 따라가면 넣은 바이트가 나와야
    bad = 0
    for u, raw, cap, refs in plan:
        for (kind, o, base), delta in refs:
            tgt = (base + W(e, o)) if kind == 'T' else (struct.unpack_from('>I', e, o)[0] - VA)
            if bytes(e[tgt - delta:tgt - delta + len(raw)]) != raw:
                bad += 1
                inside = [x['start'] for x, _, c_, _ in plan if x['start'] <= o < x['start'] + c_]
                log('  불일치 %06X %s 참조 %s@%06X 델타 %d 대상 %06X · 참조 자리가 문장 안 %s' % (u['start'], u['kind'], kind, o, delta, tgt, [hex(i) for i in inside]))
    log('검산 참조 불일치 %d' % bad)
    big = [hex(o) for o, t, base in TABS if W(e, o) >= 0x8000]
    if big: raise SystemExit('⛔표 오프셋 0x8000 이상(부호 있는 16비트라 음수가 됨) %s' % big)
    import itertools
    d = [i for i in range(0, len(e), 2) if e[i:i + 2] != e0_som[i:i + 2]]
    out = [hex(i) for i in d if not (ZONE[0] <= i < ZONE[1] or GRID <= i < GRID + 60 or 0x1293000 <= i < 0x1297400 or 0x24772E <= i < 0x24784E)]
    log('바뀐 워드 %d · 구역 밖 %d %s' % (len(d), len(out), out[:5]))
    # 옮긴 옛 자리 중 빈자리로 안 쓰인 곳 = 0 채움은 하지 않음(원래 글 남아도 가리킴 없음)
    # ── 이름 입력 영문
    e[GRID:GRID + 60] = bytes(NAME_GRID)
    # 화면 글자판 = 세로줄 글 스크립트 10개(0x24772E~: «XX08 0010» + 코드 6개(2F2F 사이) + 4040) — 격자표와 같은 배치로(2026-11-14, 그대로 가나→한글로 찍혀 하스피 지적)
    o = 0x24772E
    for c in range(10):
        assert e[o + 1] == 0x08 and e[o + 2:o + 4] == bytes([0, 0x10]), ('글자판 줄 머리', hex(o))
        o += 4
        for r in range(6):
            v = NAME_GRID[r * 10 + c]; struct.pack_into('>H', e, o, W(e, 0x30CC96 + 2 * v)); o += 2
            if r < 5: assert e[o:o + 2] == bytes([0x2F, 0x2F]), hex(o); o += 2
        assert e[o:o + 2] == bytes([0x40, 0x40]), hex(o); o += 2
    log('이름 입력 화면 글자판 10줄 영문')
    # HUD 이름 = 번호 → 8x8 코드 표(0x246E08)가 가나 번호 0x00~0x6D 까지만 있음 → 영문 번호(0x6E~)는 표 뒤 자료를 읽어 엉뚱한 칸(2026-11-14 하스피 «아래에 이름 이상하게»).
    # 영문 글자를 가나 번호 0x00~ 자리로 옮김: 큰 글꼴 목록(0x30CC96)·HUD 표 둘 다 그 번호에 영문 코드 → 배치표도 새 번호.
    L16, H8 = 0x30CC96, 0x246E08
    old = [v for v in dict.fromkeys(NAME_GRID) if v != SP]
    hud = {0x98: 0x26, 0x99: 0x21, 0x9A: 0x3F, 0x9B: 0x2D}                       # ＆ ‼→! ？ ー→-
    hud.update({0x6E + i: 0x41 + i for i in range(26)}); hud.update({0x88 + i: 0x30 + i for i in range(10)})
    hud.update({0x92 + i: 0x31 + i for i in range(5)})                           # Ⅰ~Ⅴ = 8x8 에 없음 → 1~5
    remap = {}
    for k, v in enumerate(old):
        struct.pack_into('>H', e, L16 + 2 * k, W(e0, L16 + 2 * v)); struct.pack_into('>H', e, H8 + 2 * k, hud[v]); remap[v] = k
    e[GRID:GRID + 60] = bytes(remap.get(v, v) for v in NAME_GRID)
    log('이름 번호 %d개 → 가나 번호 자리(HUD 8x8 영문)' % len(remap))
    # 랭킹 기본 이름 30명(0x149ACD0~, 16 B: 점수 4·레벨·직업·00 00·이름 8 B FF 끝) → 영문(새 번호 A=0…, 6자 이하, 2026-11-15 하스피 «ㄱ»)
    RANK = ['YAN', 'SADRAN', 'AUGSTA', 'BRAVO', 'HILKAD', 'ARKOF', 'BRAFRD', 'GRIMHD', 'LARVA', 'CREMAT', 'ILFING', 'ALMA', 'CALVRT',
            'YUINO', 'BRASS', 'GWEN', 'ALLEN', 'JEDAS', 'IJUST', 'MARIEL', 'GERANT', 'GARUN', 'ENID', 'RAGNEL', 'MARS', 'ALMINA',
            'ORFEUS', 'RELIAN', 'SHERA', 'ERLING']   # 30번째 エルリング(2026-11-15 «D19톰실»)
    for k, nm in enumerate(RANK):
        o = 0x149ACD0 + 16 * k
        assert e0[o + 8] != 0xFF and len(nm) <= 6, ('랭킹 기록', hex(o))
        e[o + 8:o + 16] = bytes(ord(c) - 65 for c in nm) + b'\xff' * (8 - len(nm))
    log('TOD 랭킹 기본 이름 %d명 영문' % len(RANK))
    # 데모·기본 캐릭터 이름 4명(가나 번호 8 B×4) 세 벌 → 같은 표 바로 뒤 영문판 이름(CRASSUS·GRELDON·LUCIA·DIMSDALE, A=0 번호) 그대로(2026-11-15 «데모 이름 깨짐»)
    EN4 = e0[0x243F30:0x243F50]
    assert EN4[:8] == bytes([2, 17, 0, 18, 18, 20, 18, 0xFF]), '영문 이름표'
    for o in (0x243F10, 0x14A3508, 0x14A3DC8):
        assert e0[o:o + 32] == e0[0x243F10:0x243F30], ('데모 이름표', hex(o))
        e[o:o + 32] = EN4
    log('데모 기본 이름 4명 영문 3벌')
    # ★실제 HUD 이름 글꼴 = dd11x 8x8 칸 0x700 + 번호(HUD 바닥 무늬 4·5·6 위 획 색 1) — 0x246E08 표가 아님(«クソテタケ», 2026-11-14)
    #   번호 0~0x2C 칸에 영문: 바닥 = 0x700~0x77F 묶음 자리별 최빈 바탕색, 획 = ASCII 8x8 칸(0x41 등)의 획(색 0~3) 모양
    hud_cells = np.stack([get8(g, 0x700 + i) for i in range(0x80)])
    bgm = np.zeros((8, 8), np.uint8)
    for y in range(8):
        for x in range(8):
            v = hud_cells[:, y, x]; v = v[v != 1]; bgm[y, x] = np.bincount(v, minlength=16).argmax()
    for v, k in remap.items():
        src = get8(g, hud[v]); m = np.isin(src, (0, 1, 2, 3))
        out = bgm.copy(); out[m] = 1; put8(g, 0x700 + k, out)
    log('HUD 이름 글꼴 0x700~ 영문 %d칸' % len(remap))
    for jp, kr in (('もどる', '뒤로'), ('おわる', '완료')):
        i = -1
        for o in range(ZONE[0], ZONE[1] - 6, 2):
            if W(e, o) == RT8[jp[0]] and W(e, o + 4) == RT8[jp[2]] and (jp[1] not in RT8 or W(e, o + 2) == RT8[jp[1]]): i = o; break
        if i < 0: log('⛔%s 없음' % jp); continue
        ws = [RT8[' ']] * (len(jp) - len(kr)) + [code8(ch) for ch in kr]   # 공백을 앞에 = 커서 자리(원문 3칸 가운데)에 맞춤(하스피 지적)
        e[i:i + 2 * len(jp)] = b''.join(struct.pack('>H', w) for w in ws)
    import eboot_ui
    eboot_ui.apply(e, log)                              # 시스템 UTF-8 문구(저장·트로피 등)
    log('TOD %s' % dict(stats))
    od = R('work', 'build'); os.makedirs(od, exist_ok=True)
    import tod_hud_gfx                                    # 아이템 이름 띠(dd11x)·캐릭터 설명 상자(dd10) — 롬 그림 글자
    d10 = bytearray(open(R('work', 'orig', 'game_data', 'dd10.bin'), 'rb').read())
    tod_hud_gfx.apply(d10, g, log)
    import tod_balloons; tod_balloons.apply(d10, log)   # 상자 함정·열쇠 말풍선(dd10 0x8C02~·0x87A0~, 2026-11-15)
    open(os.path.join(od, 'dd10.bin'), 'wb').write(d10)
    import key_hud; key_hud.apply(g, log)                # 열쇠 HUD «カギ=» → «열쇠=»(dd11x 0x2780·0x27B1·0x27C3, 2026-11-15)
    open(os.path.join(od, 'EBOOT.BIN'), 'wb').write(e); open(os.path.join(od, 'dd11x.bin'), 'wb').write(g)
    open(os.path.join(od, 'report_tod.txt'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    # 글자판 미리보기
    from PIL import Image
    pal = np.zeros((16, 3), np.uint8); pal[:] = (120, 120, 120); pal[0] = pal[1] = (255, 255, 255); pal[14] = (20, 20, 20); pal[15] = (50, 60, 100)
    tiles = [np.vstack([np.hstack([get8(g, c), get8(g, c + 1)]), np.hstack([get8(g, c + 16), get8(g, c + 17)])]) for c in list(slot.values())[:320]]
    rows = [np.hstack(tiles[i:i + 32] + [np.full((16, 16), 15, np.uint8)] * (32 - len(tiles[i:i + 32]))) for i in range(0, len(tiles), 32)]
    Image.fromarray(pal[np.vstack(rows)]).resize((512 * 2, len(rows) * 32), 0).save(R('work', 'build', 'tod_glyphs.png'))
    t8 = [get8(g, c) for c in slot8.values()]
    Image.fromarray(pal[np.hstack(t8)]).resize((len(t8) * 24, 24), 0).save(R('work', 'build', 'tod_glyphs8.png'))
if __name__ == '__main__':
    main()
