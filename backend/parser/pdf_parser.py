import re
from datetime import datetime
from io import BytesIO
from models.task import StudyTask


def parse_pdf_tasks(file, user_id):
    """解析 PDF 文件中的学习计划"""
    # 延迟导入：pdfminer 属后续阶段解析依赖，避免在应用启动时强制安装
    from pdfminer.high_level import extract_text

    # 提取文本
    text = extract_text(file)

    tasks = []
    lines = text.split('\n')

    # 正则：匹配 "2026-07-20 数学 高数强化 08:30-11:30" 或类似格式
    pattern = re.compile(
        r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s+'  # 日期
        r'([\u4e00-\u9fa5a-zA-Z0-9]+)\s+'      # 科目
        r'(.+?)\s+'                              # 内容
        r'(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})'  # 时间范围
    )

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = pattern.search(line)
        if match:
            date_str = match.group(1).replace('/', '-')
            subject = match.group(2)
            content = match.group(3).strip()
            start_str = match.group(4)
            end_str = match.group(5)

            try:
                task_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                start_time = datetime.strptime(start_str, '%H:%M').time()
                end_time = datetime.strptime(end_str, '%H:%M').time()
            except ValueError:
                continue

            task = StudyTask(
                user_id=user_id,
                date=task_date,
                subject=subject,
                content=content,
                start_time=start_time,
                end_time=end_time,
                status='pending',
                plan_source='pdf',
            )
            tasks.append(task)

    return tasks