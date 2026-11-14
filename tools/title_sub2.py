# -*- coding: utf-8 -*-
r"""sub_ID 한글 v2 (2026-11-14): 한글 = 하스피 흰 제목(my files/작업/solid_white_korean_title_only_1024x592.png, 옅은 물결 찌꺼기 alpha<80 지움)
  + D&D = 기울어진 컬러 로고에서 뽑은 실루엣(title_sub.mask) — 두 그림의 한글 부분을 ECC 닮음 변환으로 맞춰 D&D 를 같은 자리로 옮김.
  → 원본 sub 잉크 상자에 비율 유지로 맞춤 → work/title_export/sub_ko.png · preview_sub.png"""
import os, sys
import numpy as np, cv2
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.argv = sys.argv[:1] + ['60']; import title_sub as T
R = T.R
def main():
    w = np.array(Image.open(R('my files', '작업', 'solid_white_korean_title_only_1024x592.png')).convert('RGBA')).astype(np.float32)
    ko = np.clip((w[..., 3] - 150) / 70, 0, 1)                         # 번진 흔적(옅은 alpha) 지우고 가장자리만 부드럽게
    n, lab, st, _ = cv2.connectedComponentsWithStats((ko > 0).astype(np.uint8), 8)
    ko[np.isin(lab, [i for i in range(1, n) if st[i, 4] < 40])] = 0
    m = T.mask().astype(np.float32)                                   # 1774x887 컬러 로고 실루엣
    # 컬러 로고에서 한글 = 아래쪽(D&D 띠 아래). 띠 = 행마다 잉크 시작이 확 바뀌는 곳 → 대신 ECC 를 한글 그림 전체로
    s0 = (ko > 0).any(0).nonzero()[0]; s1 = (m > 0).any(0).nonzero()[0]
    sc = (s0.max() - s0.min()) / (s1.max() - s1.min())
    mm = cv2.resize(m, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    H, Wd = ko.shape
    big = np.zeros((max(H, mm.shape[0]) + 200, max(Wd, mm.shape[1]) + 200), np.float32)
    big[:mm.shape[0], :mm.shape[1]] = mm
    warp = np.array([[1, 0, s1.min() * sc - s0.min()], [0, 1, 0]], np.float32)
    # 세로 초기값: 아래쪽 끝 맞춤
    r0 = (ko > 0).any(1).nonzero()[0]; r1 = (mm > 0).any(1).nonzero()[0]; warp[1, 2] = r1.max() - r0.max()
    tgt = cv2.GaussianBlur(ko, (0, 0), 2); src = cv2.GaussianBlur(big, (0, 0), 2)
    _, warp = cv2.findTransformECC(tgt, src[:, :], warp, cv2.MOTION_AFFINE, (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 200, 1e-6), None, 5)
    al = cv2.warpAffine(big, warp, (Wd, H), flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP)
    # D&D = 맞춘 실루엣 중 한글 그림 둘레(팽창) 밖
    near = cv2.dilate((ko > 0).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    dd = np.where(near, 0, al)
    # 한글 띠 위쪽만(열마다 한글 첫 잉크 행보다 위) + 큰 덩어리만 = D&D
    top = np.where((ko > 0).any(0), (ko > 0).argmax(0), H); yy = np.arange(H)[:, None]
    dd[yy >= top[None, :] - 16] = 0
    n, lab, st, _ = cv2.connectedComponentsWithStats((dd > 0.3).astype(np.uint8), 8)
    small = np.isin(lab, [i for i in range(1, n) if st[i, 4] < 150]); dd[small] = 0
    full = np.maximum(ko, np.clip(dd, 0, 1))
    np.save(R('work', 'title_export', 'sub_full.npy'), full)
    ys, xs = np.nonzero(full > 0.3)
    print('warp', warp.round(3).tolist(), '상자', ys.min(), ys.max(), xs.min(), xs.max())
    # 원본 sub 상자에 맞춤
    o = np.array(Image.open(R('work', 'title_export', 'sub_ID.png')).convert('RGBA')); oy, ox = np.nonzero(o[..., 3] > 128)
    bx0, bx1, by0, by1 = ox.min(), ox.max(), oy.min(), oy.max()
    crop = full[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    s = min((bx1 - bx0) / crop.shape[1], (by1 - by0) / crop.shape[0]); cw, ch = int(crop.shape[1] * s), int(crop.shape[0] * s)
    sm = cv2.resize(crop, (cw, ch), interpolation=cv2.INTER_AREA)
    A = np.zeros((512, 1024), np.float32); x0 = (bx0 + bx1) // 2 - cw // 2; y0 = (by0 + by1) // 2 - ch // 2; A[y0:y0 + ch, x0:x0 + cw] = sm
    out = np.zeros((512, 1024, 4), np.uint8); out[..., :3] = 255; out[..., 3] = np.clip(A * 255 + .5, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(R('work', 'title_export', 'sub_ko.png'))
    bg = np.full((512, 1024, 3), (40, 40, 70), np.float32)
    comp = lambda a: (bg * (1 - a[..., 3:] / 255) + a[..., :3] * (a[..., 3:] / 255)).astype(np.uint8)
    Image.fromarray(np.vstack([comp(o), np.full((6, 1024, 3), 200, np.uint8), comp(out)])).save(R('work', 'title_export', 'preview_sub_v3.png'))
if __name__ == '__main__':
    main()
