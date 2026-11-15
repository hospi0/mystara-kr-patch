# -*- coding: utf-8 -*-
r"""SOM 마법 링 «화면 위 초록 설명 줄» 한글 (2026-11-15, 하스피 «마법설명 다 일어래»)
  · 출처 = dd21x 8x8 타일(64 B 중 앞 32 B, 4bpp 아래 니블 = 왼쪽) 줄 그림: 0x470~0x610, 0x10 간격 27줄, 줄마다 16칸(128x8).
  · 원본 꼴 = 글자 5 + 오른쪽·아래·오른아래 0 그림자, 바탕 15. 잉크 0~6행.
  · 글꼴 = 갈무리7 BDF 화소 그대로(한글 7행).
  python tools/magic_desc.py                 → 미리보기 work/mdesc/preview_<n>/ (원본|한글)
  python tools/magic_desc.py IN.bin OUT.bin  → dd21x 에 써 넣기
"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
from bdf import Font

W = 16  # 칸 수
KO = {
    0x470: '미티어 스웜/운석',
    0x480: '매직 미사일/마법의 화살',
    0x490: '파이어볼/불덩이',
    0x4A0: '라이트닝 볼트/번개',
    0x4B0: '아이스 스톰/얼음 폭풍',
    0x4C0: '인비저빌리티/투명',
    0x4D0: '헤이스트/스피드 업',
    0x4E0: '폴리모프 아더/적을 변신',
    0x4F0: '컨주어 엘레멘탈/정령의 힘',
    0x500: '플레시 투 스톤/석화',
    0x510: '월 오브 파이어/불의 벽',
    0x520: '프로젝티드 이미지/분신',
    0x530: '리버스 그래비티/중력 반전',
    0x540: '클라우드킬/독구름',
    0x550: '미티어 스웜/운석',
    0x560: '파워 워드 킬/폭렬',
    0x570: '홀드 퍼슨/속박',
    0x580: '컨티뉴얼 라이트/빛',
    0x590: '스틱 투 스네이크/뱀 변화',
    0x5A0: '인섹트 플레이그/벌레 대군',
    0x5B0: '파워 워드 킬/폭렬',
    0x5C0: '홀리 워드/성스러운 말',
    0x5D0: '어스퀘이크/대지진',
    0x5E0: '블레스/공격력 업',
    0x5F0: '스트라이킹/무기 위력 업',
    0x600: '큐어 시리어스 운즈/회복',
    0x610: '큐어 크리티컬 운즈/대회복',
}
INK, SHADOW, BG = 5, 0, 15


def t8(g, k):
    b = np.frombuffer(bytes(g[k * 64:k * 64 + 32]), np.uint8)
    p = np.empty(64, np.uint8); p[0::2] = b & 15; p[1::2] = b >> 4
    return p.reshape(8, 8)


def put8(g, k, a):
    f = a.reshape(-1).astype(np.uint8)
    g[k * 64:k * 64 + 32] = bytes((f[0::2] & 15) | ((f[1::2] & 15) << 4))


def strip(g, base):
    return np.hstack([t8(g, base + i) for i in range(W)])


_font = None


def render(text):
    global _font
    if _font is None:
        _font = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf')
    pts, w = _font.draw(text)
    ref, _ = _font.draw('가')
    top = min(y for _, y in ref)
    a = np.full((8, W * 8), BG, np.uint8)
    ink = np.zeros((8, W * 8 + 2), bool)
    for x, y in pts:
        yy = y - top
        assert 0 <= yy <= 6, (text, yy)
        x += 1  # 원본처럼 왼쪽 1px 띄움
        if x >= W * 8 - 1:
            raise ValueError('폭 넘침 %s (%dpx > %d)' % (text, w + 2, W * 8))
        ink[yy, x] = True
    ink = ink[:, :W * 8]
    sh = np.zeros_like(ink)
    sh[:, 1:] |= ink[:, :-1]
    sh[1:, :] |= ink[:-1, :]
    sh[1:, 1:] |= ink[:-1, :-1]
    a[sh & ~ink] = SHADOW
    a[ink] = INK
    return a, w + 2


def write(src, dst, log=print):
    g = bytearray(open(src, 'rb').read())
    for base, text in KO.items():
        a, w = render(text)
        for i in range(W):
            put8(g, base + i, a[:, i * 8:i * 8 + 8])
    open(dst, 'wb').write(g)
    log('마법 설명 줄 %d개 씀' % len(KO))
    return len(KO)


def preview():
    from PIL import Image
    g = open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd21x.bin'), 'rb').read()
    n = 1
    while os.path.exists(os.path.join(ROOT, 'work', 'mdesc', 'preview_%d' % n)):
        n += 1
    od = os.path.join(ROOT, 'work', 'mdesc', 'preview_%d' % n); os.makedirs(od)
    # 게임 화면 색 비슷하게: 5 = 초록, 0 = 검정, 15 = 어두운 바탕
    pal = {INK: (64, 255, 64), SHADOW: (0, 0, 0)}
    def rgb(a):
        o = np.zeros(a.shape + (3,), np.uint8); o[:] = (70, 55, 40)
        for v, c in pal.items():
            o[a == v] = c
        o[(a != BG) & (a != INK) & (a != SHADOW)] = (64, 200, 64)
        return o
    rows = []
    for base, text in KO.items():
        a, w = render(text)
        o = strip(g, base)
        gap = np.full((8, 6, 3), 30, np.uint8)
        rows.append(np.hstack([rgb(o), gap, rgb(a)]))
        rows.append(np.full((3, rows[-1].shape[1], 3), 30, np.uint8))
    im = Image.fromarray(np.vstack(rows))
    im = im.resize((im.width * 4, im.height * 4), Image.NEAREST)
    p = os.path.join(od, '마법설명_원본왼쪽_한글오른쪽.png')
    im.save(p)
    print(p)


if __name__ == '__main__':
    if len(sys.argv) == 3:
        write(sys.argv[1], sys.argv[2])
    else:
        for b, t in KO.items():
            a, w = render(t)
            print(hex(b), w, t)
        preview()
