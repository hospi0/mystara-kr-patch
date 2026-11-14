# -*- coding: utf-8 -*-
r"""SOM 한글 PoC (2026-11-13, 하스피 «ㄱ»): 오프닝 자막(00105) + 1스테이지 첫 대화(00106) 만 한글로.
  글꼴: 갈무리14 BDF → dd21x 한자 칸 0x2000~ 에 덮음(E 흰 글자 + 왼쪽·위 0 그림자, F 투명).
  글: EBOOT.elf(평문) 제자리. 줄바꿈 FFFF x y 의 x = −(앞 줄 글자 수×16).
  출력: work/poc/EBOOT.BIN(평문 ELF — RPCS3 는 그대로 실행) · work/poc/dd21x.bin · work/poc/glyphs.png(글자판 원본|한글)
  python tools/poc_build.py"""
import os, re, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import codetable, ps3gfx
from bdf import Font

TARGETS = [('00105', 0x6DB1B4, 0x6DB30C), ('00106', 0x72CEBC, 0x72CEDA)]
PUNCT = {' ': 0x1800, '　': 0x1800, ',': 0x1EC3, '!': 0x1EF0, '?': 0x1EEF}   # . … 는 바닥 부호 새로 그림


def jp_map():
    m = {}
    for base, row in codetable.KANA.items():
        for i, ch in enumerate(row):
            if ch not in '〓？' or ch == '？': m.setdefault(ch, base + i)
    for ln in codetable.KANJI.strip().split('\n'):
        if ln.startswith('#'): continue
        a, s = ln.split(' ', 1)
        for i, ch in enumerate(s.strip()): m.setdefault(ch, int(a, 16) + i)
    m['？'] = 0x1EEF; m['！'] = 0x1EF0
    return m


def glyph(font, ch):
    pts, w = font.draw(ch)
    ink = np.zeros((16, 16), bool)
    if pts:
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        dx = 1 + (14 - (max(xs) - min(xs) + 1)) // 2 - min(xs)
        dy = 1 + (14 - (max(ys) - min(ys) + 1)) // 2 - min(ys)
        for x, y in pts:
            if 0 <= x + dx < 16 and 0 <= y + dy < 16: ink[y + dy, x + dx] = True
    return paint(ink)


def paint(ink):
    """원본 꼴: 0 = 흰 글자, E = 그림자(오른쪽·아래), F = 투명 (1E6D·1EF0 화소로 확인)."""
    img = np.full((16, 16), 15, np.uint8)
    sh = np.zeros_like(ink)
    sh[:, 1:] |= ink[:, :-1]; sh[1:, :] |= ink[:-1, :]; sh[1:, 1:] |= ink[:-1, :-1]
    img[sh & ~ink] = 14
    img[ink] = 0
    return img


def punct_glyph(ch):
    """한국식 바닥 부호: . = 바닥 점, … = 바닥 점 셋 한 칸."""
    ink = np.zeros((16, 16), bool)
    xs = {'.': [3], '…': [2, 7, 12]}[ch]
    for x in xs: ink[12:14, x:x + 2] = True
    return paint(ink)


NAME_GRID = 0x14B6678     # 이름 입력 글자판 6x10 칸 = 글자 목록(0x6D694E) 번호, 행 간격 16 B
NAME_WEIGHT = 0x14B5F60   # 목록 번호별 숫자(성장 타입) — 영문 글자 값이 이미 영문판과 같음, 안 고침
# 영문판(아시아·북미) 글자판 배치 — 열 번호 = 숫자. 목록 번호: Ａ81~Ｚ106 · ０119~９128 · 。107 ＆108 ！109 ？110 ー111 ␣129
# Ⅰ~Ⅴ 는 일본판 목록에 없어 같은 숫자(5~9)의 기호로 채움, 無 칸은 ␣.
NAME_ROWS = [
    [81, 82, 83, 84, 85, 119, 120, 121, 122, 123],      # A B C D E | 0 1 2 3 4
    [86, 87, 88, 89, 90, 124, 125, 126, 127, 128],      # F G H I J | 5 6 7 8 9
    [91, 92, 93, 94, 95, 107, 108, 129, 111, 109],      # K L M N O | (Ⅰ~Ⅴ 대신) 。 ＆ ␣ ー ！
    [96, 97, 98, 99, 100, 129, 129, 129, 129, 129],     # P Q R S T | 無 ×5 (윗줄과 중복이던 . & _ - ! 뺌, 하스피 2026-11-14)
    [101, 102, 103, 104, 105, 129, 129, 129, 129, 110], # U V W X Y | 無 無 無 無 ?
    [106, 129, 129, 129, 129, 129, 129, 129, 129, 129], # Z 無 …
]


def name_grid_english(e):
    for r, row in enumerate(NAME_ROWS):
        o = NAME_GRID + r * 16
        print('글자판 %d행 %s → %s' % (r, bytes(e[o:o + 10]).hex(' '), bytes(row).hex(' ')))
        e[o:o + 10] = bytes(row)
    w = e[NAME_WEIGHT:NAME_WEIGHT + 130]
    print('검산 CAPCOM =', sum(w[i] for i in (83, 81, 96, 83, 95, 93)))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    ko = {}
    for ln in open(os.path.join(ROOT, 'work', 'text', 'ko', 'mys_ko.tsv'), encoding='utf-8').read().split('\n'):
        if ln.strip():
            a, b = ln.split('\t', 1); ko[a] = b
    jm = jp_map()
    font = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf')
    e = bytearray(open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read())
    g = bytearray(open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd21x.bin'), 'rb').read())
    g0 = bytes(g)
    alloc = {}; nxt = [0x2000]; reloc = [0x678000]

    def code(ch):
        if ch in '.…':
            if ch not in alloc:
                alloc[ch] = nxt[0]; ps3gfx.put(g, nxt[0], punct_glyph(ch)); nxt[0] += 1
            return alloc[ch]
        if '가' <= ch <= '힣':
            if ch not in alloc:
                alloc[ch] = nxt[0]; ps3gfx.put(g, nxt[0], glyph(font, ch)); nxt[0] += 1
            return alloc[ch]
        if ch in PUNCT: return PUNCT[ch]
        if ch in jm: return jm[ch]
        raise SystemExit('코드 없음 %r' % ch)

    for no, a, b in TARGETS:
        s = ko[no]
        out = []; n = 0
        for part in re.split(r'(\{c[0-9A-F]{2}\}|／)', s):
            if not part: continue
            if part == '／':
                out += [0xFFFF, (-n * 16) & 0xFFFF, 0x0010]; n = 0
            elif part.startswith('{c'):
                out += [0xFFFE, int(part[2:4], 16)]
            else:
                for ch in part: out.append(code(ch)); n += 1
        out.append(0x0000)
        raw = b''.join(struct.pack('>H', v) for v in out)
        # 원문 줄바꿈 y 확인용
        if len(raw) <= b - a:
            e[a:b] = raw + b'\0' * (b - a - len(raw))
            print('%s 제자리 %d/%d B' % (no, len(raw), b - a))
        else:
            # 넘치면 빈 0 구간(0x675410~0x67AE61, 직접 포인터 없음 확인)으로 옮기고 VA 포인터 교체
            na = reloc[0]; assert e[na:na + len(raw)] == b'\0' * len(raw)
            e[na:na + len(raw)] = raw; reloc[0] = (na + len(raw) + 15) & ~15
            old = struct.pack('>I', a + 0x10000); new = struct.pack('>I', na + 0x10000)
            refs = [m.start() for m in re.finditer(re.escape(old), bytes(e[:0x1402668])) if m.start() % 2 == 0]
            assert len(refs) == 1, refs
            for r in refs: e[r:r + 4] = new
            print('%s 옮김 %d B → 0x%X (포인터 0x%X)' % (no, len(raw), na, refs[0]))
    name_grid_english(e)
    od = os.path.join(ROOT, 'work', 'poc'); os.makedirs(od, exist_ok=True)
    open(os.path.join(od, 'EBOOT.BIN'), 'wb').write(e)
    open(os.path.join(od, 'dd21x.bin'), 'wb').write(g)
    # 글자판 미리보기: 원본|한글
    from PIL import Image
    codes = sorted(alloc.values())
    pal = np.full(16, 120, np.uint8); pal[14] = 20; pal[0] = 255; pal[15] = 90
    im = Image.new('L', (2 * 18 * 3 + 6, len(codes) * 18 * 3), 30)
    for i, c in enumerate(codes):
        for k, src in enumerate((g0, bytes(g))):
            t = Image.fromarray(pal[ps3gfx.tile(src, c)]).resize((48, 48), 0)
            im.paste(t, (k * (54 + 6), i * 54))
    im.save(os.path.join(od, 'glyphs.png'))
    print('한글 음절 %d칸 (0x2000~0x%04X)' % (len(alloc), nxt[0] - 1))


if __name__ == '__main__':
    main()
