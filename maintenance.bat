@echo off
REM maintenance.bat
REM Script untuk menjalankan maintenance sistem fine-tuning

echo ========================================
echo Fine-Tuning System Maintenance
echo ========================================
echo.

REM Activate virtual environment if exists
if exist "venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

echo Running maintenance tasks...
echo.

REM Run all maintenance tasks
python maintenance.py --all

echo.
echo ========================================
echo Maintenance completed!
echo ========================================

REM Keep window open
pause
