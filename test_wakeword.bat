@echo off
cd /d "%~dp0"
echo BilalAI wake-word test
 echo Say "hey Bilal" ten times from different distances.
echo Then try normal conversation and similar phrases such as "hey Bill".
echo The test lasts 60 seconds. Audio stays on this computer.
echo.
"venv\Scripts\python.exe" wakeword.py --seconds 60
 echo.
pause
