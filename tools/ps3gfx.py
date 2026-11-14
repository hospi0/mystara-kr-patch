# -*- coding: utf-8 -*-
"""PS3 미스타라 그래픽 dd11x/dd21x: 16x16 타일 128 B, 줄마다 8 B, 4bpp 아래 니블 = 왼쪽 화소. 타일 번호 t(CPS2 0x10000+) → 오프셋 (t-0x10000)*128.
글 코드 c(0x1E00~) = 타일 0x10000+c → 오프셋 c*128. (2026-11-12)"""
import numpy as np
def tile(b, c):
    t = np.frombuffer(b[c * 128:(c + 1) * 128], np.uint8)
    px = np.empty(256, np.uint8); px[0::2] = t & 15; px[1::2] = t >> 4
    return px.reshape(16, 16)
def put(b, c, img):
    f = img.reshape(-1).astype(np.uint8)
    b[c * 128:(c + 1) * 128] = bytes((f[0::2] & 15) | ((f[1::2] & 15) << 4))
def sheet(b, codes, cols=16, scale=2, label=False):
    from PIL import Image, ImageDraw
    rows = (len(codes) + cols - 1) // cols
    W = 18 if not label else 18
    im = Image.new('L', (cols * W, rows * W), 60)
    for i, c in enumerate(codes):
        a = (tile(b, c) > 0) * 255
        im.paste(Image.fromarray(a.astype(np.uint8)), ((i % cols) * W + 1, (i // cols) * W + 1))
    return im.resize((im.width * scale, im.height * scale), 0)
