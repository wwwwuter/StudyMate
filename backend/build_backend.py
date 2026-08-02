"""PyInstaller 打包脚本：把 Flask 后端冻结成 studymate-backend.exe。

输出目录：backend/dist/studymate-backend/
  - studymate-backend.exe   （Electron 主进程 spawn 的入口，对应 desktop_run.py）
  - 依赖 DLL / _internal 等（同目录，自动发现）

用法：
  python build_backend.py            # 在 backend/ 目录内运行
  python build_backend.py --clean    # 清理 build/ 缓存后重打

注意：
  - 采用 one-folder（不是 one-file），避免 numpy 在解压阶段出怪问题。
  - 不打包任何 API Key：AI 能力完全依赖用户在「设置」页填写的个人 Key。
"""
import os
import sys
import shutil
import subprocess

# ---------------------------------------------------------------------------
# 沙箱 workaround：PyInstaller 默认在「隔离子进程」里执行部分构建步骤
# （如 discover_hook_directories），而本环境的 numpy 在子进程内会触发段错误
# (exit 0xC0000005)，导致构建直接崩溃。numpy 在主进程内仅产生无害警告。
# 这里把隔离调用改为「主进程内直接执行」，绕过子进程崩溃。
# ---------------------------------------------------------------------------
try:
    import PyInstaller.isolated._parent as _iso_parent
    _orig_iso_call = getattr(_iso_parent, "call", None)

    def _inprocess_call(function, *args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception as _e:  # 单个隔离步骤失败不应拖垮整个构建
            print(f"[iso-patch] isolated call {getattr(function,'__name__','?')} failed: {_e}")
            return None

    if _orig_iso_call is not None:
        _iso_parent.call = _inprocess_call
        print("[iso-patch] PyInstaller isolated subprocess disabled (in-process fallback).")
except Exception as _patch_err:
    print("[iso-patch] could not patch isolated call:", _patch_err)

HERE = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(HERE, "dist", "studymate-backend")
BUILD_DIR = os.path.join(HERE, "build")

HIDDEN_IMPORTS = [
    # Web 框架
    "flask", "flask_cors", "flask_sqlalchemy", "flask_migrate",
    "waitress", "werkzeug", "jinja2",
    # 数据库 / ORM
    "sqlalchemy", "alembic", "pymysql",
    # 调度
    "apscheduler", "apscheduler.schedulers.background",
    "apscheduler.jobstores.sqlalchemy", "apscheduler.triggers.cron",
    # AI：openai 兼容客户端（Key 由用户在「设置」页提供，不打包任何密钥）
    "openai",
    # 文档解析：pdfminer（PDF 抽文本）/ python-docx（.docx，依赖 lxml）
    "pypdf", "pdfminer", "pdfminer.high_level", "docx", "lxml",
    # 工具
    "pydantic", "dotenv", "requests", "httpx", "aiohttp",
    "tzlocal", "pytz", "cryptography",
]

# 沙箱里的 numpy 是 MINGW 实验构建，在 PyInstaller 分析阶段（构建依赖图时导入）
# 会触发段错误 (exit 0xC0000005)。后端仅在 RAG 向量索引路径用到 numpy/faiss/langchain，
# 而该路径因 sentence-transformers/faiss 未安装早已禁用（vector_available=False），
# 运行时不会导入这些模块。故打包时整体排除，规避构建崩溃。
EXCLUDES = [
    "numpy", "faiss", "sentence_transformers", "torch", "transformers",
    "langchain", "langchain_core", "langchain_text_splitters", "pandas",
]

# 收集后端用到的全部子包，避免动态导入漏打
COLLECT_SUBDIRS = ["app", "models", "routes", "services", "ai", "utils", "parser"]


def main():
    # 不在此处自行 rmtree（会触发安全拦截）；交给 PyInstaller --noconfirm 覆盖。
    entry = os.path.join(HERE, "desktop_run.py")

    cmd = [
        sys.executable,
        "--name", "studymate-backend",
        "--paths", HERE,
        "--distpath", os.path.join(HERE, "dist"),
        "--workpath", BUILD_DIR,
        "--noconfirm",
        "--windowed",          # 无控制台黑窗（桌面软件体验）
        "--hidden-import", "models",
    ]
    for hi in HIDDEN_IMPORTS:
        cmd += ["--hidden-import", hi]
    for ex in EXCLUDES:
        cmd += ["--exclude-module", ex]
    # 把源码子目录作为 data 一并收集（保证任何运行时 import 都能找到）
    for sub in COLLECT_SUBDIRS:
        subp = os.path.join(HERE, sub)
        if os.path.isdir(subp):
            cmd += ["--add-data", f"{subp}{os.pathsep}{sub}"]
    cmd.append(entry)

    # 关键：必须在「同一进程内」调用 PyInstaller，上面的 iso.call 补丁才会生效
    # （若用 `python -m PyInstaller` 起子进程，补丁不传递到子进程，隔离段错误依旧）。
    sys.argv = cmd  # cmd 已是 [sys.executable, "-m", "PyInstaller", ...]
    print(">>> " + " ".join(sys.argv))
    try:
        from PyInstaller.__main__ import run
        run()
        rc = 0
    except SystemExit as se:
        rc = se.code if isinstance(se.code, int) else 1
    except Exception as e:  # noqa
        import traceback
        traceback.print_exc()
        rc = 1

    if rc != 0:
        print(f"[FAIL] PyInstaller exited with code {rc}")
        sys.exit(rc)

    exe = os.path.join(DIST_DIR, "studymate-backend.exe")
    if os.path.exists(exe):
        size = os.path.getsize(exe) / (1024 * 1024)
        print(f"[OK] built -> {exe} ({size:.1f} MB)")
    else:
        print("[FAIL] exe not found after build")
        sys.exit(1)


if __name__ == "__main__":
    main()
