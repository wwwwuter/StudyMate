import os
from app import create_app

app = create_app(os.getenv('FLASK_ENV', 'development'))

# 提醒调度器（APScheduler）：仅在服务进程启动时拉起；测试环境不启动。
if app.config.get('REMINDER_ENABLED', True):
    from services.reminder_service import start_scheduler
    start_scheduler(app)

if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        port=5000,
        debug=app.config.get('DEBUG', True),
    )