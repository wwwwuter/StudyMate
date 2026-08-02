# StudyMate 后端镜像（Web 化部署）
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 系统依赖（sentence-transformers / faiss 可能需要的基础库）
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# 先装依赖（利用层缓存）
COPY requirements.txt .
RUN pip install -r requirements.txt

# 拷贝后端代码（不含 venv / dist / data）
COPY app ./app
COPY models ./models
COPY routes ./routes
COPY services ./services
COPY ai ./ai
COPY utils ./utils
COPY parser ./parser
COPY migrations ./migrations
COPY prompts ./prompts
COPY run.py ./run.py
COPY desktop_run.py ./desktop_run.py

# 运行时数据卷（RAG 索引、DB 等）
VOLUME ["/app/data"]

# 开放端口（gunicorn 监听）
EXPOSE 5000

# 启动：gunicorn。
# 注意：提醒调度器（APScheduler）在 run.py 导入时启动，多 worker 会重复触发，
# 故 MVP 用单 worker；规模扩大时再把调度器拆成独立进程/容器。
# 迁移：容器启动后执行 `flask db upgrade`（见 docker-compose 注释）。
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", \
     "--timeout", "120", "run:app"]
