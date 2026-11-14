# -*- coding: utf-8 -*-
r"""TOD 롬 그림 글자 한글 (2026-11-14, FBNeo ddtodj 화면 화소 대조로 위치 찾음).
  · 아이템 이름 띠: dd11x 8x8 칸, 띠 = 8칸 × 2줄(64×16), 줄 머리 0xE80~0xFE0(일본판), 왼쪽/오른쪽 = +0/+8.
    글자 = 색 9(4~9행), 바탕 = 줄마다 한 색 그라데이션 → 글자 화소를 그 줄 최빈색으로 지우고 han8 한글(색 9) 가운데.
    링 띠(リング LB 등)는 오른쪽 약자(LB·MM…) 화소는 그대로, 왼쪽 リング 만 «링».
  · 캐릭터 설명 상자: dd10 16x16 타일, 상자마다 7장(112×16): 0x9579(회복)·0x9589(특수)·0x9599(공격마법)·0x95A9(hp검술).
    테두리 안쪽을 바탕색으로 비우고 갈무리11 한글(원래 글자 주색).
  python tools/tod_hud_gfx.py → 미리보기 work/tod/preview_bars.png · preview_caps.png (원본|한글, 실제 색)
  apply(dd10 bytearray, dd11x bytearray, log)"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools'); sys.path.insert(0, r'C:\claude\project\quovadis2-kr-patch\tools')   # han8
R =lambda *p: os.path.join(ROOT, *p)
BARS = [(0xE80, 0, '해머'), (0xE80, 1, '매직 미사일'), (0xEA0, 0, '화살'), (0xEA0, 1, '인비저빌리티'),
        (0xEC0, 0, '단도'), (0xEC0, 1, '파이어볼'), (0xEE0, 0, '오일'), (0xEE0, 1, '라이트닝 볼트'),
        (0xF00, 0, '아이스 스톰'), (0xF00, 1, '홀드 퍼슨'), (0xF20, 0, '폴리모프 아더'), (0xF20, 1, '스트라이킹'),
        (0xF40, 0, '클라우드킬'), (0xF40, 1, '큐어 운즈'), (0xF60, 0, '컨티뉴얼 라이트'), (0xF60, 1, '스틱 투 스네이크'),
        (0xF80, 0, '턴 언데드'), (0xF80, 1, '링'), (0xFA0, 0, '링'), (0xFA0, 1, '링'), (0xFC0, 0, '링'), (0xFC0, 1, '링'), (0xFE0, 0, '링')]
CAPS = [(0x9579, '회복·방어 마법'), (0x9589, '특수 공격에 강하다'), (0x9599, '공격 마법을 쓴다'), (0x95A9, 'HP·검술이 뛰어나다')]
TXT = 9
def cells(b):
    a = np.frombuffer(bytes(b), np.uint8); n = len(a) // 64; t = a[:n * 64].reshape(n, 64)[:, :32]
    p = np.empty((n, 64), np.uint8); p[:, 0::2] = t & 15; p[:, 1::2] = t >> 4; return p.reshape(n, 8, 8)
def get_bar(C, r0, side):
    c0 = r0 + side * 8
    return np.vstack([np.hstack([C[c0 + k] for k in range(8)]), np.hstack([C[c0 + 16 + k] for k in range(8)])])
def put_cell(b, i, img):
    f = img.reshape(-1).astype(np.uint8); b[i * 64:i * 64 + 32] = bytes((f[0::2] & 15) | ((f[1::2] & 15) << 4))
def put_bar(b, r0, side, img):
    c0 = r0 + side * 8
    for k in range(8):
        put_cell(b, c0 + k, img[:8, k * 8:k * 8 + 8]); put_cell(b, c0 + 16 + k, img[8:, k * 8:k * 8 + 8])
def han8_line(text, gap=1):
    import han8
    cols = []
    for ch in text:
        if ch == ' ': cols.append(np.zeros((8, 3), bool)); continue
        g, w = han8.glyph(ch); m = np.array(g, bool)[:8, :max(1, w)]
        cols.append(m)
        if gap: cols.append(np.zeros((8, gap), bool))
    m = np.hstack(cols) if cols else np.zeros((8, 1), bool)
    xs = np.nonzero(m.any(0))[0]; return m[:, xs.min():xs.max() + 1] if len(xs) else m
def g7_line(text):
    from bdf import Font
    pts, w = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf').draw(text)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    m = np.zeros((max(ys) - min(ys) + 1, max(xs) - min(xs) + 1), bool)
    for x, y in pts: m[y - min(ys), x - min(xs)] = True
    return m
def new_bar(B, ko):
    img = B.copy(); txt = img == TXT
    keep = np.zeros_like(txt)
    if ko == '링':                                         # 오른쪽 약자(LB 등) = 글자 사이 가장 넓은 빈 열 오른쪽
        cols = np.nonzero(txt.any(0))[0]; gaps = np.diff(cols); k = int(np.argmax(gaps)); keep[:, cols[k + 1]:] = True
    for y in range(16):
        row = img[y][~txt[y]]
        if len(row): img[y][txt[y] & ~keep[y]] = np.bincount(row, minlength=16).argmax()
    x1 = (np.nonzero(keep.any(0))[0].min() - 2) if keep.any() else 64
    m = g7_line(ko)                                            # 갈무리7(7줄) — han8 8x8 은 이 크기에서 ㅌ이 ㄷ 처럼 보임
    h, w = m.shape
    x0 = max(0, (x1 - w) // 2)
    if w > x1: print('⚠띠 넘침', ko, w, x1)
    ys, xs = np.nonzero(m); img[np.clip(ys + 4, 0, 15), np.clip(xs + x0, 0, 63)] = TXT          # 4~10행(하스피 «한 픽셀씩 내리고»)
    return img
def tiles16(b):
    a = np.frombuffer(bytes(b), np.uint8); n = len(a) // 128; t = a[:n * 128].reshape(n, 128)
    p = np.empty((n, 256), np.uint8); p[:, 0::2] = t & 15; p[:, 1::2] = t >> 4; return p.reshape(n, 16, 16)
def put16(b, i, img):
    f = img.reshape(-1).astype(np.uint8); b[i * 128:(i + 1) * 128] = bytes((f[0::2] & 15) | ((f[1::2] & 15) << 4))
def new_cap(Bx, ko):
    from bdf import Font
    img = Bx.copy(); H, Wd = img.shape
    bg = 14
    inner = np.zeros_like(img, bool)
    rows = [y for y in range(H) if (img[y] == bg).sum() > Wd * 0.3]
    cols = [x for x in range(Wd) if (img[:, x] == bg).sum() > 3]
    y0, y1, x0, x1 = min(rows), max(rows), min(cols), max(cols)
    txt_vals = img[y0:y1 + 1, x0:x1 + 1]; tv = txt_vals[txt_vals != bg]
    fg = int(np.bincount(tv, minlength=16).argmax()) if len(tv) else 1
    img[y0:y1 + 1, x0:x1 + 1] = bg
    for fn in ('Galmuri11.bdf', 'Galmuri11-Condensed.bdf'):                 # 넘치면 가로 좁은 판
        f = Font(os.path.join(r'C:\claude\utils\font\Galmuri-v2.40.3', fn)); pts, w = f.draw(ko)
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; W = max(xs) - min(xs) + 1; Hh = max(ys) - min(ys) + 1
        if W <= x1 - x0 + 1: break
    ox = x0 + (x1 - x0 + 1 - W) // 2; oy = y0 + (y1 - y0 + 1 - Hh) // 2
    if W > x1 - x0 + 1: print('⚠상자 넘침', ko, W, x1 - x0 + 1)
    for x, y in pts: img[y - min(ys) + oy, x - min(xs) + ox] = fg
    return img
def apply(d10, d11, log=print):
    C = cells(d11)
    for r0, side, ko in BARS: put_bar(d11, r0, side, new_bar(get_bar(C, r0, side), ko))
    T = tiles16(d10)
    for t0, ko in CAPS:
        box = np.hstack([T[t0 + k] for k in range(7)]); nb = new_cap(box, ko)
        for k in range(7): put16(d10, t0 + k, nb[:, k * 16:(k + 1) * 16])
    log('TOD 아이템 띠 %d · 설명 상자 %d' % (len(BARS), len(CAPS)))
def palette_from_fbneo(tile_img, sx, sy, scr):
    pal = {}
    for y in range(tile_img.shape[0]):
        for x in range(tile_img.shape[1]):
            pal.setdefault(int(tile_img[y, x]), tuple(scr[sy + y, sx + x]))
    return pal
def main():
    from PIL import Image
    scr = np.array(Image.open(R('work', 'tod', 'fbneo_select.png')).convert('RGB'))
    d11 = bytearray(open(R('work', 'orig', 'game_data', 'dd11x.bin'), 'rb').read()); d10 = bytearray(open(R('work', 'orig', 'game_data', 'dd10.bin'), 'rb').read())
    C = cells(d11); T = tiles16(d10)
    # 실제 색: 띠 = ダガー 띠(화면 x 8, y 204 근처에 놓임 — 0xEC3 칸이 (32,208))
    dag = get_bar(C, 0xEC0, 0); pal_b = palette_from_fbneo(dag, 8, 208, scr)
    cap = np.hstack([T[0x9579 + k] for k in range(7)]); pal_c = palette_from_fbneo(cap, 272, 80, scr)
    def rgb(a, pal): return np.array([[pal.get(int(v), (255, 0, 255)) for v in r] for r in a], np.uint8)
    rows = []
    for r0, side, ko in BARS:
        B = get_bar(C, r0, side); rows.append(np.hstack([rgb(B, pal_b), np.zeros((16, 4, 3), np.uint8), rgb(new_bar(B, ko), pal_b)])); rows.append(np.zeros((3, 132, 3), np.uint8))
    a = np.vstack(rows); Image.fromarray(a).resize((a.shape[1] * 4, a.shape[0] * 4), 0).save(R('work', 'tod', 'preview_bars.png'))
    rows = []
    for t0, ko in CAPS:
        Bx = np.hstack([T[t0 + k] for k in range(7)]); rows.append(np.hstack([rgb(Bx, pal_c), np.zeros((16, 4, 3), np.uint8), rgb(new_cap(Bx, ko), pal_c)])); rows.append(np.zeros((3, 228, 3), np.uint8))
    a = np.vstack(rows); Image.fromarray(a).resize((a.shape[1] * 4, a.shape[0] * 4), 0).save(R('work', 'tod', 'preview_caps.png'))
if __name__ == '__main__':
    main()
