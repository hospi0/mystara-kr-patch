# -*- coding: utf-8 -*-
r"""무비(interview 00~02) 한글 자막 입히기 (2026-11-14).
  · 음성 자막 work/movie/NN_ko.tsv(시작·끝·한국어) → 아래쪽, Noto Sans KR 굵게 + 검은 테두리
  · 제목 카드 work/movie/cards.json(구간) + cards_ko.tsv → 카드 가운데 프레임의 글자를 inpaint 로 지운 판 + 한글 제목,
    카드 앞뒤 페이드는 프레임 밝기 비율로 맞춰 덮음
  · 프레임 처리: ffmpeg(원본 PS 디코드) → rawvideo → 파이썬 → ffmpeg(libx264, B 없음, AUD, Main 3.1) → .h264
  python tools/movie_sub.py NN [preview초…]   (preview 가 있으면 그 시각 프레임만 PNG 로)"""
import os, sys, json, re, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = lambda *p: os.path.join(ROOT, 'work', 'movie', *p)
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
SRC = os.path.join(ROOT, 'work', 'orig_install', 'nativePS3', 'movie', 'interview')   # ★원본 보관본 — 게임 폴더는 자막 입힌 설치본이라 거기서 읽으면 자막이 겹침(2026-11-14)
FONT = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'
FPS = 30000 / 1001; Wd, Ht = 720, 400
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？：；:;～~])[ 　]+')
def font(px, w=700):
    f = ImageFont.truetype(FONT, px)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def wrap(text, f, maxw):
    """띄어쓰기 단위로 줄 나눔"""
    out = []
    for para in text.split('／'):
        cur = ''
        for wd in para.split(' '):
            t = (cur + ' ' + wd).strip()
            if f.getlength(t) <= maxw or not cur: cur = t
            else: out.append(cur); cur = wd
        out.append(cur)
    return out
def text_layer(lines, f, cy, stroke=3, fill=(255, 255, 255), bottom=False):
    im = Image.new('RGBA', (Wd, Ht), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    lh = int(f.size * 1.32); total = lh * len(lines)
    y = (cy - total) if bottom else (cy - total // 2)
    for ln in lines:
        w = f.getlength(ln)
        d.text(((Wd - w) / 2, y), ln, font=f, fill=fill + (255,), stroke_width=stroke, stroke_fill=(0, 0, 0, 255))
        y += lh
    return np.array(im).astype(np.float32) / 255
def load_subs(n, raw=False):
    out = []
    for ln in open(W(n + '_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 3 and c[2]: out.append((float(c[0]), float(c[1]), PUNCT_SP.sub(lambda m: m.group(1), c[2])))
    if raw: return out
    import movie_retime
    return movie_retime.retime(n, out)                       # 시작 = 실제 첫 단어(2026-11-14)
def load_cards(n):
    segs = json.load(open(W('cards.json')))[n]; ko = {}
    for ln in open(W('cards_ko.tsv'), encoding='utf-8').read().split('\n')[1:]:
        c = ln.split('\t')
        if len(c) >= 4 and c[0] == n: ko[int(c[1])] = PUNCT_SP.sub(lambda m: m.group(1), c[3])
    return [(a, b, ko[i]) for i, (a, b) in enumerate(segs)]
def card_patch(frame, text):
    """카드 프레임 → (덮을 판 RGB, 덮을 영역 마스크) — 글자(흰 획 + 검은 그림자) inpaint + 한글"""
    import cv2
    band = np.zeros((Ht, Wd), bool); band[150:265] = True
    g = frame.astype(np.int32); lum = g.mean(-1)
    txt = (g.min(-1) > 150) & band
    txt = cv2.dilate(txt.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    clean = cv2.inpaint(frame, txt.astype(np.uint8), 9, cv2.INPAINT_TELEA)
    lines = text.split('／'); f1 = font(26, 800); f2 = font(17, 700)
    layer = np.zeros((Ht, Wd, 4), np.float32)
    ys, xs = np.nonzero(txt)
    cy = int((ys.min() + ys.max()) / 2) if len(ys) else 205
    big = text_layer([lines[0]], f1, cy if len(lines) == 1 else cy - 10, stroke=3)
    layer = big
    if len(lines) > 1:
        small = text_layer([lines[1]], f2, cy + 20, stroke=2)
        layer = np.maximum(layer, small)
    a = layer[..., 3:4]; out = clean.astype(np.float32) * (1 - a) + layer[..., :3] * 255 * a
    return out, txt | (a[..., 0] > 0)
def run(n, previews=None):
    subs = load_subs(n); cards = load_cards(n)
    src = os.path.join(SRC, n + '.pam')
    # 카드 판(가운데 프레임)
    patches = []
    for a, b, text in cards:
        t = (a + b) / 2
        fr = subprocess.run([FF, '-hide_banner', '-loglevel', 'quiet', '-skip_initial_bytes', '2048', '-f', 'mpeg', '-ss', str(t), '-i', src,
                             '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
        frame = np.frombuffer(fr, np.uint8).reshape(Ht, Wd, 3).copy()
        p, m = card_patch(frame, text)
        ref = frame[m].astype(np.float32).mean()
        patches.append((a - 0.8, b + 0.8, p, m, ref, frame))
    fsub = font(22, 700); cache = {}
    def process(img, t):
        out = img.astype(np.float32)
        for a, b, p, m, ref, rf in patches:
            if a <= t <= b:
                cur = img[m].astype(np.float32).mean(); k = min(1.0, cur / max(ref, 1))
                out[m] = p[m] * k
        for s, e, text in subs:
            if s <= t < e:
                if text not in cache: cache[text] = text_layer(wrap(text, fsub, 660), fsub, 388, stroke=3, bottom=True)
                L = cache[text]; al = L[..., 3:4]
                out = out * (1 - al) + L[..., :3] * 255 * al
                break
        return np.clip(out + 0.5, 0, 255).astype(np.uint8)
    if previews:
        for t in previews:
            fr = subprocess.run([FF, '-hide_banner', '-loglevel', 'quiet', '-skip_initial_bytes', '2048', '-f', 'mpeg', '-ss', str(t), '-i', src,
                                 '-frames:v', '1', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
            img = np.frombuffer(fr, np.uint8).reshape(Ht, Wd, 3)
            Image.fromarray(np.vstack([img, process(img, t)])).save(W('prev_%s_%06.1f.png' % (n, t)))
        return
    dec = subprocess.Popen([FF, '-hide_banner', '-loglevel', 'error', '-skip_initial_bytes', '2048', '-f', 'mpeg', '-i', src,
                            '-fps_mode', 'passthrough', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    enc = subprocess.Popen([FF, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (Wd, Ht),
                            '-r', '30000/1001', '-i', '-', '-c:v', 'libx264', '-profile:v', 'main', '-level', '3.1', '-pix_fmt', 'yuv420p',
                            '-bf', '0', '-g', '15', '-keyint_min', '15', '-sc_threshold', '0', '-b:v', '5000k', '-maxrate', '7500k',
                            '-bufsize', '3000k', '-x264-params', 'aud=1:repeat-headers=1', '-color_primaries', 'bt709', '-color_trc', 'bt709',
                            '-colorspace', 'bt709', '-f', 'h264', W(n + '_sub.h264')], stdin=subprocess.PIPE)
    k = 0; sz = Wd * Ht * 3
    while True:
        buf = dec.stdout.read(sz)
        if len(buf) < sz: break
        img = np.frombuffer(buf, np.uint8).reshape(Ht, Wd, 3)
        enc.stdin.write(process(img, k / FPS).tobytes()); k += 1
        if k % 3000 == 0: print(n, k, flush=True)
    enc.stdin.close(); enc.wait(); dec.wait()
    print('프레임', k)
if __name__ == '__main__':
    n = sys.argv[1]
    run(n, [float(x) for x in sys.argv[2:]] or None)
