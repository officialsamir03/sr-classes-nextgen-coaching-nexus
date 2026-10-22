from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
import re
from datetime import datetime
from functools import wraps
from flask_mail import Mail, Message

app = Flask(__name__)
app.config.from_object('config.Config')

mysql = MySQL(app)
mail = Mail(app)   

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def validate_aadhaar(aadhaar):
    """Validate Aadhaar number format"""
    return re.match(r'^\d{12}$', aadhaar) is not None

def validate_mobile(mobile):
    """Validate Indian mobile number"""
    return re.match(r'^[6-9]\d{9}$', mobile) is not None

def validate_email(email):
    """Validate email format"""
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

# Login decorator
def admin_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login to access admin panel', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes - Student Interface
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM faculty")
    faculty = cur.fetchall()
    cur.close()
    return render_template('about.html', faculty=faculty)

@app.route('/programs')
def programs():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM courses")
    courses = cur.fetchall()
    cur.close()
    return render_template('programs.html', courses=courses)

@app.route('/downloads')
def downloads():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM downloads ORDER BY uploaded_at DESC")
    downloads = cur.fetchall()
    cur.close()
    return render_template('downloads.html', downloads=downloads)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        mobile = request.form.get('mobile', '')
        subject = request.form.get('subject', '')
        message = request.form['message']
        
        # Validation
        if not name or not email or not message:
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('contact'))
        
        if not validate_email(email):
            flash('Please enter a valid email address', 'danger')
            return redirect(url_for('contact'))
        
        if mobile and not validate_mobile(mobile):
            flash('Please enter a valid mobile number', 'danger')
            return redirect(url_for('contact'))
        
        # Save to database
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO feedback (name, email, mobile, subject, message) 
            VALUES (%s, %s, %s, %s, %s)
        """, (name, email, mobile, subject, message))
        mysql.connection.commit()
        cur.close()
        
        # ✅ Email send (without try block)
        msg = Message(
            subject=f"New Contact Message from {name}",
            recipients=['smroffi03@gmail.com']
        )
        
        msg.body = f"""
New Contact Message

Name: {name}
Email: {email}
Mobile: {mobile}
Subject: {subject}

Message:
{message}
"""
        
        mail.send(msg)

        flash('Thank you for your feedback! We will get back to you soon.', 'success')
        return redirect(url_for('contact'))
    
    return render_template('contact.html')

@app.route('/address')
def address():
    return render_template('address.html')

@app.route('/admission', methods=['GET', 'POST'])
def admission():
    if request.method == 'POST':
        # Get form data
        full_name = request.form['full_name']
        father_name = request.form['father_name']
        mother_name = request.form['mother_name']
        age = request.form['age']
        gender = request.form['gender']
        aadhaar = request.form['aadhaar']
        email = request.form['email']
        mobile = request.form['mobile']
        father_mobile = request.form['father_mobile']
        caste = request.form.get('caste', '')
        address = request.form['address']
        course = request.form.get('course', '')
        
        # File uploads
        tenth_file = request.files.get('tenth_marksheet')
        twelfth_file = request.files.get('twelfth_marksheet')
        
        tenth_path = None
        twelfth_path = None
        
        # Validation
        errors = []
        
        if not all([full_name, father_name, mother_name, age, gender, aadhaar, email, mobile, father_mobile, address]):
            errors.append('All fields marked with * are required')
        
        if not validate_aadhaar(aadhaar):
            errors.append('Aadhaar number must be 12 digits')
        
        if not validate_email(email):
            errors.append('Please enter a valid email address')
        
        if not validate_mobile(mobile):
            errors.append('Please enter a valid mobile number (10 digits, starting with 6-9)')
        
        if not validate_mobile(father_mobile):
            errors.append('Please enter a valid father\'s mobile number')
        
        try:
            age = int(age)
            if age < 15 or age > 60:
                errors.append('Age must be between 15 and 60')
        except ValueError:
            errors.append('Please enter a valid age')
        
        # Check uniqueness
        cur = mysql.connection.cursor()
        
        cur.execute("SELECT id FROM admissions WHERE aadhaar_number = %s", (aadhaar,))
        if cur.fetchone():
            errors.append('This Aadhaar number is already registered')
        
        cur.execute("SELECT id FROM admissions WHERE email = %s", (email,))
        if cur.fetchone():
            errors.append('This email is already registered')
        
        cur.execute("SELECT id FROM admissions WHERE mobile = %s", (mobile,))
        if cur.fetchone():
            errors.append('This mobile number is already registered')
        
        # Handle file uploads
        if tenth_file and allowed_file(tenth_file.filename):
            filename = secure_filename(f"tenth_{aadhaar}_{tenth_file.filename}")
            tenth_path = os.path.join('uploads', filename)
            tenth_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        if twelfth_file and allowed_file(twelfth_file.filename):
            filename = secure_filename(f"twelfth_{aadhaar}_{twelfth_file.filename}")
            twelfth_path = os.path.join('uploads', filename)
            twelfth_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        if errors:
            for error in errors:
                flash(error, 'danger')
            cur.close()
            return redirect(url_for('admission'))
        
        # Insert into database
        try:
            cur.execute("""
                INSERT INTO admissions (
                    full_name, father_name, mother_name, age, gender, 
                    aadhaar_number, email, mobile, father_mobile, caste, 
                    address, tenth_marksheet, twelfth_marksheet, course_applied
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (full_name, father_name, mother_name, age, gender, aadhaar, 
                  email, mobile, father_mobile, caste, address, tenth_path, 
                  twelfth_path, course))
            
            mysql.connection.commit()
            flash('Admission form submitted successfully! We will contact you soon.', 'success')
            
        except Exception as e:
            mysql.connection.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
        finally:
            cur.close()
        
        return redirect(url_for('admission'))
    
    # GET request - show form
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM courses")
    courses = cur.fetchall()
    cur.close()
    
    return render_template('admission.html', courses=courses)

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE username = %s AND password = %s", (username, password))
        admin = cur.fetchone()
        cur.close()
        
        if admin:
            session['admin_logged_in'] = True
            session['admin_id'] = admin['id']
            session['admin_username'] = admin['username']
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('admin/login.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_login_required
def admin_dashboard():
    cur = mysql.connection.cursor()
    
    # Get statistics
    cur.execute("SELECT COUNT(*) as total FROM admissions")
    total_admissions = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM admissions WHERE status = 'Pending'")
    pending_admissions = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM feedback WHERE status = 'New'")
    new_feedback = cur.fetchone()['total']
    
    cur.execute("SELECT COUNT(*) as total FROM courses")
    total_courses = cur.fetchone()['total']
    
    # Get recent admissions
    cur.execute("SELECT * FROM admissions ORDER BY applied_at DESC LIMIT 5")
    recent_admissions = cur.fetchall()
    
    # Get recent feedback
    cur.execute("SELECT * FROM feedback ORDER BY submitted_at DESC LIMIT 5")
    recent_feedback = cur.fetchall()
    
    cur.close()
    
    return render_template('admin/dashboard.html', 
                         total_admissions=total_admissions,
                         pending_admissions=pending_admissions,
                         new_feedback=new_feedback,
                         total_courses=total_courses,
                         recent_admissions=recent_admissions,
                         recent_feedback=recent_feedback)

@app.route('/admin/admissions')
@admin_login_required
def admin_admissions():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM admissions ORDER BY applied_at DESC")
    admissions = cur.fetchall()
    cur.close()
    return render_template('admin/admissions.html', admissions=admissions)

@app.route('/admin/admission/<int:id>')
@admin_login_required
def view_admission(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM admissions WHERE id = %s", (id,))
    admission = cur.fetchone()
    cur.close()
    return render_template('admin/view_admission.html', admission=admission)

@app.route('/admin/admission/update/<int:id>', methods=['POST'])
@admin_login_required
def update_admission_status(id):
    status = request.form['status']
    cur = mysql.connection.cursor()

    # Update status
    cur.execute("UPDATE admissions SET status = %s WHERE id = %s", (status, id))
    mysql.connection.commit()

    # Get student details
    cur.execute("SELECT full_name, email, course_applied FROM admissions WHERE id = %s", (id,))
    student = cur.fetchone()
    cur.close()

    if student:
        full_name = student['full_name']
        email = student['email']
        course = student['course_applied']

        if status == "Approved":
            subject = "Admission Approved - SR Classes"
            body = f"""Dear {full_name},

We are pleased to inform you that your admission for the {course} program has been **approved**. 

Congratulations on taking this step towards advancing your knowledge and skills. We look forward to welcoming you to SR Classes.

Best regards,
SHAIKH SAMIR
"""
        else:
            subject = "Admission Rejected - SR Classes"
            body = f"""Dear {full_name},

We regret to inform you that your admission for the {course} program has **not been approved** at this time. 

The decision was based on a discrepancy in the submitted documents. Please review your application and feel free to contact us for further clarification.

Best regards,
SHAIKH SAMIR
"""
        msg = Message(subject=subject, recipients=[email])
        msg.body = body
        mail.send(msg)

    flash('Admission status updated successfully', 'success')
    return redirect(url_for('admin_admissions'))

@app.route('/admin/admission/delete/<int:id>')
@admin_login_required
def delete_admission(id):
    cur = mysql.connection.cursor()
    
    # Get file paths before deleting
    cur.execute("SELECT tenth_marksheet, twelfth_marksheet FROM admissions WHERE id = %s", (id,))
    admission = cur.fetchone()
    
    if admission:
        # Delete files if they exist
        if admission['tenth_marksheet']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(admission['tenth_marksheet']))
            if os.path.exists(file_path):
                os.remove(file_path)
        
        if admission['twelfth_marksheet']:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(admission['twelfth_marksheet']))
            if os.path.exists(file_path):
                os.remove(file_path)
    
    cur.execute("DELETE FROM admissions WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    
    flash('Admission deleted successfully', 'success')
    return redirect(url_for('admin_admissions'))

import MySQLdb.cursors

@app.route('/admin/admission/edit/<int:id>', methods=['GET', 'POST'])
@admin_login_required
def edit_admission(id):
    cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # GET request: fetch current admission data
    cur.execute("SELECT * FROM admissions WHERE id=%s", (id,))
    admission = cur.fetchone()

    if request.method == 'POST':
        # Fetch & strip all form inputs
        full_name = request.form['full_name'].strip()
        age = request.form['age'].strip()
        father_name = request.form['father_name'].strip()
        mother_name = request.form['mother_name'].strip()
        gender = request.form['gender'].strip()
        caste = request.form['caste'].strip()
        email = request.form['email'].strip()
        mobile = request.form['mobile'].strip()
        father_mobile = request.form['father_mobile'].strip()
        aadhaar_number = request.form['aadhaar'].strip()
        address = request.form['address'].strip()
        course = request.form['course'].strip()
        status = request.form['status'].strip()

        # --------------------------
        # Backend Validation
        # --------------------------
    
        # Names: letters + spaces, 2-35 chars
        name_pattern = re.compile(r'^[A-Za-z ]{2,50}$')
        if not name_pattern.match(full_name):
            flash("Full Name must contain only letters and spaces (2-30 chars).", "danger")
            return redirect(request.url)
        if not name_pattern.match(father_name):
            flash("Father Name must contain only letters and spaces (2-30 chars).", "danger")
            return redirect(request.url)
        if mother_name and not name_pattern.match(mother_name):
            flash("Mother Name must contain only letters and spaces (2-35 chars).", "danger")
            return redirect(request.url)

        # Age: number 1-60
        if not age.isdigit() or int(age) < 15 or int(age) > 60:
            flash("Age must be a number between 15 and 60.", "danger")
            return redirect(request.url)

        # Mobile: exactly 10 digits
        if not re.fullmatch(r'\d{10}', mobile):
            flash("Mobile number must be exactly 10 digits.", "danger")
            return redirect(request.url)
        if not re.fullmatch(r'\d{10}', father_mobile):
            flash("Father Mobile number must be exactly 10 digits.", "danger")
            return redirect(request.url)

        # Email: valid format (basic check)
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}$')
        if not email_pattern.match(email):
            flash("Enter a valid email address.", "danger")
            return redirect(request.url)

        # Aadhaar: exactly 12 digits
        if not re.fullmatch(r'\d{12}', aadhaar_number):
            flash("Aadhaar number must be exactly 12 digits.", "danger")
            return redirect(request.url)

        # Address: minimum 5 characters
        if len(address) < 5:
            flash("Address must be at least 5 characters long.", "danger")
            return redirect(request.url)

        # Gender, Caste, Status: basic check
        if gender not in ['Male', 'Female', 'Other']:
            flash("Select a valid Gender.", "danger")
            return redirect(request.url)
        valid_castes = ['General','OBC','SC','ST','VJNT','SBC','EWS','Minority']
        if caste not in valid_castes:
            flash("Select a valid Caste.", "danger")
            return redirect(request.url)
        if status not in ['Pending','Approved','Rejected']:
            flash("Select a valid Status.", "danger")
            return redirect(request.url)
        
         # -------------------------
        # Duplicate Aadhaar Check
        # -------------------------
        cur.execute("SELECT id FROM admissions WHERE aadhaar_number=%s AND id != %s", (aadhaar_number, id))
        existing = cur.fetchone()
        if existing:
            flash(f"Aadhaar number {aadhaar_number} is already used by another student.", "danger")
            return redirect(request.url)


        # --------------------------
        # Update DB
        # --------------------------
        cur.execute("""
            UPDATE admissions SET
                full_name=%s,
                age=%s,
                father_name=%s,
                mother_name=%s,
                gender=%s,
                caste=%s,
                email=%s,
                mobile=%s,
                father_mobile=%s,
                aadhaar_number=%s,
                address=%s,
                course_applied=%s,
                status=%s
            WHERE id=%s
        """, (
            full_name,
            age,
            father_name,
            mother_name,
            gender,
            caste,
            email,
            mobile,
            father_mobile,
            aadhaar_number,
            address,
            course,
            status,
            id
        ))

        mysql.connection.commit()
        flash("Admission updated successfully.", "success")
        return redirect(url_for('admin_admissions'))

    cur.close()
    return render_template("admin/edit_admission.html", admission=admission)

UPLOAD_FOLDER = "static/uploads"

@app.route('/admin/admission/add', methods=['GET', 'POST'])
@admin_login_required
def add_student():
    if request.method == 'POST':
        # -------------------------
        # Fetch and clean inputs
        # -------------------------
        full_name = request.form['full_name'].strip()
        age = request.form['age'].strip()
        father_name = request.form['father_name'].strip()
        mother_name = request.form['mother_name'].strip()
        gender = request.form['gender'].strip()
        caste = request.form['caste'].strip()
        email = request.form['email'].strip()
        mobile = request.form['mobile'].strip()
        father_mobile = request.form['father_mobile'].strip()
        aadhaar_number = request.form['aadhaar'].strip()
        address = request.form['address'].strip()
        course = request.form['course'].strip()
        status = request.form['status'].strip()

        # -------------------------
        # Backend Validations
        # -------------------------
        name_pattern = re.compile(r'^[A-Za-z ]{2,50}$')
        if not name_pattern.match(full_name):
            flash("Full Name must contain only letters and spaces (2-50 chars).", "danger")
            return redirect(request.url)
        if not name_pattern.match(father_name):
            flash("Father Name must contain only letters and spaces (2-50 chars).", "danger")
            return redirect(request.url)
        if mother_name and not name_pattern.match(mother_name):
            flash("Mother Name must contain only letters and spaces (2-50 chars).", "danger")
            return redirect(request.url)

        if not age.isdigit() or int(age) < 15 or int(age) > 60:
            flash("Age must be a number between 15 and 60.", "danger")
            return redirect(request.url)

        if not re.fullmatch(r'\d{10}', mobile):
            flash("Mobile number must be exactly 10 digits.", "danger")
            return redirect(request.url)
        if not re.fullmatch(r'\d{10}', father_mobile):
            flash("Father Mobile number must be exactly 10 digits.", "danger")
            return redirect(request.url)

        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-z]{2,}$')
        if not email_pattern.match(email):
            flash("Enter a valid email address.", "danger")
            return redirect(request.url)

        if not re.fullmatch(r'\d{12}', aadhaar_number):
            flash("Aadhaar number must be exactly 12 digits.", "danger")
            return redirect(request.url)

        if len(address) < 5:
            flash("Address must be at least 5 characters long.", "danger")
            return redirect(request.url)

        # Validate dropdown selections
        valid_genders = ['Male', 'Female', 'Other']
        valid_castes = ['General','OBC','SC','ST','VJNT','SBC','EWS','Minority']
        valid_statuses = ['Pending','Approved']
        valid_courses = ['MS-CIT','Tally ERP 9','C Programming','C++ Programming',
                         'Java Programming','Python Programming','English Communication']

        if gender not in valid_genders:
            flash("Select a valid Gender.", "danger")
            return redirect(request.url)
        if caste not in valid_castes:
            flash("Select a valid Caste.", "danger")
            return redirect(request.url)
        if status not in valid_statuses:
            flash("Select a valid Status.", "danger")
            return redirect(request.url)
        if course not in valid_courses:
            flash("Select a valid Course.", "danger")
            return redirect(request.url)

        # -------------------------
        # Duplicate Email & Aadhaar Check
        # -------------------------
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT id FROM admissions WHERE email=%s OR aadhaar_number=%s", (email, aadhaar_number))
        existing = cur.fetchone()
        if existing:
            flash("Duplicate Email or Aadhaar found. Entry not saved.", "danger")
            return redirect(request.url)

        # -------------------------
        # Insert into Database
        # Mobile duplicates allowed
        # -------------------------
        try:
            cur.execute("""
                INSERT INTO admissions (
                    full_name, age, father_name, mother_name,
                    gender, caste, email, mobile, father_mobile,
                    aadhaar_number, address, course_applied, status
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                full_name, age, father_name, mother_name,
                gender, caste, email, mobile, father_mobile,
                aadhaar_number, address, course, status
            ))
            mysql.connection.commit()
            flash("Student added successfully.", "success")

        except MySQLdb.IntegrityError as e:
            mysql.connection.rollback()
            # Only mobile duplicates are ignored here
            if "mobile" in str(e):
                flash("Student added successfully (duplicate mobile allowed).", "success")
            else:
                flash("Database error: " + str(e), "danger")
                return redirect(request.url)

        cur.close()
        return redirect(url_for('admin_admissions'))

    # GET request
    return render_template("admin/add_student.html")

@app.route('/admin/courses')
@admin_login_required
def admin_courses():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM courses")
    courses = cur.fetchall()
    cur.close()
    return render_template('admin/courses.html', courses=courses)

@app.route('/admin/course/add', methods=['POST'])
@admin_login_required
def add_course():
    course_name = request.form['course_name']
    description = request.form['description']
    duration = request.form['duration']
    fees = request.form['fees']
    syllabus = request.form.get('syllabus', '')
    
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO courses (course_name, description, duration, fees, syllabus) 
        VALUES (%s, %s, %s, %s, %s)
    """, (course_name, description, duration, fees, syllabus))
    mysql.connection.commit()
    cur.close()
    
    flash('Course added successfully', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/course/edit/<int:id>', methods=['POST'])
@admin_login_required
def edit_course(id):
    course_name = request.form['course_name']
    description = request.form['description']
    duration = request.form['duration']
    fees = request.form['fees']
    syllabus = request.form.get('syllabus', '')
    
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE courses 
        SET course_name=%s, description=%s, duration=%s, fees=%s, syllabus=%s 
        WHERE id=%s
    """, (course_name, description, duration, fees, syllabus, id))
    mysql.connection.commit()
    cur.close()
    
    flash('Course updated successfully', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/course/delete/<int:id>')
@admin_login_required
def delete_course(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM courses WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    
    flash('Course deleted successfully', 'success')
    return redirect(url_for('admin_courses'))

@app.route('/admin/downloads')
@admin_login_required
def admin_downloads():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM downloads ORDER BY uploaded_at DESC")
    downloads = cur.fetchall()
    cur.close()
    return render_template('admin/downloads.html', downloads=downloads)

@app.route('/admin/download/add', methods=['POST'])
@admin_login_required
def add_download():
    title = request.form['title']
    description = request.form['description']
    file = request.files.get('file')
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        file_type = filename.rsplit('.', 1)[1].lower()
        
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO downloads (title, description, file_path, file_type) 
            VALUES (%s, %s, %s, %s)
        """, (title, description, file_path, file_type))
        mysql.connection.commit()
        cur.close()
        
        flash('Download added successfully', 'success')
    else:
        flash('Invalid file type', 'danger')
    
    return redirect(url_for('admin_downloads'))

@app.route('/admin/download/delete/<int:id>')
@admin_login_required
def delete_download(id):
    cur = mysql.connection.cursor()
    
    # Get file path before deleting
    cur.execute("SELECT file_path FROM downloads WHERE id = %s", (id,))
    download = cur.fetchone()
    
    if download and download['file_path']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(download['file_path']))
        if os.path.exists(file_path):
            os.remove(file_path)
    
    cur.execute("DELETE FROM downloads WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    
    flash('Download deleted successfully', 'success')
    return redirect(url_for('admin_downloads'))

@app.route('/admin/feedback')
@admin_login_required
def admin_feedback():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM feedback ORDER BY submitted_at DESC")
    feedbacks = cur.fetchall()
    cur.close()

    return render_template('admin/feedback.html', feedbacks=feedbacks)

@app.route('/admin/feedback/update/<int:id>', methods=['POST'])
@admin_login_required
def update_feedback_status(id):
    status = request.form['status']
    cur = mysql.connection.cursor()
    cur.execute("UPDATE feedback SET status = %s WHERE id = %s", (status, id))
    mysql.connection.commit()
    cur.close()
    flash('Feedback status updated successfully', 'success')
    return redirect(url_for('admin_feedback'))

@app.route('/admin/feedback/delete/<int:id>')
@admin_login_required
def delete_feedback(id):
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM feedback WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    flash('Feedback deleted successfully', 'success')
    return redirect(url_for('admin_feedback'))

@app.route('/admin/faculty')
@admin_login_required
def admin_faculty():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM faculty")
    faculty = cur.fetchall()
    cur.close()
    return render_template('admin/faculty.html', faculty=faculty)

@app.route('/admin/faculty/add', methods=['POST'])
@admin_login_required
def add_faculty():
    name = request.form['name']
    qualification = request.form['qualification']
    expertise = request.form['expertise']
    experience = request.form['experience']
    joined_at = request.form['joined_at']
    
    photo = request.files.get('photo')
    photo_path = None
    
    if photo and allowed_file(photo.filename):
        filename = secure_filename(photo.filename)
        photo_path = os.path.join('uploads', filename)
        photo.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    
    cur = mysql.connection.cursor()
    cur.execute("""
        INSERT INTO faculty (name, qualification, expertise, experience, photo, joined_at) 
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (name, qualification, expertise, experience, photo_path, joined_at))
    mysql.connection.commit()
    cur.close()
    
    flash('Faculty added successfully', 'success')
    return redirect(url_for('admin_faculty'))

@app.route('/admin/faculty/delete/<int:id>')
@admin_login_required
def delete_faculty(id):
    cur = mysql.connection.cursor()
    
    # Get photo path before deleting
    cur.execute("SELECT photo FROM faculty WHERE id = %s", (id,))
    faculty = cur.fetchone()
    
    if faculty and faculty['photo']:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(faculty['photo']))
        if os.path.exists(file_path):
            os.remove(file_path)
    
    cur.execute("DELETE FROM faculty WHERE id = %s", (id,))
    mysql.connection.commit()
    cur.close()
    
    flash('Faculty deleted successfully', 'success')
    return redirect(url_for('admin_faculty'))

if __name__ == '__main__':
    app.run(debug=True)