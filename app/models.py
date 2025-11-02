
from flask_login import UserMixin
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))

class User(UserMixin, db.Model):   # ← добавлен UserMixin
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(128), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    last_name = db.Column(db.String(128))
    first_name = db.Column(db.String(128))
    patronymic = db.Column(db.String(128))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    role = db.relationship('Role', backref='users')

    def get_id(self):
        # UserMixin уже даёт реализацию, но на всякий случай:
        return str(self.id)

    def fio(self):
        parts = [self.last_name or '', self.first_name or '', self.patronymic or '']
        return ' '.join(p for p in parts if p).strip()
