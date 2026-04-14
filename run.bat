@echo off
echo Memulai Sistem Absensi...
cd /d "%~dp0"
python -m venv venv 2>nul
call venv\Scripts\activate

:: Upgrade pip to latest version
echo Memperbarui pip ke versi terbaru...
python -m pip install --upgrade pip

:: Install dependencies
echo Menginstal paket yang diperlukan...
pip install -r requirements.txt

:: Get local IP address - improved method to find the correct network interface
FOR /F "tokens=4 delims= " %%i IN ('route print ^| find "0.0.0.0" ^| find "0.0.0.0"') DO (
    if not defined IP set IP=%%i
)

:: If route print method fails, try another approach
if "%IP%"=="" (
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /r "IPv4.*192\.168\."') do (
        if not defined IP set IP=%%a
    )
)

:: Final fallback method
if "%IP%"=="" (
    for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /r "IPv4"') do (
        if not defined IP set IP=%%a
    )
    set IP=%IP:~1%
)

cls
echo.
echo ========================================================
echo         SISTEM ABSENSI BERHASIL DIJALANKAN!
echo ========================================================
echo.
echo Untuk mengakses sistem dari perangkat ini:
echo   http://localhost:5000
echo.
echo Untuk mengakses dari perangkat lain pada jaringan WiFi yang sama:
echo   http://%IP%:5000
echo.
echo ========================================================
echo.

python app.py --host=0.0.0.0
pause