# -*- coding: utf-8 -*-
r"""1.00 빌드(work/build/EBOOT.BIN)의 바뀐 바이트를 1.02 ELF(work/v102/dec/EBOOT.elf)로 옮겨 심기 (2026-11-14).
  · 1.02 는 게임 자료가 세그먼트 3(파일 0x1090000 · VA 0x10000000)으로 옮겨져 위치·VA 가 다르지만 내용은 거의 같음.
  · 바뀐 구간마다: 1.00 원본 바이트가 1.02 의 (자리 + d)에 그대로 있으면 새 바이트를 그 자리에(d = 이웃 대응 구간의 차이값 후보).
    안 맞으면 4 B VA 포인터 칸으로 보고 «옛 값이 가리키던 곳의 1.02 자리»가 1.02 값과 같은지 확인 → 새 값도 같은 식으로 바꿔 씀.
  · 어느 쪽도 아니면 못 옮긴 구간으로 보고(조용히 건너뛰지 않음).
  python tools/v102_port.py → work/v102/build/EBOOT.elf + report_port.txt"""
import os, sys, json, struct, bisect
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = lambda *p: os.path.join(ROOT, *p)
VA0 = 0x10000                                    # 1.00: VA = 파일 + 0x10000 (세그먼트 0)
SEG3_OFF, SEG3_VA, SEG3_END = 0x1090000, 0x10000000, 0x1090000 + 0x2066500
def va102(off):
    if SEG3_OFF <= off < SEG3_END: return off - SEG3_OFF + SEG3_VA
    assert off < 0xFC55E8, hex(off); return off + 0x10000


# TOD 글 머리의 호스트 RAM 포인터(1.00) → 1.02 는 작은 번호. 짝수 자리 4 B 통째일 때만 바꿈.
HOST = {bytes.fromhex('0142f988'): bytes.fromhex('00000000'), bytes.fromhex('0142f980'): bytes.fromhex('00000004'),
        bytes.fromhex('0142f8a8'): bytes.fromhex('00000008'), bytes.fromhex('0142f918'): bytes.fromhex('0000000c')}
def norm(buf, base):
    """buf(1.00 꼴, 파일 오프셋 base 부터)의 호스트 포인터를 1.02 값으로"""
    if bytes([1, 0x42, 0xf8]) not in buf and bytes([1, 0x42, 0xf9]) not in buf: return bytes(buf)
    out = bytearray(buf); o = base & 1
    while o + 4 <= len(out):
        k = bytes(out[o:o + 4])
        if k in HOST: out[o:o + 4] = HOST[k]; o += 4
        else: o += 2
    return bytes(out)
KNOWN_D = [0x2B04AD0, 0x2B959D0, 0x2B96F40, 0x2B96F50, 0x2B06020, 0x293BB30, 0x293BAD0, 0x293BAC4, 0x293BAC0, 0x2BE8240, 0x29C5E50, 0x27E1090]
FORCE = {0x14B6678: 0x2F91410, 0x14A33E0: 0x2DA17B0}      # 이름 입력표 SOM·TOD — 내용이 같아 서로 헷갈림(이웃 표로 확정한 자리)


class Map:
    def __init__(self, segs):
        self.segs = sorted(segs); self.xs = [s[0] for s in self.segs]
    def cands(self, o, n=6):
        """o 둘레 대응 구간들의 차이값 후보(가까운 순)"""
        i = bisect.bisect_right(self.xs, o); out = []
        for k in range(1, 400):
            for j in (i - k, i + k - 1):
                if 0 <= j < len(self.segs) and self.segs[j][2] not in out: out.append(self.segs[j][2])
            if len(out) >= n: break
        return out
    def exact(self, o):
        i = bisect.bisect_right(self.xs, o) - 1
        if i >= 0 and self.segs[i][0] <= o < self.segs[i][1]: return o + self.segs[i][2]
        return None


def port(a0, a1, b, mp, log=print):
    """a0 = 1.00 원본, a1 = 1.00 빌드, b = 1.02 원본(bytearray, 제자리 고침) → 통계"""
    n = len(a0); runs = []; i = 0
    import numpy as np
    df = np.nonzero(np.frombuffer(a0, np.uint8) != np.frombuffer(a1, np.uint8))[0]
    if len(df):
        s = int(df[0]) & ~1; e = s
        for o in df.tolist():
            if o - e > 8: runs.append((s, (e + 2) & ~1)); s = o & ~1
            e = o
        runs.append((s, (e + 2) & ~1))
    st = {'그대로': 0, '포인터': 0, '섞임': 0, '못 옮김': 0}; fail = []; b0 = bytes(b); done = []
    cov = {}
    for sx, sy, sd in mp.segs: cov[sd] = cov.get(sd, 0) + sy - sx
    major = [d for d, c in sorted(cov.items(), key=lambda kv: -kv[1]) if c >= 0x800]      # 넓게 맞는 차이값(전역 후보)
    major = KNOWN_D + [d for d in major if d not in KNOWN_D]
    why = {}
    plist = []
    near = []                                               # (구간, 차이값, 다른 워드 수) — 1.02 가 원문을 조금 고친 곳
    def allc(x):
        c = mp.cands(x)
        return c + [d for d in major if d not in c]
    def try_plain(x, y):
        """구간 + 둘레(한쪽 12 B 이상)가 1.02 의 같은 차이 자리에 그대로 있는가(호스트 포인터는 1.02 값으로 본 뒤 비교)"""
        if x in FORCE:
            d = FORCE[x] - x; assert b0[x + d:y + d] == a0[x:y]; return d
        an = norm(a0[x:y], x)
        for d in allc(x):
            if not (0 <= x + d - 12 and y + d + 12 <= len(b0)) or b0[x + d:y + d] != an: continue
            if y - x >= 24 or b0[x + d - 12:x + d] == a0[x - 12:x] or b0[y + d:y + d + 12] == a0[y:y + 12]: return d
        for pre, post in ((16, 16), (32, 0), (0, 32), (8, 8)):
            ctx = a0[x - pre:y + post]; q = b0.find(ctx)
            if q >= 0 and b0.find(ctx, q + 1) < 0:
                d = q + pre - x
                if d not in major: major.insert(0, d)
                return d
        return None
    def fset(o):
        """1.00 파일 오프셋 → 1.02 후보 자리들(둘레가 같은 곳; 같은 자료 사본이 둘일 수 있음)"""
        out = []
        p = mp.exact(o)
        if p is not None: out.append(p)
        for pre, post in ((8, 16), (0, 24), (24, 0)):
            lo = max(0, o - pre); an = norm(a0[lo:o + post], lo)
            for d in allc(o):
                if 0 <= lo + d and b0[lo + d:o + post + d] == an and o + d not in out: out.append(o + d)
        return out
    def near_d(o):
        """o 에서 가장 가까운(±512 B) 대응 자리의 차이값들 — 포인터 표 안처럼 둘레가 안 맞는 자리용"""
        for k in range(2, 4098, 2):
            for q in (o - k, o + k):
                c = fset(q)
                if c: return [x_ - q for x_ in c]
        return []
    def conv(old, new, cur):
        """포인터 칸: 1.02 값(cur) = 옛 대상 + 알려진 차이값 이면, 새 대상의 1.02 VA. 아니면 None"""
        if not (VA0 + 0x90000 <= old < VA0 + 0x900000 and VA0 + 0x90000 <= new < VA0 + 0x900000): return None
        if not (SEG3_VA <= cur < SEG3_VA + 0x2066500): return None
        d_old = cur - SEG3_VA + SEG3_OFF - (old - VA0)
        if d_old not in major and d_old not in [c - (old - VA0) for c in fset(old - VA0)]: why[('conv', old, new)] = '옛 대상 차이값 %+X 모름' % d_old; return None
        cn = [c - (new - VA0) for c in fset(new - VA0)] or near_d(new - VA0)
        if not cn: why[('conv', old, new)] = '새 대상 자리 모름'; return None
        cn.sort(key=lambda d: abs(d - d_old))
        return va102(new - VA0 + cn[0])
    def try_ptrs(x, y):
        """구간이 4 B 포인터 칸들로 이루어졌는가 → [(1.02 자리, 새 값)]"""
        for d in allc(x):
            for al in (0, 2):
                xs = (x - al) & ~3 if al == 0 else ((x - 2) & ~3) + 2
                out = []; ok = True; o = xs
                while o < y:
                    old = struct.unpack('>I', a0[o:o + 4])[0]; new = struct.unpack('>I', a1[o:o + 4])[0]
                    if old == new: o += 4; continue
                    cur = struct.unpack('>I', b0[o + d:o + d + 4])[0] if 0 <= o + d < len(b0) - 4 else None
                    v = conv(old, new, cur) if cur else None
                    if v is None: ok = False; break
                    out.append((o + d, v, o)); o += 4
                if ok and out: return out
        return None
    def try_near(x, y):
        if y - x < 64: return None
        an = norm(a0[x:y], x); nn = norm(a1[x:y], x)
        for d in allc(x):
            if not (0 <= x + d and y + d <= len(b0)): continue
            bad = [o for o in range(0, y - x, 2) if b0[x + d + o:x + d + o + 2] != an[o:o + 2]]
            if len(bad) > 4: continue
            out = bytearray(nn); note = []
            for o in bad:
                ab = x + o; fixed = False
                for st_ in (ab, ab - 2):
                    old = struct.unpack('>I', a0[st_:st_ + 4])[0]; new = struct.unpack('>I', a1[st_:st_ + 4])[0]
                    v = conv(old, new, struct.unpack('>I', b0[st_ + d:st_ + d + 4])[0])
                    if v is not None and x <= st_ and st_ + 4 <= y:
                        out[st_ - x:st_ - x + 4] = struct.pack('>I', v); plist.append((st_, st_ + d)); fixed = True; note.append('%07X 포인터' % st_); break
                if fixed: continue
                if a0[ab:ab + 2] == a1[ab:ab + 2]: out[o:o + 2] = b0[x + d + o:x + d + o + 2]; note.append('%07X 1.02 값 유지' % ab)
                else: note.append('%07X 1.02 원문 %s(1.00 %s) → 번역으로 덮음' % (ab, b0[x + d + o:x + d + o + 2].hex(), a0[ab:ab + 2].hex()))
            near.append((x, y, d, note)); return [(x + d, bytes(out))]
        return None
    def try_mixed(x, y):
        """포인터 칸과 그냥 워드가 섞인 구간: 한 차이값 d 로 구간 전체가 풀려야 함(2 B 씩: 포인터면 4 B, 아니면 1.02 가 1.00 원본과 같아야)"""
        if y - x < 6: return None
        an = norm(a0[x - 2:y + 4], x - 2); nn = norm(a1[x - 2:y + 4], x - 2)
        for d in allc(x):
            if not (0 <= x + d - 4 and y + d + 4 <= len(b0)): continue
            out = []; o = x; ok = True; npl = 0; plist2 = []
            while o < y:
                if a0[o:o + 2] == a1[o:o + 2]: o += 2; continue
                hit = False
                for st_ in (o, o - 2):
                    old = struct.unpack('>I', a0[st_:st_ + 4])[0]; new = struct.unpack('>I', a1[st_:st_ + 4])[0]
                    if not (VA0 + 0x90000 <= old < VA0 + 0x900000 and VA0 + 0x90000 <= new < VA0 + 0x900000): continue
                    if struct.unpack('>I', b0[st_ + d:st_ + d + 4])[0] == 0: continue
                    v = conv(old, new, struct.unpack('>I', b0[st_ + d:st_ + d + 4])[0])
                    if v is None: continue
                    out.append((st_ + d, struct.pack('>I', v))); plist2.append((st_, st_ + d)); o = st_ + 4; hit = True; break
                if hit: continue
                if b0[o + d:o + d + 2] != an[o - x + 2:o - x + 4]:
                    ok = False
                    if o > why.get((x, y), (0,))[0]: why[(x, y)] = (o, d, a0[o - 2:o + 6].hex(), a1[o - 2:o + 6].hex(), b0[o + d - 2:o + d + 6].hex())
                    break
                out.append((o + d, nn[o - x + 2:o - x + 4])); o += 2; npl += 1
            if ok and len(out) > npl: plist.extend(plist2); return out
        return None
    for x, y in runs:
        d = try_plain(x, y)
        if d is not None:
            b[x + d:y + d] = norm(a1[x:y], x); st['그대로'] += 1; done.append((x, y, d)); continue
        ps = try_ptrs(x, y)
        if ps:
            for o, v, L in ps: b[o:o + 4] = struct.pack('>I', v); plist.append((L, o))
            st['포인터'] += len(ps); continue
        mx = try_mixed(x, y) or try_near(x, y)
        if mx:
            for o, v in mx: b[o:o + len(v)] = v
            st['섞임'] += 1; continue
        st['못 옮김'] += 1; fail.append((x, y))
    port.plist = plist
    port.dbg = dict(conv=conv, fset=fset, near_d=near_d, allc=allc, major=major)
    return st, fail, runs, done, near, why


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    a0 = open(R('work', 'bin', 'EBOOT.elf'), 'rb').read(); a1 = open(R('work', 'build', 'EBOOT.BIN'), 'rb').read()
    b = bytearray(open(R('work', 'v102', 'dec', 'EBOOT.elf'), 'rb').read())
    mp = Map(json.load(open(R('work', 'v102', 'map.json'))))
    st, fail, runs, done, near, why = port(a0, a1, b, mp)
    rep = ['바뀐 구간 %d · %s' % (len(runs), st)]
    import collections
    reg = collections.Counter(x >> 16 for x, y in runs)
    rep.append('구간 분포(64KB 단위): ' + ' '.join('%X:%d' % (k << 16, v) for k, v in sorted(reg.items())))
    rep.append('워드 몇 개만 다른 긴 구간:')
    for x, y, d, note in near: rep.append('  %07X~%07X d=%+X: %s' % (x, y, d, ' / '.join(note)))
    rep.append('옮긴 자리 차이값: ' + ' '.join('%+X×%d' % kv for kv in collections.Counter(d for x, y, d in done).most_common()))
    rep.append('못 옮긴 구간 %d:' % len(fail))
    for x, y in fail[:400]: rep.append('  %07X~%07X (%d B) 옛 %s → 새 %s' % (x, y, y - x, a0[x:y][:8].hex(' '), a1[x:y][:8].hex(' ')) + ((' · 막힌 칸 %07X d=%+X 옛 %s 새 %s 1.02 %s' % why[(x, y)]) if (x, y) in why else ''))
    os.makedirs(R('work', 'v102', 'build'), exist_ok=True)
    open(R('work', 'v102', 'build', 'report_port.txt'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    print('\n'.join(rep[:60]))
    for k, v in list(why.items())[:0]: pass
    cv = [(k, v) for k, v in why.items() if k[0] == 'conv']
    print('포인터 변환 실패 사유', len(cv), [('%08X→%08X' % (k[1], k[2]), v) for k, v in cv[:12]])
    UI102 = {0xE597C0: ('ゲームデータが壊れています。\nゲームを終了して、Dungeons & Dragons ―ミスタラ英雄戦記―のゲームデータの削除を行ってください。',
                        '게임 데이터가 손상되었습니다.\n게임을 끝내고 Dungeons & Dragons ―미스타라 영웅전기―의 게임 데이터를 삭제해 주세요.'),
             0xE59F30: ('Dungeons & Dragons® ―ミスタラ英雄戦記―でTower of Doomを一緒にプレイしませんか？',
                        'Dungeons & Dragons® ―미스타라 영웅전기―에서 Tower of Doom을 함께 플레이할까요?'),
             # 1.02 에만 있는 UTF-8 시스템 문구(온라인 기능) — 2026-11-14
             0xE59DD0: ('年齢制限により、あなたはこのアプリケーションでは PlayStation®Network を使った機能をご利用になれません。',
                        '연령 제한으로 이 애플리케이션에서는 PlayStation®Network를 사용하는 기능을 이용할 수 없습니다.'),
             0xE59E68: ('あなたのアカウントでは、このアプリケーションのチャットやゲーム内での名前入力の機能のご利用が許可されていません。',
                        '계정에 이 애플리케이션의 채팅과 게임 안 이름 입력 기능을 이용할 권한이 없습니다.'),
             0xE59FA0: ('Dungeons & Dragons® ―ミスタラ英雄戦記―でShadow over Mystaraを一緒にプレイしませんか？',
                        'Dungeons & Dragons® ―미스타라 영웅전기―에서 Shadow over Mystara를 함께 플레이할까요?'),
             0xE5A500: ('Dungens & Dragons® -ミスタラ英雄戦記-で一緒に遊んだ',
                        'Dungens & Dragons® -미스타라 영웅전기-에서 함께함')}
    skip = {0x1296D80, 0x129738E}
    for off, (jp, ko) in UI102.items():
        j = jp.encode('utf-8'); k = ko.encode('utf-8')
        assert bytes(b[off:off + len(j) + 1]) == j + bytes(1), hex(off); assert len(k) <= len(j)
        b[off:off + len(j)] = k + bytes(len(j) - len(k))
    # 랭킹 기본 이름(1.00 0x149B184·0x14B8288, 레코드 16 B 중 이름 6 B = +2) — 1.02 는 같은 표 두 벌이 0x105E20C·0x2F93D58 에 있음
    #   (자리 짐작 +1ADAE80 이 틀려 «막힌 칸» → 직접 씀, 2026-11-15)
    for off in (0x105E20C, 0x2F93D58):
        for r in range(10):
            assert bytes(b[off + 16 * r + 8:off + 16 * r + 16]) == a0[0x14B8288 + 16 * r + 8:0x14B8288 + 16 * r + 16], (hex(off), r)
            b[off + 16 * r + 2:off + 16 * r + 8] = a1[0x14B8288 + 16 * r + 2:0x14B8288 + 16 * r + 8]
    skip |= {x for x, y in fail if 0x14B8288 <= x < 0x14B8328}
    rep.append('랭킹 기본 이름 = 1.02 두 벌(0x105E20C·0x2F93D58)에 직접 씀')
    fail = [f_ for f_ in fail if f_[0] not in skip]
    rep.append('1.02 UI 문구 %d줄은 1.02 자리에 직접 씀(바뀐 2줄 + 1.02 에만 있는 4줄)' % len(UI102))
    open(R('work', 'v102', 'build', 'report_port.txt'), 'w', encoding='utf-8').write('\n'.join(rep) + '\n')
    json.dump(port.plist, open(R('work', 'v102', 'build', 'ptrs.json'), 'w'))
    if not fail: open(R('work', 'v102', 'build', 'EBOOT.elf'), 'wb').write(b)
    else: print('⛔못 옮긴 구간이 남아 ELF 를 안 씀')
