import re
from datetime import datetime
from io import BytesIO
from models.task import StudyTask
from utils.subject_utils import normalize_subject


def parse_pdf_tasks(file, user_id):
    """解析 PDF 文件中的学习计划。

    支持两类行：
      1) 带时间段：「2026-07-20 数学 高数强化 08:30-11:30」
      2) 仅日期+科目+内容：「2026-07-20 英语 单词背诵」（无时间段也保留，时间置空）

    科目经 normalize_subject 归一化（高数→数学 等）；非法/缺日期或内容的行跳过。
    """
    # 延迟导入：pdfminer 属后续阶段解析依赖，避免在应用启动时强制安装
    from pdfminer.high_level import extract_text

    # 提取文本
    text = extract_text(file)

    tasks = []
    lines = text.split('\n')

    # 宽松匹配：日期 + 科目 + 内容(+可选 时间段)
    date_re = r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})'
    time_re = r'(\d{1,2}:\d{2})\s*[-~]\s*(\d{1,2}:\d{2})'

    for line in lines:
        line = line.strip()
        if not line:
            continue

        m_date = re.search(date_re, line)
        if not m_date:
            continue
        date_str = m_date.group(1).replace('/', '-')

        try:
            task_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            continue

        # 去掉日期片段后，剩余文本按空白切分：首段=科目，其后=内容
        rest = line[m_date.end():].strip()
        m_time = re.search(time_re, rest)
        start_time = None
        end_time = None
        if m_time:
            try:
                start_time = datetime.strptime(m_time.group(1), '%H:%M').time()
                end_time = datetime.strptime(m_time.group(2), '%H:%M').time()
                # 去掉时间段片段，避免混进内容
                rest = (rest[:m_time.start()] + rest[m_time.end():]).strip()
            except ValueError:
                pass

        parts = rest.split(None, 1)
        if len(parts) < 2:
            # 至少要能拆出「科目 + 内容」两段
            continue
        subject_raw, content = parts[0], parts[1].strip()
        if not content:
            continue

        subject = normalize_subject(subject_raw)

        tasks.append(StudyTask(
            user_id=user_id,
            date=task_date,
            subject=subject,
            content=content,
            start_time=start_time,
            end_time=end_time,
            status='pending',
            plan_source='pdf',
        ))

    return tasks
