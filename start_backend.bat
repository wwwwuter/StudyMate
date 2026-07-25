@echo off
REM StudyMate 后端启动脚本
REM 用法：双击本文件，或在项目根目录执行 start_backend.bat

cd /d "%~dp0backend"
call "%~dp0.venv\Scripts\activate.bat"
python run.py
pause
