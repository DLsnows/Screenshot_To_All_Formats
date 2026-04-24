@echo off
cd /d "%~dp0.."
echo Starting Img2Text ...
echo.
python -m Screenshot_To_All_Formats.main
if %errorlevel% neq 0 (
    echo.
    echo Failed to start. Make sure Python is installed and dependencies are ready:
    echo   python -m pip install -r Screenshot_To_All_Formats/requirements.txt
    pause
)
