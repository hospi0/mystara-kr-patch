# -*- coding: utf-8 -*-
r"""바깥 메뉴 글꼴(GUI/font/Font.gfd + Font_00_ID.tex 2048² DXT5) 한글 (2026-11-14).
  GFD: 머리 0x46 B + 항목 3331 × 16 B = (코드 u32, 위치 u32[이미지<<24 | x<<12 | y], 크기 u32[w<<12 | h], 진행 u32).
  아틀라스: 흰 RGB + 알파(글자 모양). 한자 칸 28×36, 잉크 2~27행.
  방식: 번역에 안 쓰는 한자 항목의 코드를 한글(과 없는 부호)로 바꾸고 그 칸에 Noto Sans KR 로 다시 그림 → 코드 순 정렬.
  python tools/gui_font.py 번역.tsv… → work/gui/out/Font.gfd · Font_00_ID.tex · 미리보기 work/gui/preview_font.png"""
import os, sys, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import mttex, gmd
R = lambda *p: os.path.join(ROOT, *p)
FONT = r'C:\Windows\Fonts\NotoSansKR-VF.ttf'; WGHT = 600; ADV = 27
def entries(b):
    n = struct.unpack('>I', b[0x1C:0x20])[0]; st = len(b) - n * 16
    return st, [list(struct.unpack('>4I', b[st + i * 16:st + i * 16 + 16])) for i in range(n)]
def rect(e):
    return (e[1] >> 12) & 0xFFF, e[1] & 0xFFF, (e[2] >> 12) & 0xFFF, e[2] & 0xFFF
def bottom_ellipsis(w, h, top, bot):
    a = np.zeros((h, w), np.uint8); y = bot - 3
    for k in range(3):
        x = 3 + k * 8; a[y:y + 4, x:x + 4] = 255
    return a
class Glyphs:
    def __init__(self):
        self.f = ImageFont.truetype(FONT, 27)
        try: self.f.set_variation_by_axes([WGHT])
        except Exception: pass
        # 크기 맞춤: «한» 잉크 높이가 25px 이 되게
        for size in range(22, 34):
            f = ImageFont.truetype(FONT, size)
            try: f.set_variation_by_axes([WGHT])
            except Exception: pass
            l, t, r, b = f.getbbox('한')
            if b - t >= 26: break
        self.f = f; l, t, r, b = f.getbbox('한'); self.top = t
    def draw(self, ch, w=28, h=36):
        if ch == '…': return bottom_ellipsis(w, h, 2, 27)
        im = Image.new('L', (w, h), 0); d = ImageDraw.Draw(im)
        l, t, r, b = self.f.getbbox(ch)
        x = (w - (r - l)) // 2 - l
        d.text((x, 1 - self.top), ch, 255, font=self.f)
        return np.array(im)
def enc_alpha(blk):
    """4x4 알파 → DXT5 알파 8바이트(작은 끝)"""
    a = blk.reshape(-1).astype(int); a0, a1 = int(a.max()), int(a.min())
    if a0 == a1: return bytes([a0, a1]) + b'\0' * 6
    lv = [a0, a1] + [((7 - k) * a0 + k * a1) // 7 for k in range(1, 7)]
    idx = [min(range(8), key=lambda j: abs(lv[j] - v)) for v in a]
    bits = 0
    for i, v in enumerate(idx): bits |= v << (3 * i)
    return bytes([a0, a1]) + bits.to_bytes(6, 'little')
WHITE_COLOR = bytes([0xFF, 0xFF, 0xFF, 0xFF, 0, 0, 0, 0])   # c0=c1=흰색, 인덱스 0
def put_cell(tex, off, W, x, y, A):
    """A(h×w 알파)를 아틀라스 (x,y)에 — x·y·크기는 4 배수 가정이 아니므로 블록 단위로 원래 알파와 합쳐 다시 인코딩"""
    h, w = A.shape
    bx0, by0, bx1, by1 = x // 4, y // 4, (x + w + 3) // 4, (y + h + 3) // 4
    return (bx0, by0, bx1, by1)
def build(tsvs, out_dir):
    b = bytearray(open(R('work', 'orig', 'GUI', 'font', 'Font.gfd'), 'rb').read())
    t = bytearray(open(R('work', 'orig', 'GUI', 'font', 'Font_00_ID.tex'), 'rb').read())
    info = mttex.info(t); W, H, off = info['W'], info['H'], info['off']
    im, _ = mttex.load(R('work', 'orig', 'GUI', 'font', 'Font_00_ID.tex')); A = np.array(im)[..., 3].copy()
    st, ents = entries(b); have = {e[0] for e in ents}
    texts = [s for p in tsvs for s in gmd.load_tsv(p)]
    used = set(''.join(texts))
    need = sorted(c for c in used if ord(c) not in have and c not in '\r\n')
    spare = [e for e in ents if 0x4E00 <= e[0] <= 0x9FFF and chr(e[0]) not in used]
    assert len(spare) >= len(need), (len(spare), len(need))
    G = Glyphs(); dirty = set()
    redraw = [e for e in ents if e[0] == 0x2026 and '…' in used]          # 기존 … 칸은 바닥 점으로 다시
    for ch, e in list(zip(need, spare)) + [(chr(e[0]), e) for e in redraw]:
        x, y, w, h = rect(e)
        A[y:y + h, x:x + w] = G.draw(ch, w, h)
        e[0] = ord(ch)
        if 0xAC00 <= e[0] <= 0xD7A3: e[3] = (e[3] & 0x000FFFFF) | (ADV << 20)   # 한글 진행폭
        for by in range(y // 4, (y + h + 3) // 4):
            for bx in range(x // 4, (x + w + 3) // 4): dirty.add((bx, by))
    # DXT5 다시 인코딩(바뀐 블록만) — 블록 순서 = 행 우선 선형(mttex 가 PIL bcn 으로 그대로 풂)
    for bx, by in dirty:
        o = off + (by * (W // 4) + bx) * 16
        t[o:o + 16] = enc_alpha(A[by * 4:by * 4 + 4, bx * 4:bx * 4 + 4]) + WHITE_COLOR
    ents.sort(key=lambda e: e[0])
    for i, e in enumerate(ents): b[st + i * 16:st + i * 16 + 16] = struct.pack('>4I', *e)
    os.makedirs(out_dir, exist_ok=True)
    open(os.path.join(out_dir, 'Font.gfd'), 'wb').write(b); open(os.path.join(out_dir, 'Font_00_ID.tex'), 'wb').write(t)
    return need, len(spare)
def preview(out_dir, text, path):
    """새 GFD·아틀라스로 문장을 그려 봄(진행폭 = 칸 폭)"""
    b = open(os.path.join(out_dir, 'Font.gfd'), 'rb').read(); st, ents = entries(b); m = {e[0]: e for e in ents}
    im, _ = mttex.load(os.path.join(out_dir, 'Font_00_ID.tex')); A = np.array(im)[..., 3]
    lines = text.split('\n'); Wd = 1400; can = np.zeros((40 * len(lines) + 8, Wd), np.uint8)
    for li, ln in enumerate(lines):
        x = 4
        for ch in ln:
            e = m.get(ord(ch))
            if not e: x += 14; continue
            gx, gy, w, h = rect(e); adv = (e[3] >> 20) & 0xFFF or w
            if x + w < Wd: can[li * 40 + 4:li * 40 + 4 + h, x:x + w] = np.maximum(can[li * 40 + 4:li * 40 + 4 + h, x:x + w], A[gy:gy + h, gx:gx + w])
            x += adv
    rgb = np.stack([can] * 3, -1); bg = np.array([30, 40, 70], np.uint8)
    out = (bg * (1 - can[..., None] / 255) + 255 * (can[..., None] / 255)).astype(np.uint8)
    Image.fromarray(out).save(path)
if __name__ == '__main__':
    out = R('work', 'gui', 'out')
    need, ns = build([R('work', 'gui', 'common_ko.tsv')], out)
    print('새 글자', len(need), '/ 쓸 수 있는 한자 칸', ns, '·', ''.join(need)[:80])
    preview(out, '갤러리　옵션　설명서　크레딧　저장\n「던전 앤 드래곤 섀도 오버 미스타라」를 플레이합니다\n게임 화면을 매끄럽게 표시할지 설정합니다\n랭킹을 받고 있습니다…\n메인 캐릭터 일러스트 † 클레릭　ABC 123', R('work', 'gui', 'preview_font.png'))
