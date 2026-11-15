# -*- coding: utf-8 -*-
r"""SOM 무대 제목 한글 (2026-11-13).
  · 제목 줄 타일 = 잉크가 8행 아래까지 내려오는 타일(STAGE 줄은 0~7행) — 그대로 둠.
  · 묶음(stage_pos.groups) = 이어 찍히는 제목 조각. 묶음마다 한글 조각을 하나씩 준다(None = 원래 그림 유지: ー・Ⅰ 등).
  · 일본판 제목은 가나 타일을 여러 제목이 같이 써서 한글이 겹친다 → 고치는 블록은 전부 새 타일로:
    여러 제목이 같이 쓰는 블록만 «영문판 제목 기록만 쓰는 타일»(free_tiles)로 옮김, 혼자 쓰는 블록은 제자리.
    블록 가로 타일은 16칸 줄 안에서만 이어짐(CPS2) → 줄을 넘지 않게 배정.
  · 글꼴 = 대사와 같은 갈무리14, 흰 글자(0) + 오른쪽·아래 그림자(E). 일본 글자 잉크 가운데에 맞춤.
  python tools/stage_title_ko.py [dd22 입력 출력] → work/ring/preview/stage_titles.png(원본|한글)"""
import os, sys, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
import ps3gfx, stage_pos as S, poc_build as P
from bdf import Font
def _recs(e, lo, hi):
    W = lambda o: struct.unpack('>H', e[o:o + 2])[0]; out = []; o = lo
    while o < hi:
        if W(o) == 0x0002 and W(o + 6) == 0x4000:
            p = o + 8
            while not (0x6000 <= W(p) < 0x8000 and (W(p + 2) & 0xFF) < 0x20) and p < o + 16: p += 2
            bl = []
            while 0x6000 <= W(p) < 0x8000 and (W(p + 2) & 0xFF) < 0x20:
                a = W(p + 2); bl.append((W(p), (a >> 8 & 15) + 1, (a >> 12) + 1)); p += 4
            if bl: out.append((o, bl)); o = p; continue
        o += 2
    return out
def free_tiles(e):
    """영문판 제목 기록(EBOOT 0x51F4E0~0x51F860)만 쓰는 0x7Cxx 이상 타일 — 다른 스프라이트(1P·2P 표시 0x7E6E·0x7E71~ 등)가 쓰는 칸 제외
    (2026-11-13 0x7D40~0x7E76 통째로 썼다가 1P 밑에 «유성»·P 깨짐)"""
    T = lambda bl: {t + i + 16 * j for t, nx, ny in bl for j in range(ny) for i in range(nx)}
    en = set(); oth = set()
    for o, bl in _recs(e, 0x500000, 0x530000):
        if 0x51F4E0 <= o < 0x51F860: en |= {t for t in T(bl) if t >= 0x7C00}
        else: oth |= T(bl)
    return en - oth
# 묶음 순서대로(stage_pos.report2 출력 순서). '' = 지움, None = 원래 그림 유지
KO = {
    0x511664: ['브로큰 랜드 북쪽 산맥'],
    0x511694: ['트', '린', '탄', '', '마', '을', '로'],
    0x5116C8: ['중전차 저거너트'],
    0x5116EC: ['격류', None, '베', '스', '비', '아', '강을 타라!'],
    0x511728: ['격류', None, '베', '스', '비', '아', '강을 타라!'],
    0x511760: ['아엥모어 숲 상공'],
    0x511780: ['부해라 불리는 숲', ''],          # «森» 조각이 오른쪽 끝에 따로 있어 «불리는     숲» 으로 벌어짐 → 첫 조각(160px)에 통째로, 森 조각 비움(2026-11-14 밤 하스피 스샷)
    0x5117A4: ['정보를 찾아서', None, '아', '인', '슨', '', '시', '가', '지', None],
    0x5117E8: ['엘', '프', '', None, '나', '무', '의', '', '다', '리', None],
    0x51182C: ['공방!', '', '거', '목', '의', '대', '요새'],
    0x511864: ['마수가 사는 숲'],
    0x511884: ['미로의 숲', ''],                # 부해 숲과 같은 꼴(森 조각 따로) — 첫 조각에 통째로(2026-11-14 밤)
    0x5118C0: ['노움 마을을', '구', '하라!!'],
    0x5118E8: ['정령', None, '', '라', '파', '엘', '의', '', '동굴', '의', '이변'],
    0x511920: ['숨 겨 진  보 물'],            # 隠された財宝(글자 사이 8px 띄운 원문 꼴 그대로) — 목록에서 빠져 있었음(2026-11-15 하스피 스샷 01:11, 대사 글꼴 대조로 dd22 0x6EF4 찾음)
    0x511930: ['작열!', '', '용암계'],
    0x51195C: ['로스', '트', None, '월', '드', '', ''],
    0x511990: ['드워프의 숨겨진 지하 통로'],
    0x5119B4: ['부유성', None, ('침입', [(41, 48)]), None],
    0x5119F0: ['부유성', ('결전', [(0, 8)]), None, None],
    0x511A1C: ['부유성', None, ('투기장', [(70, 80)]), None],
    0x511A58: ['부유성', ('결전', [(0, 8)]), None, None],
    0x511A84: ['부유성', ('투기장', [(0, 8), (85, 96)]), None],
    0x511AAC: ['부유성', None, '최상층', '문', '으', '로', None],
}
FONT = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri14.bdf')
def render(text, width):
    """한 줄 잉크(16행). 음절 간격 16(넘치면 15·14…), 공백 8(넘치면 6)"""
    for pitch, sp in ((16, 8), (15, 6), (14, 5), (13, 4), (12, 4)):
        cells = []
        for ch in text:
            if ch == ' ': cells.append((sp, None)); continue
            g = P.glyph(FONT, ch) == 0 if ch not in '!' else P.glyph(FONT, '！') == 0
            cols = np.nonzero(g.any(0))[0]
            if ch in '!': g = g[:, cols.min():cols.max() + 1]; cells.append((g.shape[1] + 2, g)); continue
            cells.append((pitch, g))
        w = sum(c[0] for c in cells)
        if w <= width or pitch == 12: break
    ink = np.zeros((16, w + 16), bool); x = 0
    for adv, g in cells:
        if g is not None:
            ink[:, x:x + g.shape[1]] |= g if g.shape[1] <= 16 else g[:, :16]
        x += adv
    cols = np.nonzero(ink.any(0))[0]
    return ink[:, :cols.max() + 1] if len(cols) else ink[:, :1]
def build(e, g, log=print):
    """e(EBOOT bytearray)·g(dd22 bytearray) 고침 → 미리보기용 [(원본 묶음 그림, 한글 묶음 그림)…]"""
    g0 = bytes(g); prev = []
    free = free_tiles(bytes(e)); used = set()
    def alloc(nx, ny):
        """영문 제목 전용 칸(free) 안에서 16칸 줄을 넘지 않는 nx×ny 자리"""
        for t in sorted(free - used):
            if (t & 15) + nx > 16: continue
            cells = {t + i + 16 * j for j in range(ny) for i in range(nx)}
            if cells <= free - used: used.update(cells); return t
        raise SystemExit('⛔무대 제목 빈 타일 모자람')
    # 일본판 제목 기록들의 타일 쓰임 횟수 — 한 번만 쓰는 블록은 제자리에 그림, 공유 블록만 옮김
    cnt = {}
    for o_ in S.TITLES:
        for bo, t, nx, ny in S.blocks_at(bytes(e), o_):
            for j in range(ny):
                for i in range(nx): cnt[t + i + 16 * j] = cnt.get(t + i + 16 * j, 0) + 1
    moved = [0]
    for o, chars in S.TITLES.items():
        ko = KO[o]
        occ, gs = S.groups(bytes(e), o, chars)
        assert len(gs) == len(ko), ('%X 묶음 수' % o, len(gs), len(ko))
        newbase = {}
        for grp, k in zip(gs, ko):
            if k is None: continue
            for kk, x in grp['occ']:
                bo = occ[kk]['bo']
                if bo in newbase: continue
                t0 = struct.unpack('>H', e[bo:bo + 2])[0]; a = struct.unpack('>H', e[bo + 2:bo + 4])[0]
                nx, ny = (a >> 8 & 15) + 1, (a >> 12) + 1
                if all(cnt[t0 + i + 16 * j] == 1 for j in range(ny) for i in range(nx)):
                    newbase[bo] = t0; continue                  # 혼자 쓰는 블록 = 제자리
                nt = alloc(nx, ny); newbase[bo] = nt; moved[0] += nx * ny
                for j in range(ny):
                    for i in range(nx): ps3gfx.put(g, nt + i + 16 * j, ps3gfx.tile(g0, t0 + i + 16 * j).copy())
                e[bo:bo + 2] = struct.pack('>H', nt)
        for grp, k in zip(gs, ko):
            W = grp['w']; jp = np.full((16, W), 15, np.uint8)
            for kk, x in grp['occ']: jp[:, x:x + 16] = ps3gfx.tile(g0, occ[kk]['t'])
            if k is None: prev.append((o, jp, jp)); continue
            ink = np.zeros((16, W), bool)
            keeps = []
            if isinstance(k, tuple): k, keeps = k
            lo, hi = 0, W                                  # 남겨 둘 기호(ー Ⅰ Ⅱ) 열을 뺀 쓸 수 있는 범위
            for a, b in keeps:
                if a == 0: lo = max(lo, b)
                else: hi = min(hi, a)
            jink = np.nonzero((jp != 15).any(0))[0]; jink = jink[(jink >= lo) & (jink < hi)]
            if k:
                r = render(k, hi - lo); c = (int(jink.min()) + int(jink.max()) + 1) // 2 if len(jink) else (lo + hi) // 2
                x0 = c - r.shape[1] // 2
                if len(k.replace(' ', '')) > 1 and len(jink): x0 = int(jink.min())   # 여러 글자 묶음 = 원문 첫 글자 자리에서 시작(STAGE 줄과 왼쪽 맞춤, 하스피 지적)
                x0 = max(lo, min(x0, hi - r.shape[1] - 1)) if r.shape[1] < hi - lo else lo
                if r.shape[1] + 1 > hi - lo: log('  넘침 %X «%s» %d > %d' % (o, k, r.shape[1] + 1, hi - lo))
                ink[:, x0:x0 + r.shape[1]] = r[:, :hi - x0]
            sh = np.zeros_like(ink); sh[:, 1:] |= ink[:, :-1]; sh[1:, :] |= ink[:-1, :]; sh[1:, 1:] |= ink[:-1, :-1]
            img = np.full((16, W), 15, np.uint8); img[sh & ~ink] = 14; img[ink] = 0
            for a, b in keeps: img[:, a:b] = jp[:, a:b]
            for kk, x in grp['occ']:
                oc = occ[kk]; nt = newbase[oc['bo']] + oc['i'] + 16 * oc['j']
                ps3gfx.put(g, nt, img[:, x:x + 16].copy())
            prev.append((o, jp, img))
    # 엔딩 «―冒険の記録―» 제목(기록 0x51F2B8, 블록 0x51F2C4~: ― 6E9C · 冒険 7CAE(2칸) · の 6E9E · 記録 7CB8(2칸) · ― 6E9C)
    #   2026-11-15 하스피 스테이트 모험의기록_1_8 스프라이트 목록으로 확인. 7CAE~·7CB8~ 은 이 기록만 씀(제자리), の 6E9E 는 무대 제목 3개와 공유 → 빈 칸으로 옮김.
    HB = 0x51F2C8
    blk = [(HB, 2), (HB + 4, 1), (HB + 8, 2)]
    assert [struct.unpack('>H', e[a:a + 2])[0] for a, _ in blk] == [0x7CAE, 0x6E9E, 0x7CB8], '모험의 기록 블록'
    nt = alloc(1, 1); moved[0] += 1; e[HB + 4:HB + 6] = struct.pack('>H', nt)
    tiles = [0x7CAE, 0x7CAF, nt, 0x7CB8, 0x7CB9]
    jp = np.hstack([ps3gfx.tile(g0, t) for t in (0x7CAE, 0x7CAF, 0x6E9E, 0x7CB8, 0x7CB9)])
    r = render('모험의 기록', 80); x0 = (80 - r.shape[1]) // 2
    ink = np.zeros((16, 80), bool); ink[:, x0:x0 + r.shape[1]] = r[:, :80 - x0]
    sh = np.zeros_like(ink); sh[:, 1:] |= ink[:, :-1]; sh[1:, :] |= ink[:-1, :]; sh[1:, 1:] |= ink[:-1, :-1]
    img = np.full((16, 80), 15, np.uint8); img[sh & ~ink] = 14; img[ink] = 0
    for k, t in enumerate(tiles): ps3gfx.put(g, t, img[:, 16 * k:16 * k + 16].copy())
    prev.append((0x51F2C4, jp, img))
    # 페널티 스테이지 «ペナルティ・ステージ / VS！ブラックドラゴン»(기록 0x5118A0: 블록 0x6ED0 7×2 + 0x6ED7 5×1, 2026-11-15 하스피 스샷)
    #   윗줄(0x6ED0~6ED6) = 작은 글자(줄마다 색 13,13,12,12,11,10,0 + 그림자 14) · 큰 줄 = 0x6EE0~6EE6 + 0x6ED7~6EDB 이어 192px
    PB = 0x5118AC
    assert [struct.unpack('>H', e[PB + 4 * k:PB + 4 * k + 2])[0] for k in range(2)] == [0x6ED0, 0x6ED7], '페널티 제목 블록'
    other = set()
    for o_ in S.TITLES:
        for bo, t, nx, ny in S.blocks_at(bytes(e), o_):
            other |= {t + i + 16 * j for j in range(ny) for i in range(nx)}
    mine = {0x6ED0 + i + 16 * j for i in range(7) for j in range(2)} | {0x6ED7 + i for i in range(5)}
    assert not (mine & other), ('페널티 제목 칸을 다른 제목이 씀', sorted(hex(x) for x in mine & other))
    small = [0x6ED0 + i for i in range(7)]
    big = [0x6EE0 + i for i in range(7)] + [0x6ED7 + i for i in range(5)]
    jp_s = np.hstack([ps3gfx.tile(g0, t) for t in small]); jp_b = np.hstack([ps3gfx.tile(g0, t) for t in big])
    f7 = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf')
    pts, _ = f7.draw('페널티 스테이지'); ref, _ = f7.draw('가'); top = min(y for _, y in ref)
    ink = np.zeros((16, 112), bool)
    for x, y in pts: ink[y - top, x + 8] = True
    sh = np.zeros_like(ink); sh[:, 1:] |= ink[:, :-1]; sh[1:, :] |= ink[:-1, :]; sh[1:, 1:] |= ink[:-1, :-1]
    img_s = np.full((16, 112), 15, np.uint8); img_s[sh & ~ink] = 14
    rowc = [13, 13, 12, 12, 11, 10, 0]
    for y in range(7): img_s[y][ink[y]] = rowc[y]
    for k, t in enumerate(small): ps3gfx.put(g, t, img_s[:, 16 * k:16 * k + 16].copy())
    r = render('VS ! 블랙 드래곤', 192); jink = np.nonzero((jp_b != 15).any(0))[0]
    x0 = int(jink.min()) if len(jink) else 8
    ink = np.zeros((16, 192), bool); ink[:, x0:x0 + r.shape[1]] = r[:, :192 - x0]
    sh = np.zeros_like(ink); sh[:, 1:] |= ink[:, :-1]; sh[1:, :] |= ink[:-1, :]; sh[1:, 1:] |= ink[:-1, :-1]
    img_b = np.full((16, 192), 15, np.uint8); img_b[sh & ~ink] = 14; img_b[ink] = 0
    for k, t in enumerate(big): ps3gfx.put(g, t, img_b[:, 16 * k:16 * k + 16].copy())
    prev.append((PB, jp_s, img_s)); prev.append((PB, jp_b, img_b))
    log('무대 제목: 옮긴 칸 %d (영문 제목 전용 칸 %d 중) · 나머지는 제자리' % (moved[0], len(free)))
    return prev
def main():
    from PIL import Image
    src = sys.argv[1] if len(sys.argv) > 2 else os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd22.bin')
    e = bytearray(open(os.path.join(ROOT, 'work', 'bin', 'EBOOT.elf'), 'rb').read())
    g = bytearray(open(src, 'rb').read())
    prev = build(e, g)
    if len(sys.argv) > 2: open(sys.argv[2], 'wb').write(g)
    pal = np.zeros((16, 3), np.uint8); pal[:] = (120, 120, 120); pal[0] = (255, 255, 255); pal[14] = (10, 10, 10); pal[15] = (60, 80, 110)
    lines = {}
    for o, jp, ko in prev: lines.setdefault(o, []).append((jp, ko))
    rows = []
    for o, parts in lines.items():
        gap = np.full((16, 6, 3), (30, 30, 30), np.uint8)
        a = np.hstack(sum([[pal[p[0]], gap] for p in parts], [])); b = np.hstack(sum([[pal[p[1]], gap] for p in parts], []))
        Wd = 430; a = a[:, :Wd]; b = b[:, :Wd]
        a = np.pad(a, ((0, 0), (0, Wd - a.shape[1]), (0, 0))); b = np.pad(b, ((0, 0), (0, Wd - b.shape[1]), (0, 0)))
        rows += [a, b, np.full((4, Wd, 3), 0, np.uint8)]
    img = np.vstack(rows)
    Image.fromarray(img).resize((img.shape[1] * 3, img.shape[0] * 3), 0).save(os.path.join(ROOT, 'work', 'ring', 'preview', 'stage_titles.png'))
if __name__ == '__main__':
    main()
