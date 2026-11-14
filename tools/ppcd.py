# -*- coding: utf-8 -*-
r"""PS3 ELF PPC64 디스어셈블(capstone) — python tools/ppcd.py <elf> <파일 오프셋 hex> <길이 hex>
  1.02 ELF: 세그먼트 0 VA = 파일 + 0x10000. bl 대상·TOC(r2) 상대 접근은 숫자 그대로 보여 줌."""
import sys, struct
from capstone import Cs, CS_ARCH_PPC, CS_MODE_64, CS_MODE_BIG_ENDIAN
def dis(e, off, n, va_delta=0x10000):
    md = Cs(CS_ARCH_PPC, CS_MODE_64 | CS_MODE_BIG_ENDIAN); out = []
    o = off
    while o < off + n:
        ins = list(md.disasm(e[o:o + 4], o + va_delta))
        if ins: out.append('%07X  %-8s %s' % (o, ins[0].mnemonic, ins[0].op_str))
        else: out.append('%07X  .long    %s' % (o, e[o:o + 4].hex()))
        o += 4
    return out
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    e = open(sys.argv[1], 'rb').read()
    print('\n'.join(dis(e, int(sys.argv[2], 16), int(sys.argv[3], 16))))
