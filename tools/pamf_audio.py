# -*- coding: utf-8 -*-
r"""PAMF(.pam) 안 ATRAC3plus 음성(개인 스트림 BD, 하위 00) → OMA → ffmpeg 로 WAV (2026-11-14 무비 자막).
  PES 몸 = 개인 머리 4 B + 프레임(0F D0 pp pp 00 00 00 00 + 데이터). OMA = «EA3» 머리 0x60 B(코덱 1 = ATRAC3plus, 값 00 pp pp) + 데이터.
  python tools/pamf_audio.py 입력.pam 출력.wav"""
import struct, sys, subprocess, os
FF = r'C:\claude\utils\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe'
def extract(path):
    f = open(path, 'rb'); hdr = f.read(8); hsz = struct.unpack('>I', open(path, 'rb').read(12)[8:12])[0] * 0x800
    f.seek(hsz); d = f.read(); pay = bytearray(); o = 0
    while o < len(d) - 6:
        if d[o:o + 3] == b'\0\0\1':
            sid = d[o + 3]
            if sid == 0xBA: o += 14; continue
            ln = struct.unpack('>H', d[o + 4:o + 6])[0]
            if sid == 0xBD and d[o + 9 + d[o + 8]] == 0: pay += d[o + 9 + d[o + 8] + 4:o + 6 + ln]
            o += 6 + ln
        else: o += 1
    params = pay[2:4]; fs = ((struct.unpack('>H', params)[0] & 0x3FF) * 8) + 8
    out = bytearray(); i = 0
    while i + 8 + fs <= len(pay):
        if pay[i:i + 2] != b'\x0f\xd0': i += 1; continue
        out += pay[i + 8:i + 8 + fs]; i += 8 + fs
    h = bytearray(0x60); h[0:3] = b'EA3'; h[3] = 1; h[5] = 0x60; h[6] = h[7] = 0xFF; h[32] = 1; h[33] = 0; h[34:36] = params
    return bytes(h) + bytes(out)
if __name__ == '__main__':
    oma = sys.argv[2][:-4] + '.oma'; open(oma, 'wb').write(extract(sys.argv[1]))
    subprocess.run([FF, '-y', '-hide_banner', '-loglevel', 'error', '-i', oma, '-ac', '1', '-ar', '16000', sys.argv[2]], check=True)
    os.remove(oma); print('ok', sys.argv[2])
