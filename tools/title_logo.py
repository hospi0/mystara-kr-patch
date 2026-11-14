# -*- coding: utf-8 -*-
r"""타이틀 logo_ID(1024x592 DXT5) 한글 (2026-11-14 하스피).
  위(0~297행) = 하스피 컬러 로고 mistara_korean_logo_fixed_transparent_1024x592.png 그대로
  아래 그림자판 = 원본 영문(D&D) 그림자 화소 그대로(300~392행) + 하스피 한글 그림자(mistara_korean_shadow_only_gradient)를
    원본 규칙(위 글자 알파 흐림 σ4 · (+2,+292) 이동 · 검정 · 불투명 0.36, 원본 실측)으로 — 한글 위치 = 컬러 로고 한글 상자 + (2,292)
  → work/title_export/logo_ko.png · 미리보기 preview_logo.png"""
import os
import numpy as np, cv2
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = lambda *p: os.path.join(ROOT, *p)
A = lambda p: np.array(Image.open(p).convert('RGBA')).astype(np.float32)
def bbox(al, y0=0, y1=None):
    m = al[y0:y1] > 0.25; ys, xs = np.nonzero(m); return xs.min(), ys.min() + y0, xs.max(), ys.max() + y0
def main():
    o = A(R('work', 'title_export', 'logo_ID.png'))
    col = A(R('my files', '작업', 'mistara_korean_logo_fixed_transparent_1024x592.png'))
    shd = A(R('my files', '작업', 'mistara_korean_shadow_only_gradient_1024x592.png'))
    out = np.zeros_like(o)
    out[:298] = col[:298]                                            # 위 = 컬러 로고
    out[298:393] = o[298:393]                                        # 영문 그림자 = 원본
    ca = col[..., 3] / 255; kx0, ky0, kx1, ky1 = bbox(ca, 117, 298)  # 컬러 로고 한글 상자
    sa = shd[..., 3] / 255; sx0, sy0, sx1, sy1 = bbox(sa)
    s = (kx1 - kx0) / (sx1 - sx0)
    M = np.float32([[s, 0, kx0 + 2 - sx0 * s], [0, s, ky0 + 292 - sy0 * s]])
    w = cv2.warpAffine(sa, M, (1024, 592), flags=cv2.INTER_LINEAR)
    w = cv2.GaussianBlur(w, (0, 0), 4) * 0.36
    w[:393] = 0
    out[393:, :, :3] = 0; out[393:, :, 3] = np.clip(w[393:] * 255 + .5, 0, 255)
    out = np.clip(out, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(R('work', 'title_export', 'logo_ko.png'))
    bg = np.full((592, 1024, 3), (150, 150, 165), np.float32)       # 밝은 바탕(그림자 보이게)
    comp = lambda a: (bg * (1 - a[..., 3:] / 255.) + a[..., :3] * (a[..., 3:] / 255.)).astype(np.uint8)
    Image.fromarray(np.hstack([comp(o.astype(np.uint8)), np.full((592, 6, 3), 30, np.uint8), comp(out)])).save(R('work', 'title_export', 'preview_logo.png'))
    print('배율', round(s, 3), '한글 그림자 행', int(ky0 + 292), int(ky0 + 292 + (sy1 - sy0) * s))
if __name__ == '__main__':
    main()
