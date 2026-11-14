# -*- coding: utf-8 -*-
r"""배포 묶음 (2026-11-14) — D&D 미스타라 영웅전기 (PS3 일본판 BLJM61055) 한글 패치
  dist/MystaraEiyuuSenki_PS3_KR_v0.9/        본편(EBOOT·글꼴·그림·메뉴 등 20개)
  dist/MystaraEiyuuSenki_PS3_KR_v0.9_Movie/  무비 갤러리 대담 영상 3편 자막(큼, 선택)
  각 묶음 = patch\<경로 _ 로 바꾼 이름>.xdelta + xdelta.exe + readme.txt + 한글패치_적용.bat + 되돌리기.bat (+ zip)
  xdelta 원본 = work/orig·work/orig_install(프로젝트 시작 때 뜬 원본 사본), 새것 = 설치된 게임 폴더 파일.
  만들고 나서 «원본에 적용 → 새것과 바이트 동일» 전수 되짚기.
  규칙: MD5 대문자 · 한국어 문서·bat CP949(CRLF) · 버전 v0.9 · bat 의 if 블록 안 echo 에 괄호 금지.
  python tools/make_dist.py"""
import hashlib, os, shutil, subprocess, sys, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
R = lambda *p: os.path.join(ROOT, *p)
VER = 'v0.92'
XDELTA = r'C:\claude\utils\xdelta.exe'
GAME = r'D:\hospi\rpcs3\games\Dungeons & Dragons - Mystara Eiyuu Senki (Japan)\PS3_GAME'
TID = 'BLJM61055'
MAIN = ['ICON0.PNG', 'USRDIR/EBOOT.BIN',
        'USRDIR/nativePS3/GUI/font/Font.gfd', 'USRDIR/nativePS3/GUI/font/Font_00_ID.tex', 'USRDIR/nativePS3/GUI/message/common_jpn.gmd',
        'USRDIR/nativePS3/arc/gui.arc', 'USRDIR/nativePS3/contents/ICON0.PNG',
        'USRDIR/nativePS3/game_data/dd10.bin', 'USRDIR/nativePS3/game_data/dd11x.bin', 'USRDIR/nativePS3/game_data/dd21x.bin',
        'USRDIR/nativePS3/game_data/dd22.bin', 'USRDIR/nativePS3/game_data/warning_jp.tex',
        'USRDIR/nativePS3/game_texture/copy_announce_NOMIP.tex',
        'USRDIR/nativePS3/movie/00_ID_THUM.tex', 'USRDIR/nativePS3/movie/01_ID_THUM.tex', 'USRDIR/nativePS3/movie/02_ID_THUM.tex',
        'USRDIR/nativePS3/options/chpt_title0_LIN.tex', 'USRDIR/nativePS3/options/descripter0_LIN.tex',
        'USRDIR/nativePS3/options/record0_LIN.tex', 'USRDIR/nativePS3/options/setting1_LIN.tex',
        'TROPDIR/NPWR04685_00/TROPHY.TRP']                # 트로피 한글(2026-11-15, tools/trophy_ko.py)
MOVIE = ['USRDIR/nativePS3/movie/interview/%02d.pam' % i for i in range(3)]
# 1.02 업데이트(dev_hdd0\game\BLJM61055)가 덮는 파일 — 1.02 묶음은 디스크 쪽에서 이것들을 빼고, 업데이트 폴더 쪽에 1.02용을 넣음
OVERRIDDEN = {'USRDIR/EBOOT.BIN', 'USRDIR/nativePS3/GUI/font/Font.gfd', 'USRDIR/nativePS3/GUI/font/Font_00_ID.tex',
              'USRDIR/nativePS3/GUI/message/common_jpn.gmd', 'USRDIR/nativePS3/arc/gui.arc'}
UPD = ['USRDIR/EBOOT.BIN', 'USRDIR/nativePS3/GUI/font/Font.gfd', 'USRDIR/nativePS3/GUI/font/Font_00_ID.tex',
       'USRDIR/nativePS3/GUI/message/common_jpn.gmd', 'USRDIR/nativePS3/arc/gui.arc', 'USRDIR/nativePS3/options/setting2_LIN.tex']
def new_of(rel):
    """새것 = 빌드 폴더(2026-11-14 v0.91 부터. 설치 폴더는 하스피가 원본으로 다시 깔기도 해서 안 믿음)"""
    if rel.startswith('TROPDIR/'): return R('work', 'trophy', 'build', 'TROPHY.TRP')
    if rel == 'ICON0.PNG': return R('work', 'build', 'ICON0.PNG')
    if rel == 'USRDIR/EBOOT.BIN': return R('work', 'build', 'EBOOT.BIN')
    sub = rel.split('nativePS3/', 1)[1]
    if sub.startswith('game_data/dd'): return R('work', 'build', sub.split('/')[-1])
    return R('work', 'build', *sub.split('/'))
def upd_orig(rel): return R('work', 'v102', 'orig_hdd0', *rel.split('/'))
# ★1.02 은 부팅 때 «업데이트 확인» 스레드와 «자원 읽기» 스레드가 경쟁 — 읽기가 먼저면 업데이트 폴더를 건너뛰고 디스크 쪽을 읽음
#  (2026-11-14 하스피 실기 5번 중 3번 멈춤: 디스크에 setting2 가 없어 읽기 실패). → 디스크 쪽에도 같은 1.02 한글 파일(껍질 없는 평문)을 둠.
DISK102 = ['USRDIR/nativePS3/GUI/font/Font.gfd', 'USRDIR/nativePS3/GUI/font/Font_00_ID.tex', 'USRDIR/nativePS3/GUI/message/common_jpn.gmd',
           'USRDIR/nativePS3/arc/gui.arc', 'USRDIR/nativePS3/options/setting2_LIN.tex']
SEED = {'USRDIR/nativePS3/options/setting2_LIN.tex'}     # 디스크에 원래 없는 파일 — bat 가 업데이트 폴더의 1.02 원본을 복사해 와서 패치
def disk102_new(rel): return R('work', 'v102', 'build', 'disk', *rel.split('/'))
def disk102_orig(rel): return upd_orig(rel) if rel in SEED else orig_of(rel)
def upd_new(rel):
    if rel == 'USRDIR/EBOOT.BIN': return R('work', 'v102', 'build', 'EBOOT.elf')
    return R('work', 'v102', 'build', 'hdd0', *rel.split('/'))
def orig_of(rel):
    if rel.startswith('TROPDIR/'): return R('work', 'trophy', 'orig', 'TROPHY.TRP')
    sub = rel.split('nativePS3/', 1)[1] if 'nativePS3/' in rel else rel.split('USRDIR/', 1)[1] if 'USRDIR/' in rel else rel
    for c in ('work/orig', 'work/orig_install/nativePS3', 'work/orig_install'):
        q = R(c, sub)
        if os.path.isfile(q): return q
    raise SystemExit('원본 없음 ' + rel)
def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest().upper()
pname = lambda rel: rel.replace('/', '_')

README = """D&D 미스타라 영웅전기 (Dungeons & Dragons: Mystara Eiyuu Senki, PS3) 한글 패치 {ver}{kind}
================================================================

일본판 디스크 (BLJM61055) 용입니다. ★RPCS3 전용입니다.
(EBOOT.BIN 이 복호화된 형태라 실기 PS3 에서는 돌지 않습니다)
{extra}
바꾸는 파일 : {n}개


[ 적용 방법 ]

0. ★원본 게임 파일에 적용합니다. 예전 한글 패치(v0.9 등)를 깔았다면 먼저 그 묶음의
   「되돌리기.bat」 으로 원본으로 돌린 뒤 적용하세요(그대로 두면 「원본과 다릅니다」 로 멈춥니다).
1. 이 묶음을 아무 폴더에나 풉니다.
2. 「한글패치_적용.bat」 을 실행하고, 게임 폴더를 끌어다 놓거나 경로를 적고 Enter.
   (게임 최상위 폴더, PS3_GAME, USRDIR 어느 것을 줘도 찾아갑니다){step2}
3. 배치가 파일마다
     원본 MD5 확인 → 원본을 이 묶음의 「원본백업」 폴더에 복사 → 패치 → 결과 MD5 확인
   을 하고 덮어씁니다. 이미 한글판인 파일은 건너뜁니다.
4. ★RPCS3 캐시를 지웁니다.
   RPCS3 는 게임 데이터를 「dev_hdd1\\caches\\BLJM61055_BLJM61055」 에 따로 복사해 두고 그것을 읽습니다.
   이 폴더를 지워야 한글 데이터가 반영됩니다(지워도 게임이 다시 만듭니다).
5. ★패치 전에 만든 스테이트(상태 저장)는 쓰지 마세요. 원본 데이터가 다시 깔립니다.
   새로 부팅해서 확인하세요.

되돌리기 : 「되돌리기.bat」 → 같은 폴더를 주면 「원본백업」 의 파일로 되돌립니다.
          (「원본백업」 폴더를 지우지 마세요. 되돌린 뒤에도 4번처럼 캐시를 지웁니다)


[ 바뀌는 것 ]
{changes}

[ 원본 → 한글판 MD5 ]

{table}
"""
CHANGES_MAIN = """
■ 타이틀 로고, 경고 화면, 메뉴·설정·기록·도움말(설명서 제외), 메뉴 글꼴(고해상도 한글)
■ 섀도 오버 미스타라 : 대사 전부, 아이템·마법 이름(링 메뉴), 함정 말풍선, 무대 제목,
   캐릭터 선택 설명, 이름 입력(영문 A~Z·0~9, 글자 숫자는 영문판과 같음)
■ 타워 오브 둠 : 대사 전부, 가게, 아이템 이름, 캐릭터 선택 설명, 아이템 이름 띠,
   이름 입력(영문 A~Z·0~9)
■ 저장·트로피 등 시스템 메시지, 저작권 경고, 무비 갤러리 썸네일, 게임 아이콘

[ 알려진 사항 ]

■ 엔딩 스태프 롤은 원문 그대로입니다.
■ 설명서(55쪽)는 바뀌지 않았습니다.
■ 무비 갤러리 대담 영상 3편 자막은 「_Movie」 묶음에 따로 있습니다(용량이 커서 나눔, 1.00·1.02 공용).

[ v0.91 에서 바뀐 것 ]

■ 섀도 오버 미스타라 이름 입력을 영문 글자판으로(돌판 글자를 커서 칸에 맞춰 다시 배치)
■ 챕터 선택 무대 이름을 본편 대사와 같은 표기로(아테노스·코룬글레인·란넬즈)
■ 1.02 업데이트용 묶음을 따로 만듦
{v102}
[ v0.92 에서 바뀐 것 ]

■ 빠져 있던 그림 글자 : 무대 제목 「숨겨진 보물」, 엔딩 「모험의 기록」 창, 상점 소지품 칸 이름표,
   링 위 「저주의 검」, 「원더 에그」 등
■ 랭킹·캐릭터 기본 이름을 영문판 이름으로, 상점 대사 칸 넘침, 그 밖 대사 오류 수정
■ 트로피 이름·설명 한글(RPCS3 에 이 게임 트로피가 이미 등록돼 있으면 원문 그대로일 수 있음)

"""
CHANGES_V102 = """
■ 1.02 업데이트에서 새로 생긴 것 : 네트워크(통신 플레이·게임 만들기·검색·랭킹) 메뉴 문구 전부,
   업데이트 내역 그림 2장, 온라인 일시 정지 메뉴, 난이도 「전부」, 온라인 시스템 메시지
"""
CHANGES_MOVIE = """
■ 무비 갤러리 「개발 비화」 대담 영상 3편(게임 내용 편 · 캐릭터 편 · 명(망)언집)에
   한글 자막과 한글 제목 카드를 입혔습니다(영상을 다시 인코딩, 음성은 원본 그대로).
■ 본편 패치와 따로 적용합니다. 본편 없이 이것만 적용해도 됩니다.
"""

BAT = r"""@echo off
setlocal
chcp 949 >nul
cd /d "%~dp0"
set "XD=%~dp0xdelta.exe"
set "BK=%~dp0원본백업"

echo.
echo  ================================================================
echo    D^&D Mystara Eiyuu Senki PS3 Korean Patch {ver}{kind}   [{tid}]
echo  ================================================================
echo.

if not exist "%XD%" goto NOXD

set "TARGET=%~1"
if not defined TARGET set /p TARGET=  게임 폴더를 끌어다 놓거나 경로를 적고 Enter:
set "TARGET=%TARGET:"=%"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"

set "DEST="
if exist "%TARGET%\USRDIR\nativePS3\game_data\dd21x.bin" set "DEST=%TARGET%"
if exist "%TARGET%\PS3_GAME\USRDIR\nativePS3\game_data\dd21x.bin" set "DEST=%TARGET%\PS3_GAME"
if exist "%TARGET%\nativePS3\game_data\dd21x.bin" for %%P in ("%TARGET%\..") do set "DEST=%%~fP"
if not defined DEST goto NODEST
echo  대상 : "%DEST%"
echo.
set "DISK=%DEST%"
{upd}
if not exist "%BK%" mkdir "%BK%"
set /a DONE=0
set /a SKIP=0
{calls}
echo.
echo  [OK] 끝났습니다. 새로 패치 %DONE%개 · 이미 한글판 %SKIP%개
echo       원본은 "원본백업" 폴더에 있습니다.
echo.
echo  ★ RPCS3 의 dev_hdd1\caches\BLJM61055_BLJM61055 폴더를 지워야 반영됩니다.
goto END

:DO
set "NAME=%~1"
set "PN=%~2"
set "SRCMD5=%~3"
set "DSTMD5=%~4"
set "ALTMD5=%~5"
set "XP=patch\%PN%.xdelta"
if not exist "%DEST%\%NAME%" goto MISSING
call :HASH "%DEST%\%NAME%"
if /I "%H%"=="%DSTMD5%" set /a SKIP+=1
if /I "%H%"=="%DSTMD5%" exit /b 0
if defined ALTMD5 if /I "%H%"=="%ALTMD5%" set "XP=patch\%PN%.alt.xdelta"
if defined ALTMD5 if /I "%H%"=="%ALTMD5%" set "SRCMD5=%ALTMD5%"
if /I not "%H%"=="%SRCMD5%" goto WRONG
copy /y "%DEST%\%NAME%" "%BK%\%PN%" >nul
"%XD%" -d -f -s "%DEST%\%NAME%" "%XP%" "%BK%\%PN%.new"
if errorlevel 1 goto XFAIL
call :HASH "%BK%\%PN%.new"
if /I not "%H%"=="%DSTMD5%" goto XFAIL
move /y "%BK%\%PN%.new" "%DEST%\%NAME%" >nul
set /a DONE+=1
echo      %NAME%
exit /b 0

:SEED
set "NAME=%~1"
if exist "%DISK%\%NAME%" exit /b 0
if not exist "%UPD%\%NAME%" goto MISSING
copy /y "%UPD%\%NAME%" "%DISK%\%NAME%" >nul
exit /b 0

:HASH
set "H="
for /f "skip=1 tokens=* delims=" %%A in ('certutil -hashfile "%~1" MD5') do if not defined H set "H=%%A"
set "H=%H: =%"
exit /b 0

:MISSING
echo  [!] %NAME% 이 대상 폴더에 없습니다. 판이 맞는지 확인하세요 - 이 묶음은 {tid} 용입니다.
goto FAIL
:WRONG
echo  [!] %NAME% 이 원본과 다릅니다. 다른 판이거나 이미 다른 패치가 들어가 있습니다.
echo      예전 한글 패치를 깔았다면 그 묶음의 되돌리기.bat 로 원본으로 돌린 뒤 다시 적용하세요.
echo      이 묶음은 {tid} 용입니다. 원본 MD5 %SRCMD5%
goto FAIL
:XFAIL
echo  [!] %NAME% 패치에 실패했습니다. 원본은 원본백업 폴더에 있습니다.
if exist "%BK%\%PN%.new" del "%BK%\%PN%.new"
goto FAIL
:NOXD
echo  [!] xdelta.exe 가 이 폴더에 없습니다. 묶음을 통째로 푸세요.
goto FAIL
:NODEST
echo  [!] 게임 폴더를 찾지 못했습니다. PS3_GAME 이 있는 폴더를 주세요.
goto FAIL
:NOUPD
echo  [!] 1.02 업데이트 폴더를 찾지 못했습니다. RPCS3 폴더 또는 dev_hdd0\game\{tid} 폴더를 주세요.
echo      업데이트를 설치하지 않았다면 1.00 용 묶음을 쓰세요.
goto FAIL
:FAIL
echo.
pause
exit /b 1
:END
echo.
pause
exit /b 0
"""
UNDO = r"""@echo off
setlocal
chcp 949 >nul
cd /d "%~dp0"
set "BK=%~dp0원본백업"
set "TARGET=%~1"
if not defined TARGET set /p TARGET=  게임 폴더를 끌어다 놓거나 경로를 적고 Enter:
set "TARGET=%TARGET:"=%"
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"
set "DEST="
if exist "%TARGET%\USRDIR\nativePS3\game_data\dd21x.bin" set "DEST=%TARGET%"
if exist "%TARGET%\PS3_GAME\USRDIR\nativePS3\game_data\dd21x.bin" set "DEST=%TARGET%\PS3_GAME"
if exist "%TARGET%\nativePS3\game_data\dd21x.bin" for %%P in ("%TARGET%\..") do set "DEST=%%~fP"
if not defined DEST goto NODEST
set "DISK=%DEST%"
{upd}
{calls}
echo.
echo  [OK] 원본으로 되돌렸습니다. RPCS3 의 dev_hdd1\caches\BLJM61055_BLJM61055 폴더도 지우세요.
goto END
:NODEST
echo  [!] 게임 폴더를 찾지 못했습니다.
goto END
:NOUPD
echo  [!] 1.02 업데이트 폴더를 찾지 못했습니다.
:END
echo.
pause
"""
def cp949(path, text):
    open(path, 'w', encoding='cp949', newline='\r\n').write(text)
UPD_BAT = r"""set "UPD="
set "T2=%~2"
if not defined T2 set /p T2=  RPCS3 폴더를 끌어다 놓거나 경로를 적고 Enter:
set "T2=%T2:"=%"
if "%T2:~-1%"=="\" set "T2=%T2:~0,-1%"
if exist "%T2%\dev_hdd0\game\{tid}\USRDIR\EBOOT.BIN" set "UPD=%T2%\dev_hdd0\game\{tid}"
if exist "%T2%\game\{tid}\USRDIR\EBOOT.BIN" set "UPD=%T2%\game\{tid}"
if exist "%T2%\{tid}\USRDIR\EBOOT.BIN" set "UPD=%T2%\{tid}"
if exist "%T2%\USRDIR\EBOOT.BIN" if exist "%T2%\PARAM.SFO" set "UPD=%T2%"
if not defined UPD goto NOUPD
echo  업데이트 : "%UPD%"
echo.""".replace('{tid}', TID)
STEP2_V102 = """
   이어서 RPCS3 폴더(rpcs3.exe 가 있는 곳)를 끌어다 놓거나 경로를 적고 Enter.
   (1.02 업데이트가 깔린 dev_hdd0\\game\\BLJM61055 폴더를 줘도 됩니다)"""
def build_pkg2(name, kind, items, changes, extra, upd=False):
    """items = [(구역 'disk'|'upd', 경로, 원본 파일, 새 파일)]"""
    od = R('dist', name)
    if os.path.exists(od): shutil.rmtree(od)
    os.makedirs(os.path.join(od, 'patch'))
    shutil.copy(XDELTA, os.path.join(od, 'xdelta.exe'))
    rows = []; calls = []; undo = []; cur = None
    for area, rel, src, dst in items:
        seed = area == 'disk2' and rel in SEED
        area_ = 'disk' if area == 'disk2' else area
        pn = ('update_' if area == 'upd' else 'disk102_' if area == 'disk2' else '') + pname(rel)
        a, b = md5(src), md5(dst)
        assert a != b, ('바뀐 것 없음', rel)
        xd = os.path.join(od, 'patch', pn + '.xdelta')
        subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src, dst, xd], check=True)
        tmp = xd + '.chk'
        subprocess.run([XDELTA, '-d', '-f', '-s', src, xd, tmp], check=True)
        assert md5(tmp) == b, ('되짚기 실패', rel); os.remove(tmp)
        win = rel.replace('/', '\\')
        if area_ != cur:
            cur = area_; sw = 'set "DEST=%%%s%%"' % ('UPD' if area_ == 'upd' else 'DISK')
            calls.append(sw); undo.append(sw)
        if seed: calls.append('call :SEED "%s"\nif errorlevel 1 goto FAIL' % win)
        rows.append('%s%s\n    %s -> %s' % ('[업데이트] ' if area == 'upd' else '[디스크 1.02] ' if area == 'disk2' else '', win, a, b))
        alt = ''
        if seed:                                                     # 업데이트 쪽이 이미 한글판(SFH)이면 그것에서 출발하는 패치
            src2 = upd_new(rel); a2 = md5(src2); xd2 = os.path.join(od, 'patch', pn + '.alt.xdelta')
            subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src2, dst, xd2], check=True)
            subprocess.run([XDELTA, '-d', '-f', '-s', src2, xd2, xd2 + '.chk'], check=True)
            assert md5(xd2 + '.chk') == b; os.remove(xd2 + '.chk'); alt = ' ' + a2
        calls.append('call :DO "%s" "%s" %s %s%s\nif errorlevel 1 goto FAIL' % (win, pn, a, b, alt))
        if seed: undo.append('if exist "%%DEST%%\\%s" del "%%DEST%%\\%s"' % (win, win))      # 원래 디스크에 없던 파일 = 지움
        else: undo.append('if exist "%%BK%%\\%s" copy /y "%%BK%%\\%s" "%%DEST%%\\%s" >nul' % (pn, pn, win))
        print(' ', area, rel, a[:8], '->', b[:8], os.path.getsize(xd))
    ub = UPD_BAT if upd else ''
    cp949(os.path.join(od, 'readme.txt'), README.format(ver=VER, kind=kind, n=len(items), changes=changes, extra=extra,
          table='\n'.join(rows), step2=STEP2_V102 if upd else ''))
    cp949(os.path.join(od, '한글패치_적용.bat'), BAT.replace('{upd}', ub).replace('{ver}', VER).replace('{kind}', kind).replace('{tid}', TID).replace('{calls}', '\n'.join(calls)))
    cp949(os.path.join(od, '되돌리기.bat'), UNDO.replace('{upd}', ub).replace('{calls}', '\n'.join(undo)))
    zp = od + '.zip'
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, ds, fs in os.walk(od):
            for f in fs:
                p_ = os.path.join(root, f); z.write(p_, os.path.join(name, os.path.relpath(p_, od)))
    print(name, 'zip', md5(zp), os.path.getsize(zp))
    return zp
def build_pkg(name, kind, files, changes, extra):
    od = R('dist', name)
    if os.path.exists(od): shutil.rmtree(od)
    os.makedirs(os.path.join(od, 'patch'))
    shutil.copy(XDELTA, os.path.join(od, 'xdelta.exe'))
    rows = []; calls = []; undo = []
    for rel in files:
        src = orig_of(rel); dst = os.path.join(GAME, rel.replace('/', os.sep)); pn = pname(rel)
        a, b = md5(src), md5(dst)
        xd = os.path.join(od, 'patch', pn + '.xdelta')
        subprocess.run([XDELTA, '-e', '-9', '-f', '-s', src, dst, xd], check=True)
        # 되짚기
        tmp = xd + '.chk'
        subprocess.run([XDELTA, '-d', '-f', '-s', src, xd, tmp], check=True)
        assert md5(tmp) == b, ('되짚기 실패', rel); os.remove(tmp)
        win = rel.replace('/', '\\')
        rows.append('%s\n    %s -> %s' % (win, a, b))
        calls.append('call :DO "%s" "%s" %s %s\nif errorlevel 1 goto FAIL' % (win, pn, a, b))
        undo.append('if exist "%%BK%%\\%s" copy /y "%%BK%%\\%s" "%%DEST%%\\%s" >nul' % (pn, pn, win))
        print(' ', rel, a[:8], '->', b[:8], os.path.getsize(xd))
    cp949(os.path.join(od, 'readme.txt'), README.format(ver=VER, kind=kind, n=len(files), changes=changes, extra=extra, table='\n'.join(rows)))
    cp949(os.path.join(od, '한글패치_적용.bat'), BAT.replace('{ver}', VER).replace('{kind}', kind).replace('{tid}', TID).replace('{calls}', '\n'.join(calls)))
    cp949(os.path.join(od, '되돌리기.bat'), UNDO.replace('{calls}', '\n'.join(undo)))
    zp = od + '.zip'
    with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for root, ds, fs in os.walk(od):
            for f in fs:
                p = os.path.join(root, f); z.write(p, os.path.join(name, os.path.relpath(p, od)))
    print(name, 'zip', md5(zp), os.path.getsize(zp))
    return zp
EXTRA_100 = """
★게임 1.00(업데이트 없음) 용입니다. 1.02 업데이트를 설치했다면 「_1.02」 묶음을 쓰세요.
"""
EXTRA_102 = """
★1.02 업데이트를 설치한 게임 용입니다. 업데이트가 없으면 「_1.00」 묶음을 쓰세요.
 디스크 쪽(게임 폴더)과 업데이트 쪽(RPCS3 의 dev_hdd0\\game\\BLJM61055) 두 곳을 고칩니다.
 (1.02 는 부팅 때 가끔 업데이트 폴더 대신 디스크 쪽 파일을 읽어서, 디스크 쪽에도 1.02 용 한글 메뉴 파일을 같이 넣습니다.
  그래서 이 묶음을 적용한 뒤 업데이트를 지우면 메뉴가 깨집니다. 그때는 되돌리기 후 1.00 묶음을 쓰세요)
"""
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    which = sys.argv[1:] or ['100', '102', 'movie']
    base = 'MystaraEiyuuSenki_PS3_KR_' + VER
    if '100' in which:
        build_pkg2(base + '_1.00', ' (1.00 용)', [('disk', r, orig_of(r), new_of(r)) for r in MAIN],
                   CHANGES_MAIN.replace('{v102}', ''), EXTRA_100)
    if '102' in which:
        items = ([('disk', r, orig_of(r), new_of(r)) for r in MAIN if r not in OVERRIDDEN]
                 + [('disk2', r, disk102_orig(r), disk102_new(r)) for r in DISK102]
                 + [('upd', r, upd_orig(r), upd_new(r)) for r in UPD])
        build_pkg2(base + '_1.02', ' (1.02 업데이트 용)', items, CHANGES_MAIN.replace('{v102}', CHANGES_V102), EXTRA_102, upd=True)
    if 'movie' in which:
        build_pkg2('MystaraEiyuuSenki_PS3_KR_Movie', ' (무비 자막)', [('disk', r, orig_of(r), new_of(r)) for r in MOVIE], CHANGES_MOVIE,
                   '\n무비 갤러리 대담 영상 3편 자막 묶음입니다(선택, 1.00·1.02 공용). 본편 묶음과 따로 적용합니다.\n')
if __name__ == '__main__':
    main()
