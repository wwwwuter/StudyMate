"""Phase 5 + Phase 6 生产库迁移：新增资料库/提醒相关表与计时扩展字段

Revision ID: d4e5f6a7b8c9
Revises: 0b7f891a6d8e
Create Date: 2026-07-26 20:30:00.000000

说明：
- Phase 5（计时系统 + 升级方向 U3/U5）：
  * 新增 materials 表（RAG 资料库素材，U3）
  * study_tasks 新增 priority / estimated_minutes / tags 三列（U5 字段扩展）
  * study_records 新增 subject / planned_duration / note 三列（计时模式扩展）
- Phase 6（提醒系统）：
  * 新增 reminders 表（任务开始前提醒）
  * 新增 reminder_settings 表（每用户提醒偏好）

适用于 SQLite（开发）与 MySQL（生产，utf8mb4）。
新增列均为 nullable，老数据保持兼容；新行由 ORM 默认值填充。
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd4e5f6a7b8c9'
down_revision = '0b7f891a6d8e'
branch_labels = None
depends_on = None


def upgrade():
    # ### Phase 5：新增 materials 表（U3 RAG 资料库素材） ###
    op.create_table(
        'materials',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('source', sa.String(length=16), nullable=True, comment='text/pdf'),
        sa.Column('create_time', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_materials_user_id', 'materials', ['user_id'])

    # ### Phase 5：study_tasks 字段扩展（U5） ###
    with op.batch_alter_table('study_tasks', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('priority', sa.Integer(), nullable=True,
                      comment='优先级：0 普通 / 1 高 / 2 紧急')
        )
        batch_op.add_column(
            sa.Column('estimated_minutes', sa.Integer(), nullable=True,
                      comment='预估时长（分钟）')
        )
        batch_op.add_column(
            sa.Column('tags', sa.String(length=128), nullable=True,
                      comment='标签，逗号分隔')
        )

    # ### Phase 5：study_records 计时模式扩展 ###
    with op.batch_alter_table('study_records', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('subject', sa.String(length=32), nullable=True,
                      comment='关联科目（冗余存储便于统计）')
        )
        batch_op.add_column(
            sa.Column('planned_duration', sa.Integer(), nullable=True,
                      comment='计划时长（秒，倒计时用）')
        )
        batch_op.add_column(
            sa.Column('note', sa.String(length=255), nullable=True, comment='备注')
        )

    # ### Phase 6：新增 reminders 表 ###
    op.create_table(
        'reminders',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('type', sa.String(length=16), nullable=True,
                  comment='提醒类型：task=任务开始前'),
        sa.Column('subject', sa.String(length=32), nullable=False, comment='科目'),
        sa.Column('content', sa.String(length=512), nullable=False, comment='任务内容'),
        sa.Column('fire_at', sa.DateTime(), nullable=False,
                  comment='任务开始时间（提醒指向的时刻）'),
        sa.Column('lead_minutes', sa.Integer(), nullable=True,
                  comment='提前提醒分钟数'),
        sa.Column('delivered', sa.Boolean(), nullable=True,
                  comment='是否已送达（前端已弹通知）'),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['study_tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_reminders_user_id', 'reminders', ['user_id'])
    op.create_index('ix_reminders_task_id', 'reminders', ['task_id'])
    op.create_index('ix_reminders_delivered', 'reminders', ['delivered'])

    # ### Phase 6：新增 reminder_settings 表 ###
    op.create_table(
        'reminder_settings',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True,
                  comment='是否开启任务开始前提醒'),
        sa.Column('lead_minutes', sa.Integer(), nullable=True,
                  comment='提前提醒分钟数（任务开始前 N 分钟）'),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('user_id')
    )


def downgrade():
    # ### Phase 6：回滚 reminders / reminder_settings ###
    op.drop_index('ix_reminders_delivered', table_name='reminders')
    op.drop_index('ix_reminders_task_id', table_name='reminders')
    op.drop_index('ix_reminders_user_id', table_name='reminders')
    op.drop_table('reminders')
    op.drop_table('reminder_settings')

    # ### Phase 5：回滚 study_records 计时扩展列 ###
    with op.batch_alter_table('study_records', schema=None) as batch_op:
        batch_op.drop_column('note')
        batch_op.drop_column('planned_duration')
        batch_op.drop_column('subject')

    # ### Phase 5：回滚 study_tasks 字段扩展列 ###
    with op.batch_alter_table('study_tasks', schema=None) as batch_op:
        batch_op.drop_column('tags')
        batch_op.drop_column('estimated_minutes')
        batch_op.drop_column('priority')

    # ### Phase 5：回滚 materials 表 ###
    op.drop_index('ix_materials_user_id', table_name='materials')
    op.drop_table('materials')
