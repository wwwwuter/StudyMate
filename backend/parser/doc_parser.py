"""Word 文档文本抽取。

仅负责把 .docx 转成纯文本，交给 AI（用户在「设置」页配置的 Key）识别计划。
不含任何离线正则解析 / 降级逻辑——系统只认 AI 解析结果。
"""
import io


def extract_docx_text(file_storage) -> str:
    """从 .docx 提取纯文本（段落拼接），供 AI 解析使用。"""
    try:
        from docx import Document
    except ImportError:
        raise ValueError('解析 .docx 需要 python-docx，请先安装')
    if hasattr(file_storage, 'seek'):
        file_storage.seek(0)
    doc = Document(io.BytesIO(file_storage.read()))
    parts = [p.text for p in doc.paragraphs if p.text and p.text.strip()]
    return '\n'.join(parts)
