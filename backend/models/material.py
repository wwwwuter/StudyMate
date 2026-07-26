from datetime import datetime
from app.extensions import db


class Material(db.Model):
    """用户上传的复习资料（RAG 知识库素材，Phase 5 升级方向 U3）。"""

    __tablename__ = 'materials'

    SOURCE_TEXT = 'text'
    SOURCE_PDF = 'pdf'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(128), nullable=False)
    content = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(16), default=SOURCE_TEXT)
    create_time = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'content': self.content,
            'source': self.source,
            'create_time': self.create_time.strftime('%Y-%m-%d %H:%M:%S') if self.create_time else None,
        }
