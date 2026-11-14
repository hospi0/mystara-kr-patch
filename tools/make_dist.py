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
VER = 'v0.9'
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
        'USRDIR/nativePS3/options/record0_LIN.tex', 'USRDIR/nativePS3/options/setting1_LIN.tex']
MOVIE = ['USRDIR/nativePS3/movie/interview/%02d.pam' % i for i in range(3)]
def orig_of(rel):
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
바꾸는 파일 : PS3_GAME 아래 {n}개


[ 적용 방법 ]

1. 이 묶음을 아무 폴더에나 풉니다.
2. 「한글패치_적용.bat」 을 실행하고, 게임 폴더를 끌어다 놓거나 경로를 적고 Enter.
   (게임 최상위 폴더, PS3_GAME, USRDIR 어느 것을 줘도 찾아갑니다)
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
   캐릭터 선택 설명, 이름 입력 버튼 (이름은 일본판 그대로 가나로 입력)
■ 타워 오브 둠 : 대사 전부, 가게, 아이템 이름, 캐릭터 선택 설명, 아이템 이름 띠,
   이름 입력(영문 A~Z·0~9)
■ 저장·트로피 등 시스템 메시지, 저작권 경고, 무비 갤러리 썸네일, 게임 아이콘

[ 알려진 사항 ]

■ 엔딩 스태프 롤은 원문 그대로입니다.
■ 설명서(55쪽)는 바뀌지 않았습니다.
■ 무비 갤러리 대담 영상 3편 자막은 「_Movie」 묶음에 따로 있습니다(용량이 커서 나눔).
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
set TARGET=%TARGET:"=%
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"

set "DEST="
if exist "%TARGET%\USRDIR\nativePS3\game_data\dd21x.bin" set "DEST=%TARGET%"
if exist "%TARGET%\PS3_GAME\USRDIR\nativePS3\game_data\dd21x.bin" set "DEST=%TARGET%\PS3_GAME"
if exist "%TARGET%\nativePS3\game_data\dd21x.bin" for %%P in ("%TARGET%\..") do set "DEST=%%~fP"
if not defined DEST goto NODEST
echo  대상 : %DEST%
echo.

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
if not exist "%DEST%\%NAME%" goto MISSING
call :HASH "%DEST%\%NAME%"
if /I "%H%"=="%DSTMD5%" set /a SKIP+=1
if /I "%H%"=="%DSTMD5%" exit /b 0
if /I not "%H%"=="%SRCMD5%" goto WRONG
copy /y "%DEST%\%NAME%" "%BK%\%PN%" >nul
"%XD%" -d -f -s "%DEST%\%NAME%" "patch\%PN%.xdelta" "%BK%\%PN%.new"
if errorlevel 1 goto XFAIL
call :HASH "%BK%\%PN%.new"
if /I not "%H%"=="%DSTMD5%" goto XFAIL
move /y "%BK%\%PN%.new" "%DEST%\%NAME%" >nul
set /a DONE+=1
echo      %NAME%
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
set TARGET=%TARGET:"=%
if "%TARGET:~-1%"=="\" set "TARGET=%TARGET:~0,-1%"
set "DEST="
if exist "%TARGET%\USRDIR\nativePS3\game_data\dd21x.bin" set "DEST=%TARGET%"
if exist "%TARGET%\PS3_GAME\USRDIR\nativePS3\game_data\dd21x.bin" set "DEST=%TARGET%\PS3_GAME"
if exist "%TARGET%\nativePS3\game_data\dd21x.bin" for %%P in ("%TARGET%\..") do set "DEST=%%~fP"
if not defined DEST goto NODEST
{calls}
echo.
echo  [OK] 원본으로 되돌렸습니다. RPCS3 의 dev_hdd1\caches\BLJM61055_BLJM61055 폴더도 지우세요.
goto END
:NODEST
echo  [!] 게임 폴더를 찾지 못했습니다.
:END
echo.
pause
"""
def cp949(path, text):
    open(path, 'w', encoding='cp949', newline='\r\n').write(text)
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
def main():
    sys.stdout.reconfigure(encoding='utf-8')
    which = sys.argv[1:] or ['main', 'movie']
    if 'main' in which:
        build_pkg('MystaraEiyuuSenki_PS3_KR_' + VER, '', MAIN, CHANGES_MAIN, '')
    if 'movie' in which:
        build_pkg('MystaraEiyuuSenki_PS3_KR_' + VER + '_Movie', ' (무비 자막)', MOVIE, CHANGES_MOVIE,
                  '\n무비 갤러리 대담 영상 3편 자막 묶음입니다(선택). 본편 묶음과 따로 적용합니다.\n')
if __name__ == '__main__':
    main()
