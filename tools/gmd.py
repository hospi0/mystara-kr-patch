# -*- coding: utf-8 -*-
r"""MT 프레임워크 PS3 GMD v0x010201(큰 끝) 읽기·쓰기 (2026-11-14 미스타라 바깥 메뉴).
  머리 40 B: magic «\0DMG» · ver · lang · 0 · 0 · 라벨 수 · 문자열 수 · 라벨 블록 크기 · 문자열 블록 크기 · 이름 길이 → 이름 + NUL
  그 뒤 라벨 표·라벨 이름 블록, 파일 끝 = 문자열 블록(UTF-8, NUL 끝) — 문자열만 바꾸고 크기 칸(0x20) 고침.
  python tools/gmd.py dump 입력.gmd 출력.tsv  /  python tools/gmd.py build 입력.gmd 번역.tsv 출력.gmd"""
import struct, sys
def read(path):
    g = open(path, 'rb').read()
    ns, ssz = struct.unpack('>I', g[0x18:0x1C])[0], struct.unpack('>I', g[0x20:0x24])[0]
    strs = g[-ssz:].split(b'\0')[:ns]
    lsz = struct.unpack('>I', g[0x1C:0x20])[0]
    labels = g[-ssz - lsz:-ssz].split(b'\0')
    return g, ssz, [s.decode('utf-8') for s in strs], [l.decode('utf-8', 'replace') for l in labels]
def build(path, texts):
    g, ssz, strs, _ = read(path)
    assert len(texts) == len(strs)
    body = b''.join(t.encode('utf-8') + b'\0' for t in texts)
    out = bytearray(g[:-ssz]) + body
    out[0x20:0x24] = struct.pack('>I', len(body))
    return bytes(out)
def esc(s): return s.replace('\r', '\\r').replace('\n', '\\n')
def unesc(s): return s.replace('\\r', '\r').replace('\\n', '\n')
def load_tsv(path):
    """번호·원문·한글 TSV → 문자열 목록(한글 칸 비면 원문)"""
    rows = [l.rstrip('\n').split('\t') for l in open(path, encoding='utf-8')][1:]
    return [unesc(r[2] if len(r) > 2 and r[2] else r[1]) for r in rows]
if __name__ == '__main__':
    if sys.argv[1] == 'dump':
        g, ssz, strs, labels = read(sys.argv[2])
        with open(sys.argv[3], 'w', encoding='utf-8') as f:
            f.write('번호\t원문\t한글\n')
            for i, s in enumerate(strs): f.write('%03d\t%s\t\n' % (i, esc(s)))
    else:
        texts = load_tsv(sys.argv[3])
        open(sys.argv[4], 'wb').write(build(sys.argv[2], texts))
