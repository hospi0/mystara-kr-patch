# -*- coding: utf-8 -*-
"""CPS2 그래픽 롬 합치기·타일 그리기 (MAME cps1_layout16x16/8x8). 2026-11-12 미스타라.
  합친 영역: 64비트 묶음마다 13m·15m·17m·19m 워드(파일 순서 2바이트씩) — 뒤 묶음 14m·16m·18m·20m.
  16x16 타일 128 B: 행 64비트, x = 비트 0..7 + 32..39, 평면 비트 24·16·8·0 (MSB 먼저)."""
import os, numpy as np
def merge(files):
    arrs = [np.frombuffer(open(f, 'rb').read(), '>u2') for f in files]
    n = min(len(a) for a in arrs)
    out = np.empty(n * 4, '>u2')
    for k, a in enumerate(arrs): out[k::4] = a[:n]
    g = np.frombuffer(out.tobytes(), np.uint64).copy()
    bank = 0x200000 // 8                 # MAME cps2_gfx_decode: 2 MB 은행마다 unshuffle
    for i in range(0, len(g), bank): unshuffle(g, i, min(bank, len(g) - i))
    return g.tobytes()
def unshuffle(buf, st, ln):
    """MAME cps2 unshuffle (64비트 단위, 재귀) — numpy 반복판."""
    # 재귀를 아래에서 위로: 크기 4,8,16,… 블록마다 가운데 두 사분면 맞바꿈
    size = 4
    while size <= ln:
        h = size // 2; q = h // 2
        blk = buf[st:st + ln].reshape(-1, size)
        tmp = blk[:, q:h].copy(); blk[:, q:h] = blk[:, h:h + q]; blk[:, h:h + q] = tmp
        buf[st:st + ln] = blk.reshape(-1)
        size *= 2
def tile16(g, code):
    t = np.frombuffer(g[code * 128:(code + 1) * 128], np.uint8)
    bits = np.unpackbits(t)            # MSB 먼저
    img = np.zeros((16, 16), np.uint8)
    for y in range(16):
        row = bits[y * 64:(y + 1) * 64]
        for x in range(16):
            xo = x if x < 8 else 32 + (x - 8)
            v = 0
            for pi, po in enumerate((24, 16, 8, 0)):
                v |= int(row[xo + po]) << (3 - pi)
            img[y, x] = v
    return img
def sheet(g, codes, cols=16, scale=3):
    from PIL import Image
    rows = (len(codes) + cols - 1) // cols
    im = Image.new('L', (cols * 17, rows * 17), 40)
    for i, c in enumerate(codes):
        a = tile16(g, c) * 17
        im.paste(Image.fromarray(a.astype(np.uint8)), ((i % cols) * 17, (i // cols) * 17))
    return im.resize((im.width * scale, im.height * scale), 0)
