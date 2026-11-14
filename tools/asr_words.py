# -*- coding: utf-8 -*-
r"""무비 단어 시각 받아쓰기(자막 시작을 실제 첫 단어에 맞추려고, 2026-11-14 하스피 «자막 시작이 너무 빠름»).
  word_timestamps=True · VAD 켬(음악 구간 건너뜀 → 30초 창 밀림 방지) → work/movie/NN_words.tsv(시작·끝·단어) + NN_ja2.tsv(문장)
  python(whisper-venv) tools/asr_words.py 00 01 02"""
import sys, os, wave
import numpy as np
from faster_whisper import WhisperModel
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def load(p):
    w = wave.open(p, 'rb'); a = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    return a.reshape(-1, w.getnchannels()).mean(1) if w.getnchannels() > 1 else a
m = WhisperModel('large-v3', device='cuda', compute_type='float16')
for n in sys.argv[1:]:
    a = load(os.path.join(ROOT, 'work', 'movie', n + '.wav'))
    segs, info = m.transcribe(a, language='ja', vad_filter=True, vad_parameters=dict(min_silence_duration_ms=300, speech_pad_ms=100),
                              beam_size=5, condition_on_previous_text=False, word_timestamps=True)
    W = open(os.path.join(ROOT, 'work', 'movie', n + '_words.tsv'), 'w', encoding='utf-8'); S = open(os.path.join(ROOT, 'work', 'movie', n + '_ja2.tsv'), 'w', encoding='utf-8')
    W.write('시작\t끝\t단어\n'); S.write('시작\t끝\t일본어\n')
    for s in segs:
        S.write('%.2f\t%.2f\t%s\n' % (s.start, s.end, s.text.strip())); S.flush()
        for w in (s.words or []): W.write('%.2f\t%.2f\t%s\n' % (w.start, w.end, w.word.strip()))
        W.flush()
    W.close(); S.close(); print('끝', n, flush=True)
