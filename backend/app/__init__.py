from flask import Flask
from app.config import config_map
from app.extensions import db, migrate, cors, limiter


def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    # CORS：生产环境收紧到前端域名；'*' 仅用于本地同源/演示。
    cors_origins = app.config.get('CORS_ORIGINS', '*')
    cors.init_app(
        app,
        resources={r"/api/*": {"origins": cors_origins.split(',') if cors_origins != '*' else '*'}},
    )
    limiter.init_app(app)

    # 注册蓝图
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.task import task_bp
    from routes.record import record_bp
    from routes.ai_route import ai_bp
    from routes.plan import plan_bp
    from routes.reminder import pending, ack, get_settings, save_settings, sweep
    from routes.schedule import schedule_bp
    from routes.stat import stat_bp
    from routes.system import system_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(task_bp, url_prefix='/api/tasks')
    app.register_blueprint(record_bp, url_prefix='/api/records')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(plan_bp, url_prefix='/api/plans')
    app.register_blueprint(schedule_bp, url_prefix='/api/schedule')
    app.register_blueprint(stat_bp, url_prefix='/api/stat')
    app.register_blueprint(system_bp, url_prefix='/api/system')

    # 提醒路由
    from flask import Blueprint
    reminder_bp = Blueprint('reminder', __name__)
    reminder_bp.add_url_rule('/reminders/pending', 'reminder_pending', pending, methods=['GET'])
    reminder_bp.add_url_rule('/reminders/ack', 'reminder_ack', ack, methods=['POST'])
    reminder_bp.add_url_rule('/reminders/settings', 'reminder_settings_get', get_settings, methods=['GET'])
    reminder_bp.add_url_rule('/reminders/settings', 'reminder_settings_save', save_settings, methods=['POST'])
    reminder_bp.add_url_rule('/reminders/sweep', 'reminder_sweep', sweep, methods=['POST'])
    app.register_blueprint(reminder_bp, url_prefix='/api')

    # 健康检查（Electron 桌面端拉起后端后靠此探活）
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'message': 'StudyMate API is running'}

    # 根路由：用于快速确认后端已启动
    @app.route('/')
    def index():
        return 'StudyMate Backend Running'

    return app