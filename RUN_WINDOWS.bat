@echo off
chcp 65001 > nul
title FatigueGuardian - Khởi động hệ thống
color 0B

echo.
echo ============================================================
echo   FATIGUE GUARDIAN - He thong bao ve suc khoe van phong
echo ============================================================
echo.

REM Kiểm tra Python
python --version > nul 2>&1
if errorlevel 1 (
    echo [LOI] Python chua duoc cai dat!
    echo Vui long tai Python tai: https://python.org/downloads
    echo Nho tick chon "Add Python to PATH"
    pause
    exit /b 1
)

echo [OK] Da tim thay Python
echo.

REM Cài packages
echo [SETUP] Dang cai dat cac thu vien can thiet...
pip install opencv-python mediapipe flask numpy plyer pygame --quiet --upgrade
if errorlevel 1 (
    echo [CANH BAO] Mot so thu vien co the chua cai dat duoc
    echo He thong se tu xu ly khi chay...
)

echo.
echo [START] Khoi dong FatigueGuardian...
echo.
echo  Dashboard Web: http://127.0.0.1:5050
echo  Camera AI: Cua so rieng se mo
echo  Nhan Ctrl+C de dung
echo.

python main.py

echo.
echo [EXIT] He thong da dung.
pause
