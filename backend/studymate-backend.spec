# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 配置：StudyMate 桌面端后端 exe。

构建：cd backend && pyinstaller studymate-backend.spec --noconfirm
产物：dist/studymate-backend/studymate-backend.exe（onedir，启动快、体积可控）

体积策略：排除 torch / sentence-transformers / faiss / pandas 等超重依赖。
RAG 服务对向量模型是懒加载 + 失败自动回退关键词检索，排除后功能仍可用
（检索质量降级为关键词匹配）。若需完整向量检索，删除相应 excludes 重打
（体积将 +2GB 以上）。
"""

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = (
    ['desktop_run', 'waitress']
    + collect_submodules('models')
    + collect_submodules('routes')
    + collect_submodules('services')
    + collect_submodules('parser')
    + collect_submodules('ai')
    + collect_submodules('utils')
    + [
        # Flask / SQLAlchemy 生态
        'flask_sqlalchemy', 'flask_migrate', 'flask_cors',
        'sqlalchemy.dialects.sqlite', 'sqlalchemy.dialects.mysql',
        'pymysql',
        # APScheduler（显式 Trigger 类，但保险起见收全）
        'apscheduler.schedulers.background',
        'apscheduler.triggers.interval',
        # 文件解析（延迟导入，PyInstaller 静态分析可能漏收）
        'openpyxl', 'xlrd', 'pypdf', 'pdfminer.six', 'pdfminer.high_level',
        # AI 客户端
        'openai',
        # 其他延迟导入
        'jwt', 'dotenv', 'requests',
    ]
)

a = Analysis(
    ['desktop_run.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('prompts', 'prompts'),  # 文件化提示词（PromptManager 优先读文件）
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        # ---- 超重 AI 依赖：RAG 自动回退关键词检索 ----
        'torch', 'torchvision', 'torchaudio',
        'sentence_transformers', 'transformers', 'faiss',
        'huggingface_hub', 'tokenizers', 'safetensors',
        # ---- 未被后端使用的科学栈 ----
        'pandas', 'matplotlib', 'scipy', 'sklearn', 'sympy', 'numba',
        'PIL', 'cv2',
        # ---- 开发/测试工具 ----
        'pytest', 'IPython', 'jupyter', 'notebook',
        'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='studymate-backend',
    debug=False,
    strip=False,
    upx=False,
    console=True,  # 保留控制台输出便于日志重定向（Electron spawn 捕获 stdout）
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='studymate-backend',
)
