# -*- coding: utf-8 -*-
r"""저작권 경고 game_texture/copy_announce_NOMIP.tex(1280x720 RGBA8 선형) 한글 (2026-11-14).
  검은 바탕 → 「주의」 + 본문 5줄을 원본 줄 위치(본문 잉크 줄 가운데)에 Noto Sans KR. 후리가나는 없앰.
  python tools/copy_announce.py → work/build/game_texture/copy_announce_NOMIP.tex · work/gui/preview_copy.png"""
import os, sys, re
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import texio
R = lambda *p: os.path.join(ROOT, *p)
FONT = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'
PUNCT_SP = re.compile(r'([,.!?…、。，．！？：；:;～~])[ 　]+')
TITLE = '주의'
BODY = ['게임 소프트웨어를 권리자의 허락 없이 인터넷을',
        '통해 배포·전송하는 행위, 또 불법 인터넷',
        '배포인 줄 알면서 내려받는 행위는',
        '일본 법률로 엄격히 금지되어 있습니다.',
        '여러분의 이해와 협조를 부탁드립니다.']
YS = [278, 346, 413, 480, 547]; YT = 152
def font(px, w):
    f = ImageFont.truetype(FONT, px)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def main():
    src = R('work', 'orig', 'game_texture', 'copy_announce_NOMIP.tex'); a0, info = texio.load(src)
    col = tuple(int(x) for x in np.percentile(a0[..., :3][a0[..., :3].max(-1) > 150], 50, axis=0))
    im = Image.new('RGB', (1280, 720), (0, 0, 0)); d = ImageDraw.Draw(im)
    ft = font(60, 800); fb = font(34, 500)
    for txt, y, f in [(TITLE, YT, ft)] + [(PUNCT_SP.sub(lambda m: m.group(1), t), y, fb) for t, y in zip(BODY, YS)]:
        l, t, r, b = f.getbbox(txt); d.text(((1280 - (r - l)) // 2 - l, y - (t + b) // 2), txt, col, font=f)
    out = np.concatenate([np.array(im), np.full((720, 1280, 1), 255, np.uint8)], -1)
    os.makedirs(R('work', 'build', 'game_texture'), exist_ok=True)
    texio.save(src, R('work', 'build', 'game_texture', 'copy_announce_NOMIP.tex'), out)
    Image.fromarray(np.hstack([a0[..., :3], np.full((720, 8, 3), 90, np.uint8), out[..., :3]])).resize((1284, 360)).save(R('work', 'gui', 'preview_copy.png'))
if __name__ == '__main__':
    main()
