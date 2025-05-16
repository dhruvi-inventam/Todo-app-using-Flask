from app import db
from flask_login import UserMixin
from datetime import datetime

# Todo task model
class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)          
    description = db.Column(db.Text, nullable=True)     
    category = db.Column(db.String(20), nullable=False, default='Other') 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reminder_time = db.Column(db.DateTime, nullable=True)
    completed = db.Column(db.Boolean, default=False) 
    due_date = db.Column(db.DateTime, nullable=True)
    priority = db.Column(db.String(10), nullable=False, default='Medium') 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    todos = db.relationship('Todo', backref='owner', lazy=True)
    