# -*- coding: utf-8 -*-
r"""1.02 옮겨 심기 검산 (2026-11-14) — python tools/v102_check.py
  ① 1.02 결과에서 바뀐 포인터 칸(세그먼트 3 VA) 수 = 1.00 빌드의 바뀐 포인터 칸 수
  ② 바뀐 포인터가 가리키는 곳의 24 B 가 1.00 빌드에서 «바뀐 포인터가 가리키던 문자열 머리» 집합에 있음
  ③ 바뀐 바이트가 자료 세그먼트 3 과 UI 문구 구역(세그먼트 0 의 0xE55000~0xE5B000) 안에만 있음, 바뀐 바이트 수 대조"""
import os, sys, struct
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import v102_port as P
R = P.R


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    a0 = open(R('work', 'bin', 'EBOOT.elf'), 'rb').read(); a1 = open(R('work', 'build', 'EBOOT.BIN'), 'rb').read()
    b0 = open(R('work', 'v102', 'dec', 'EBOOT.elf'), 'rb').read(); b1 = open(R('work', 'v102', 'build', 'EBOOT.elf'), 'rb').read()
    assert len(b0) == len(b1)
    import json
    pl = json.load(open(R('work', 'v102', 'build', 'ptrs.json')))
    da = np.nonzero(np.frombuffer(a0, np.uint8) != np.frombuffer(a1, np.uint8))[0]
    db = np.nonzero(np.frombuffer(b0, np.uint8) != np.frombuffer(b1, np.uint8))[0]
    bad = []; moved = 0
    for L, L2 in pl:
        T = struct.unpack('>I', a1[L:L + 4])[0] - 0x10000; v = struct.unpack('>I', b1[L2:L2 + 4])[0]
        assert P.SEG3_VA <= v < P.SEG3_VA + 0x2066500, hex(L2)
        t2 = v - P.SEG3_VA + P.SEG3_OFF
        moved += a0[L:L + 4] != a1[L:L + 4]
        if b1[t2:t2 + 24] != P.norm(a1[T:T + 24], T): bad.append((L, L2, a1[T:T + 12].hex(' '), b1[t2:t2 + 12].hex(' ')))
    print('① 옮긴 포인터 칸 %d (값이 바뀐 것 %d)' % (len(pl), moved))
    print('② 가리키는 곳의 24 B 가 1.00 빌드와 다른 포인터 %d' % len(bad))
    for b_ in bad[:12]: print('   1.00 %07X → 1.02 %07X: %s | %s' % b_)
    out = [int(o) for o in db if not (P.SEG3_OFF <= o < P.SEG3_END or 0xE55000 <= o < 0xE5B000 or 0x105E20C <= o < 0x105E2AC)]   # 0x105E20C~ = 랭킹 기본 이름 직접 씀(세그먼트 0 사본, 2026-11-15)
    print('③ 바뀐 바이트: 1.00 빌드 %d · 1.02 결과 %d · 허용 구역 밖 %d %s' % (len(da), len(db), len(out), [hex(o) for o in out[:8]]))


if __name__ == '__main__':
    main()
