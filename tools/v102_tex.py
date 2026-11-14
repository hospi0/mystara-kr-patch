# -*- coding: utf-8 -*-
r"""1.02 에 새로 생긴 그림 글자 한글 (2026-11-14).
  ① options/setting2_LIN.tex(256x352 RGBA8, 온라인 일시정지 메뉴 글자 목록, 줄 간격 32) — texlabel 의 흰 꼴(224 + 그림자)
  ② gui.arc GUI\hostcondition\tex\difficulty0_ID(192x32 DXT5) «すべて» → «전부» (앞 아이콘 4개 그대로)
  ③ gui.arc GUI\changelog\changelog_ID_NOMIP·changelog2_ID_NOMIP(1920x1080 DXT1, 패치 1.01·1.02 업데이트 내역)
     글자 화소(밝음)만 지우고 둘레 판으로 메움(inpaint) → 같은 줄 자리·시작 x 에 Noto Sans KR · 바뀐 4x4 블록만 DXT1 다시 인코딩.
  미리보기는 «만든 tex 파일을 다시 풀어서» 원본|한글 → work/v102/미리보기_그림글자_N차/
  python tools/v102_tex.py preview [차수]   /   build(빌드 반영: v102_gui 가 부름)"""
import os, sys, re, json, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import texio, texlabel, mttex, mtarc
R = lambda *p: os.path.join(ROOT, *p)
PLAIN = R('work', 'v102', 'plain'); BS = chr(92)
PUNCT_SP = re.compile(r'([,.!?…‼⁉、。，．！？：；:;～~])[ 　]+')
FONT = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'
sp = lambda s: PUNCT_SP.sub(lambda m: m.group(1), s)

# ---------------- ① setting2 ----------------
S2 = [  # (상자 번호, 한글, 맞춤)  상자 = texlabel.detect_grid(줄 간격 32)
    (0, '이 게임에서 나갑니다', 'l'), (1, '보이스 채팅', 'l'), (2, '보이스 채팅 음량', 'l'), (3, '음소거 전환', 'l'),
    (4, '강퇴', 'l'), (5, 'SELECT 버튼을 계속 누르면', 'l'), (6, '이 게임에서 나갈 수 있습니다', 'c'),
    (9, '통신 중입니다.', 'l'), (10, '잠시 기다려 주세요.', 'l')]
S2_HOLD = '길게 눌러 나가기'          # 7번 줄(SELECT 아이콘 오른쪽, 어두운 번짐 위)
def blend(a, rgba, X0, Y0):
    H, W = a.shape[:2]; h_, w_ = rgba.shape[:2]
    ys0, xs0 = max(0, -Y0), max(0, -X0); ye, xe = min(h_, H - Y0), min(w_, W - X0)
    dst = a[Y0 + ys0:Y0 + ye, X0 + xs0:X0 + xe].astype(np.float32); s = rgba[ys0:ye, xs0:xe]
    sa = s[..., 3:4] / 255; da = dst[..., 3:4] / 255; oa = sa + da * (1 - sa)
    orgb = (s[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-6)
    a[Y0 + ys0:Y0 + ye, X0 + xs0:X0 + xe] = np.concatenate([orgb, oa * 255], -1).clip(0, 255).astype(np.uint8)
def setting2(a):
    import cv2
    a = a.copy(); H, W = a.shape[:2]; P = 32
    bx = texlabel.detect_grid(a, P)
    hs = []
    for k, t, al in S2:
        x0, y0, x1, y1, r = bx[k]; f = a[y0:y1, x0:x1, 3] > 200; ys = np.nonzero(f.any(1))[0]; hs.append(ys.max() - ys.min() + 1)
    INK = int(sorted(hs)[len(hs) // 2] * 0.9)
    log = ['setting2 글자 높이 %d' % INK]
    for k, t, al in S2:
        x0, y0, x1, y1, r = bx[k]
        a[max(r * P, y0 - 3):min((r + 1) * P, y1 + 3), max(0, x0 - 3):min(W, x1 + 3)] = 0
        maxw = W - 4 - (x0 if al == 'l' else 2)
        m = texlabel.text_mask(sp(t), INK, maxw); rgba, pad = texlabel.styled(m, 'white')
        tx = x0 if al == 'l' else (W - m.shape[1]) // 2
        ty = r * P + (P - (INK + 3)) // 2 - 2
        if m.shape[1] >= maxw: log.append('압축 %s' % t)
        blend(a, rgba, tx - pad, ty - pad)
    # 7번 줄: 아이콘(x<84) 오른쪽 글자만 — 밝은 획을 지우고 번짐(어두운 반투명)은 inpaint 로 메움
    y0, y1, x0, x1 = 232, 280, 84, 230
    sub = a[y0:y1, x0:x1].astype(np.float32)
    lum = sub[..., :3].mean(2)
    m = ((lum > 70) & (sub[..., 3] > 60)).astype(np.uint8)
    m = cv2.dilate(m, np.ones((5, 5), np.uint8))
    for c in range(4):
        ch = np.ascontiguousarray(sub[..., c]).astype(np.uint8)
        sub[..., c] = cv2.inpaint(ch, m, 4, cv2.INPAINT_TELEA)
    a[y0:y1, x0:x1] = sub.clip(0, 255).astype(np.uint8)
    mk = texlabel.text_mask(S2_HOLD, INK, W - 4 - 88); rgba, pad = texlabel.styled(mk, 'white')
    blend(a, rgba, 88 - pad, 240 - pad)
    if mk.shape[1] >= W - 4 - 88: log.append('압축 %s' % S2_HOLD)
    return a, log

# ---------------- ② difficulty0 ----------------
def difficulty(a):
    a = a.copy()
    a[:, 90:192] = 0
    m = texlabel.text_mask('전부', 19, 96); rgba, pad = texlabel.styled(m, 'white')
    blend(a, rgba, 95 - pad, 5 - pad)
    return a, ['difficulty «전부»']

# ---------------- ②-2 로비 «이름 입력» 아이콘 «名» → «이름»(가로, 하스피 2026-11-14 A안) ----------------
NAME_ICON = (925, 226, 953, 253)          # roomlist common1_ID 안 «名» 칸(x928~950·y228~252) + 여유 — 오른쪽 x957~ 은 프로필 틀이라 안 건드림
def name_icon(im):
    from PIL import ImageFont as IF
    x0, y0, x1, y1 = NAME_ICON; W, H = x1 - x0, y1 - y0; S = 6
    f = IF.truetype(FONT, 60)
    try: f.set_variation_by_axes([900])
    except Exception: pass
    l, t, r, b = f.getbbox('이름'); tw, th = r - l, b - t
    T = Image.new('L', (tw + 4, th + 4), 0); ImageDraw.Draw(T).text((2 - l, 2 - t), '이름', 255, font=f)
    sc = min(24 * S / tw, 13 * S / th)
    T = T.resize((max(1, int((tw + 4) * sc / S)), max(1, int((th + 4) * sc / S))), Image.LANCZOS)
    m = np.zeros((H, W)); h, w = T.size[1], T.size[0]; yy = (H - h) // 2; xx = (W - w) // 2 - 1
    m[yy:yy + h, xx:xx + w] = np.array(T) / 255.; m = np.clip(m * 1.25, 0, 1)
    sh = np.zeros_like(m); sh[2:, 2:] = m[:-2, :-2]                                   # 원본처럼 오른쪽 아래 검은 그림자
    sh = np.maximum(sh, np.pad(m, ((1, 0), (1, 0)))[:-1, :-1]); sh = np.maximum(sh, np.pad(m, ((0, 0), (1, 0)))[:, :-1])
    alpha = np.clip(m + sh * (1 - m), 0, 1)
    out = np.zeros((H, W, 4)); out[..., :3] = (255 * m / np.maximum(alpha, 1e-6))[..., None] * (m > 0)[..., None]; out[..., 3] = alpha * 255
    a = im.copy(); a[y0:y1, x0:x1] = out.clip(0, 255).astype(np.uint8)
    return a, ['로비 이름 아이콘 «이름»']

# ---------------- ③ changelog ----------------
CL = {
 'changelog_ID_NOMIP': ('패치 Ver.1.01 업데이트 내역', [
   (294, 201, True, '네트워크 플레이에 대응했습니다.'),
   (340, 233, False, '전국의 플레이어와 네트워크로 협력 플레이를 즐길 수 있습니다.'),
   (390, 265, True, '네트워크 플레이 중에는 R3 버튼으로 온라인 ID 표시 위치를 바꿀 수 있습니다.'),
   (461, 201, True, '하이 스코어를 업로드해 전국의 플레이어와 점수를 겨룰 수 있습니다.'),
   (511, 236, False, '『던전 앤 드래곤 타워 오브 둠』, 『던전 앤 드래곤 섀도 오버 미스타라』'),
   (559, 234, False, '각각 종합 랭킹과 주간 랭킹이 있습니다. 주간 랭킹 점수 초기화는'),
   (608, 233, False, '매주 금요일 오전 3시쯤입니다. 시간은 조금 앞뒤로 달라질 수 있으니 주의해 주세요.'),
   (681, 201, True, '로컬 플레이 중 일시 정지 메뉴에 「플레이어 옵션」 항목이 추가되었습니다.'),
   (755, 201, True, '「설명서」에 네트워크 플레이 설명이 추가되었습니다.'),
   (803, 234, False, '메인 메뉴의 설명서에서 확인할 수 있습니다.')]),
 'changelog2_ID_NOMIP': ('패치 Ver.1.02 업데이트 내역', [
   (294, 201, True, '「함께 플레이한 플레이어」에 온라인 ID가 등록되게 되었습니다.'),
   (348, 233, False, '네트워크 플레이에서 함께 플레이한 플레이어의 온라인 ID가'),
   (397, 234, False, 'XMB™의 친구 카테고리에 있는 「함께 플레이한 플레이어」에 등록됩니다.'),
   (487, 201, True, '네트워크 플레이에서 게임을 나갈 수 있게 되었습니다.'),
   (546, 233, False, '중간 참가로 게임을 시작하기 전, 그리고 컨티뉴하지 않았을 때에 한해'),
   (594, 234, False, 'SELECT 버튼을 길게 눌러 언제든 나갈 수 있습니다.'),
   (686, 201, True, '게임 중 버그를 고쳤습니다.')])}
LH = 31                                    # 원문 줄 높이(잉크 띠)
def kf(px, w=500):
    f = ImageFont.truetype(FONT, px)
    try: f.set_variation_by_axes([w])
    except Exception: pass
    return f
def fit_font(ink, w=500):
    for px in range(12, 80):
        f = kf(px, w); l, t, r, b = f.getbbox('한')
        if b - t >= ink: return f
    return f
def changelog(rgb, name):
    import cv2
    g = rgb.astype(np.int32); lum = g.mean(2); H, W = lum.shape
    title, lines = CL[name]
    col = np.median(g[lum > 200], 0).astype(int)          # 원문 글자 색
    mask = np.zeros((H, W), np.uint8)
    # 제목 칸 안쪽(테두리 152..818 × 168..257 은 남김)
    tb = (lum > 150); tb[:, :170] = False; tb[:, 800:] = False; tb[:182] = False; tb[244:] = False
    mask |= tb.astype(np.uint8)
    keep_to = {}
    for y, x, keep, t in lines:
        band = lum[y - 2:y + LH + 2] > 130
        xs = np.nonzero(band.any(0))[0]; xs = xs[xs >= x - 4]
        st = x - 4
        if keep:                                             # 첫 글자(● ※)는 원본 그대로
            runs = np.split(xs, np.nonzero(np.diff(xs) > 2)[0] + 1); st = int(runs[0].max()) + 2; keep_to[y] = st   # 첫 글자 끝 + 1px(뒤 글자 왼쪽 획 안 남게)
        sub = band.copy(); sub[:, :st] = False; sub[:, 1740:] = False      # 오른쪽 판 테두리(x≈1765~) 보호
        mask[y - 2:y + LH + 2] |= sub.astype(np.uint8)
    m2 = cv2.dilate(mask, np.ones((11, 11), np.uint8))
    for y, x, keep, t in lines:                                     # 남기는 첫 글자도 메움 재료에서 뺌(밝은 번짐 방지) → 아래서 원본으로 되돌림
        if keep: m2[y - 6:y + LH + 6, x - 8:keep_to[y]] = 1                # 글자 둘레 어두운 테두리(2~3px)까지
    out = cv2.inpaint(rgb.astype(np.uint8), m2, 6, cv2.INPAINT_TELEA)
    for y, x, keep, t in lines:                                     # 남기는 첫 글자(● ※)는 원본 화소로 되돌림(지우기 번짐이 오른쪽을 깎음)
        if keep: out[y - 6:y + LH + 6, x - 8:keep_to[y]] = rgb[y - 6:y + LH + 6, x - 8:keep_to[y]]
    im = Image.fromarray(out); d = ImageDraw.Draw(im)
    fb = fit_font(27, 700); ft = fit_font(43, 800)                   # 원문 본문 한자 31px·굵게, 제목 49px
    ref_t = fb.getbbox('한')[1]
    fillc = tuple(int(c) for c in col)
    for y, x, keep, t in lines:
        tx = keep_to.get(y, x) + (6 if keep else 0)
        tt = sp(t); w_ = d.textlength(tt, font=fb)
        f_ = fb
        if tx + w_ > 1730: f_ = fit_font(int(27 * (1730 - tx) / w_), 700)
        oy = y + 2 - ref_t
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1), (2, 2)): d.text((tx + dx, oy + dy), tt, (9, 9, 9), font=f_)   # 원문처럼 어두운 테두리
        d.text((tx, oy), tt, fillc, font=f_)
    rt = ft.getbbox('한')[1]; tw = d.textlength(title, font=ft)
    tx = 196; ty = 192 - rt
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1), (2, 2)): d.text((tx + dx, ty + dy), title, (9, 9, 9), font=ft)
    d.text((tx, ty), title, fillc, font=ft)
    new = np.array(im)
    ch = np.abs(new.astype(int) - rgb.astype(int)).sum(2) > 0
    return new, ch, ['%s 글자색 %s' % (name, fillc)]

# DXT1 인코더(바뀐 블록만): 주축 양 끝 → 565, 4색 모드
def enc_dxt1_block(blk):
    p = blk.reshape(-1, 3).astype(np.float32); mu = p.mean(0); c = p - mu
    if np.abs(c).max() < 1e-3: e0 = e1 = mu
    else:
        u = np.linalg.svd(c, full_matrices=False)[2][0]; pr = c @ u
        e0 = mu + u * pr.max(); e1 = mu + u * pr.min()
    def q(e):
        r, g, b = [int(round(max(0, min(255, v)))) for v in e]
        return ((r * 31 + 127) // 255) << 11 | ((g * 63 + 127) // 255) << 5 | ((b * 31 + 127) // 255)
    def dq(v): return np.array([((v >> 11) & 31) * 255 / 31, ((v >> 5) & 63) * 255 / 63, (v & 31) * 255 / 31], np.float32)
    a0, a1 = q(e0), q(e1)
    if a0 < a1: a0, a1 = a1, a0
    if a0 == a1:
        return struct.pack('<HHI', a0, a1, 0)
    c0, c1 = dq(a0), dq(a1); pal = np.stack([c0, c1, (2 * c0 + c1) / 3, (c0 + 2 * c1) / 3])
    idx = ((p[:, None, :] - pal[None]) ** 2).sum(2).argmin(1); bits = 0
    for i, v in enumerate(idx): bits |= int(v) << (2 * i)
    return struct.pack('<HHI', a0, a1, bits)
def write_dxt1(tex, rgb, changed):
    i = mttex.info(tex); W, H, off = i['W'], i['H'], i['off']; t = bytearray(tex); n = 0
    by, bx = np.nonzero(changed[:H // 4 * 4, :W // 4 * 4].reshape(H // 4, 4, W // 4, 4).any((1, 3)))
    for y, x in zip(by.tolist(), bx.tolist()):
        o = off + (y * (W // 4) + x) * 8
        t[o:o + 8] = enc_dxt1_block(rgb[y * 4:y * 4 + 4, x * 4:x * 4 + 4]); n += 1
    return bytes(t), n

# ---------------- 묶기 ----------------
def make(outdir):
    """→ {상대 경로·arc 항목: 새 바이트}, 로그. 그림은 1.02 원본(work/v102/plain)에서"""
    import tempfile, shutil
    res = {}; log = []
    src = os.path.join(PLAIN, 'options', 'setting2_LIN.tex'); a, _ = texio.load(src)
    b, lg = setting2(a); log += lg
    p = os.path.join(outdir, 'setting2_LIN.tex'); texio.save(src, p, b); res['options/setting2_LIN.tex'] = open(p, 'rb').read()
    arc = {n: d for n, th, d, fl in mtarc.entries(os.path.join(PLAIN, 'arc', 'gui.arc'))}
    nm = 'GUI' + BS + 'hostcondition' + BS + 'tex' + BS + 'difficulty0_ID'
    s = os.path.join(outdir, 'difficulty0_ID.tex'); open(s, 'wb').write(arc[nm]); a, _ = texio.load(s)
    b, lg = difficulty(a); log += lg
    p = os.path.join(outdir, 'difficulty0_ID_ko.tex'); texio.save(s, p, b); res[nm] = open(p, 'rb').read()
    nm = 'GUI' + BS + 'roomlist' + BS + 'tex' + BS + 'common1_ID'
    s = os.path.join(outdir, 'common1_ID.tex'); open(s, 'wb').write(arc[nm]); a, _ = texio.load(s)
    b, lg = name_icon(a); log += lg
    p = os.path.join(outdir, 'common1_ID_ko.tex'); texio.save(s, p, b)
    # 다시 압축한 것 중 «이름» 칸이 걸친 DXT5 4x4 블록만 원본에 갈아 끼움(다른 아이콘은 원본 바이트 그대로 — 전체 재압축은 화소 4천 개가 미세하게 바뀜)
    o_, n_ = bytearray(arc[nm]), open(p, 'rb').read(); inf = mttex.info(o_); W_, off = inf['W'], inf['off']; assert inf['fmt'] == 0x17
    x0, y0, x1, y1 = NAME_ICON
    for by in range(y0 // 4, (y1 + 3) // 4):
        for bx in range(x0 // 4, (x1 + 3) // 4):
            q = off + (by * (W_ // 4) + bx) * 16; o_[q:q + 16] = n_[q:q + 16]
    res[nm] = bytes(o_)
    for n in CL:
        nm = 'GUI' + BS + 'changelog' + BS + n
        s = os.path.join(outdir, n + '.tex'); open(s, 'wb').write(arc[nm])
        im, _ = mttex.load(s); rgb = np.array(im.convert('RGB'))
        new, ch, lg = changelog(rgb, n); log += lg
        t, k = write_dxt1(arc[nm], new, ch); res[nm] = t; log.append('%s DXT1 블록 %d 다시 인코딩' % (n, k))
    return res, log

def preview(no):
    import tempfile, shutil
    od = R('work', 'v102', '미리보기_그림글자_%d차' % no); os.makedirs(od, exist_ok=True)
    td = tempfile.mkdtemp()
    try:
        res, log = make(td)
        def rd(data, fmt):
            p = os.path.join(td, '_r.tex'); open(p, 'wb').write(data)
            if fmt == 'dxt1': return np.array(mttex.load(p)[0].convert('RGBA'))
            return texio.load(p)[0]
        def onbg(x, s):
            im = Image.fromarray(x).convert('RGBA'); bg = Image.new('RGBA', im.size, (40, 40, 48, 255)); bg.alpha_composite(im)
            return bg.resize((im.width * s, im.height * s), Image.NEAREST).convert('RGB')
        def pair(o, n, s, path, vertical=False):
            A, B = onbg(o, s), onbg(n, s)
            if vertical: c = Image.new('RGB', (A.width, A.height * 2 + 8), (200, 200, 200)); c.paste(A, (0, 0)); c.paste(B, (0, A.height + 8))
            else: c = Image.new('RGB', (A.width * 2 + 8, A.height), (200, 200, 200)); c.paste(A, (0, 0)); c.paste(B, (A.width + 8, 0))
            c.save(path)
        o, _ = texio.load(os.path.join(PLAIN, 'options', 'setting2_LIN.tex'))
        pair(o, rd(res['options/setting2_LIN.tex'], 'rgba'), 3, os.path.join(od, '3_온라인_일시정지메뉴_원본_한글_x3.png'))
        arc = {nm: d for nm, th, d, fl in mtarc.entries(os.path.join(PLAIN, 'arc', 'gui.arc'))}
        nm = 'GUI' + BS + 'hostcondition' + BS + 'tex' + BS + 'difficulty0_ID'
        pair(rd(arc[nm], 'rgba'), rd(res[nm], 'rgba'), 4, os.path.join(od, '4_난이도_전부_원본_한글_x4.png'), True)
        for k, n in enumerate(CL, 1):
            nm = 'GUI' + BS + 'changelog' + BS + n
            pair(rd(arc[nm], 'dxt1'), rd(res[nm], 'dxt1'), 1, os.path.join(od, '%d_업데이트내역_1.0%d_원본_한글.png' % (k, k)), True)
        print('\n'.join(log)); print(od)
    finally:
        shutil.rmtree(td, True)
if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    if sys.argv[1] == 'preview': preview(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
