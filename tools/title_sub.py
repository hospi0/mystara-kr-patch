# -*- coding: utf-8 -*-
r"""타이틀 sub_ID(1024x512 DXT5, 기울어진 흰 실루엣) 한글 (2026-11-14 하스피 기울어진 로고).
  입력 my files/작업/a_clean_transparent_background_graphic_logo_image.png = RGB(바둑판 무늬 박힘)
  로고 화소 = 채도 높음 or 어두움 → 구멍 메움·작은 찌꺼기 제거 → 원본 sub 잉크 상자에 비율 유지로 맞춤, 가장자리 원본처럼 살짝 부드럽게.
  → work/title_export/sub_ko.png · 미리보기 work/title_export/preview_sub.png"""
import os, sys
import numpy as np, cv2
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); R = lambda *p: os.path.join(ROOT, *p)
SRC = R('my files', '작업', 'a_clean_transparent_background_graphic_logo_image.png')
HOLE = int(sys.argv[1]) if len(sys.argv) > 1 else 900
def mask():
    a = np.array(Image.open(SRC).convert('RGB')).astype(np.int32)
    mx, mn = a.max(-1), a.min(-1); sat = mx - mn
    bg = ((sat < 36) & (mn >= 110)).astype(np.uint8)
    bg = cv2.morphologyEx(bg, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8)).astype(bool)   # 바둑판 칸 사이 틈 잇기(ㅇ 속이 조각나 메워지지 않게)                         # 바둑판 무늬 = 무채색 회색 두 값(≈150·205)
    m = (~bg).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.zeros_like(m)
    for i in range(1, n):
        if st[i, 4] >= 150: keep[lab == i] = 1
    inv = (1 - keep).astype(np.uint8)                                  # 글자 안 밝은 반사·회색 결 = 작은 구멍 → 메움(ㅇ·O 속 같은 큰 구멍은 둠)
    n, lab, st, _ = cv2.connectedComponentsWithStats(inv, 4)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < HOLE and x > 0 and y > 0 and x + w < inv.shape[1] and y + h < inv.shape[0]: keep[lab == i] = 1
    return keep
def main():
    m = mask(); ys, xs = np.nonzero(m); m = m[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    o = np.array(Image.open(R('work', 'title_export', 'sub_ID.png')).convert('RGBA')); oa = o[..., 3]
    oy, ox = np.nonzero(oa > 128); bx0, bx1, by0, by1 = ox.min(), ox.max(), oy.min(), oy.max()
    s = min((bx1 - bx0) / m.shape[1], (by1 - by0) / m.shape[0])
    w, h = int(m.shape[1] * s), int(m.shape[0] * s)
    sm = cv2.resize(m.astype(np.float32), (w, h), interpolation=cv2.INTER_AREA)
    glow = cv2.GaussianBlur(cv2.dilate(sm, np.ones((3, 3), np.uint8)), (0, 0), 1.6) * 0.45   # 원본처럼 둘레 흐린 빛
    sm = np.maximum(cv2.GaussianBlur(sm, (3, 3), 0.8), glow)
    al = np.zeros((512, 1024), np.float32)
    x0 = (bx0 + bx1) // 2 - w // 2; y0 = (by0 + by1) // 2 - h // 2
    al[y0:y0 + h, x0:x0 + w] = sm
    out = np.zeros((512, 1024, 4), np.uint8); out[..., :3] = 255; out[..., 3] = np.clip(al * 255 + .5, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(R('work', 'title_export', 'sub_ko.png'))
    bg = np.full((512, 1024, 3), (40, 40, 70), np.float32)
    comp = lambda a: (bg * (1 - a[..., 3:] / 255) + a[..., :3] * (a[..., 3:] / 255)).astype(np.uint8)
    Image.fromarray(np.vstack([comp(o), np.full((6, 1024, 3), 200, np.uint8), comp(out)])).save(R('work', 'title_export', 'preview_sub.png'))
    print('원본 상자', (bx0, by0, bx1, by1), '새', (x0, y0, x0 + w, y0 + h))
if __name__ == '__main__':
    main()
