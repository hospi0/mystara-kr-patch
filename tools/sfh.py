# -*- coding: utf-8 -*-
r"""MT 프레임워크 PS3 «\0SFH» 껍질(1.02 업데이트 dev_hdd0 파일·dev_hdd1 캐시) 풀기·싸기 (2026-11-14, 1.02 EBOOT 0x5CD500 디스어셈).
  머리 16 B: «\0SFH» · 0001 0001 · 자료 크기(BE u32) · 0  +  [자료 0x1FFF0 B(마지막은 16 B 로 0 채움) + 검사값 16 B] 반복
  검사값 = 시작값 INIT 에 블록의 16 B 줄들을 바이트별로 더하고(mod 256), 바이트마다 ROT 만큼 왼쪽 회전.
  python tools/sfh.py unwrap 입력 출력 / wrap 입력 출력 / check 파일..."""
import struct, sys
import numpy as np
INIT = bytes.fromhex('875507b54b04a5aec767becb01505844')          # 1.02 ELF 파일 0xDFDE00(VA 0xE0DE00)
ROT = bytes.fromhex('07020504060301040206070305070105')
BLK = 0x1FFF0
def csum(block):
    a = np.frombuffer(block, np.uint8).reshape(-1, 16).sum(0, dtype=np.uint64)
    v = (a + np.frombuffer(INIT, np.uint8)) & 255
    r = np.frombuffer(ROT, np.uint8).astype(np.uint64) & 7
    return bytes((((v << r) | (v >> (8 - r))) & 255).astype(np.uint8))
def unwrap(d, verify=True):
    assert d[:8] == b'\0SFH\0\x01\0\x01', d[:8]
    n = struct.unpack('>I', d[8:12])[0]; out = b''; o = 16
    while len(out) < n:
        k = min(BLK, (n - len(out) + 15) & ~15); blk = d[o:o + k]
        if verify: assert csum(blk) == d[o + k:o + k + 16], ('검사값 다름', hex(o))
        out += blk; o += k + 16
    assert o == len(d), (o, len(d))
    return out[:n]
def wrap(data):
    out = bytearray(b'\0SFH\0\x01\0\x01' + struct.pack('>II', len(data), 0))
    for o in range(0, len(data), BLK):
        blk = data[o:o + BLK]; blk += b'\0' * (-len(blk) % 16)
        out += blk + csum(blk)
    return bytes(out)
if __name__ == '__main__':
    if sys.argv[1] == 'unwrap': open(sys.argv[3], 'wb').write(unwrap(open(sys.argv[2], 'rb').read()))
    elif sys.argv[1] == 'wrap': open(sys.argv[3], 'wb').write(wrap(open(sys.argv[2], 'rb').read()))
    else:
        for p in sys.argv[2:]:
            d = open(p, 'rb').read(); print(p, '되싸기 일치' if wrap(unwrap(d)) == d else '⛔다름')
