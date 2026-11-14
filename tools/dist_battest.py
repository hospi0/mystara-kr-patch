# -*- coding: utf-8 -*-
r"""배포 bat 시험 (2026-11-14): «& ( )» 든 임시 폴더에 원본을 깔고 적용 → 재적용(건너뜀) → 되돌리기, 단계마다 MD5 대조.
  readme 표의 [업데이트] = RPCS3 dev_hdd0 쪽, [디스크 1.02] = 디스크 쪽(1.02 용), 표시 없음 = 디스크 쪽.
  [디스크 1.02] 중 make_dist.SEED(디스크에 원래 없는 파일)는 처음에 없고, 되돌린 뒤에도 없어야 함.
  python tools/dist_battest.py 묶음이름   (임시 폴더 = %TEMP% 아래, 끝나면 지움 · bat 가 묶음 폴더에 만든 원본백업도 지움)"""
import os, sys, re, hashlib, shutil, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); import make_dist as M
BS = chr(92)
def md5(p): return hashlib.md5(open(p, 'rb').read()).hexdigest().upper()
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    pkg = os.path.join(ROOT, 'dist', sys.argv[1])
    t = open(os.path.join(pkg, 'readme.txt'), encoding='cp949').read()
    items = [({'[업데이트] ': 'upd', '[디스크 1.02] ': 'disk2'}.get(m.group(1), 'disk'), m.group(2).replace(BS, '/'), m.group(3), m.group(4))
             for m in re.finditer(r'^(\[(?:업데이트|디스크 1\.02)\] )?(\S+)\n    ([0-9A-F]{32}) -> ([0-9A-F]{32})', t, re.M)]
    root = tempfile.mkdtemp(prefix='mysbat_')
    try:
        game = os.path.join(root, 'D&D Mystara (Japan) & test', 'PS3_GAME')
        rp = os.path.join(root, 'rp & cs3 (x)'); upd = os.path.join(rp, 'dev_hdd0', 'game', 'BLJM61055')
        where = lambda k, rel: os.path.join(upd if k == 'upd' else game, *rel.split('/'))
        seeded = lambda k, rel: k == 'disk2' and rel in M.SEED
        for k, rel, a, b in items:
            if seeded(k, rel): continue
            src = M.upd_orig(rel) if k == 'upd' else M.orig_of(rel)
            dst = where(k, rel); os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy(src, dst); assert md5(dst) == a, rel
        if any(k == 'upd' for k, *_ in items): shutil.copy(M.upd_orig('PARAM.SFO'), os.path.join(upd, 'PARAM.SFO'))
        mark = os.path.join(game, 'USRDIR', 'nativePS3', 'game_data', 'dd21x.bin')      # bat 가 게임 폴더를 알아보는 파일(무비 묶음엔 없음)
        if not os.path.exists(mark): os.makedirs(os.path.dirname(mark), exist_ok=True); open(mark, 'wb').close()
        def state():
            out = ''
            for k, rel, a, b in items:
                p = where(k, rel)
                if not os.path.exists(p): out += '없'; continue
                h = md5(p); out += '새' if h == b else '원' if h == a else '?'
            return out
        def run(bat):
            r = subprocess.run(['cmd', '/c', os.path.join(pkg, bat), game, rp], stdin=subprocess.DEVNULL, capture_output=True)
            o = r.stdout.decode('cp949', 'replace')
            return [l.strip() for l in o.splitlines() if 'OK' in l or '[!]' in l]
        print('파일', len(items), '(처음에 없는 파일 %d)' % sum(1 for k, r, *_ in items if seeded(k, r)), '· 시험 폴더', root)
        print('적용 전  ', state())
        print(run('한글패치_적용.bat')); print('적용 뒤  ', state())
        print(run('한글패치_적용.bat')); print('재적용 뒤', state())
        print(run('되돌리기.bat')); print('되돌린 뒤', state())
    finally:
        shutil.rmtree(root, True)
        shutil.rmtree(os.path.join(pkg, '원본백업'), True)          # bat 가 묶음 폴더에 만든 백업(배포 폴더에 남지 않게)
if __name__ == '__main__':
    main()
