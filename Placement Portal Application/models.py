from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone


db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(70), unique=True, nullable=False) # @user name
    password = db.Column(db.String(150) , nullable=False) #user password
    role = db.Column(db.String(20), nullable=False) # Admin Student Company

    # to delete both at once 
    student_profile = db.relationship('Student', backref='user', cascade="all, delete", uselist=False)
    company_profile = db.relationship('Company', backref="user", cascade="all, delete", uselist=False)


class Company(db.Model):
    __tablename__ = "company_profile"
    company_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    company_name = db.Column(db.String(50), nullable=False)
    hr_contact = db.Column(db.String(100), nullable=False)
    website = db.Column(db.String(50), nullable=False)
    approval_status = db.Column(db.String(20), default="Pending") # Admin control
    is_blacklisted = db.Column(db.Boolean, default=False)  # Admin control

    drives = db.relationship('Placement', backref='company', lazy=True, cascade="all, delete-orphan") # Access all deives posted by (company.drives)


class Student(db.Model):
    __tablename__ = "student_profile"
    student_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True, nullable=False)
    #collage_name = db.Column(db.String(50), nullable=False)######################
    full_name = db.Column(db.String(50), nullable=False)
    cgpa = db.Column(db.Float, nullable=False)
    branch = db.Column(db.String(50), nullable=False)
    resume_url = db.Column(db.String(100), nullable=True)

    applications = db.relationship('Applications', backref='student', lazy=True) # Access all application of this student by (student.applications)


class Placement(db.Model):
    __tablename__ = "placement_drives"
    drive_id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey("company_profile.company_id"), nullable=False)
    job_title = db.Column(db.String(50), nullable=False)
    min_cgpa = db.Column(db.Float, nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    drive_status = db.Column(db.String(50), default="Pending")
    job_description = db.Column(db.Text, nullable=True)

    applications = db.relationship('Applications', backref='drive', lazy=True, cascade="all, delete-orphan") # Access all drive of this application by (drive.applications)


class Applications(db.Model):
    __tablename__ = "application"
    app_id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("student_profile.student_id"), nullable=False)
    drive_id = db.Column(db.Integer, db.ForeignKey("placement_drives.drive_id"), nullable=False)
    app_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc)) # Automatically add current date time
    status = db.Column(db.String(50), default="Applied")
