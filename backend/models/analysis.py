from datetime import datetime
from app.extensions import db


class AIAnalysis(db.Model):
    __tablename__ = 'ai_analysis'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    analysis_type = db.Column(db.String(32), nullable=False, comment='daily_summary/plan_optimization/qa')
    input_data = db.Column(db.Text, nullable=True, comment='分析输入')
    output_data = db.Column(db.Text, nullable=True, comment='分析结果')
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'analysis_type': self.analysis_type,
            'input_data': self.input_data,
            'output_data': self.output_data,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        }