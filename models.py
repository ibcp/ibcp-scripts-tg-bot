import json
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class UserFiles(db.Model):
    __tablename__ = 'userfiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    chat_id = db.Column(db.Integer, nullable=False)
    message_id = db.Column(db.Integer, nullable=False)
    file_id = db.Column(db.String(64), nullable=False)
    file_name = db.Column(db.String(64), nullable=False)

    def __str__(self):
        return json.dumps({
            "id": self.id,
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "message_id": self.message_id,
            "file_id": self.file_id,
            "file_name": self.file_name
            })

    def __repr__(self):
        return str(self)
