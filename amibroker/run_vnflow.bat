@echo off
REM ============================================================================
REM  run_vnflow.bat [MA1 MA2 ...]
REM  - Khong tham so: dong bo du lieu tu GitHub, xuat va nap TAT CA ma vao AmiBroker.
REM  - Co tham so (VD: run_vnflow.bat SSI MBB HPG): thu thap them khop lenh HOM NAY
REM    cho cac ma do ngay luc chay (ke ca trong phien), roi xuat va nap cac ma do.
REM  Mo AmiBroker truoc khi chay. Doi duong dan AmiBroker bang bien AMIBROKER_DIR neu can.
REM ============================================================================
setlocal
chcp 65001 >nul
cd /d "%~dp0.."
if "%AMIBROKER_DIR%"=="" set "AMIBROKER_DIR=C:\Program Files\AmiBroker"

echo [1/4] Dong bo du lieu tu GitHub...
git pull --ff-only || echo     (bo qua: khong pull duoc, dung du lieu dang co)

if "%~1"=="" goto noCollect
echo [2/4] Thu thap khop lenh hom nay cho: %*
set "VNFLOW_DATA=data_local"
python -m vnflow.collect --symbols %* --allow-partial
set "VNFLOW_DATA="
goto export
:noCollect
echo [2/4] Khong thu thap tay ma nao.

:export
echo [3/4] Xuat du lieu cho AmiBroker...
if "%~1"=="" (python -m vnflow.amibroker) else (python -m vnflow.amibroker --symbols %*)
if errorlevel 1 goto fail

echo [4/4] Nap vao AmiBroker...
copy /Y "amibroker\vnflow.format" "%AMIBROKER_DIR%\Formats\vnflow.format" >nul
if errorlevel 1 echo     Khong chep duoc vnflow.format vao "%AMIBROKER_DIR%\Formats" - chep tay 1 lan hoac chay CMD bang quyen Administrator.
cscript //nologo "amibroker\import_vnflow.js"
echo Xong.
endlocal
exit /b 0

:fail
echo Loi khi xuat du lieu.
endlocal
exit /b 1
