"""StudyMate 桌面端后端入口（PyInstaller 打包用）。

与 run.py（开发入口）的差异：
- 数据库默认 SQLite（用户可写目录），无需安装 MySQL；首次启动自动建表。
- 使用 waitress 生产级 WSGI 服务器（Flask 内置服务器不适合分发）。
- 数据目录（DB / RAG 索引）默认取 --data-dir 参数；未传时回退
  %APPDATA%/StudyMate/backend-data（Windows）或 ~/.studymate（其他平台）。
- 端口取 --port 参数（Electron 主进程探测空闲端口后传入），默认 5000。

重要：app/config.py 在 import 时即读取环境变量，因此本文件必须
「先设 os.environ，后 import app」，不能调整顺序。
"""
import argparse
import os
import sys
from pathlib import Path


def default_data_dir() -> Path:
    if sys.platform == 'win32':
        base = os.environ.get('APPDATA') or str(Path.home())
        return Path(base) / 'StudyMate' / 'backend-data'
    return Path.home() / '.studymate'


def main() -> None:
    parser = argparse.ArgumentParser(description='StudyMate desktop backend')
    parser.add_argument('--port', type=int, default=int(os.environ.get('STUDYMATE_PORT', '5000')))
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--data-dir', default=None, help='数据目录（SQLite DB / RAG 索引）')
    args = parser.parse_args()

    data_dir = Path(args.data_dir) if args.data_dir else default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    # ---- 必须先设环境变量，后 import app（config.py 在 import 时求值）----
    db_path = (data_dir / 'studymate.db').as_posix()
    os.environ.setdefault('DATABASE_URL', f'sqlite:///{db_path}')
    os.environ.setdefault('FLASK_ENV', 'production')
    # AI Key 只来自用户在「设置」页的个人配置，此处不注入任何全局密钥。

    from app import create_app
    from app.extensions import db

    app = create_app('production')

    # SQLite 单机模式跳过 Alembic，直接按 models 建表（幂等）
    with app.app_context():
        import models as _models  # noqa: F401  确保所有模型已注册到 metadata
        assert _models  # 显式使用，避免 pyflakes 未使用告警
        db.create_all()

    # 对已有的 SQLite 库补新增列（幂等，MySQL 走 Alembic 不在此处理）
    from app.schema_migrate import ensure_schema
    ensure_schema(app)

    # 提醒调度器（与 run.py 行为一致）
    if app.config.get('REMINDER_ENABLED', True):
        from services.reminder_service import start_scheduler
        start_scheduler(app)

    # Phase 6-5：启动时立即清理上次异常退出遗留的僵尸计时会话
    try:
        from scheduler.timer_cleanup import cleanup_stale_sessions
        cleaned = cleanup_stale_sessions(app)
        if cleaned:
            print(f'[studymate-backend] cleaned {cleaned} stale timer session(s)', flush=True)
    except Exception as e:
        print(f'[studymate-backend] timer cleanup skipped: {e}', flush=True)

    print(f'[studymate-backend] serving on http://{args.host}:{args.port} '
          f'(data: {data_dir})', flush=True)

    from waitress import serve
    serve(app, host=args.host, port=args.port, threads=8)


if __name__ == '__main__':
    main()
