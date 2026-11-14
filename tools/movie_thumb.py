# -*- coding: utf-8 -*-
r"""무비 갤러리 썸네일 movie/00~02_ID_THUM.tex(256², 밉 RGBA8 스위즐) 글자 한글 (2026-11-14).
  · 말풍선 «開発秘話!» : 말풍선 판 색(줄마다 글자 아닌 화소 중앙값)으로 글자 메움 → «개발 비화!»
  · 두루마리 제목 : 양피지 = 글자 화소 inpaint → 한글(원래 글자 색)
  python tools/movie_thumb.py → work/build/movie/*.tex · work/gui/preview_thumb.png(원본|한글)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import texio
R = lambda *p: os.path.join(ROOT, *p)
FONT = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'
BALS = [(63, 72, 148, 94), (63, 72, 146, 94), (71, 72, 156, 94)]   # 말풍선 글자 상자(실측)
SCRS = [(54, 199, 184, 225), (57, 199, 193, 225), (70, 199, 181, 225)]   # 두루마리 글자 상자(실측)
TITLES = ['게임 내용 편', '캐릭터 편', '명(망)언집']
def font(px, w=800):
    f = ImageFont.truetype(FONT, px)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def draw_text(a, box, text, color, ink_h, outline=None):
    x0, y0, x1, y1 = box
    px = 8
    while True:
        f = font(px); l, t, r, b = f.getbbox('한')
        if b - t >= ink_h: break
        px += 1
    l, t, r, b = f.getbbox(text); w = r - l
    if w > x1 - x0: f = font(int(px * (x1 - x0) / w)); l, t, r, b = f.getbbox(text); w = r - l
    im = Image.new('L', (a.shape[1], a.shape[0]), 0); d = ImageDraw.Draw(im)
    ref = f.getbbox('한')
    d.text(((x0 + x1) // 2 - w // 2 - l, (y0 + y1) // 2 - (ref[1] + ref[3]) // 2), text, 255, font=f)
    m = np.array(im).astype(np.float32) / 255
    if outline is not None:
        import cv2
        o = cv2.GaussianBlur(cv2.dilate(m, np.ones((3, 3), np.uint8)), (0, 0), 0.7)
        o = np.clip(o * 1.2, 0, 1) * (1 - m)
        a[..., :3] = (a[..., :3] * (1 - o[..., None]) + np.array(outline) * o[..., None])
    a[..., :3] = (a[..., :3] * (1 - m[..., None]) + np.array(color) * m[..., None])
    return a
def main():
    import cv2
    os.makedirs(R('work', 'build', 'movie'), exist_ok=True); prev = []
    for k in range(3):
        src = R('work', 'orig', 'movie', '%02d_ID_THUM.tex' % k)
        a0, info = texio.load(src); a = a0.astype(np.float32).copy()
        # 말풍선: 판 색 = 범위 안 가운데 밝기, 글자 = 판보다 훨씬 밝은 화소
        X0, Y0, X1, Y1 = BALS[k]; sub = a[Y0:Y1, X0:X1, :3]; lum = sub.mean(-1)
        txt0 = lum > np.percentile(lum, 20) + 50          # 말풍선 판(어두움)보다 훨씬 밝은 화소 = 글자
        bx = (X0, Y0, X1, Y1); hb = 18
        txt = cv2.dilate(txt0.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        bal_col = np.median(sub[~txt], 0); tcol = np.median(sub[txt0], 0) if txt0.any() else np.array([240., 220., 160.])
        for yy in range(sub.shape[0]):
            row = sub[yy]; ok = ~txt[yy]
            seg = row[max(0, bx[0] - X0 - 6):bx[2] - X0 + 6]; okseg = ok[max(0, bx[0] - X0 - 6):bx[2] - X0 + 6]
            c = np.median(seg[okseg], 0) if okseg.sum() > 3 else bal_col
            row[txt[yy]] = c
        a[Y0:Y1, X0:X1, :3] = sub
        a = draw_text(a, bx, '개발 비화!', tcol, 16)
        # 두루마리
        X0, Y0, X1, Y1 = SCRS[k]; sub = a[Y0:Y1, X0:X1, :3]; lum = sub.mean(-1)
        txt0 = lum < np.percentile(lum, 80) - 40          # 양피지(밝음)보다 훨씬 어두운 화소 = 글자
        bx = (X0, Y0, X1, Y1); hs = 19
        txt = cv2.dilate(txt0.astype(np.uint8), np.ones((3, 3), np.uint8))
        tcol2 = np.median(sub[lum <= np.percentile(lum, 4)], 0)
        rgb = np.clip(a[..., :3], 0, 255).astype(np.uint8).copy()
        mask = np.zeros(rgb.shape[:2], np.uint8); mask[Y0:Y1, X0:X1] = txt
        rgb = cv2.inpaint(rgb, mask, 7, cv2.INPAINT_TELEA); a[..., :3] = rgb
        a = draw_text(a, bx, TITLES[k], tcol2, 19)
        out = np.clip(a + 0.5, 0, 255).astype(np.uint8); out[..., 3] = a0[..., 3]
        texio.save(src, R('work', 'build', 'movie', '%02d_ID_THUM.tex' % k), out)
        bg = np.full((256, 256, 3), (60, 60, 90), np.float32)
        comp = lambda x: (x[..., :3] * (x[..., 3:4] / 255) + bg * (1 - x[..., 3:4] / 255)).astype(np.uint8)
        prev.append(np.vstack([comp(a0), np.full((4, 256, 3), 200, np.uint8), comp(out)]))
    p = np.hstack(sum([[x, np.full((x.shape[0], 6, 3), 30, np.uint8)] for x in prev], []))
    Image.fromarray(p).resize((p.shape[1] * 2, p.shape[0] * 2), Image.NEAREST).save(R('work', 'gui', 'preview_thumb.png'))
if __name__ == '__main__':
    main()
