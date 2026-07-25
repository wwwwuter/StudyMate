# StudyMate 后端启动脚本 (PowerShell)
# 用法：在项目根目录执行 .\start_backend.ps1

$ErrorActionPreference = 'Stop'
$backendDir = Join-Path $PSScriptRoot 'backend'
Set-Location $backendDir

$venvPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Error "未找到项目虚拟环境，请先运行环境初始化。"
    exit 1
}

# 确保 MySQL 正在运行（若未运行则尝试拉起）
$mysql = Get-Process -Name mysqld -ErrorAction SilentlyContinue
if (-not $mysql) {
    Write-Host "MySQL 未运行，尝试启动..." -ForegroundColor Yellow
    $mysqlBin = "C:\Program Files\MySQL\MySQL Server 8.4\bin\mysqld.exe"
    $dataDir  = "D:\StudyMate\mysql_data"
    Start-Process -FilePath $mysqlBin -ArgumentList "--datadir=$dataDir","--port=3306","--skip-log-bin","--tmpdir=$dataDir\tmp" -WindowStyle Hidden
    Start-Sleep -Seconds 8
}

& $venvPython run.py
