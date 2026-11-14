# -*- coding: utf-8 -*-
r"""무비 음성 받아쓰기(faster_whisper large-v3, 일본어) → work/movie/NN_ja.tsv(시작·끝·일본어) (2026-11-14).
  python(whisper-venv) tools/asr_movie.py 00 01 02"""
import sys, os, wave
import numpy as np
from faster_whisper import WhisperModel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p):
    w = wave.open(p, 'rb'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768; return a
m = WhisperModel('large-v3', device='cuda', compute_type='float16')
for n in sys.argv[1:]:
    a = load(os.path.join(ROOT, 'work', 'movie', n + '.wav'))
    segs, info = m.transcribe(a, language='ja', vad_filter=False, beam_size=5, condition_on_previous_text=False)
    with open(os.path.join(ROOT, 'work', 'movie', n + '_ja.tsv'), 'w', encoding='utf-8') as f:
        f.write('시작\t끝\t일본어\n')
        for s in segs: f.write('%.2f\t%.2f\t%s\n' % (s.start, s.end, s.text.strip())); f.flush()
    print('끝', n, flush=True)
