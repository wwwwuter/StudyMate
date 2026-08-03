# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\StudyMate\\backend\\desktop_run.py'],
    pathex=['D:\\StudyMate\\backend'],
    binaries=[],
    datas=[('D:\\StudyMate\\backend\\app', 'app'), ('D:\\StudyMate\\backend\\models', 'models'), ('D:\\StudyMate\\backend\\routes', 'routes'), ('D:\\StudyMate\\backend\\services', 'services'), ('D:\\StudyMate\\backend\\ai', 'ai'), ('D:\\StudyMate\\backend\\utils', 'utils'), ('D:\\StudyMate\\backend\\parser', 'parser'), ('D:\\StudyMate\\backend\\prompts', 'prompts')],
    hiddenimports=['models', 'flask', 'flask_cors', 'flask_sqlalchemy', 'flask_migrate', 'waitress', 'werkzeug', 'jinja2', 'sqlalchemy', 'alembic', 'pymysql', 'apscheduler', 'apscheduler.schedulers.background', 'apscheduler.jobstores.sqlalchemy', 'apscheduler.triggers.cron', 'openai', 'pypdf', 'pdfminer', 'pdfminer.high_level', 'docx', 'lxml', 'pydantic', 'dotenv', 'requests', 'httpx', 'aiohttp', 'tzlocal', 'pytz', 'cryptography'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'faiss', 'sentence_transformers', 'torch', 'transformers', 'langchain', 'langchain_core', 'langchain_text_splitters', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='studymate-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='studymate-backend',
)
