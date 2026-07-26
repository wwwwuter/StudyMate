import re
from datetime import datetime
from io import BytesIO
from models.task import StudyTask
from utils.subject_utils import normalize_subject


def extract_pdf_text(file):
    """从 PDF 文件中提取纯文本（延迟导入 pdfminer，避免应用启动强依赖）。"""
    from pdfminer.high_level import extract_text
    if hasattr(file, 'seek'):
        file.seek(0)
    return extract_text(file)


def is_scanned_pdf(file):
    """粗判是否为扫描件/图片型 PDF（U4 OCR 占位）。

    通过检测文本层字符量判断：几乎没有可提取文本则视为扫描件。
    真实「图片→文字」OCR 识别需在后续阶段接入 paddleocr 等引擎。
    """
    text = extract_pdf_text(file)
    if hasattr(file, 'seek'):
        file.seek(0)
    return len(text.strip()) < 30


def parse_pdf_tasks(file, user_id):
    """解析 PDF 文件中的学习计划（基于提取文本做正则识别）。"""
    text = extract_pdf_text(file)
    return _parse_pdf_text(text, user_id)


def _parse_pdf_text(text, user_id):
    """从文本中按行正则识别「日期 科目 内容 [时间范围]」结构的任务。"""
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
