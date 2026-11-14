# -*- coding: utf-8 -*-
r"""SOM 링 위 이름 그림(dd22.bin 16x16 타일 0x1460~0x17FF) — 라벨 칸 찾기·묶기 (2026-11-13).
  라벨 = 2타일(32px) 폭 스프라이트, 글자 A/B 색 + 오른쪽·아래 0 그림자, 한 줄 = 위 8px · 두 줄 = 16px.
  python tools/ringlab.py → work/ring/chunks.json · chunks_N.png(번호판)"""
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import ps3gfx
LO, HI = 0x1460, 0x1800
def load(b):
    rows = [np.hstack([ps3gfx.tile(b, r0 + k) for k in range(16)]) for r0 in range(LO, HI, 16)]
    return np.vstack(rows)
def text_tiles(canvas):
    ok = np.zeros((canvas.shape[0] // 16, 16), bool)
    for r in range(ok.shape[0]):
        for k in range(16):
            t = canvas[r*16:(r+1)*16, k*16:(k+1)*16]
            c = np.bincount(t.reshape(-1), minlength=16)
            other = 256 - c[15] - c[10] - c[11] - c[9] - c[0]
            box = np.isin(t, [10, 11]).all(1).any() or np.isin(t, [10, 11]).all(0).any()
            ok[r, k] = (c[10] + c[11]) >= 4 and other <= 4 and not box
    return ok
def chunks(canvas):
    ok = text_tiles(canvas); ink = np.isin(canvas, [10, 11]); out = []
    for r in range(ok.shape[0]):
        k = 0
        while k < 16:
            if not ok[r, k]: k += 1; continue
            w = 2 if k + 1 < 16 and ok[r, k + 1] else 1
            reg = ink[r*16:(r+1)*16, k*16:(k+w)*16]
            ys = np.nonzero(reg.any(1))[0]
            lines = 2 if ys.max() >= 8 else 1
            col = 10 if (canvas[r*16:(r+1)*16, k*16:(k+w)*16] == 10).sum() >= (canvas[r*16:(r+1)*16, k*16:(k+w)*16] == 11).sum() else 11
            out.append(dict(tile=LO + r*16 + k, w=w, lines=lines, col=col, key=reg.tobytes().hex()))
            k += w
    return out
def main():
    from PIL import Image, ImageDraw
    b = open(os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd22.bin'), 'rb').read()
    cv = load(b); ch = chunks(cv)
    uniq = {}
    for c in ch: uniq.setdefault(c['key'], []).append(c)
    U = list(uniq.values())
    print(len(ch), 'chunks', len(U), 'unique')
    pal = np.full(16, 60, np.uint8); pal[10] = 255; pal[11] = 255; pal[9] = 30; pal[15] = 15; pal[0] = 30
    s = 4; cols = 6; cw = 32 * s + 60; chh = 16 * s + 16
    im = Image.new('L', (cols * cw, ((len(U) + cols - 1) // cols) * chh), 10); d = ImageDraw.Draw(im)
    for n, g in enumerate(U):
        c = g[0]; x = (n % cols) * cw; y = (n // cols) * chh
        r = (c['tile'] - LO) // 16; k = (c['tile'] - LO) % 16
        a = cv[r*16:(r+1)*16, k*16:(k+c['w'])*16]
        d.text((x, y), '%d %X n%d' % (n, c['tile'], len(g)), fill=255)
        im.paste(Image.fromarray(pal[a]).resize((a.shape[1] * s, a.shape[0] * s), 0), (x, y + 12))
    H = im.height; step = chh * 8
    for i, y0 in enumerate(range(0, H, step)): im.crop((0, y0, im.width, min(H, y0 + step))).save(os.path.join(ROOT, 'work', 'ring', 'chunks_%d.png' % i))
    json.dump([[{k: v for k, v in c.items() if k != 'key'} for c in g] for g in U], open(os.path.join(ROOT, 'work', 'ring', 'chunks.json'), 'w'))
if __name__ == '__main__':
    main()


# ---- 한글 그리기 (2026-11-13) ----
def galmuri():
    sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
    from bdf import Font
    return Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri7.bdf')
def render_line(font, text):
    """→ bool 배열(높이 8, 폭 W) — 잉크 윗선 0행."""
    pts, w = font.draw(text)
    if not pts: return np.zeros((1, 1), bool)
    ys = [p[1] for p in pts]; xs = [p[0] for p in pts]
    y0 = min(ys); x0 = min(xs)
    W = max(xs) - x0 + 1; H = max(ys) - y0 + 1
    a = np.zeros((H, W), bool)
    for x, y in pts: a[y - y0, x - x0] = True
    return a
def draw_label(cv, tile, w, lines, col, text, font):
    """cv(캔버스) 안 라벨 칸을 지우고 한글을 그림. 넘치면 False."""
    r = (tile - LO) // 16; k = (tile - LO) % 16
    X0, Y0 = k * 16, r * 16; Wpx = w * 16
    hh = 16 if lines == 2 else 8
    reg = cv[Y0:Y0 + hh, X0:X0 + Wpx]
    reg[np.isin(reg, [10, 11, 0, 9])] = 15
    parts = text.split('／')
    ok = True
    for li, t in enumerate(parts):
        a = render_line(font, t)
        if a.shape[0] > 7 or a.shape[1] + 1 > Wpx: ok = False
        a = a[:7, :Wpx - 1]
        x = 1 if a.shape[1] + 2 <= Wpx else 0
        ink = np.zeros((8, Wpx), bool); ink[0:a.shape[0], x:x + a.shape[1]] = a
        sh = np.zeros_like(ink); sh[:, 1:] |= ink[:, :-1]; sh[1:, :] |= ink[:-1, :]
        y = li * 8
        band = reg[y:y + 8]
        band[sh & ~ink] = 0; band[ink] = col
    return ok
def build_ko(b_in):
    """→ (새 dd22 bytes, 넘침 목록)"""
    b = bytearray(b_in); cv = load(b_in)
    ko = {}
    for ln in open(os.path.join(ROOT, 'work', 'ring', 'ring_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        if ln.strip():
            c = ln.split('\t'); ko[int(c[0])] = c[2]
    U = json.load(open(os.path.join(ROOT, 'work', 'ring', 'chunks.json')))
    font = galmuri(); over = []
    for n, g in enumerate(U):
        if n not in ko: continue
        for c in g:
            if not draw_label(cv, c['tile'], c['w'], c['lines'], c['col'], ko[n], font): over.append((n, ko[n]))
    apply_composites(cv, font)
    # 캔버스 → 타일
    for r in range((HI - LO) // 16):
        for k in range(16):
            ps3gfx.put(b, LO + r * 16 + k, cv[r*16:(r+1)*16, k*16:(k+1)*16].copy())
    return bytes(b), sorted(set(over))


# ---- 타일 나눠 쓰는 라벨 (ITEM COLLECTION 스프라이트 목록으로 확인, 2026-11-13) ----
# (타일 목록, [(줄, x, 글)...]) — 글자를 x 위치에 직접 놓는다. 공유 타일은 같은 그림이 되게 배치.
COMPOSITE = [
    ((0x160F, 0x1607), [(0, 1, '번개의'), (1, 1, '검')]),     # 雷のつるぎ(주황) — 1607 = 炎のつるぎ 뒤 타일
    ((0x1612, 0x1609), [(0, 1, '번개의'), (1, 1, '검')]),     # 雷のつるぎ(흰)  — 1609 = 炎のつるぎ 흰 사본 뒤 타일
    ((0x1606, 0x1607), [(0, 1, '화염의'), (1, 1, '검')]),
    ((0x1608, 0x1609), [(0, 1, '화염의'), (1, 1, '검')]),
    ((0x1668, 0x1661), [(0, 1, '번개의'), (1, 1, '완드')]),   # 雷のワンド — 1661 = 炎のワンド 뒤 타일
    ((0x1669, 0x1663), [(0, 1, '번개의'), (1, 1, '완드')]),
    ((0x1660, 0x1661), [(0, 1, '화염의'), (1, 1, '완드')]),
    ((0x1662, 0x1663), [(0, 1, '화염의'), (1, 1, '완드')]),
    ((0x161F, 0x1630), [(0, 1, '저주의'), (1, 1, '검'), (1, 18, '1')]),   # 呪いのつるぎ1·2 앞 타일 공유
    ((0x161F, 0x1637), [(0, 1, '저주의'), (1, 1, '검'), (1, 18, '2')]),
    ((0x1631, 0x1632), [(0, 1, '저주의'), (1, 1, '검'), (1, 18, '1')]),
    ((0x1631, 0x1638), [(0, 1, '저주의'), (1, 1, '검'), (1, 18, '2')]),
    ((0x1631, 0x16F4), [(0, 1, '저주의'), (1, 1, '검')]),
    ((0x16F3, 0x16F4), [(0, 1, '저주의'), (1, 1, '검')]),   # 16F3 = 노란 «呪い/つ» — 16F4 의 또 다른 앞 타일(원본 그대로였음)   # 링 위 저주의 검 1·2 = 161F/1631 + 16F4(숫자 없는 뒤 타일) + 숫자 타일 15F8~ 겹침 — 16F4 빠져 «저주の／검 ぎ1»(2026-11-15 하스피 스샷·스테이트 2_16)
    # 0x16BB NOTHING 은 회색 상자 아이콘(글자 색이 달라) 영어 그대로 둠
    ((0x1704, 0x1705), [(0, 2, '없음')]),
    ((0x1690, 0x1691), [(0, 1, '스트라이'), (1, 1, '킹')]),                # ストライキングのつえ — 앞 타일을 마법과 공유 · «봉» 뺌(하스피 2026-11-14)
    ((0x1692, 0x1693), [(0, 1, '스트라이'), (1, 1, '킹')]),
    ((0x1690, 0x1781), [(0, 1, '스트라이'), (1, 1, '킹')]),                # 마법 ストライキング (1690+1781 / 1692+1783)
    ((0x1692, 0x1783), [(0, 1, '스트라이'), (1, 1, '킹')]),
    ((0x16C5, 0x16C6), [(0, 1, 'D.비스트'), (1, 1, '의'), (1, 18, '눈')]),      # D비스트의 눈 — 앞 타일 16C5 공유
    ((0x16C5, 0x16C9), [(0, 1, 'D.비스트'), (1, 1, '의'), (1, 17, '가죽')]),    # D비스트의 가죽
]
def draw_composite(cv, tiles, items, font):
    """타일 목록을 가로로 이어 붙인 칸에 글을 놓고 다시 나눠 씀. → {타일: 16x16 배열}"""
    w = len(tiles) * 16
    col = None; strip = []
    for t in tiles:
        r = (t - LO) // 16; k = (t - LO) % 16
        strip.append(cv[r*16:(r+1)*16, k*16:(k+1)*16].copy())
    S = np.hstack(strip)
    c10 = (S == 10).sum(); c11 = (S == 11).sum(); col = 10 if c10 >= c11 else 11
    S[np.isin(S, [10, 11, 0, 9])] = 15
    ink = np.zeros((16, w), bool)
    for line, x, t in items:
        a = render_line(font, t)
        ink[line*8:line*8 + a.shape[0], x:x + a.shape[1]] |= a[:, :max(0, w - x)]
    shh = np.zeros_like(ink); shh[:, 1:] = ink[:, :-1]
    shh[:, 16::16] = False          # 타일 경계를 넘는 그림자는 빼서 공유 타일이 같은 그림이 되게
    sh = shh.copy(); sh[1:, :] |= ink[:-1, :]
    S[sh & ~ink] = 0; S[ink] = col
    return {t: S[:, i*16:(i+1)*16] for i, t in enumerate(tiles)}
def apply_composites(cv, font):
    done = {}
    for tiles, items in COMPOSITE:
        for t, a in draw_composite(cv, tiles, items, font).items():
            if t in done and not (done[t] == a).all(): print('⚠공유 타일 그림 다름 %X' % t)
            done[t] = a
    for t, a in done.items():
        r = (t - LO) // 16; k = (t - LO) % 16; cv[r*16:(r+1)*16, k*16:(k+1)*16] = a
    return sorted(done)
