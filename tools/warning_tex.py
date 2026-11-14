# -*- coding: utf-8 -*-
r"""경고 화면 game_data/warning_jp.tex(640x448 RGBA8, ARGB 순) 한글 (2026-11-14).
  검은 바탕 + 흰 글자 → 원본 줄 위치(잉크 줄 가운데)에 Noto Sans KR 로 가운데 정렬. 줄 수 = 원본과 같게(빈 줄 포함).
  python tools/warning_tex.py → work/build/game_data/warning_jp.tex · 미리보기 work/gui/preview_warning.png(원본|한글)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import mttex
R = lambda *p: os.path.join(ROOT, *p)
FONT = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'
LINES = ['주의!',
         '이 소프트웨어를 사용할 때는 방을 밝게 하고,',
         '화면에서 충분히 떨어져 눈에 부담이 가지 않게 해 주세요.',
         '또 건강을 위해 1시간마다 10~20분씩 쉬고,',
         '피곤할 때나 잠이 부족할 때는 사용을 삼가 주세요.',
         '드물게 강한 빛의 자극이나 깜빡임, TV 화면을 보다가',
         '일시적인 근육 경련·의식 상실 등을 일으키는 사람이 있습니다.',
         '이런 경험이 있는 분은',
         '이 소프트웨어를 사용하기 전에 반드시 의사와 상담해 주세요.',
         '또 사용 중에 이런 증상이 나타나면',
         '바로 사용을 멈추고 의사의 진찰을 받아 주세요.']
import re
PUNCT_SP = re.compile(r'([,.!?…、。，．！？：；:;～~])[ 　]+')
LINES = [PUNCT_SP.sub(lambda m: m.group(1), t) for t in LINES]
def line_centers(a):
    ink = (a[..., :3].max(-1) > 80).any(1); ys = []; y = 0
    while y < len(ink):
        if ink[y]:
            s = y
            while y < len(ink) and ink[y]: y += 1
            ys.append(((s + y) // 2, y - s))
        else: y += 1
    return ys
def font(size, w=500):
    f = ImageFont.truetype(FONT, size)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def main():
    src = R('work', 'orig', 'game_data', 'warning_jp.tex')
    d = bytearray(open(src, 'rb').read()); im, info = mttex.load(src); a = np.array(im)
    cs = line_centers(a); assert len(cs) == len(LINES), (len(cs), [c for c in cs])
    size = 22
    while max(font(size).getlength(t) for t in LINES) > 616: size -= 1
    f = font(size); fb = font(size + 2, 700)
    out = Image.new('RGB', (640, 448), (0, 0, 0)); dr = ImageDraw.Draw(out)
    for (cy, h), t in zip(cs, LINES):
        ff = fb if t == '주의!' else f
        l, tp, r, b = ff.getbbox(t); w = r - l
        dr.text(((640 - w) // 2 - l, cy - (tp + b) // 2), t, (255, 255, 255), font=ff)
    o = np.array(out); argb = np.concatenate([np.full((448, 640, 1), 255, np.uint8), o], -1)
    d[info['off']:info['off'] + 640 * 448 * 4] = argb.tobytes()
    od = R('work', 'build', 'game_data'); os.makedirs(od, exist_ok=True)
    open(os.path.join(od, 'warning_jp.tex'), 'wb').write(d)
    Image.fromarray(np.hstack([a[..., :3], np.full((448, 6, 3), 90, np.uint8), o])).save(R('work', 'gui', 'preview_warning.png'))
    print('글자 크기', size)
if __name__ == '__main__':
    main()
