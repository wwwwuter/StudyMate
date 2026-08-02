"""轻量 schema 迁移（仅 SQLite 本地库）。

MySQL 环境走 Alembic（flask db migrate / upgrade）；SQLite 单机库没有迁移目录，
这里在启动时对「已存在但缺新列」的表做幂等的 ALTER，避免破坏已有数据。

注意：只在 SQLite 下生效；MySQL 下直接跳过（由迁移脚本负责）。
"""
from sqlalchemy import inspect, text

from app.extensions import db


def ensure_schema(app):
    """确保运行中 SQLite 库的表结构与模型一致（幂等）。"""
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri.startswith('sqlite'):
        return
    with app.app_context():
        try:
            insp = inspect(db.engine)
            if not insp.has_table('timer_sessions'):
                return
            cols = {c['name'] for c in insp.get_columns('timer_sessions')}
            if 'mode' not in cols:
                db.session.execute(
                    text("ALTER TABLE timer_sessions ADD COLUMN mode VARCHAR(20) NOT NULL DEFAULT 'countup'")
                )
                db.session.commit()
        except Exception as e:  # 极小概率：表未初始化，交给 create_all 兜底
            app.logger.warning(f'ensure_schema skipped: {e}')
