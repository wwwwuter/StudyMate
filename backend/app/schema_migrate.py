"""轻量 schema 迁移（仅 SQLite 本地库）。

MySQL 环境走 Alembic（flask db migrate / upgrade）；SQLite 单机库没有迁移目录，
这里在启动时对「已存在但缺新列」的表做幂等的 ALTER，避免破坏已有数据。

注意：只在 SQLite 下生效；MySQL 下直接跳过（由迁移脚本负责）。
"""
from sqlalchemy import inspect, text

from app.extensions import db

# (表名, 列名, ADD COLUMN DDL) —— 幂等补列
_COLUMN_MIGRATIONS = [
    ('timer_sessions', 'mode', "ALTER TABLE timer_sessions ADD COLUMN mode VARCHAR(20) NOT NULL DEFAULT 'countup'"),
    ('timer_sessions', 'plan_start_time', "ALTER TABLE timer_sessions ADD COLUMN plan_start_time DATETIME"),
    ('timer_sessions', 'plan_end_time', "ALTER TABLE timer_sessions ADD COLUMN plan_end_time DATETIME"),
    ('study_tasks', 'plan_id', "ALTER TABLE study_tasks ADD COLUMN plan_id INTEGER"),
    ('study_records', 'extra_duration', "ALTER TABLE study_records ADD COLUMN extra_duration INTEGER NOT NULL DEFAULT 0"),
    ('study_records', 'effective_duration', "ALTER TABLE study_records ADD COLUMN effective_duration INTEGER NOT NULL DEFAULT 0"),
]


def _backfill_effective_duration(app):
    """历史数据回填：effective_duration = duration - extra_duration（CASE 保护防负数）。

    仅对「有真实计时但 effective 仍为 0」的旧记录执行一次（新写入记录 effective>0 不受影响）。
    """
    with app.app_context():
        try:
            db.session.execute(
                text(
                    "UPDATE study_records SET effective_duration = "
                    "CASE WHEN duration > extra_duration THEN duration - extra_duration ELSE 0 END "
                    "WHERE duration > 0 AND effective_duration = 0"
                )
            )
            db.session.commit()
        except Exception as e:  # 表不存在等：交给 create_all 兜底
            app.logger.warning(f'backfill effective_duration skipped: {e}')


def ensure_schema(app):
    """确保运行中 SQLite 库的表结构与模型一致（幂等）。"""
    uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not uri.startswith('sqlite'):
        return
    with app.app_context():
        try:
            insp = inspect(db.engine)
            changed = False
            for table, col, ddl in _COLUMN_MIGRATIONS:
                if not insp.has_table(table):
                    continue
                cols = {c['name'] for c in insp.get_columns(table)}
                if col not in cols:
                    db.session.execute(text(ddl))
                    changed = True
            if changed:
                db.session.commit()
        except Exception as e:  # 极小概率：表未初始化，交给 create_all 兜底
            app.logger.warning(f'ensure_schema skipped: {e}')
    # 补列完成后回填历史 effective_duration（幂等）
    _backfill_effective_duration(app)
