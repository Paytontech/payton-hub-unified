from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    full_name = db.Column(db.String(120))
    role = db.Column(db.String(50), default='Staff')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    __tablename__ = 'attendance'
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(120), nullable=False)
    punch_in = db.Column(db.DateTime, default=datetime.utcnow)
    punch_out = db.Column(db.DateTime)
    status = db.Column(db.String(50)) # PUNCHED_IN, PUNCHED_OUT
    active_mins = db.Column(db.Integer, default=0)
    break_mins = db.Column(db.Integer, default=0)
    role_at_time = db.Column(db.String(50))

class Case(db.Model):
    __tablename__ = 'cases'
    id = db.Column(db.String(50), primary_key=True) # Case ID from Sheets
    patient_name = db.Column(db.String(200))
    hospital = db.Column(db.String(200))
    status = db.Column(db.String(100))
    billed_amt = db.Column(db.Float, default=0.0)
    stage_code = db.Column(db.String(50))
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class BreakLog(db.Model):
    __tablename__ = 'break_logs'
    id = db.Column(db.Integer, primary_key=True)
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'))
    reason = db.Column(db.String(200))
    duration_mins = db.Column(db.Integer)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
