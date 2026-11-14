# -*- coding: utf-8 -*-
r"""PAMF(.pam) 영상 바꿔 넣기 — 자막 입힌 새 H.264 + 원본 ATRAC3plus 음성 팩 그대로 (2026-11-14 무비 자막).
  원본 꼴(실측): 팩 2048 B · 키프레임 팩 = 팩 머리 + 시스템 머리(BB) + 0xBF 134 B + E0(PTS·DTS·P-STD 확장, 머리 13)
                 그 밖 프레임 첫 팩 = E0(PTS·DTS, 머리 10) · 이어지는 팩 = E0(머리 0) · 프레임 끝 팩 = 0xBE 채움
                 음성 팩 = BD(PTS) 2048 B 꽉 참. PAMF 머리 0x800 B, EP 표 0개 → 데이터 크기(0xC)만 고침.
  새 영상: B 프레임 없음(PTS = DTS), AUD·SPS/PPS 반복, 첫 PTS = 원본 첫 영상 PTS, 프레임 간격 3003.
  mux(원본.pam, 새.h264, 출력.pam)"""
import struct
def pts_bytes(pfx, v):
    return bytes([(pfx << 4) | (((v >> 30) & 7) << 1) | 1, (v >> 22) & 0xFF, (((v >> 15) & 0x7F) << 1) | 1, (v >> 7) & 0xFF, ((v & 0x7F) << 1) | 1])
def read_pts(b):
    return (((b[0] >> 1) & 7) << 30) | (b[1] << 22) | ((b[2] >> 1) << 15) | (b[3] << 7) | (b[4] >> 1)
def pack_header(scr, mux=0x01d4c0):
    base, ext = scr, 0
    b = bytearray(14); b[0:4] = b'\0\0\1\xba'
    b[4] = 0x44 | (((base >> 30) & 7) << 3) | ((base >> 28) & 3)
    b[5] = (base >> 20) & 0xFF
    b[6] = (((base >> 15) & 0x1F) << 3) | 0x04 | ((base >> 13) & 3)
    b[7] = (base >> 5) & 0xFF
    b[8] = ((base & 0x1F) << 3) | 0x04 | ((ext >> 7) & 3)
    b[9] = ((ext & 0x7F) << 1) | 1
    b[10] = (mux >> 14) & 0xFF; b[11] = (mux >> 6) & 0xFF; b[12] = ((mux & 0x3F) << 2) | 3; b[13] = 0xF8
    return bytes(b)
def parse_orig(path):
    d = open(path, 'rb').read(); hsz = struct.unpack('>I', d[8:12])[0] * 0x800
    hdr = d[:hsz]; packs = [d[i:i + 2048] for i in range(hsz, len(d), 2048)]
    audio = []; first_v = None; sysh = bf = None
    for pk in packs:
        o = 14
        while o < 2048 and pk[o:o + 3] == b'\0\0\1':
            sid = pk[o + 3]; ln = struct.unpack('>H', pk[o + 4:o + 6])[0]
            if sid == 0xBB and sysh is None: sysh = pk[o:o + 6 + ln]
            if sid == 0xBF and bf is None: bf = pk[o:o + 6 + ln]
            if sid == 0xE0 and first_v is None and pk[o + 7] & 0x80: first_v = (read_pts(pk[o + 9:o + 14]), read_pts(pk[o + 14:o + 19]) if pk[o + 7] & 0x40 else None)
            if sid == 0xBD:
                pts = read_pts(pk[o + 9:o + 14]) if pk[o + 7] & 0x80 else None
                audio.append([pts, pk])
            o += 6 + ln
    last = next((a[0] for a in audio if a[0] is not None), 0)   # PTS 없는 음성 팩은 앞 팩 시각(맨 앞은 첫 PTS)
    for a in audio:
        if a[0] is None: a[0] = last
        last = a[0]
    return hdr, sysh, bf, audio, first_v
def split_aus(es):
    """Annex B → AUD(00 00 00 01 09) 기준 접근 단위 목록 [(bytes, is_idr)]"""
    idx = []; i = 0
    while True:
        i = es.find(b'\x00\x00\x00\x01\x09', i)
        if i < 0: break
        idx.append(i); i += 5
    aus = []
    for k, s in enumerate(idx):
        e = idx[k + 1] if k + 1 < len(idx) else len(es); au = es[s:e]
        idr = False; j = 0
        while True:
            j = au.find(b'\x00\x00\x01', j)
            if j < 0: break
            if au[j + 3] & 0x1F == 5: idr = True; break
            j += 3
        aus.append((au, idr))
    return aus
def mux(orig, h264, out):
    hdr, sysh, bf, audio, (pts0, dts0) = parse_orig(orig)
    aus = split_aus(open(h264, 'rb').read())
    D = 3003; vstart = pts0
    items = []                                      # (시각, 종류, 자료)
    for n, (au, idr) in enumerate(aus): items.append((vstart + n * D - 9000, 0, n))   # 영상은 0.1초 앞서 보냄
    for a in audio: items.append((a[0] - 9000, 1, a[1]))
    items.sort(key=lambda x: (x[0], x[1]))
    body = bytearray(); scr = max(0, items[0][0] - 9000)
    def emit(payload_pes_list):
        nonlocal scr
        p = bytearray(pack_header(scr))
        for x in payload_pes_list: p += x
        assert len(p) <= 2048, len(p)
        if len(p) < 2048:
            pad = 2048 - len(p)
            if pad < 6: p[-0:] = p; p += b'\xff' * pad          # 거의 없음(아래에서 막음)
            else: p += b'\0\0\1\xbe' + struct.pack('>H', pad - 6) + b'\xff' * (pad - 6)
        body.extend(p); scr += 300
    for t, kind, x in items:
        scr = max(scr, t - 18000)
        if kind == 1:
            pk = bytearray(x); pk[0:14] = pack_header(scr); body.extend(pk); scr += 300; continue
        au, idr = aus[x]; pts = vstart + x * D; dts = pts
        if idr:
            first_hdr = bytes([0x81, 0xC1, 13]) + pts_bytes(3, pts) + pts_bytes(1, dts) + b'\x1e\x63\x05'
            pre = sysh + bf
        else:
            first_hdr = bytes([0x81, 0xC0, 10]) + pts_bytes(3, pts) + pts_bytes(1, dts); pre = b''
        pos = 0; first = True
        while pos < len(au):
            h = first_hdr if first else bytes([0x81, 0x00, 0])
            room = 2048 - 14 - (len(pre) if first else 0) - 6 - len(h)
            take = au[pos:pos + room]
            rest = room - len(take)
            if 0 < rest < 6:                         # 채움 패킷이 못 들어가는 틈 → PES 머리에 채움 바이트
                h = h[:2] + bytes([h[2] + rest]) + h[3:] + b'\xff' * rest
            pes = b'\0\0\1\xe0' + struct.pack('>H', len(h) + len(take)) + h + take
            emit([pre if first else b'', pes]); pos += len(take); first = False; pre = b''
    out_hdr = bytearray(hdr); struct.pack_into('>I', out_hdr, 12, len(body) // 0x800)
    open(out, 'wb').write(bytes(out_hdr) + bytes(body))
    return len(aus), len(audio), len(body)
