# -*- coding: utf-8 -*-
r"""글자 그림 텍스처(옵션·기록·챕터 제목 등) 항목 찾기·한글로 다시 그리기 (2026-11-14).
  detect: 알파 > 40 화소를 가로 10px·세로 2px 이어 붙여 덩어리 → 상자(번호 = 열·위아래 순)
  python tools/texlabel.py sheet 이름   → work/gui/sheet_이름.png (번호 붙은 항목판)"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import texio
R = lambda *p: os.path.join(ROOT, *p)
FONT = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'
def detect(a, gx=10, gy=2, thr=40):
    import cv2
    m = a[..., 3] > thr
    d = cv2.dilate(m.astype(np.uint8), np.ones((2 * gy + 1, 2 * gx + 1), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(d, connectivity=8); boxes = []
    for k in range(1, n):
        x0, y0, w, h = st[k, 0], st[k, 1], st[k, 2], st[k, 3]; x1, y1 = x0 + w, y0 + h
        sub = m[y0:y1, x0:x1] & (lab[y0:y1, x0:x1] == k)
        if not sub.any(): continue
        ys, xs = np.nonzero(sub)
        boxes.append([int(x0 + xs.min()), int(y0 + ys.min()), int(x0 + xs.max() + 1), int(y0 + ys.max() + 1)])
    W = a.shape[1]
    boxes.sort(key=lambda b: (b[0] >= W // 2, b[1], b[0]))
    return boxes
def sheet(name):
    a, i = texio.load(R('work', 'orig', 'options', name + '.tex'))
    bx = detect(a)
    json.dump(bx, open(R('work', 'gui', 'boxes_%s.json' % name), 'w'))
    bg = np.zeros_like(a); bg[...] = (60, 60, 90, 255); al = a[..., 3:4] / 255
    im = Image.fromarray((a[..., :3] * al + bg[..., :3] * (1 - al)).astype(np.uint8)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 14)
    for k, (x0, y0, x1, y1) in enumerate(bx):
        d.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(255, 80, 80)); d.text((x1 + 2, y0), str(k), (255, 255, 0), font=f)
    im.save(R('work', 'gui', 'sheet_%s.png' % name)); print(name, len(bx))
if __name__ == '__main__':
    if sys.argv[1] == 'sheet':
        for n in sys.argv[2:]: sheet(n)

PITCH = {'descripter0_LIN': 64, 'setting1_LIN': 32, 'record0_LIN': 32, 'chpt_title0_LIN': 32}
def detect_grid(a, pitch, gap=16, thr=40):
    m = a[..., 3] > thr; H, W = m.shape; out = []
    for r in range(H // pitch):
        band = m[r * pitch:(r + 1) * pitch]; cols = band.any(0)
        x = 0
        while x < W:
            if cols[x]:
                s = x; last = x
                while x < W and (cols[x] or x - last < gap):
                    if cols[x]: last = x
                    x += 1
                ys = np.nonzero(band[:, s:last + 1].any(1))[0]
                out.append([s, r * pitch + int(ys.min()), last + 1, r * pitch + int(ys.max()) + 1, r])
            else: x += 1
    out.sort(key=lambda b: (b[0] >= W // 2, b[4], b[0]))
    return out
def sheet2(name):
    a, i = texio.load(R('work', 'orig', 'options', name + '.tex'))
    bx = detect_grid(a, PITCH[name])
    json.dump(bx, open(R('work', 'gui', 'boxes_%s.json' % name), 'w'))
    bg = np.zeros_like(a); bg[...] = (60, 60, 90, 255); al = a[..., 3:4] / 255
    im = Image.fromarray((a[..., :3] * al + bg[..., :3] * (1 - al)).astype(np.uint8)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 13)
    for k, (x0, y0, x1, y1, r) in enumerate(bx):
        d.rectangle((x0, y0, x1 - 1, y1 - 1), outline=(255, 80, 80)); d.text((x1 + 2, y0), str(k), (255, 255, 0), font=f)
    im.save(R('work', 'gui', 'sheet_%s.png' % name)); print(name, len(bx))
if __name__ == '__main__' and sys.argv[1] == 'sheet2':
    for n in sys.argv[2:]: sheet2(n)

# ---------------- 한글로 다시 그리기 ----------------
import re
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？：；:;～~])[ 　]+')
STYLE = {'descripter0_LIN': 'white', 'setting1_LIN': 'white', 'record0_LIN': 'white', 'chpt_title0_LIN': 'brown'}
def col_limits(name, box, W):
    x0, y0, x1, y1, r = box[:5]
    if name == 'setting1_LIN':
        return (0, 255) if x0 < 256 else (256, 511)
    if name == 'descripter0_LIN': return (0, 780)
    if name == 'record0_LIN': return (0, 511) if x0 < 512 else (512, 1023)
    if name == 'chpt_title0_LIN':
        return (125, 508) if x0 < 512 else ((516, 1020) if x0 < 640 else (640, 1020))
    return (0, W - 1)
def align(name, box):
    x0 = box[0]
    if name == 'chpt_title0_LIN': return 'c'
    if name == 'setting1_LIN' and x0 >= 256 and not (box[0] < 300): return 'c'
    return 'l'
def kfont(px, w=700):
    f = ImageFont.truetype(FONT, px)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def text_mask(text, ink_h, maxw):
    """한 줄 글자 알파(0..255), 한글 잉크 높이 ≈ ink_h, 폭 넘치면 가로 압축"""
    px = 10
    while True:
        f = kfont(px); l, t, r, b = f.getbbox('한')
        if b - t >= ink_h or px > 80: break
        px += 1
    l, t, r, b = f.getbbox(text); ref_t = f.getbbox('한')[1]
    w = r - l + 2; h = ink_h + 8
    im = Image.new('L', (w, h), 0); ImageDraw.Draw(im).text((1 - l, 2 - ref_t), text, 255, font=f)
    a = np.array(im)
    if w > maxw: a = np.array(Image.fromarray(a).resize((maxw, h), Image.LANCZOS))
    return a
def styled(mask, style):
    """마스크 → RGBA(그림자·번짐 포함)"""
    H, W = mask.shape; pad = 6
    m = np.zeros((H + 2 * pad, W + 2 * pad), np.float32); m[pad:pad + H, pad:pad + W] = mask / 255.0
    import cv2
    out = np.zeros(m.shape + (4,), np.float32)
    if style == 'white':
        sh = np.roll(np.roll(m, 2, 0), 2, 1); sh = cv2.GaussianBlur(sh, (0, 0), 1.0); sh = np.clip(sh * 1.1, 0, 0.85)
        fill = np.array([224, 224, 224], np.float32); shc = np.array([28, 9, 9], np.float32)
        a = m + sh * (1 - m)
        rgb = (fill * m[..., None] + shc * (sh * (1 - m))[..., None]) / np.maximum(a, 1e-6)[..., None]
    else:
        gl = cv2.GaussianBlur(cv2.dilate(m, np.ones((3, 3), np.uint8)), (0, 0), 2.0); gl = np.clip(gl * 0.75, 0, 0.6)
        fill = np.array([82, 52, 16], np.float32); glc = np.array([164, 85, 0], np.float32)
        a = m + gl * (1 - m)
        rgb = (fill * m[..., None] + glc * (gl * (1 - m))[..., None]) / np.maximum(a, 1e-6)[..., None]
    out[..., :3] = rgb; out[..., 3] = a * 255
    return out, pad
def load_ko(name):
    out = {}
    for ln in open(R('work', 'gui', 'tex_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 4 and c[0] == name and c[3]: out[c[1]] = PUNCT_SP.sub(lambda m_: m_.group(1), c[3])
    return out
def build(name, out_path=None):
    src = R('work', 'orig', 'options', name + '.tex'); a, info = texio.load(src); a = a.copy()
    boxes = json.load(open(R('work', 'gui', 'boxes_%s.json' % name))); ko = load_ko(name)
    pitch = PITCH[name]; H, W = a.shape[:2]; style = STYLE[name]; log = []
    hs = []
    for key in ko:
        if '／' in ko[key]: continue
        for i_ in key.split('+'):
            x0_, y0_, x1_, y1_ = boxes[int(i_)][:4]; f_ = a[y0_:y1_, x0_:x1_, 3] > 200
            ys_ = np.nonzero(f_.any(1))[0]
            if len(ys_): hs.append(int(ys_.max() - ys_.min() + 1))
    hs.sort(); INK = int(hs[len(hs) // 2] * 0.95) if hs else int(pitch * 0.6)
    log.append('글자 높이 %d' % INK)
    for key, text in ko.items():
        ids = [int(k) for k in key.split('+')]
        bs = [boxes[i] for i in ids]
        x0 = min(b[0] for b in bs); y0 = min(b[1] for b in bs); x1 = max(b[2] for b in bs); y1 = max(b[3] for b in bs); r = bs[0][4]
        lines = text.split('／')
        band0, band1 = r * pitch, (r + 1) * pitch
        # 지우기: 상자 + 3px (줄 띠 안)
        sub_ = ids[0] >= 200                           # 아이콘 사이 글자 조각(흰 글꼴, 좁게 지움)
        ex = 1 if sub_ else 3
        a[max(band0, y0 - 3):min(band1, y1 + 3), max(0, x0 - ex):min(W, x1 + ex + 1)] = 0
        lo, hi = col_limits(name, bs[0], W)
        n = len(lines); lh = (y1 - y0) // n if n > 1 else (y1 - y0)
        ink = INK
        for li, ln in enumerate(lines):
            al = align(name, bs[0])
            sub_ = ids[0] >= 200
            maxw = (hi - x0) if al == 'l' else 2 * min((x0 + x1) // 2 - lo, hi - (x0 + x1) // 2)
            if sub_: al = 'l'; maxw = (x1 - x0) + (40 if ids[0] in (202,) else 0)
            maxw = max(maxw, 30); m = text_mask(ln, int(ink * 0.85) if sub_ else ink, maxw); rgba, pad = styled(m, 'white' if sub_ else style)
            mh, mw = m.shape
            if al == 'l': tx = x0
            else: tx = (x0 + x1) // 2 - mw // 2
            ty = (y0 + li * lh) if n > 1 else (band0 + (pitch - (ink + 3)) // 2 - 1) - 1
            if mw >= maxw: log.append('압축 %s %s' % (key, ln))
            X0, Y0 = tx - pad, ty - pad; h_, w_ = rgba.shape[:2]
            ys0, xs0 = max(0, -Y0), max(0, -X0); ye, xe = min(h_, H - Y0), min(w_, W - X0)
            dst = a[Y0 + ys0:Y0 + ye, X0 + xs0:X0 + xe].astype(np.float32); s = rgba[ys0:ye, xs0:xe]
            sa = s[..., 3:4] / 255; da = dst[..., 3:4] / 255; oa = sa + da * (1 - sa)
            orgb = (s[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
            a[Y0 + ys0:Y0 + ye, X0 + xs0:X0 + xe] = np.concatenate([orgb, oa * 255], -1).clip(0, 255).astype(np.uint8)
    if out_path: texio.save(src, out_path, a)
    bg = np.zeros_like(a); bg[...] = (60, 60, 90, 255); o0, _ = texio.load(src)
    def comp(x):
        al_ = x[..., 3:4] / 255; return (x[..., :3] * al_ + bg[..., :3] * (1 - al_)).astype(np.uint8)
    Image.fromarray(np.hstack([comp(o0), np.full((H, 6, 3), 200, np.uint8), comp(a)])).save(R('work', 'gui', 'preview_%s.png' % name))
    return log
if __name__ == '__main__' and sys.argv[1] == 'build':
    for n in sys.argv[2:]:
        os.makedirs(R('work', 'build', 'options'), exist_ok=True)
        print(n, build(n, R('work', 'build', 'options', n + '.tex')))
