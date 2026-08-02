@echo off
REM Stop StudyMate local servers (kill listeners on ports 5088 and 5173).
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5088 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5173 ^| findstr LISTENING') do taskkill /f /pid %%a >nul 2>&1
echo StudyMate stopped.
pause
