from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_number = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    class_name = db.Column(db.String(50), nullable=False)
    action_type = db.Column(db.String(4), nullable=True)
    team = db.Column(db.String, nullable=True)
    team_updated_by = db.Column(db.String(150), nullable=True)
    answers = db.relationship('Answer', backref='student', lazy=True, cascade="all, delete-orphan")

class Statement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    statement_number = db.Column(db.Integer, nullable=False)
    choices = db.relationship('StatementChoice', backref='statement', lazy=True)

class StatementChoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    statement_id = db.Column(db.Integer, db.ForeignKey('statement.id'), nullable=False)
    choice_number = db.Column(db.Integer, nullable=False)
    choice_text = db.Column(db.String(200), nullable=False)
    choice_result = db.Column(db.String(1), nullable=False)

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    statement_id = db.Column(db.Integer, db.ForeignKey('statement.id'), nullable=False)
    choice = db.Column(db.Integer, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())

class Teacher(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
