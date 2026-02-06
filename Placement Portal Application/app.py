from flask import Flask, request, redirect, render_template, flash, url_for, session
from models import db, User, Company, Student, Placement, Applications
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
# LINK THE DATABASE
db.init_app(app)

# Create all data tables if they not exist
with app.app_context():
    db.create_all()
    logger.info("Database tables initialized")

@app.route('/', methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        logger.info(f"Login attempt for user: {email}")
        
        if user and check_password_hash(user.password, password):  # CHECKING PASSWORD AND EMAIL OF EXISTING USER
            session['user_id'] = user.id
            session['role'] = user.role

            flash(f"Welcome, {user.email}")

            user_role = user.role.strip().capitalize() if user.role else ""
            if user_role == "Company":  # FOR ROLE BASED ACCESS
                return redirect(url_for('company_dashboard'))
            
            elif user_role == "Student":
                return redirect(url_for('student_dashboard'))
            
            elif user_role == "Admin":
                return redirect(url_for('admin_dashboard'))
        else:  
            flash("Invalid email or password please try again")  # IF LOGIN FAILS FOR INCORRECT EMAIL OR PASSWORD
            return redirect(url_for('login'))
    
    return render_template("login.html")


@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    flash("You have been logged out successfully")
    return redirect(url_for('index'))


@app.route('/register/student', methods=["GET", "POST"])  # Student route
def register_student():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        branch = request.form.get('branch')
        
        # Validate CGPA
        try:
            cgpa = float(request.form.get('cgpa', 0))
            if cgpa < 0 or cgpa > 10:
                flash("CGPA must be between 0 and 10")
                return redirect(url_for('register_student'))
        except ValueError:
            flash("Invalid CGPA value")
            return redirect(url_for('register_student'))

        # Validate password strength
        if len(password) < 6:
            flash("Password must be at least 6 characters long")
            return redirect(url_for('register_student'))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email is already registered")
            return redirect(url_for('register_student'))
        
        try:
            hashed_password = generate_password_hash(password)
            new_user = User(email=email, password=hashed_password, role='Student')
            db.session.add(new_user)
            db.session.flush()

            new_student = Student(
                user_id=new_user.id,
                full_name=full_name,
                cgpa=cgpa,
                branch=branch
            )

            db.session.add(new_student)
            db.session.commit()

            flash("Registration successful")
            logger.info(f"New student registered: {email}")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in student registration: {str(e)}")
            flash("An error occurred during registration. Please try again.")
            return redirect(url_for('register_student'))
        
    return render_template('register_student.html')


@app.route('/register/company', methods=["GET", "POST"])  # Company route
def register_company():
    if request.method == "POST":
        email = request.form.get('company_email')
        password = request.form.get('password')
        company_name = request.form.get('company_name')
        website = request.form.get('website')
        hr_contact = request.form.get('hr_contact')

        # Validate password strength
        if len(password) < 6:
            flash("Password must be at least 6 characters long")
            return redirect(url_for('register_company'))

        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Company already registered")
            return redirect(url_for('register_company'))
        
        try:
            hashed_password = generate_password_hash(password)
            new_user = User(email=email, password=hashed_password, role='Company')
            db.session.add(new_user)
            db.session.flush()

            new_company = Company(
                user_id=new_user.id,
                company_name=company_name,
                website=website,
                hr_contact=hr_contact
            )

            db.session.add(new_company)
            db.session.commit()

            flash("Registration is successful")
            logger.info(f"New company registered: {email}")
            return redirect(url_for('login'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in company registration: {str(e)}")
            flash("An error occurred during registration. Please try again.")
            return redirect(url_for('register_company'))
    
    return render_template("register_company.html")


@app.route('/dashboard/company', methods=["GET", "POST"])  # COMPANY DASHBOARD
def company_dashboard():
    if 'user_id' not in session or session.get('role') != 'Company':  # CHECK IF USER IS LOGGED IN
        flash("Please login as a company to access the company dashboard")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])  # GET THE USER FROM DB

    company = user.company_profile if user else None  # THIS WORKS BECAUSE OF COMPANY_PROFILE RELATION IN USER
    
    if not company:  # HANDLE NONETYPE ERROR
        flash("Company profile not found. Please contact support")
        return redirect(url_for('index'))
    
    my_drives = Placement.query.filter_by(company_id=company.company_id).all()

    return render_template('company_dashboard.html', company=company, drives=my_drives)

@app.route('/post-drive', methods=["GET", "POST"])
def post_drive():
    if 'user_id' not in session or session.get('role') != "Company":
        flash("Unauthorized access.")
        return redirect(url_for('login'))
    
    if request.method == "POST":
        user = User.query.get(session['user_id'])
        company_id = user.company_profile.company_id

        job_title = request.form.get('job_title')
        min_cgpa = request.form.get('min_cgpa')
        deadline_str = request.form.get('deadline')
        description = request.form.get('description')

        try:
            # Validate CGPA
            min_cgpa = float(min_cgpa)
            if min_cgpa < 0 or min_cgpa > 10:
                flash("Minimum CGPA must be between 0 and 10")
                return redirect(url_for('post_drive'))
            
            # Parse and validate deadline
            deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')
            if deadline_dt < datetime.now():
                flash("Deadline cannot be in the past")
                return redirect(url_for('post_drive'))

            new_drive = Placement(
                company_id=company_id,
                job_title=job_title,
                min_cgpa=min_cgpa,
                deadline=deadline_dt,
                job_description=description
            )

            db.session.add(new_drive)
            db.session.commit()

            flash("Job drive posted successfully")
            logger.info(f"New job drive posted by company {company_id}: {job_title}")
            return redirect(url_for('company_dashboard'))
        
        except ValueError as e:
            logger.error(f"Invalid value in job posting: {str(e)}")
            flash("Invalid input. Please check your entries.")
            return redirect(url_for('post_drive'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in posting drive: {str(e)}")
            flash("Error in posting drive. Please try again.")
            return redirect(url_for('post_drive'))
        
    return render_template('post_drive.html')

@app.route('/dashboard/student', methods=["GET", "POST"])  # STUDENT DASHBOARD
def student_dashboard():
    if 'user_id' not in session or session.get('role') != "Student":
        flash("Please login as a student to access the student dashboard")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    student = user.student_profile if user else None  # RELATION IN USER
    
    if not student:
        flash("Student profile not found. Please contact support.")
        return redirect(url_for('index'))
    
    available_drives = Placement.query.all()

    applied_drive_ids = [application.drive_id for application in student.applications]  # LIST FOR APPLIED JOBS
    
    return render_template("student_dashboard.html", student=student, drives=available_drives, applied_id=applied_drive_ids)

@app.route('/apply/<int:drive_id>', methods=["GET", "POST"])
def apply_for_job(drive_id):
    if 'user_id' not in session or session.get('role') != 'Student':
        flash("Please login as a student to apply.")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    student = user.student_profile if user else None

    if not student:
        flash("Student profile not found.")
        return redirect(url_for('login'))

    # Check if already applied
    existing_app = Applications.query.filter_by(
        student_id=student.student_id,
        drive_id=drive_id
    ).first()

    # Check if job exists
    drive = Placement.query.get(drive_id)
    if not drive:
        flash("This job no longer available.")
        return redirect(url_for('student_dashboard'))
    
    # Check CGPA eligibility
    if student.cgpa < drive.min_cgpa:
        flash("You are not eligible for this position.")
        return redirect(url_for('student_dashboard'))

    if existing_app:
        flash("You already applied for this job.")
        return redirect(url_for('student_dashboard'))
    else:
        try:
            new_app = Applications(
                student_id=student.student_id,
                drive_id=drive_id,
                status="Applied"
            )

            db.session.add(new_app)
            db.session.commit()
            flash("Application submitted successfully.")
            logger.info(f"Student {student.student_id} applied for job {drive_id}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error in applying for job: {str(e)}")
            flash("Error submitting application. Please try again.")

    return redirect(url_for('student_dashboard'))

@app.route('/view-applications/<int:drive_id>', methods=["GET"])
def view_applications(drive_id):
    """View all applications for a specific job drive"""
    if 'user_id' not in session or session.get('role') != 'Company':
        flash("Unauthorized access.")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    company = user.company_profile if user else None
    
    if not company:
        flash("Company profile not found.")
        return redirect(url_for('login'))
    
    # Verify that the drive belongs to this company
    drive = Placement.query.get(drive_id)
    if not drive or drive.company_id != company.company_id:
        flash("You do not have permission to view these applications.")
        return redirect(url_for('company_dashboard'))
    
    applications = Applications.query.filter_by(drive_id=drive_id).all()
    
    return render_template('view_applications.html', drive=drive, applications=applications)

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('error.html', error_code=404, error_message="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {str(error)}")
    return render_template('error.html', error_code=500, error_message="Internal server error"), 500


if __name__ == "__main__":
    app.run(debug=False)