# -*- coding: utf-8 -*-
r"""SOM 이름 입력 영문화 (2026-11-14 밤 4) — 돌판 글자층을 «진짜 커서 사각형» 안에 다시 배치.
  · 커서 강조 = EBOOT 0x14B6094 표(4 B × 64: u16 타일맵 오프셋 x칸<<7|y칸<<2 · 폭−1 · 높이−1, 8px 칸)의 사각형 안
    scroll1 칸 팔레트를 0x1C → 0x18 로 바꿈(빈칸 포함). 스테이트 이름_아·이름_이 타일맵으로 확정: ア = 48..72×56..80, イ = 72..96×56..80.
    화면 좌표 = x칸×8, y칸×8−16. 열 폭 24·24·16·24·24 | 24·16·24·24·16, 행 높이 24·24·16·24·24·24. (표는 안 고침)
  · 화면 배치표 = EBOOT 0x58E286: 머리 «0000 0017 002E»(23행 × 46열) + 0x58E28C~ 열 우선 (타일, 속성) 4 B, 끝 FFFF.
    칸 (x, y) = 0x58E28C + (x/8)×0x5C + ((y−24)/8)×4. 빈칸 = 0020. 스테이트 타일맵과 전 칸 일치(옛 ovlfull_JP.json 은 18칸 틀림).
  · 글자 = 하스피 돌판 그림(work/ring/tablet_user_layer.npy)의 획(번호 8~14)만 떼어 칸 사각형 가운데로.
    글자가 걸치는 빈칸·공용 점 타일 칸은 배치표에 새 타일(일본판이 안 쓰는 영문 돌판 타일 0x2B9C~)을 넣어 채움.
  python tools/name_en.py preview            → work/name_en/미리보기_돌판_영문.png (원본에 적용해 본 파일을 되읽어 그림)
  build_som.py 가 patch_table(e) · write(dd21x) 를 부름"""
import os, sys, json, struct
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = lambda *p: os.path.join(ROOT, *p)
CURSOR_TAB = 0x14B6094
SCR_TAB = 0x58E28C; SCR_ROWS = 23; SCR_COLS = 46; SCR_Y0 = 24
LAYOUT = ['ABCDE01234', 'FGHIJ56789', 'KLMNO.&_-!', 'PQRST     ', 'UVWXY    ?', 'Z         ']   # 4행 오른쪽 «.&_-!» 중복은 뺌(하스피 2026-11-14)
USER_COLS = [60, 83, 104, 126, 147, 185, 206, 230, 253, 275]      # 하스피 그림의 글자 중심(대략) — 덩어리를 칸에 붙이는 데만 씀
USER_ROWS = [68, 90, 115, 137, 162, 185]
LO, HI = 0x2983, 0x2B9C                                           # 글자층 타일(일본판)
FREE = (0x2B9C, 0x2D5E)                                           # 영문 돌판 타일 — 일본판 배치표에 없음
BTN = set()
for a_, b_ in ((0x2B3D, 0x2B42), (0x2B45, 0x2B4A), (0x2B57, 0x2B5C), (0x2B62, 0x2B67), (0x2B6E, 0x2B73), (0x2B76, 0x2B7B), (0x2B85, 0x2B8A), (0x2B8E, 0x2B93)):
    BTN |= set(range(a_, b_))
# 하스피 그림에서 글자에 붙어 온 낱점(커서 때 주황·붉은 찌꺼기로 보임) — 짚은 글자만(2026-11-14 실기: 5 왼쪽 아래·6 오른쪽 위). (y, x, 번호) = 그림 좌표
DROP = {(1, 5): lambda y, x, v: v == 9 or y >= 97,      # 5: 위 회색 점 2개(82~83행) + 꼬리 아래 떨어진 점(97~99행)
        (1, 6): lambda y, x, v: v == 9}                 # 6: 오른쪽 위 회색 점들(86·87·90행)
AREA = (40, 48, 296, 200)                                         # 다시 쓰는 범위(가나가 있던 곳 전부, 버튼 x≥304 제외)
PAL = {0: 0x112233, 1: 0x222233, 2: 0x333344, 3: 0x334455, 4: 0x445566, 5: 0x556666, 6: 0x667777, 7: 0xccddee, 8: 0x111122, 9: 0x555566,
       10: 0xbbbbcc, 11: 0xccccdd, 12: 0xddddee, 13: 0xeeeeff, 14: 0xffffff}
PAL_CUR = {**PAL, 8: 0x550000, 9: 0x990000, 10: 0xff3300, 11: 0xff5500, 12: 0xff6600, 13: 0xff8800, 14: 0xffaa00}
ORIG_ELF = R('work', 'bin', 'EBOOT.elf')


def cell_off(x, y): return SCR_TAB + (x // 8) * SCR_ROWS * 4 + ((y - SCR_Y0) // 8) * 4


def screen_table(e):
    """{(x, y): (타일, 속성)} — 빈칸(0020) 포함 전 칸"""
    assert bytes(e[SCR_TAB - 6:SCR_TAB]) == bytes.fromhex('00000017002e') and bytes(e[SCR_TAB + SCR_COLS * SCR_ROWS * 4:][:2]) == b'\xff\xff'
    return {(c * 8, SCR_Y0 + r * 8): struct.unpack('>HH', e[cell_off(c * 8, SCR_Y0 + r * 8):][:4]) for c in range(SCR_COLS) for r in range(SCR_ROWS)}


def zones(e):
    """커서 표 → 글자 칸 6×10 사각형 (x, y, w, h) 화면 좌표"""
    recs = []
    for i in range(64):
        off, w, h = struct.unpack('>HBB', e[CURSOR_TAB + 4 * i:CURSOR_TAB + 4 * i + 4])
        recs.append(((off >> 7) * 8, ((off >> 2) & 31) * 8 - 16, (w + 1) * 8, (h + 1) * 8))
    recs = [z for z in recs if z[0] < 304]                         # 버튼 4개 빼면 60
    assert len(recs) == 60
    return [recs[r * 10:(r + 1) * 10] for r in range(6)]


def paintable(tab):
    """다시 써도 되는 칸 {(x, y): 타일} — 글자층 타일 · 한 번만 쓰임 · 뒤집힘 없음 · 버튼 아님"""
    cnt = {}
    for t, at in tab.values(): cnt[t] = cnt.get(t, 0) + 1
    out = {}
    for (x, y), (t, at) in tab.items():
        if not (AREA[0] <= x < AREA[2] and AREA[1] <= y < AREA[3]): continue
        if not (LO <= t < HI) or t in BTN or cnt[t] != 1 or at != 0x1c: continue
        out[(x, y)] = t
    return out


def letters():
    """하스피 그림에서 글자 획(8~14)만 → {(행, 열): [(y, x, 번호)]}"""
    import cv2
    u = np.load(R('work', 'ring', 'tablet_user_layer.npy'))
    m = (u >= 8) & (u != 15); m[:AREA[1]] = False; m[AREA[3]:] = False; m[:, :AREA[0]] = False; m[:, AREA[2]:] = False
    n, lab = cv2.connectedComponents(cv2.dilate(m.astype(np.uint8), np.ones((3, 3), np.uint8)), connectivity=8)
    out = {}
    for k in range(1, n):
        ys, xs = np.nonzero((lab == k) & m)
        if len(ys) < 3: continue                                    # 낱점 찌꺼기
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        c = min(range(10), key=lambda i: abs(USER_COLS[i] - cx)); r = min(range(6), key=lambda i: abs(USER_ROWS[i] - cy))
        out.setdefault((r, c), []).extend((int(y), int(x), int(u[y, x])) for y, x in zip(ys, xs))
    want = {(r, c) for r, row in enumerate(LAYOUT) for c, ch in enumerate(row) if ch not in ' _'}
    assert want <= set(out), ('글자 덩어리와 배치가 안 맞음', sorted(want - set(out)))
    for k, f in DROP.items(): out[k] = [p for p in out[k] if not f(*p)]
    return {k: v for k, v in out.items() if k in want}          # 배치에서 뺀 칸의 그림은 버림


def compose(e0=None, log=print):
    """→ (새 글자층 그림, {(x, y): 타일}(다시 쓸 칸 전부), {(x, y): 새 타일}(배치표에 새로 넣을 칸))"""
    e0 = e0 if e0 is not None else open(ORIG_ELF, 'rb').read()
    tab = screen_table(e0); Z = zones(e0); cm = paintable(tab); L = letters()
    used = {t for t, at in tab.values()}
    free = [t for t in range(*FREE) if t not in used]
    new = np.full((224, 384), 15, np.uint8); added = {}
    for r in range(6):
        cells = [(c, L[r, c]) for c in range(10) if (r, c) in L]
        if not cells: continue
        # 키 큰 글자는 저마다 «아랫단»을 같은 줄에(하스피 그림은 글자마다 위아래 1px 씩 어긋남), 부호(. -)는 글자와의 높낮이 그대로
        ext = {c: (min(p[0] for p in px), max(p[0] for p in px) + 1) for c, px in cells}
        tall = [ext[c] for c, px in cells if ext[c][1] - ext[c][0] >= 10]
        Hm = int(np.median([b - t for t, b in tall])); bot = int(np.median([b for t, b in tall]))
        zy, zh = Z[r][0][1], Z[r][0][3]
        base = zy + (zh + Hm) // 2                                 # 글자 아랫단 줄
        for c, px in cells:
            zx, _, zw, _ = Z[r][c]; t, b = ext[c]
            oy = base - (b if b - t >= 10 else bot)
            oy = min(max(oy, zy - t), zy + zh - b)                 # 칸 안으로
            x0 = min(p[1] for p in px); x1 = max(p[1] for p in px) + 1
            br = [p[1] for p in px if p[2] >= 10]                  # 가로 = 밝은 획 기준 가운데(그림자 폭이 글자마다 달라서), 전체가 칸 안에 들게
            ox = zx + (zw - (max(br) + 1 - min(br))) // 2 - min(br)
            ox = min(max(ox, zx - x0), zx + zw - x1)
            assert zx <= x0 + ox and x1 + ox <= zx + zw and zy <= t + oy and b + oy <= zy + zh, ('칸 밖', LAYOUT[r][c])
            for y, x, v in px:
                X, Y = x + ox, y + oy; k = (X & ~7, Y & ~7)
                if k not in cm:                                     # 빈칸·공용 점 타일 칸 → 새 타일
                    if k not in added: added[k] = free.pop(0)
                new[Y, X] = v
    cm = {**cm, **added}
    log('이름 돌판: 글자 %d개 · 다시 쓰는 칸 %d(그중 배치표에 새로 넣는 칸 %d: %s)' % (len(L), len(cm), len(added),
        ' '.join('%d,%d=%04X(옛 %04X)' % (x, y, t, tab[(x, y)][0]) for (x, y), t in sorted(added.items()))))
    return new, cm, added


def patch_table(e, log=print):
    """EBOOT 화면 배치표에 새 칸 타일 넣기(속성 0x1C) → 바꾼 칸 수"""
    e0 = open(ORIG_ELF, 'rb').read()
    new, cm, added = compose(e0, log)
    for (x, y), t in added.items():
        o = cell_off(x, y)
        assert bytes(e[o:o + 4]) == e0[o:o + 4] and e0[o + 2:o + 4] in (b'\x00\x1c', b'\x00\x3c', b'\x00\x7c'), ('배치표 칸이 예상과 다름', x, y, e0[o:o + 4].hex())
        e[o:o + 4] = struct.pack('>HH', t, 0x1c)
    return len(added)


def write(src, dst, log=lambda *a: None):
    """dd21x 글자층 타일에 새 글자판 → 바꾼 타일 수"""
    new, cm, added = compose(None, log)
    raw = bytearray(open(src, 'rb').read()); g0 = open(R('work', 'orig', 'game_data', 'dd21x.bin'), 'rb').read(); n = 0
    for (x, y), t in cm.items():
        o = t * 64
        assert raw[o:o + 64] == g0[o:o + 64], ('앞 단계가 이미 고친 타일', hex(t))
        tt = new[y:y + 8, x:x + 8].reshape(-1)
        b = bytes((tt[0::2] & 15) | ((tt[1::2] & 15) << 4))
        n += raw[o:o + 32] != b; raw[o:o + 32] = b
    open(dst, 'wb').write(raw)
    return n


def read_layer(gfx, e):
    """파일의 타일을 배치표대로 되읽어 글자층 그림(224×384, 15 = 투명) — 공용·뒤집힌 칸 포함"""
    raw = np.frombuffer(open(gfx, 'rb').read() if isinstance(gfx, str) else gfx, np.uint8)
    img = np.full((224, 384), 15, np.uint8)
    for (x, y), (t, at) in screen_table(e).items():
        if t == 0x20 or not (AREA[0] <= x < AREA[2] and AREA[1] <= y < AREA[3]) or at & 0x1f != 0x1c: continue
        b = raw[t * 64:t * 64 + 32]; tt = np.empty(64, np.uint8); tt[0::2] = b & 15; tt[1::2] = b >> 4; tt = tt.reshape(8, 8)
        if at & 0x20: tt = tt[:, ::-1]
        if at & 0x40: tt = tt[::-1]
        img[y:y + 8, x:x + 8] = tt
    return img


def preview(gfx=None, elf=None, name='미리보기_돌판_영문.png'):
    """gfx·elf 를 안 주면 원본에 적용해 본 임시 파일로. 그림은 언제나 «파일 바이트 → 배치표 → 타일»로 되읽은 것."""
    from PIL import Image, ImageDraw, ImageFont
    import tempfile, shutil
    e0 = open(ORIG_ELF, 'rb').read(); g0 = R('work', 'orig', 'game_data', 'dd21x.bin')
    td = None
    if gfx is None:
        td = tempfile.mkdtemp(); gfx = os.path.join(td, 'dd21x.bin')
        print('바꾼 타일', write(g0, gfx, print))
        e = bytearray(e0); print('배치표 새 칸', patch_table(e, lambda *a: None))
    else:
        e = open(elf, 'rb').read()
    Z = zones(e0)
    stone = np.array(Image.open(R('work', 'ring', 'tablet_clean_1x.png')).convert('RGB'))      # 돌 바탕(가나 지운 그림 — 글자 밑 돌 무늬는 어림)
    # 바탕 그림에 남은 글자 흔적(영문판 화면에서 따 온 밝은 화소 등) 지움: 일본 화면에서 글자층이 투명한 화소는 그 화면값,
    # 글자층 밑은 글자 색이면 둘레 돌로 메움 — 미리보기 전용(빌드 파일과 무관)
    import cv2, name_overlay
    KJ = name_overlay.screen('JP'); J = read_layer(g0, e0)
    kj = np.stack([(KJ >> 16) & 255, (KJ >> 8) & 255, KJ & 255], -1).astype(np.uint8)
    ar = np.zeros(J.shape, bool); ar[AREA[1]:AREA[3], AREA[0]:AREA[2]] = True
    ar[56:80, 40:76] = False                                       # 일본 화면의 커서(ア 주황)·1P 손 둘레는 옛 바탕 그대로
    sure = ar & (J == 15); stone[sure] = kj[sure]
    sv = stone.astype(np.int64); sv = (sv[..., 0] << 16) | (sv[..., 1] << 8) | sv[..., 2]
    bad = ar & (J != 15) & np.isin(sv, [0xbbbbcc, 0xccccdd, 0xddddee, 0xeeeeff, 0xffffff, 0x111122])
    if bad.any(): stone = cv2.inpaint(stone, cv2.dilate(bad.astype(np.uint8), np.ones((3, 3), np.uint8)), 3, cv2.INPAINT_TELEA)
    def draw(layer, cur=None):
        out = stone.copy()
        for i, c in PAL.items(): out[layer == i] = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
        for x, y, w, h in (cur or []):
            sub = layer[y:y + h, x:x + w]; o = out[y:y + h, x:x + w]
            for i, c in PAL_CUR.items(): o[sub == i] = ((c >> 16) & 255, (c >> 8) & 255, c & 255)
        return out
    old = read_layer(g0, e0); new = read_layer(gfx, e)
    if td: shutil.rmtree(td, True)
    S = 3; crop = lambda a: a[40:204, 36:300]
    def up(a): return Image.fromarray(crop(a)).resize((crop(a).shape[1] * S, crop(a).shape[0] * S), 0)
    a = up(draw(old)); b = up(draw(new)); c = up(draw(new, [Z[0][0], Z[1][2], Z[2][6], Z[3][4], Z[4][9]]))   # 커서 예 = A · H · & · T · ?
    g = b.copy(); d = ImageDraw.Draw(g)
    for row in Z:
        for x, y, w, h in row:
            d.rectangle([(x - 36) * S, (y - 40) * S, (x + w - 36) * S - 1, (y + h - 40) * S - 1], outline=(255, 150, 0))
    W, H = a.size; pad = 26
    sheet = Image.new('RGB', (W * 2 + 12, (H + pad) * 2 + 4), (24, 24, 28)); d = ImageDraw.Draw(sheet)
    f = ImageFont.truetype(r'C:\Windows\Fonts\malgun.ttf', 17)
    for k, (im, t) in enumerate(((a, '원본(일본판 가나)'), (b, '새 돌판(영문) — 빌드 파일 되읽음'), (g, '새 돌판 + 커서 사각형(주황 선 = 게임 표 그대로)'), (c, '커서가 있을 때 예(A·H·&·T·? — 그 칸만 주황)'))):
        x = (k % 2) * (W + 12); y = (k // 2) * (H + pad + 4)
        d.text((x + 4, y + 2), t, fill=(240, 240, 240), font=f); sheet.paste(im, (x, y + pad))
    os.makedirs(R('work', 'name_en'), exist_ok=True)
    sheet.save(R('work', 'name_en', name)); print(R('work', 'name_en', name))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) > 3: preview(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else '미리보기_돌판_영문_빌드.png')
    else: preview()
