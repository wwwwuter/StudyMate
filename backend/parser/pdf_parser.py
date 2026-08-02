"""PDF 文本抽取。

仅负责把 PDF 转成纯文本，交给 AI（用户在「设置」页配置的 Key）识别计划。
不含任何离线正则解析 / 降级逻辑——系统只认 AI 解析结果。
"""
from io import BytesIO


def extract_pdf_text(file):
    """从 PDF 文件中提取纯文本（延迟导入 pdfminer，避免应用启动强依赖）。

    兼容 Flask/Werkzeug 的 FileStorage 对象（先读 bytes 再包成 BytesIO）。
    """
    from pdfminer.high_level import extract_text
    if hasattr(file, 'read'):
        data = file.read()
        if hasattr(file, 'seek'):
            file.seek(0)
        return extract_text(BytesIO(data))
    return extract_text(file)
