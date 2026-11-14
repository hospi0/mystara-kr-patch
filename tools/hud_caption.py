# -*- coding: utf-8 -*-
r"""캐릭터 선택 화면 위 표시줄 설명문(직업 설명) 한글 (2026-11-14).
  · 배치 = EBOOT 0x58D3E0~ 띠 12개(일본 6 + 영문 6) × 20열, 열마다 (위 코드, 아래 코드, 0x260B 테두리) 6 B.
  · scroll1 코드 c 의 그림 = dd21x 8x8 타일 c*2. 바탕 벽돌 = 코드 0x08E1(8x8 반복 무늬).
  · 글자 = 흰색 D + 검은 테두리 0 (원본 꼴). 글꼴 갈무리11.
  · 일본 띠 6개를 다시 그림: 글자 걸친 칸만 새 코드 — 코드는 «설명문 띠들만 쓰는 코드»(일본+영문 띠, 벽돌 제외) 풀에서.
  python tools/hud_caption.py → work/ring/preview/hud_caption.png(원본|한글)"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
from bdf import Font
BASE = 0x58D3E0; NB = 12; NC = 20; BRICK = 0x08E1
KO = ['신성 마법을 쓴다', '마법 공격에 강하다', '검과 마법을 쓸 수 있다', '검의 달인', '공격 마법이 특기', '도둑질·함정 해제의 전문가']
W = lambda e, o: struct.unpack('>H', e[o:o + 2])[0]
def unpack(raw):
    a = np.frombuffer(bytes(raw), np.uint8); p = np.empty(a.size * 2, np.uint8); p[0::2] = a & 15; p[1::2] = a >> 4
    return p.reshape(-1, 8, 8)
def bars(e):
    out = []
    for k in range(NB):
        cols = []
        for c in range(NC):
            o = BASE + (k * NC + c) * 6
            assert W(e, o + 4) == 0x260B, hex(o)
            cols.append((o, W(e, o), W(e, o + 2)))
        out.append(cols)
    return out
def render(text, font):
    pts, w = font.draw(text)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    a = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for x, y in pts: a[y - min(ys), x - min(xs)] = True
    return a
def build(e, g, log=print):
    T = unpack(g); bs = bars(e); brick = T[BRICK * 2].copy()
    pool = sorted({v for b in bs for (_, t, u) in b for v in (t, u)} - {BRICK})
    # 풀 코드가 띠 밖 EBOOT 배치에 또 나오는지(설명문 띠 구역 0x58D3E0~0x58D980 밖, 같은 HUD 표 구역 0x58C000~0x58F000)
    outside = set()
    for o in range(0x58C000, 0x58F000, 2):
        if BASE <= o < BASE + NB * NC * 6: continue
        v = W(e, o)
        if v in pool: outside.add(v)
    pool = [c for c in pool if c not in outside]
    font = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri11.bdf'); free = list(pool); prev = []
    for k, text in enumerate(KO):
        cols = bs[k]
        jp = np.vstack([np.hstack([T[t * 2] for _, t, _ in cols]), np.hstack([T[u * 2] for _, _, u in cols])])
        jink = np.nonzero((jp == 13).any(0))[0]; x0 = int(jink.min()) if len(jink) else 16
        cv = np.vstack([np.hstack([brick] * NC)] * 2).copy()
        r = render(text, font); h, w = r.shape
        if x0 + w + 1 > NC * 8: x0 = max(1, NC * 8 - w - 1)
        if w + 2 > NC * 8: log('⛔설명 넘침 %s %d' % (text, w))
        oy = (16 - h) // 2
        ink = np.zeros((16, NC * 8), bool); ink[oy:oy + h, x0:x0 + w] = r[:, :NC * 8 - x0]
        ol = np.zeros_like(ink)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                ol |= np.roll(np.roll(ink, dy, 0), dx, 1)
        cv[ol & ~ink] = 0; cv[ink] = 13
        for c, (o, t, u) in enumerate(cols):
            new = []
            for rr in (0, 1):
                tile = cv[rr * 8:rr * 8 + 8, c * 8:c * 8 + 8]
                if (tile == brick).all(): new.append(BRICK); continue
                code = free.pop(0); new.append(code)
                nib = tile.reshape(-1).astype(np.uint8)
                g[code * 2 * 32:code * 2 * 32 + 32] = bytes((nib[0::2] & 15) | ((nib[1::2] & 15) << 4))
            e[o:o + 4] = struct.pack('>HH', new[0], new[1])
        prev.append((jp, cv))
    log('캐릭터 선택 설명문 6개 한글 · 코드 풀 %d 중 %d 씀(띠 밖 쓰임 %d 제외)' % (len(pool), len(pool) - len(free), len(outside)))
    return prev
def main():
    from PIL import Image
    e = bytearray(open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read())
    g = bytearray(open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd21x.bin'), 'rb').read())
    prev = build(e, g)
    pal = np.array([(0x11, 0x00, 0x00), (0x55, 0x22, 0x11), (0x77, 0x33, 0x11), (0x88, 0x44, 0x22), (0x44, 0x11, 0x00)] + [(i * 17, i * 17, i * 17) for i in range(5, 16)], np.uint8)
    pal[13] = (0xee, 0xee, 0xff); pal[12] = (0xbb, 0xbb, 0xcc); pal[11] = (0x99, 0x99, 0xaa)
    rows = []
    for jp, ko in prev: rows += [pal[jp], pal[ko], np.full((3, NC * 8, 3), 40, np.uint8)]
    a = np.vstack(rows); Image.fromarray(a).resize((a.shape[1] * 4, a.shape[0] * 4), 0).save(os.path.join(ROOT, 'work', 'ring', 'preview', 'hud_caption.png'))
if __name__ == '__main__':
    main()
