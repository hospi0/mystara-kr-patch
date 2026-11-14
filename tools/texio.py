# -*- coding: utf-8 -*-
r"""MT PS3 .tex 읽기·쓰기 (RGBA8 선형·밉 있는 RGBA8 = 모턴 스위즐, DXT5) (2026-11-14).
  RGBA8 바이트 순 = A R G B. 밉 있는 RGBA8 은 RSX 스위즐(작은 쪽 비트까지 x·y 번갈아, 남는 비트는 큰 쪽).
  load(path) → (RGBA ndarray 0번 밉, info) · save(path_in, path_out, rgba) — 밉은 2x2 평균으로 다시 만듦."""
import struct
import numpy as np
from PIL import Image
def info(d):
    w1, w2, w3, off = struct.unpack('>IIII', d[4:20])
    return dict(mip=w2 & 0x3F, W=(w2 >> 6) & 0x1FFF, H=(w2 >> 19) & 0x1FFF, fmt=(w3 >> 8) & 0xFF, off=off)
def swz_index(W, H):
    """선형 (y,x) → 스위즐 순번 표(H×W)"""
    xs = np.arange(W); ys = np.arange(H); idx = np.zeros((H, W), np.int64)
    bx = W.bit_length() - 1; by = H.bit_length() - 1; out_bit = 0
    X = np.broadcast_to(xs[None, :], (H, W)); Y = np.broadcast_to(ys[:, None], (H, W))
    for b in range(max(bx, by)):
        if b < bx: idx |= ((X >> b) & 1) << out_bit; out_bit += 1
        if b < by: idx |= ((Y >> b) & 1) << out_bit; out_bit += 1
    return idx
def mip_offsets(i):
    W, H, o = i['W'], i['H'], i['off']; out = []
    if i['mip'] > 1 and o >= 20 + 4 * i['mip']:      # 밉 오프셋 표가 머리 뒤에 있음
        pass
    for k in range(i['mip']):
        w, h = max(1, W >> k), max(1, H >> k)
        out.append((o, w, h)); o += w * h * (4 if i['fmt'] == 0x27 else 1)
    return out
def load(path):
    d = open(path, 'rb').read(); i = info(d); W, H, o = i['W'], i['H'], i['off']
    if i['fmt'] == 0x27:
        a = np.frombuffer(d[o:o + W * H * 4], np.uint8).reshape(-1, 4)
        if i['mip'] > 1:
            idx = swz_index(W, H); a = a[idx.reshape(-1)]
        a = a.reshape(H, W, 4)
        return a[:, :, [1, 2, 3, 0]].copy(), i
    if i['fmt'] in (0x17, 0x18, 0x19):
        return np.array(Image.frombytes('RGBA', (W, H), d[o:o + W * H], 'bcn', 3)), i
    raise SystemExit('형식 %X' % i['fmt'])
def pack_rgba(rgba, swz):
    H, W = rgba.shape[:2]; argb = rgba[:, :, [3, 0, 1, 2]].reshape(-1, 4)
    if swz:
        idx = swz_index(W, H).reshape(-1); out = np.empty_like(argb); out[idx] = argb; argb = out
    return argb.tobytes()
def save(src, dst, rgba):
    d = bytearray(open(src, 'rb').read()); i = info(d)
    if i['fmt'] == 0x27:
        o = i['off']; lvl = rgba.astype(np.float32); W, H = i['W'], i['H']
        for k in range(i['mip']):
            w, h = max(1, W >> k), max(1, H >> k)
            if k:
                p = lvl; ph, pw = p.shape[:2]
                if ph > 1 and pw > 1: lvl = (p[0::2, 0::2] + p[1::2, 0::2] + p[0::2, 1::2] + p[1::2, 1::2]) / 4
                elif ph > 1: lvl = (p[0::2] + p[1::2]) / 2
                else: lvl = (p[:, 0::2] + p[:, 1::2]) / 2
            b = pack_rgba(np.clip(lvl + 0.5, 0, 255).astype(np.uint8), i['mip'] > 1)
            d[o:o + len(b)] = b; o += len(b)
    elif i['fmt'] == 0x17:
        d[i['off']:i['off'] + i['W'] * i['H']] = dxt5(rgba)
    else: raise SystemExit('쓰기 미지원 %X' % i['fmt'])
    open(dst, 'wb').write(d)
def _enc_alpha(a):
    a0, a1 = int(a.max()), int(a.min())
    if a0 == a1: return bytes([a0, a1]) + b'\0' * 6
    lv = np.array([a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)])
    idx = np.abs(a.reshape(-1, 1).astype(int) - lv[None, :]).argmin(1)
    bits = 0
    for j, v in enumerate(idx.tolist()): bits |= v << (3 * j)
    return bytes([a0, a1]) + bits.to_bytes(6, 'little')
def _565(c): return ((int(c[0]) >> 3) << 11) | ((int(c[1]) >> 2) << 5) | (int(c[2]) >> 3)
def _enc_color(rgb):
    px = rgb.reshape(-1, 3).astype(float)
    lum = px @ [0.3, 0.59, 0.11]; c0 = px[lum.argmax()]; c1 = px[lum.argmin()]
    a, b = _565(c0), _565(c1)
    if a < b: a, b = b, a; c0, c1 = c1, c0
    if a == b: return struct.pack('<HHI', a, b, 0)
    def un(v): return np.array([((v >> 11) & 31) * 255 / 31, ((v >> 5) & 63) * 255 / 63, (v & 31) * 255 / 31])
    p0, p1 = un(a), un(b); pal = np.array([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3])
    idx = ((px[:, None, :] - pal[None]) ** 2).sum(-1).argmin(1); bits = 0
    for j, v in enumerate(idx.tolist()): bits |= v << (2 * j)
    return struct.pack('<HHI', a, b, bits)
def dxt5(rgba):
    H, W = rgba.shape[:2]; out = bytearray()
    for by in range(0, H, 4):
        for bx in range(0, W, 4):
            blk = rgba[by:by + 4, bx:bx + 4]
            out += _enc_alpha(blk[..., 3]) + _enc_color(blk[..., :3])
    return bytes(out)
