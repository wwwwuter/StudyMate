from flask import Flask
from flask_cors import CORS
from config import config_map
from app.extensions import db, migrate


def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config_map.get(config_name, config_map['default']))

    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # 注册蓝图
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.task import task_bp
    from routes.record import record_bp
    from routes.ai_route import ai_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(task_bp, url_prefix='/api/tasks')
    app.register_blueprint(record_bp, url_prefix='/api/records')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')

    # 健康检查
    @app.route('/api/health')
    def health():
        return {'status': 'ok', 'message': 'StudyMate API is running'}

    return app