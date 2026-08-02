@echo off
REM StudyMate local launcher (no Docker). Starts backend on 5088 and frontend on 5173.
start "StudyMate Backend" cmd /k "cd /d D:\StudyMate\backend && C:\Users\www\.workbuddy\binaries\python\envs\studymate\Scripts\python.exe desktop_run.py --port 5088 --host 127.0.0.1"
start "StudyMate Frontend" cmd /k "cd /d D:\StudyMate\desktop\vue && C:\Users\www\.workbuddy\binaries\node\versions\22.22.2\node.exe ./node_modules/vite/bin/vite.js --port 5173 --strictPort"
echo.
echo StudyMate is starting...
echo   Frontend: http://localhost:5173
echo   Backend : http://127.0.0.1:5088
echo (Two console windows opened for backend/frontend. Close them to stop.)
pause
