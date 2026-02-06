from flask import Flask, request, redirect, render_template, flash, url_for, session
from models import db, User, Company, Student, Placement, Applications
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///placement.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'super_secret_key_for_session'
#LINK THE DATA BASE
db.init_app(app)

#create all data tables if they not exists
with app.app_context():
    db.create_all()
    print("done")

@app.route('/', methods=["GET", "POST"])
def index():
    return render_template("index.html")

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method=="POST":
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        print(f"User: {email} | Role in DB: '{user.role if user else 'None'}'")
        if user and check_password_hash(user.password, password): # CHECKING PASSWORD AND EMAIL OF EXISTING USER
            session['user_id'] = user.id
            session['role'] = user.role

            flash(f"Wellcome, {user.email}")

            user.role = user.role.strip().capitalize() if user.role else ""
            if user.role == "Company":                         # FOR ROLE BASED ACCESS
                return redirect(url_for('company_dashboard'))
            
            elif user.role == "Student":
                return redirect(url_for('student_dashboard'))
            
            elif user.role == "Admin":
                return redirect(url_for('admin_dashboard'))
        else:  
            flash("Invalid email or password please try again")  # IF LOGIN FAIL FOR INCORRECT EMAIL OR PASSWORD
            return redirect(url_for('login'))
    
    return render_template("login.html")


@app.route('/logout', methods=["GET", "POST"])
def logout():
    session.clear()
    flash("You have been logout successfully")

    return redirect(url_for('index'))

            

@app.route('/register/student', methods=["GET", "POST"]) # Student route
def register_student():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        cgpa = float(request.form.get('cgpa'))
        branch = request.form.get('branch')

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

                user_id = new_user.id,
                full_name = full_name,
                cgpa = cgpa,
                branch=branch

            )

            db.session.add(new_student)

            db.session.commit()

            flash("Registration successful")
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            return f"An error occured {str(e)}"
        
    return render_template('register_student.html')



@app.route('/register/company', methods=["GET", "POST"]) #Company route
def register_company():
    if request.method=="POST":
        email = request.form.get('company_email')
        password = request.form.get('password')
        company_name = request.form.get('company_name')
        website = request.form.get('website')
        hr_contact = request.form.get('hr_contact')

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

                user_id = new_user.id,
                company_name = company_name,
                website = website,
                hr_contact = hr_contact
            )

            db.session.add(new_company)
            db.session.commit()

            flash("Registration is Successful")
            return redirect(url_for('login'))
        
        except Exception as e:
            db.session.rollback()
            return f"An error occured {str(e)}"
    
    return render_template("register_company.html")


@app.route('/dashboard/company', methods=["GET", "POST"])          #COMPANY DASHBOARD
def company_dashboard():
    if 'user_id' not in session or session.get('role') != 'Company':       #CHECH IF USER LOGIN
        flash("Please login as a company to access to company dashboard")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])          #GET THE USER FORM DB

    company = user.company_profile                     #THIS WORK BECAUSE COMPANY_PROFILE RELATION IN USER
    
    
    if not company:                                     # FOR NONETYPE ERROR
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
            deadline_dt = datetime.strptime(deadline_str, '%Y-%m-%dT%H:%M')

            new_drive = Placement(
                company_id=company_id,
                job_title=job_title,
                min_cgpa=float(min_cgpa),
                deadline=deadline_dt,
                job_description=description
            )

            db.session.add(new_drive)
            db.session.commit()

            flash("Job drive post successfully")
            return redirect(url_for('company_dashboard'))
        
        except Exception as e:
            db.session.rollback()
            flash(f"Error in posting drive: {str(e)}")
            return redirect(url_for('post_drive'))
        
    return render_template('post_drive.html')


@app.route('/dashboard/student', methods=["GET", "POST"])      #STUDENT DASHBOARD
def student_dashboard():
    if 'user_id' not in session or session.get('role') != "Student":
        flash("Please login as a Student to access the student dashboard")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    student = user.student_profile                          #RELATION IN USER
    
    if not student:
        flash("Student profile not found. Please contact support.")
        return redirect(url_for('index'))
    
    available_drives = Placement.query.all()

    applied_drive_ids = [app.drive_id for app in student.applications]  #LIST FOR APPLIED JOB
    
    return render_template("student_dashboard.html", student=student, drives=available_drives, applied_id=applied_drive_ids)


@app.route('/apply/<int:drive_id>', methods=["GET", "POST"])
def apply_for_job(drive_id):
    if 'user_id' not in session or session.get('role') != 'Student':
        flash("Please login as a student to apply.")
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    student = user.student_profile

    existing_app = Applications.query.filter_by(
        student_id = student.student_id,
        drive_id=drive_id
    ).first()


    
    drive = Placement.query.get(drive_id)              #IF JOB IS DELETE
    if not drive:
        flash("This job no longer available.")
        return redirect(url_for('student_dashboard'))
    
    if student.cgpa < drive.min_cgpa :                  # STUDENT WIL NOT BYPASS
        flash("Your are not elegible")
        return redirect(url_for('student_dashboard'))

    if existing_app:
        flash("You already applied for this job.")

    else:
        new_app = Applications(
            student_id=student.student_id,
            drive_id=drive_id,
            status="Applied"
        )

        db.session.add(new_app)
        db.session.commit()
        flash("Application Sumited Successfully.")

    

    return redirect(url_for('student_dashboard',))


if __name__=="__main__":
    app.run(debug=True)