# -*- coding: utf-8 -*-
r"""자막 시각을 새 받아쓰기 문장 시각(work/movie/NN_ja2.tsv, asr_words.py · VAD)에 맞춤 (2026-11-14 하스피 «게임내용편 자막 시작이 너무 빠름»).
  줄마다: 시작 = [시작-0.15, 끝-0.2) 안 첫 단어 시작(없으면 그대로) · 끝 = 그 줄 단어 마지막 끝+0.4, 다음 줄 시작 넘지 않게, 최소 1.0초.
  retime(n) → [(시작, 끝, 한국어)]  (movie_sub.load_subs 가 부름)"""
import os, bisect
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); W = lambda *p: os.path.join(ROOT, 'work', 'movie', *p)
def rows(p):
    return [l.split('\t') for l in open(p, encoding='utf-8').read().split('\n')[1:] if l.count('\t') >= 2]
def retime(n, subs):
    p = W(n + '_ja2.tsv')
    if not os.path.exists(p): return subs
    seg = [(float(r[0]), float(r[1])) for r in rows(p)]
    out = []
    for s, e, t in subs:
        best = max(seg, key=lambda g: min(e, g[1]) - max(s, g[0]))
        ov = min(e, best[1]) - max(s, best[0])
        ns = max(s, best[0]) if ov > 0.3 else s                  # 시작은 늦추기만 — 가장 많이 겹치는 문장(VAD 로 잘린 실제 말) 시작
        out.append([ns, e, t])
    for i in range(len(out)):
        if i and out[i][0] < out[i - 1][0] + 0.3: out[i][0] = out[i - 1][0] + 0.3
    for i in range(len(out)):
        nxt = out[i + 1][0] if i + 1 < len(out) else 1e9
        out[i][1] = min(max(out[i][1], out[i][0] + 1.0), nxt)
    return [tuple(r) for r in out]
if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__))); import movie_sub
    for n in sys.argv[1:]:
        a = movie_sub.load_subs(n, raw=True); b = retime(n, a)
        d = [b[i][0] - a[i][0] for i in range(len(a))]
        print(n, '줄', len(a), '시작 늦춤 평균 %.2f 최대 %.2f · 당김 최대 %.2f' % (sum(d) / len(d), max(d), min(d)))
        for i in range(4): print('   %.2f→%.2f  %s' % (a[i][0], b[i][0], b[i][2]))
