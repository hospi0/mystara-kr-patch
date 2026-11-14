# -*- coding: utf-8 -*-
r"""번역(work/text/ko/{mys,tod}_ko.tsv = 번호→한국어)을 원문 TSV 에 채우고 «쓰는 순간» 규칙 검사 (2026-11-13).
  규칙(막음): ① 번호 누락 ② 원문 토큰({c18}{N0}{＊}{w..}{1E54}…) 다중집합이 같아야 ③ 줄 수 ≤ 원문
              (선택지·ＹＥＳ/ＮＯ·１．처럼 줄 자리가 커서와 묶인 글은 «같아야») ④ 줄 폭 ≤ 예산
              ⑤ 일본어(가나·한자) 남음 ⑥ 매크로 {N1~N9} 바로 뒤 받침 타는 조사 / {N0} 앞 낱말 받침 없음
  예산: 원문 최대 줄 > 14 → 그 값(엔딩·오프닝·아이템 메시지) / 원문 2줄+ 이고 최대 ≤ 10 → 그 값(좁은 말풍선) / 그 밖 14.
        폭 = 글자 수(태그 0, {N…}·글리프 태그 1). 말줄임: …… ... ・・・ → … 로 합친 뒤 잰다.
  출력: work/text/tsv_ko/{mys,tod}_NNN.tsv (번호·위치·JP·KO)
  python tools/ko_merge.py"""
import os, re, sys, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TAG = re.compile(r'\{[^}]*\}')
JP = re.compile('[぀-ヺヽ-ヿ一-鿿]')   # ・(30FB) ー(30FC) 는 부호로 허용
JOSA_BATCHIM = ('은', '이', '을', '과', '이여', '으로', '이라', '이야', '인가')
JOSA_ANY = ('는', '가', '를', '와', '은', '이', '을', '과', '로', '라')


def norm(s):
    s = re.sub(r'…{2,}', '…', s)
    s = re.sub(r'\.{3,}', '…', s)
    s = re.sub(r'・{2,}', '…', s)
    s = re.sub(r'…+', '…', s)
    return s


def width(line):
    n = 0
    for part in re.split(r'(\{[^}]*\})', line):
        if not part: continue
        if part.startswith('{'):
            t = part[1:-1]
            if t.startswith('N') or re.fullmatch(r'[0-9A-F]{4}', t): n += 1
        else: n += len(part)
    return n


def has_batchim(ch):
    o = ord(ch) - 0xAC00
    return 0 <= o < 11172 and o % 28 != 0


def check(no, jp, ko):
    errs = []; warn = []
    jl = jp.split('／'); kl = ko.split('／')
    if sorted(TAG.findall(jp)) != sorted(TAG.findall(ko)):
        errs.append('토큰 다름 원문%s 번역%s' % (sorted(TAG.findall(jp)), sorted(TAG.findall(ko))))
    fixed = bool(re.search(r'[ＡＢＣ]．|ＹＥＳ|Ｙｅｓ|[１２３４]．', jp))
    if fixed and len(kl) != len(jl): errs.append('줄 수 %d≠원문 %d(선택지)' % (len(kl), len(jl)))
    elif len(kl) > len(jl): errs.append('줄 수 %d>원문 %d' % (len(kl), len(jl)))
    jm = max(width(norm(x)) for x in jl)
    if jm > 14: bud = jm
    elif len(jl) >= 2 and jm <= 10: bud = jm
    else: bud = 14
    for i, x in enumerate(kl):
        w = width(x)
        if w > bud: errs.append('줄%d 폭 %d>%d 「%s」' % (i + 1, w, bud, x))
    if JP.search(TAG.sub('', ko)): errs.append('일본어 남음 「%s」' % JP.findall(TAG.sub('', ko)))
    for m in re.finditer(r'\{N([0-9])\}', ko):
        after = TAG.sub('', ko[m.end():])
        before = ko[:m.start()]
        if m.group(1) == '0':
            if after[:1] and after[:1] in '은이을과' and (not before or not has_batchim(before[-1])):
                errs.append('{N0} 앞 «%s» 받침 없음 + 조사 %s' % (before[-1:], after[:1]))
        else:
            if after[:1] in ('은', '는', '이', '가', '을', '를', '과', '와', '로', '라') and not after.startswith('로서'):
                errs.append('{N%s} 뒤 받침 타는 조사 «%s»' % (m.group(1), after[:2]))
    return errs, warn, bud


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print('규칙: 토큰 같음 · 줄 수 ≤ 원문(선택지는 같음) · 폭 ≤ 예산(14/좁은 풍선/넓은 원문) · 일본어 금지 · 매크로 뒤 조사')
    out = os.path.join(ROOT, 'work', 'text', 'tsv_ko'); os.makedirs(out, exist_ok=True)
    total_err = 0
    for pre in ('mys', 'tod'):
        ko = {}
        for ln in open(os.path.join(ROOT, 'work', 'text', 'ko', pre + '_ko.tsv'), encoding='utf-8').read().split('\n'):
            if ln.strip():
                a, b = ln.split('\t', 1); ko[a] = norm(b)
        for f in sorted(glob.glob(os.path.join(ROOT, 'work', 'text', 'tsv', pre + '_*.tsv'))):
            rows = open(f, encoding='utf-8').read().split('\n')
            res = [rows[0]]
            for ln in rows[1:]:
                if not ln: continue
                c = ln.split('\t')
                no, jp = c[0], c[2]
                if no not in ko:
                    print('⛔%s %s 번역 없음' % (pre, no)); total_err += 1; res.append(ln); continue
                errs, warn, bud = check(no, jp, ko[no])
                for e in errs: print('⛔%s %s %s' % (pre, no, e))
                total_err += len(errs)
                res.append('\t'.join([c[0], c[1], c[2], ko[no]]))
            open(os.path.join(out, os.path.basename(f)), 'w', encoding='utf-8', newline='\n').write('\n'.join(res) + '\n')
        extra = set(ko) - {ln.split('\t')[0] for f in glob.glob(os.path.join(ROOT, 'work', 'text', 'tsv', pre + '_*.tsv'))
                           for ln in open(f, encoding='utf-8').read().split('\n')[1:] if ln}
        if extra: print('⛔%s 원문에 없는 번호 %s' % (pre, sorted(extra))); total_err += 1
    print('오류 %d' % total_err)


if __name__ == '__main__':
    main()
