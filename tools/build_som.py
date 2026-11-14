# -*- coding: utf-8 -*-
r"""SOM 본편 한글 빌더 (2026-11-13) — 번역 TSV 전부를 EBOOT 에 넣고 dd21x 글꼴 칸에 한글을 그린다.
  입력: work/text/tsv_ko/mys_*.tsv(번호·위치·JP·KO) · work/text/units.tsv(덩어리) · work/bin/EBOOT.elf · work/orig/game_data/dd21x.bin
  규칙(원본 실측):
   · 줄바꿈 FFFF x y — x = −16 × 앞 줄 칸 수(글자·글리프·이름 매크로 = 1칸, 색 = 0), y = 원문 그 줄 값
   · 아이템 메시지({c0C} 로 시작, 머리 2워드) 머리 x = (368 − 16 × 첫 줄 칸 수)/2 — 원문이 그 공식을 따를 때만
   · 덩어리가 원래 자리보다 길면 빈 0 구간(0x675410~)으로 옮기고 그 덩어리 시작을 가리키는 VA 포인터 전부 교체
   · 한글 음절 → 글꼴 칸: 한자 0x2000~0x21FF(‼ 2170·⁉ 217D 제외) → 1D40~1D51 → 가나 1E00~1EBF(괴물 문자 1E54~1E5A 제외)
   · 글꼴 = 갈무리14 BDF, 0 = 흰 글자 · E = 오른쪽·아래 그림자 · F = 투명 (poc_build 와 같음) · 바닥 «.» «…» «+» 새로 그림
   · 이름 입력 글자판 = 영문판 배치(poc_build.name_grid_english)
  출력: work/build/EBOOT.BIN(평문 ELF) · work/build/dd21x.bin · work/build/report.txt · work/build/glyphs.png
  python tools/build_som.py"""
import os, re, sys, glob, struct, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import codetable, ps3gfx
import extract_units as X
import poc_build as P
from bdf import Font

END = 0x1402668; VA = 0x10000
# 포인터 교체는 글 데이터 구역 안의 표에서만 — 실행 코드 안 우연한 2정렬 값(0x9C4586 «0074 2C88» 등)을 바꿔 부팅 실패(2026-11-13)
PTR_ZONES = [(0x6C0000, 0x760000), (0x8F0000, 0x900000)]
KEEP = {0x2003, 0x2013, 0x2018, 0x2169, 0x2170, 0x217D} | set(range(0x1E54, 0x1E5B))   # 2003 = 達 — {N0} 매크로가 직접 찍음 → «들» · 2018 = 様 — {N3} 이 혼자일 때 직접 찍음 → «님»(«당신프의», 2026-11-14 밤)
# 매크로가 코드로 직접 가리키는 짧은 문자열(VA 포인터 없음) — 같은 자리 안에서 바꿈 (2026-11-13 «당신워의»)
MACRO_STR = {0x6D68C8: '님', 0x6D68E4: '.', 0x6D68E8: ',', 0x6D6918: '', 0x6D691C: '들'}   # さん 。 よ、 様 方
CAPTIONS = {0x9A08C0: ['그 거목을 본 자는', '아무도 돌아오지 못했다.'],      # その大樹を見たものは、／誰１人として帰ってこない。
            0x9A08FC: ['글란트리 공국'],                                   # グラントリ公国(무대 제목)
            0x9A0910: ['글란트리 공국 왕자　말라키 뒤 마레']}              # グラントリ公国王子　マラキー・ドゥ・マライ
SLOTS = [c for c in range(0x2000, 0x2200) if c not in KEEP] + list(range(0x1D40, 0x1D52)) + \
        [c for c in range(0x1E00, 0x1EC0) if c not in KEEP]
HALF = {' ': 0x1800, '　': 0x1800, ',': 0x1EC3, '!': 0x1EF0, '?': 0x1EEF, '&': 0x1EEE, '“': 0x1ED4,
        '～': 0x1ECE, '・': 0x1EC5, '（': 0x1ED9, '）': 0x1EDA, '！': 0x1EF0, '？': 0x1EEF, '＆': 0x1EEE,
        '‼': 0x2170, '⁉': 0x217D}   # ⁉ = 217D(원문 731ADC «…⁉» 바이트), 217E 는 録 — 예전 217E 로 잘못 잡아 «…録» 찍힘(2026-11-15 하스피 스샷)
NEW_PUNCT = '.．…＋'
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？・：；:;～~])[ 　]+')
TOK = re.compile(r'(\{c[0-9A-F]{2}\}|\{N[0-9A-F]\}|\{[0-9A-F]{4}\}|\{＊\}|／)')


def plus_glyph():
    ink = np.zeros((16, 16), bool); ink[7:9, 3:13] = True; ink[3:13, 7:9] = True
    return P.paint(ink)


def load_ko():
    jp2ko = {}
    for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'tsv_ko', 'mys_*.tsv'))):
        for ln in open(f, encoding='utf-8').read().split('\n')[1:]:
            c = ln.split('\t')
            if len(c) >= 4: jp2ko[c[2]] = (c[0], c[3])
    return jp2ko


def _cells(buf, o):
    lines = [0]; i = o
    while True:
        w = struct.unpack('>H', buf[i:i + 2])[0]
        if w == 0: break
        if w == 0xFFFF: lines.append(0); i += 6; continue
        if w == 0xFFFE: i += 4; continue
        lines[-1] += 1; i += 2
    return max(lines)
def recenter_windows(e0, e, log):
    """글 창 기록 «0806 n 포인터 x y …»(0x72A000~0x72C000): 원문이 가운데(x + 8×원문 최대 칸 ≈ 256±4)였던 것만
    번역 최대 칸에 맞춰 x 다시 계산 — 왼쪽 정렬(148·146 고정) 기록은 그대로 (2026-11-13 여관 «당신은 트린탄» 밀림)"""
    for h in range(0x72A000, 0x72C000, 2):
        if e0[h:h + 2] != b'\x08\x06': continue
        va0 = struct.unpack('>I', e0[h + 4:h + 8])[0]; va = struct.unpack('>I', e[h + 4:h + 8])[0]
        if not (0x6D0000 <= va0 - 0x10000 < 0x760000): continue
        x = struct.unpack('>H', e0[h + 8:h + 10])[0]
        co = _cells(e0, va0 - 0x10000); cn = _cells(e, va - 0x10000)
        if abs(x + 8 * co - 256) > 4 or co == cn: continue
        nx = x + 8 * (co - cn); e[h + 8:h + 10] = struct.pack('>H', nx)
        log('창 가운데 맞춤 %X x %d→%d (%d칸→%d칸)' % (h, x, nx, co, cn))
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    rep = []
    def log(s): print(s); rep.append(s)
    t = codetable.table(); t[0x1800] = '　'
    e0 = open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read()
    e = bytearray(e0)
    g = bytearray(open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd21x.bin'), 'rb').read())
    jm = P.jp_map()
    font = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf')
    jp2ko = load_ko()
    # VA 포인터 자리 (추출기와 같은 기준)
    refs = collections.defaultdict(list)
    for o in range(0, END - 3, 2):
        v = struct.unpack_from('>I', e0, o)[0] - VA
        if 0 <= v < END and not v & 1 and any(lo_ <= o < hi_ for lo_, hi_ in PTR_ZONES): refs[v].append(o)
    units = [l.split('\t') for l in open(os.path.join(ROOT, 'work', 'text', 'units.tsv'), encoding='utf-8').read().split('\n')[1:] if l]
    alloc = {}; slots = iter(SLOTS); drawn = {}
    def code(ch):
        if '가' <= ch <= '힣' or ch in NEW_PUNCT:
            k = '.' if ch == '．' else ch
            if k not in alloc:
                c = next(slots); alloc[k] = c
                img = P.glyph(font, k) if '가' <= k <= '힣' else (plus_glyph() if k == '＋' else P.punct_glyph(k))
                ps3gfx.put(g, c, img); drawn[c] = (k, bytes(g[c * 128:(c + 1) * 128]))
            return alloc[k]
        if ch in HALF: return HALF[ch]
        if ch in jm: return jm[ch]
        raise KeyError(ch)
    stats = collections.Counter(); built = []
    for u in units:
        a0, end = int(u[0], 16), int(u[1], 16); jp = u[7]
        if jp not in jp2ko: stats['번역 없음'] += 1; log('⛔번역 없음 %06X %s' % (a0, jp[:30])); continue
        no, ko = jp2ko[jp]
        ko = PUNCT_SP.sub(lambda m: m.group(1), ko)                 # 문장부호 뒤 공백은 빌더에서 무조건 지움(전 프로젝트 규칙)
        r = X.parse(e0, t, a0)
        head, toks, _ = r
        ys = [x[2] for x in toks if x[0] == 'nl']
        inner = [int(s_, 16) for s_ in u[4].split(',') if s_]
        out = []; n = 0; li = 0; first_n = None; marks = []
        try:
            for part in TOK.split(ko):
                if not part: continue
                if part == '／':
                    if first_n is None: first_n = n
                    y = ys[li] if li < len(ys) else (ys[-1] if ys else 0x10); li += 1
                    out += [0xFFFF, (-16 * n) & 0xFFFF, y]; n = 0
                elif part == '{＊}': marks.append(len(out))
                elif part.startswith('{c'): out += [0xFFFE, int(part[2:4], 16)]
                elif part.startswith('{N'): out.append(0x7000 + int(part[2], 16)); n += 1
                elif part.startswith('{'): out.append(int(part[1:5], 16)); n += 1
                else:
                    for ch in part: out.append(code(ch)); n += 1
        except KeyError as k:
            log('⛔%s %06X 코드 없음 %r' % (no, a0, k.args[0])); stats['코드 없음'] += 1; continue
        if first_n is None: first_n = n
        out.append(0)
        hd = list(head)
        if len(hd) == 2 and ko.startswith('{c0C}'):
            hd[0] = max(0, (368 - 16 * first_n) // 2)
        raw = b''.join(struct.pack('>H', w) for w in hd + out)
        for s_ in inner:
            assert not X.parse(e0, t, s_)[0], '안쪽 문자열 머리 있음 %06X' % s_
        if inner and len(marks) != len(inner): log('⚠%s 안쪽 포인터 표시 수 다름' % no)
        built.append(dict(no=no, a0=a0, end=end, raw=raw, inner=list(zip(inner, [2 * len(hd) + 2 * m for m in marks]))))
    # ---- 블록 안 다시 쌓기 (원래 문장 자리 밖은 안 씀 — 0 구간·롬 데이터 보호, 2026-11-13 크래시 교훈) ----
    built.sort(key=lambda x: x['a0'])
    blocks = []; cur = [built[0]]
    for x in built[1:]:
        pb = cur[-1]['end']
        if x['a0'] >= pb and e0[pb:x['a0']].strip(b'\0') == b'' and x['a0'] - pb < 64: cur.append(x)
        else: blocks.append(cur); cur = [x]
    blocks.append(cur)
    unit_starts = {x['a0'] for x in built}
    refpos = {o for x in built for o in refs.get(x['a0'], [])}
    # 1) 원래 자리에 들어가면 그대로(포인터 안 바꿈) — 남는 꼬리는 빈틈으로
    newpos = {}; holes = []; deferred = []; seen = {}
    for x in built:
        need = len(x['raw']) + (len(x['raw']) & 1)
        if need <= x['end'] - x['a0']:
            e[x['a0']:x['end']] = x['raw'] + b'\0' * (x['end'] - x['a0'] - len(x['raw']))
            newpos[x['a0']] = x['a0']
            for s_, off in x['inner']: newpos[s_] = x['a0'] + off
            if not x['inner']: seen.setdefault(x['raw'], x['a0'])
            h0 = x['a0'] + need
            if x['end'] - h0 >= 4: holes.append([h0, x['end']])
            stats['제자리'] += 1
        else:
            e[x['a0']:x['end']] = b'\0' * (x['end'] - x['a0'])          # 옛 자리 = 빈 문자열(혹시 남은 참조 대비)
            deferred.append(x); holes.append([x['a0'], x['end']])
    # 붙어 있는 빈틈 잇기(사이가 0 바이트뿐이면)
    holes.sort(); mh = []
    for h in holes:
        if mh and h[0] - mh[-1][1] < 64 and e[mh[-1][1]:h[0]].strip(b'\0') == b'': mh[-1][1] = max(mh[-1][1], h[1])
        else: mh.append(list(h))
    holes = mh
    # 2) 넘친 것 = 같은 글이 이미 있으면 공유, 아니면 빈틈(가장 작게 맞는 곳)에
    deferred.sort(key=lambda x: -len(x['raw']))
    for x in deferred:
        if not x['inner'] and x['raw'] in seen:
            newpos[x['a0']] = seen[x['raw']]; stats['같은 글 공유'] += 1; continue
        need = len(x['raw']) + (len(x['raw']) & 1)
        fit = [h for h in holes if h[1] - h[0] >= need]
        if not fit: raise SystemExit('⛔자리 없음 %s %d B' % (x['no'], need))
        h = min(fit, key=lambda h: h[1] - h[0])
        pos = h[0]; e[pos:pos + len(x['raw'])] = x['raw']; h[0] += need
        newpos[x['a0']] = pos
        for s_, off in x['inner']: newpos[s_] = pos + off
        if not x['inner']: seen.setdefault(x['raw'], pos)
        stats['빈틈으로'] += 1; log('  %s %06X → %06X (%d B)' % (x['no'], x['a0'], pos, len(x['raw'])))
    for old, new in newpos.items():
        if old != new:
            for o in refs.get(old, []): e[o:o + 4] = struct.pack('>I', new + VA)
            stats['포인터 바꿈'] += len(refs.get(old, []))
    stats['덩어리'] = len(built)
    # 매크로 짧은 문자열(원래 길이 안)
    for a_, txt in MACRO_STR.items():
        n0 = 0
        while e0[a_ + 2 * n0:a_ + 2 * n0 + 2] != b'\0\0': n0 += 1
        ws = [code(ch) for ch in txt]
        assert len(ws) <= n0, (hex(a_), txt)
        e[a_:a_ + 2 * n0 + 2] = b''.join(struct.pack('>H', w) for w in ws) + b'\0' * (2 * (n0 - len(ws)) + 2)
    # 그림 자막(추출 구역 밖 0x9A08C0~, 머리 = x·y 두 워드, 줄바꿈 FFFF −폭 0010) — 2026-11-14 밤 리뷰 스샷 «グラントリⅡ부»·«…王子 マラキ람…»
    #   번역은 같은 내용 대사(00218·00235)와 같게. x = 원래 x + 8×(원래 첫 줄 글자 수 − 새 첫 줄 글자 수)(원래 맞춤 유지), 원래 길이 안.
    for a_, lines in CAPTIONS.items():
        x0, y0 = struct.unpack_from('>HH', e0, a_)
        n0 = 0
        while e0[a_ + 4 + 2 * n0:a_ + 6 + 2 * n0] != b'\0\0': n0 += 1
        first0 = 0
        while first0 < n0 and struct.unpack_from('>H', e0, a_ + 4 + 2 * first0)[0] != 0xFFFF: first0 += 1
        ws = []
        for i, ln in enumerate(lines):
            if i: ws += [0xFFFF, (-16 * len(lines[i - 1])) & 0xFFFF, 0x0010]
            ws += [code(ch) for ch in ln]
        assert len(ws) <= n0, (hex(a_), lines)
        x = x0 + 8 * (first0 - len(lines[0]))
        e[a_:a_ + 4 + 2 * n0 + 2] = struct.pack('>HH', x, y0) + b''.join(struct.pack('>H', w) for w in ws) + b'\0' * (2 * (n0 - len(ws)) + 2)
        log('그림 자막 %X x %d→%d %s' % (a_, x0, x, '／'.join(lines)))
    # 엔딩 «冒険の記録» 창 항목 이름(2026-11-15 하스피 스샷 01:47 «밝단널외햇») = 글자 칸 12개(코드·속성 001F, 0x6C7FD0~) + 칸별 위치 표(x·y, 0x6C8000~)
    #   원문 宝箱獲得数(5칸, y 0)·隠し部屋発見数(7칸, y 16). 위치가 칸마다 있어 띄어쓰기는 칸 없이 x 만 8 벌림, 남는 칸은 공백 1800.
    REC_CELLS, REC_POS, REC_N = 0x6C7FD0, 0x6C8000, 12
    cells = []
    for txt, y in (('보물상자 획득', 0), ('숨은 방 발견', 16)):
        x = 0
        for ch in txt:
            if ch == ' ': x += 8; continue
            cells.append((code(ch), x, y)); x += 16
    assert len(cells) <= REC_N, cells
    cells += [(0x1800, 0x60, 0x10)] * (REC_N - len(cells))
    for i, (c, x, y) in enumerate(cells):
        assert struct.unpack_from('>H', e0, REC_CELLS + 4 * i + 2)[0] == 0x001F
        struct.pack_into('>HH', e, REC_CELLS + 4 * i, c, 0x001F); struct.pack_into('>HH', e, REC_POS + 4 * i, x, y)
    log('모험 기록 창 항목 = 보물상자 획득 · 숨은 방 발견(칸 %d/%d)' % (len([c for c in cells if c[0] != 0x1800]), REC_N))
    ps3gfx.put(g, 0x2003, P.glyph(font, '들')); ps3gfx.put(g, 0x2013, P.glyph(font, '들')); ps3gfx.put(g, 0x2018, P.glyph(font, '님'))   # {N3} = あなた様(2018, 혼자)/あなた方(2013, 여럿) → «용사님/용사들»   # 2013 = 方 — {N3}(あなた方) 매크로가 직접 찍음(«당신드의», 2026-11-14)
    log('매크로 문자열 %s · 0x2003(達)·0x2013(方) = 들 · 0x2018(様) = 님' % MACRO_STR)
    NAME_EN = True                                     # 2026-11-14 밤 4 하스피 «영문입력 만들어줘» — 입력표 영문 배치 + 돌판 글자를 진짜 커서 사각형 안에(tools/name_en.py). False = 일본판 가나 그대로
    import name_en
    if NAME_EN:
        P.name_grid_english(e)
        log('이름 돌판 화면 배치표 새 칸 %d' % name_en.patch_table(e, log))
    recenter_windows(e0, e, log)
    # 랭킹 기본 이름(가나 ヤマノウ… — {N5} «전설의 용사 ○○의 검» 에도 1위 이름이 끼워짐, 2026-11-14 밤 리뷰 스샷) → 롬의 영문판 표(ERLING·GYGAX…) 이름 칸만
    #   레코드 16 B = 2 B · 이름 6 B(글자 목록 번호, FF 채움) · 8 B 꼬리. 꼬리 «0010000000000000» 이 1위. 일본판 표 두 벌(0x149B18C·0x14B8290) ← 영문판 0x14B8724
    for jp_tail in (0x149B18C, 0x14B8290):
        for r in range(10):
            e[jp_tail - 6 + 16 * r:jp_tail + 16 * r] = e0[0x14B8724 - 6 + 16 * r:0x14B8724 + 16 * r]
    log('랭킹 기본 이름 = 영문판(ERLING·GYGAX·JMWORD·ALMA·AREX·ANTONI·BRASS·CREMAT·LAY·LEFTY)')
    # 캐릭터 기본 이름(이름 안 넣고 시작할 때) 가나 12칸 → 롬의 영문판 12칸(하스피 2026-11-14 «기본이름까지 영문으로»)
    #   0x14B8328 + 8k: k0~11 = 가나(クラッサス·ジャーレッド·グレルダン·マイルズ·ルシア·ケイラ·(0x98~ 그림)·ヘンデル·サイアス·ドレイヴン·モリア·シャノン)
    #   k12~23 = 영문(같은 차례, 6자 넘는 이름은 0x80~ 특수 번호 — 일본판 드워프 이름도 같은 방식). ⚠특수 번호 영문 이름은 화면 확인 필요.
    e[0x14B8328:0x14B8328 + 96] = e0[0x14B8388:0x14B8388 + 96]
    log('캐릭터 기본 이름 = 영문판 12칸')
    import hud_caption
    hud_caption.build(e, g, log)                       # 캐릭터 선택 위 표시줄 설명문(dd21x scroll1 그림 + EBOOT 띠 배치)
    # dd22(스프라이트) = 원본 → 반지 이름 → 함정 말풍선 → 상자판 이름표 → 무대 제목(EBOOT 제목 기록 타일 번호도 바꿈)
    import ringlab, trap_balloons, stage_title_ko
    g22, over = ringlab.build_ko(open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd22.bin'), 'rb').read())
    log('반지 이름 넘침 %s' % over)
    g22 = bytearray(g22); log('함정 말풍선 넘침 %s' % trap_balloons.apply(g22))
    import boxlabels; boxlabels.apply(g22, log)        # 상점 위 소지품 칸 상자판 이름표 0x16A2~0x16BE(슬링 등, 2026-11-15)
    stage_title_ko.build(e, g22, log)
    od =os.path.join(ROOT, 'work', 'build'); os.makedirs(od, exist_ok=True)
    open(os.path.join(od, 'EBOOT.BIN'), 'wb').write(e)
    open(os.path.join(od, 'dd21x.bin'), 'wb').write(g)
    open(os.path.join(od, 'dd22.bin'), 'wb').write(g22)
    # 이름 입력 버튼 4개(공백·이름·지움·완료) — dd21x 8x8 타일 0x2B3D~0x2B92
    import subprocess
    subprocess.run([sys.executable, os.path.join(HERE, 'name_buttons.py'), os.path.join(od, 'dd21x.bin'), os.path.join(od, 'dd21x.bin')], check=True)
    log('이름 입력 버튼 4개 새김(공백·이름·지움·완료)')
    nn = name_en.write(os.path.join(od, 'dd21x.bin'), os.path.join(od, 'dd21x.bin')) if NAME_EN else 0
    fin = open(os.path.join(od, 'dd21x.bin'), 'rb').read()                 # 검산: 대사 한글 칸이 뒤 단계(8x8 띠·돌판·버튼)에 덮였나
    broke = ['%s(%X)' % (k, c) for c, (k, bb) in drawn.items() if fin[c * 128:(c + 1) * 128] != bb]
    log(('⛔대사 글자 칸 덮임 %d %s' % (len(broke), broke[:20])) if broke else '대사 글자 칸 덮임 0')
    log(('이름 입력 돌판 글자층 = 영문 %d타일' % nn) if NAME_EN else '이름 입력 = 일본판 가나 그대로(돌판·입력표)')
    log('덩어리 %s · 한글 음절·부호 %d칸 (마지막 %04X)' % (dict(stats), len(alloc), max(alloc.values())))
    open(os.path.join(od, 'report.txt'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    # 글자판(원본|한글)
    from PIL import Image
    pal = np.full(16, 90, np.uint8); pal[0] = 255; pal[14] = 20
    g0 = open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd21x.bin'), 'rb').read()
    cs = sorted(alloc.values()); cols = 16
    im = Image.new('L', (cols * 2 * 34 + cols * 4, ((len(cs) + cols - 1) // cols) * 34), 40)
    for i, c in enumerate(cs):
        x = (i % cols) * (2 * 34 + 4); y = (i // cols) * 34
        for k, src in enumerate((g0, bytes(g))):
            im.paste(Image.fromarray(pal[ps3gfx.tile(src, c)]).resize((32, 32), 0), (x + k * 34, y))
    im.save(os.path.join(od, 'glyphs.png'))


if __name__ == '__main__':
    main()
