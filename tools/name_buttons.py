# -*- coding: utf-8 -*-
r"""이름 입력 버튼 4개(dd21x 8x8 타일, 5x2칸 = 40x16) 한글 새기기 (2026-11-13).
  원본 꼴: 획 = 어두운 선(1, 끝 0) + 아래·오른쪽 1px 밝은 선(E→A 왼쪽에서 오른쪽으로). 바탕 = 돌판(4~8).
  빈 판 = 버튼 4개 화소 최빈값(글자 아닌 칸) 하나를 공유. 글꼴 = 갈무리9(+가로 1px 굵게).
  python tools/name_buttons.py [dd21x 입력] [출력] → 미리보기 work/ring/preview/name_buttons.png"""
import os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, r'C:\claude\project\anearth-kr-patch\tools')
from bdf import Font
BTN = {'space': (0x2B3D, 0x2B45, '공백'), 'name': (0x2B57, 0x2B62, '이름'),
       'back': (0x2B6E, 0x2B76, '지움'), 'end': (0x2B85, 0x2B8E, '완료')}
SCREEN = {0: '112233', 1: '223344', 2: '334455', 3: '445566', 4: '778899', 5: '99aabb', 6: 'bbccdd', 7: 'ccddee',
          8: 'ddeeff', 9: '555555', 10: '666666', 11: '888888', 12: '999999', 13: 'aaaaaa', 14: 'cccccc', 15: '506080'}
TEXT = {0, 1, 2, 9, 10, 11, 12, 13, 14}          # 글자 획·밝은 선에 쓰인 번호(돌판 4~8 과 겹치지 않는 것)
def tiles(b):
    p = np.empty(len(b) * 2, np.uint8); a = np.frombuffer(b, np.uint8); p[0::2] = a & 15; p[1::2] = a >> 4
    return p.reshape(-1, 16, 8)
def get(T, t0, t1):
    return np.vstack([np.hstack([T[t0 + i, :8] for i in range(5)]), np.hstack([T[t1 + i, :8] for i in range(5)])])
def put(b, t0, t1, img):
    for r, tb in enumerate((t0, t1)):
        for i in range(5):
            blk = img[r * 8:(r + 1) * 8, i * 8:(i + 1) * 8]
            o = (tb + i) * 64
            nib = blk.reshape(-1)
            b[o:o + 32] = bytes((nib[0::2] & 15) | ((nib[1::2] & 15) << 4))
def plate(imgs):
    st = np.stack(imgs)                     # 4×16×40
    out = np.empty(st.shape[1:], np.uint8)
    for y in range(16):
        for x in range(40):
            v = [int(a) for a in st[:, y, x] if a not in TEXT or y in (0, 1, 13, 14, 15) or x < 3 or x > 35]
            v = v or [int(a) for a in st[:, y, x]]
            out[y, x] = max(set(v), key=v.count)
    # 안쪽(2~12행, 3~35열): 화소마다 네 버튼 중 그 자리가 돌판 색(4~8)인 값의 최빈값 → 돌 질감 유지, 글자 흔적 없음
    for y in range(2, 13):
        for x in range(3, 36):
            v = [int(a) for a in st[:, y, x] if 5 <= a <= 8]
            out[y, x] = max(set(v), key=v.count) if v else 255
    for y in range(2, 13):
        for x in range(3, 36):
            if out[y, x] == 255:
                nb = [int(out[yy, xx]) for yy in range(y - 1, y + 2) for xx in range(x - 2, x + 3) if out[yy, xx] != 255 and 5 <= out[yy, xx] <= 8]
                out[y, x] = max(set(nb), key=nb.count) if nb else 6
    # 왼쪽 가장자리 안쪽(1~2열, 2~12행): 네 버튼 가나 획 끝(0·2)이 최빈값으로 남아 찌꺼기 → 돌판·테두리 색(3~8)만(2026-11-14 하스피 «전부 왼쪽에 찌꺼기»)
    for y in range(2, 13):
        for x in (1, 2):
            if out[y, x] < 3 or out[y, x] > 8:
                v = [int(a) for a in st[:, y, x] if 3 <= a <= 8] + [int(out[yy, x]) for yy in (y - 1, y + 1) if 3 <= out[yy, x] <= 8]
                out[y, x] = max(set(v), key=v.count) if v else 6
    # 왼쪽 안쪽 옅은 세로줄(1~3열)도 지움 — 같은 행 안쪽(8~10열) 돌 질감을 그대로 옮김(2026-11-14 하스피 «왼쪽도 지워»)
    for y in range(2, 13):
        out[y, 1:4] = out[y, 8:11]
    return out
def carve(base, text, font):
    pts, w = font.draw(text)
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    W = max(xs) - min(xs) + 1; H = max(ys) - min(ys) + 1
    m = np.zeros((16, 40), bool)
    ox = (40 - W) // 2 - 1; oy = 3 + (10 - H) // 2
    for x, y in pts:
        X = x - min(xs) + ox; Y = y - min(ys) + oy
        m[Y, X] = True
    img = base.copy()
    # v4(하스피 선택): 획 = 어두운 선(1, 끝 0) + 아래·오른쪽 1px 밝은 선(E→A 왼쪽에서 오른쪽)
    hl = np.zeros_like(m); hl[1:, 1:] = m[:-1, :-1]; hl &= ~m
    xs_m = np.nonzero(m.any(0))[0]; x0, x1 = xs_m.min(), xs_m.max()
    grad = [14, 13, 12, 11, 10]
    for y, x in zip(*np.nonzero(hl)):
        img[y, x] = grad[min(4, int((x - x0) * 5 / max(1, x1 - x0 + 1)))]
    img[m] = 1
    end = m.copy(); end[:, :-1] &= ~m[:, 1:]; end[:-1, :] &= ~m[1:, :]
    img[end & m] = 0
    return img
def main():
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'work', 'orig', 'game_data', 'dd21x.bin')
    dst = sys.argv[2] if len(sys.argv) > 2 else None
    b = bytearray(open(src, 'rb').read()); T = tiles(bytes(b))
    orig = {k: get(T, t0, t1) for k, (t0, t1, _) in BTN.items()}
    pl = plate(list(orig.values()))
    font = Font(r'C:\claude\utils\font\Galmuri-v2.40.3\Galmuri9.bdf')
    new = {k: carve(pl, BTN[k][2], font) for k in BTN}
    if dst:
        for k, (t0, t1, _) in BTN.items(): put(b, t0, t1, new[k])
        open(dst, 'wb').write(b)
    from PIL import Image
    pal = np.array([[int(SCREEN[i][j:j + 2], 16) for j in (0, 2, 4)] for i in range(16)], np.uint8)
    rows = [np.hstack([pal[orig[k]], np.full((16, 4, 3), 20, np.uint8), pal[pl], np.full((16, 4, 3), 20, np.uint8), pal[new[k]]]) for k in BTN]
    a = np.vstack([np.vstack([r, np.full((4, r.shape[1], 3), 20, np.uint8)]) for r in rows])
    # 화면 비율(가로 2·세로 2.57)로 키움
    Image.fromarray(a).resize((a.shape[1] * 8, int(a.shape[0] * 8 * 1.285)), 0).save(os.path.join(ROOT, 'work', 'ring', 'preview', 'name_buttons_build.png'))
if __name__ == '__main__':
    main()
