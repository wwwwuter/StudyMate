from datetime import datetime
from models.task import StudyTask

# 支持的科目映射
SUBJECT_MAP = {
    '数学': '数学', '高数': '数学', '线代': '数学', '概率': '数学',
    '英语': '英语',
    '政治': '政治',
    '408': '408', '数据结构': '408', '计组': '408', '操作系统': '408', '计网': '408',
}


def parse_excel_tasks(file, user_id):
    """解析 Excel 文件中的学习计划"""
    # 延迟导入：openpyxl 属后续阶段解析依赖，避免在应用启动时强制安装
    from openpyxl import load_workbook

    wb = load_workbook(file)
    ws = wb.active
    tasks = []

    for row in ws.iter_rows(min_row=2, values_only=True):
        # 期望列：日期, 科目, 内容, 开始时间, 结束时间
        if len(row) < 3:
            continue

        date_val = row[0]
        subject_val = str(row[1]).strip() if row[1] else ''
        content_val = str(row[2]).strip() if row[2] else ''

        if not content_val:
            continue

        # 解析日期
        if isinstance(date_val, datetime):
            task_date = date_val.date()
        elif isinstance(date_val, str):
            try:
                task_date = datetime.strptime(date_val.strip(), '%Y-%m-%d').date()
            except ValueError:
                continue
        else:
            continue

        # 映射科目
        subject = SUBJECT_MAP.get(subject_val, subject_val)

        # 解析时间
        start_time = None
        end_time = None
        if len(row) >= 4 and row[3]:
            try:
                if isinstance(row[3], datetime):
                    start_time = row[3].time()
                elif isinstance(row[3], str):
                    start_time = datetime.strptime(row[3].strip(), '%H:%M').time()
            except (ValueError, TypeError):
                pass

        if len(row) >= 5 and row[4]:
            try:
                if isinstance(row[4], datetime):
                    end_time = row[4].time()
                elif isinstance(row[4], str):
                    end_time = datetime.strptime(row[4].strip(), '%H:%M').time()
            except (ValueError, TypeError):
                pass

        task = StudyTask(
            user_id=user_id,
            date=task_date,
            subject=subject,
            content=content_val,
            start_time=start_time,
            end_time=end_time,
            status='pending',
            plan_source='excel',
        )
        tasks.append(task)

    return tasks