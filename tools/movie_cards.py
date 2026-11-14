# -*- coding: utf-8 -*-
r"""무비 제목 카드(돌 무늬 + 흰 글자) 구간 찾기·글자 띠 모으기 (2026-11-14).
  2fps 축소 프레임(work/movie/tNN)의 위아래 띠가 기준 카드와 같으면 카드. → work/movie/cards.json · cards_NN.png"""
import os, json, subprocess
import numpy as np
from PIL import Image
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = lambda *p: os.path.join(ROOT, 'work', 'movie', *p)
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
SRC = r'D:\hospi\rpcs3\games\Dungeons & Dragons - Mystara Eiyuu Senki (Japan)\PS3_GAME\USRDIR\nativePS3\movie\interview'
def detect():
    ref = np.array(Image.open(W('t00', '%05d.png' % 391)).convert('RGB')).astype(int)
    bg = lambda a: np.vstack([a[5:35], a[65:95]]); Rb = bg(ref); out = {}
    for f in ('00', '01', '02'):
        fs = sorted(os.listdir(W('t' + f))); segs = []; cur = None
        for i, fn in enumerate(fs):
            a = np.array(Image.open(W('t' + f, fn)).convert('RGB')).astype(int); t = i / 2
            if np.abs(bg(a) - Rb).mean() < 12:
                if cur is None: cur = [t, t]
                else: cur[1] = t
            elif cur: segs.append(cur); cur = None
        if cur: segs.append(cur)
        out[f] = segs
    json.dump(out, open(W('cards.json'), 'w')); return out
def sheet(cards):
    for f, segs in cards.items():
        crops = []
        for a, b in segs:
            t = (a + b) / 2; p = W('card_%s_%05.1f.png' % (f, t))
            subprocess.run([FF, '-hide_banner', '-loglevel', 'quiet', '-y', '-skip_initial_bytes', '2048', '-f', 'mpeg', '-ss', str(t), '-i', os.path.join(SRC, f + '.pam'), '-frames:v', '1', p])
            crops.append(np.array(Image.open(p).convert('RGB'))[170:235])
        img = np.vstack([np.vstack([c, np.full((4, 720, 3), 255, np.uint8)]) for c in crops])
        Image.fromarray(img).save(W('cards_%s.png' % f))
if __name__ == '__main__':
    sheet(detect())
