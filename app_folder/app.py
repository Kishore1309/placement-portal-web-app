from flask import Flask, render_template, request, redirect, session, flash
import sqlite3

def init_db():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        phone TEXT,
        department TEXT,
        year TEXT,
        cgpa REAL,
        resume_filename TEXT
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS companies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT,
        password TEXT,
        hr_contact TEXT,
        website TEXT,
        status TEXT DEFAULT 'Pending'
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        company_id INTEGER,
        title TEXT,
        description TEXT,
        eligibility TEXT,
        deadline TEXT,
        status TEXT DEFAULT 'Pending'
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        job_id INTEGER,
        status TEXT DEFAULT 'Applied'
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )
    ''')

    cursor.execute("SELECT * FROM admins WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ("admin", "kishore@13")
        )

    conn.commit()
    conn.close()

init_db()


app = Flask(__name__)
app.secret_key = "mysecretkey"


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        phone = request.form.get('phone', '')
        department = request.form.get('department', '')
        year = request.form.get('year', '')
        cgpa = request.form.get('cgpa', None)

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            """INSERT INTO students 
            (name, email, password, phone, department, year, cgpa) 
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, email, password, phone, department, year, cgpa)
        )

        conn.commit()
        conn.close()

        flash("Registration successful! Please login.")
        return redirect('/login')

    return render_template('register.html')


@app.route('/company_register', methods=['GET', 'POST'])
def company_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hr_contact = request.form.get('hr_contact', '')
        website = request.form.get('website', '')

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            "INSERT INTO companies (name, email, password, hr_contact, website, status) VALUES (?, ?, ?, ?, ?, ?)",
            (name, email, password, hr_contact, website, 'Pending')
        )

        conn.commit()
        conn.close()

        flash("Company registered successfully! Please login.")
        return redirect('/login')

    return render_template('company_register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form['role']
        email = request.form['email']
        password = request.form['password']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        if role == 'student':
            cursor.execute(
                "SELECT * FROM students WHERE email=? AND password=?",
                (email, password)
            )
            user = cursor.fetchone()

            if user:
                session['user_id'] = user[0]
                session['user_name'] = user[1]
                session['role'] = 'student'
                return redirect('/dashboard')

        elif role == 'company':
            email = request.form['email'].strip()
            password = request.form['password'].strip()

            cursor.execute(
                "SELECT * FROM companies WHERE email=? AND password=?",
                (email, password)
            )
            user = cursor.fetchone()
            
            if user:
                status = user[6]
                if status == 'Approved':
                    session['company_id'] = user[0]
                    session['company_name'] = user[1]
                    conn.close()
                    return redirect('/company_dashboard')
                elif status == 'Pending':
                    flash("Your company registration is pending admin approval. Please wait.")
                    return redirect('/login')
                elif status == 'Rejected':
                    flash("Your company registration has been REJECTED by admin.")
                    return redirect('/login')
                else:
                    flash("Invalid email or password")
                    return redirect('/login')
                    
        elif role == 'admin':
            cursor.execute(
                "SELECT * FROM admins WHERE username=? AND password=?",
                (email, password)
            )
            admin = cursor.fetchone()

            if admin:
                session['admin_id'] = admin[0]
                session['admin_name'] = admin[1]
                session['role'] = 'admin'
                conn.close()
                return redirect('/admin_dashboard')

        conn.close()
        flash("Invalid email/password or role mismatch")
        return redirect('/login')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    
    student_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    student = cursor.execute("SELECT * FROM students WHERE id=?", (student_id,)).fetchone()
    
    stats = cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status='Shortlisted' THEN 1 ELSE 0 END) as shortlisted,
            SUM(CASE WHEN status='Selected' THEN 1 ELSE 0 END) as selected,
            SUM(CASE WHEN status='Rejected' THEN 1 ELSE 0 END) as rejected
        FROM applications WHERE student_id=?
    ''', (student_id,)).fetchone()
    
    recent_jobs = cursor.execute('''
        SELECT jobs.*, companies.name 
        FROM jobs 
        JOIN companies ON jobs.company_id = companies.id 
        WHERE jobs.status='Approved'
        ORDER BY jobs.id DESC LIMIT 5
    ''').fetchall()
    
    
    my_applications = cursor.execute('''
        SELECT jobs.title, companies.name, applications.status, applications.job_id
        FROM applications
        JOIN jobs ON applications.job_id = jobs.id
        JOIN companies ON jobs.company_id = companies.id
        WHERE applications.student_id=?
        ORDER BY applications.id DESC
    ''', (student_id,)).fetchall()
    
    conn.close()
    
    return render_template('student_dashboard.html',
                           student=student,
                           total_applied=stats[0] or 0,
                           shortlisted=stats[1] or 0,
                           selected=stats[2] or 0,
                           rejected=stats[3] or 0,
                           recent_jobs=recent_jobs,
                           my_applications=my_applications)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


@app.route('/company_dashboard')
def company_dashboard():
    if 'company_id' not in session:
        return redirect('/login')
    
    company_id = session['company_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM companies WHERE id=?", (company_id,))
    company = cursor.fetchone()
    
    cursor.execute('''
    SELECT jobs.*, COUNT(applications.id) as app_count 
    FROM jobs 
    LEFT JOIN applications ON jobs.id = applications.job_id 
    WHERE jobs.company_id=? 
    GROUP BY jobs.id
    ''', (company_id,))
    jobs = cursor.fetchall()
    
    conn.close()
    
    return render_template('company_dashboard.html',
                       name=session['company_name'],
                       company_email=company[2],
                       hr_contact=company[4],
                       website=company[5],
                       company_status=company[6],
                       jobs=jobs)

@app.route('/post_job', methods=['GET', 'POST'])
def post_job():
    if 'company_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        eligibility = request.form['eligibility']
        deadline = request.form['deadline']
        company_id = session['company_id']

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute(
            '''INSERT INTO jobs 
            (company_id, title, description, eligibility, deadline, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')''',
            (company_id, title, description, eligibility, deadline)
        )

        conn.commit()
        conn.close()

        flash("Placement job created successfully!")
        return redirect('/company_dashboard')

    return render_template('post_job.html')


@app.route('/jobs')
def jobs():
    if 'user_id' not in session:
        return redirect('/login')
    
    student_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get all approved jobs
    cursor.execute('''
    SELECT jobs.*, companies.name 
    FROM jobs 
    JOIN companies ON jobs.company_id = companies.id 
    WHERE jobs.status='Approved'
    ''')
    jobs = cursor.fetchall()
    
    # Get job IDs that student has already applied to
    cursor.execute('''
    SELECT job_id FROM applications WHERE student_id=?
    ''', (student_id,))
    applied_jobs = cursor.fetchall()
    applied_job_ids = [job[0] for job in applied_jobs]
    
    conn.close()
    
    return render_template('jobs.html', jobs=jobs, applied_job_ids=applied_job_ids)

@app.route('/apply/<int:job_id>')
def apply(job_id):
    if 'user_id' not in session:
        return redirect('/login')

    student_id = session['user_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM applications WHERE student_id=? AND job_id=?",
        (student_id, job_id)
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        flash("Already applied!")
        return redirect('/dashboard') 

    cursor.execute(
        "INSERT INTO applications (student_id, job_id) VALUES (?, ?)",
        (student_id, job_id)
    )

    conn.commit()
    conn.close()

    flash("Applied successfully!")
    return redirect('/dashboard')


@app.route('/view_applicants/<int:job_id>')
def view_applicants_for_job(job_id):
    if 'company_id' not in session:
        return redirect('/login')

    company_id = session['company_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id=? AND company_id=?", (job_id, company_id))
    job = cursor.fetchone()
    
    if not job:
        conn.close()
        flash("Job not found or unauthorized")
        return redirect('/company_dashboard')

    cursor.execute('''
    SELECT applications.id, students.name, students.email, applications.status
    FROM applications
    JOIN students ON applications.student_id = students.id
    WHERE applications.job_id=?
    ''', (job_id,))

    applicants = cursor.fetchall()
    conn.close()

    return render_template('view_applicants.html', applicants=applicants, job=job)


@app.route('/edit_job/<int:job_id>', methods=['GET', 'POST'])
def edit_job(job_id):
    if 'company_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id=? AND company_id=?", (job_id, session['company_id']))
    job = cursor.fetchone()

    if not job:
        conn.close()
        flash("Job not found or unauthorized")
        return redirect('/company_dashboard')

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        eligibility = request.form['eligibility']
        deadline = request.form['deadline']

        cursor.execute('''
        UPDATE jobs 
        SET title=?, description=?, eligibility=?, deadline=?
        WHERE id=?
        ''', (title, description, eligibility, deadline, job_id))

        conn.commit()
        conn.close()
        flash("Job updated successfully!")
        return redirect('/company_dashboard')

    conn.close()
    return render_template('edit_job.html', job=job)


@app.route('/delete_job/<int:job_id>')
def delete_job(job_id):
    if 'company_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM jobs WHERE id=? AND company_id=?", (job_id, session['company_id']))
    job = cursor.fetchone()

    if not job:
        conn.close()
        flash("Job not found or unauthorized")
        return redirect('/company_dashboard')

    cursor.execute("DELETE FROM applications WHERE job_id=?", (job_id,))
    cursor.execute("DELETE FROM jobs WHERE id=?", (job_id,))

    conn.commit()
    conn.close()
    flash("Job deleted successfully!")
    return redirect('/company_dashboard')


@app.route('/view_applicants_all')
def view_applicants_all():
    if 'company_id' not in session:
        return redirect('/login')

    company_id = session['company_id']

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('''
    SELECT applications.id, students.name, jobs.title, applications.status, jobs.id as job_id
    FROM applications
    JOIN students ON applications.student_id = students.id
    JOIN jobs ON applications.job_id = jobs.id
    WHERE jobs.company_id=?
    ''', (company_id,))

    data = cursor.fetchall()
    conn.close()

    return render_template('view_applicants_all.html', data=data)


@app.route('/update_status/<int:app_id>/<status>')
def update_status(app_id, status):
    if 'company_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("SELECT job_id FROM applications WHERE id=?", (app_id,))
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        flash("Application not found")
        return redirect('/company_dashboard')
    
    job_id = result[0]

    cursor.execute(
        "UPDATE applications SET status=? WHERE id=?",
        (status, app_id)
    )

    conn.commit()
    conn.close()

    flash(f"Application status updated to {status}")

    return redirect(f'/view_applicants/{job_id}')


@app.route('/admin_dashboard')
def admin_dashboard():
    if session.get('role') != 'admin':
        return redirect('/login')

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    students = cursor.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    companies = cursor.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    jobs = cursor.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    applications = cursor.execute("SELECT COUNT(*) FROM applications").fetchone()[0]
    
    pending_companies = cursor.execute("SELECT * FROM companies WHERE status='Pending'").fetchall()
    pending_jobs = cursor.execute('''
        SELECT jobs.*, companies.name 
        FROM jobs 
        JOIN companies ON jobs.company_id = companies.id 
        WHERE jobs.status='Pending'
    ''').fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
                           students=students,
                           companies=companies,
                           jobs=jobs,
                           applications=applications,
                           pending_companies=pending_companies, 
                           pending_jobs=pending_jobs)


@app.route('/approve_company/<int:id>')
def approve_company(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("UPDATE companies SET status='Approved' WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/admin_companies')

@app.route('/reject_company/<int:id>')
def reject_company(id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute("UPDATE companies SET status='Rejected' WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/admin_companies')


@app.route('/approve_job/<int:job_id>')
def approve_job(job_id):
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status='Approved' WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    flash("Job approved successfully!")
    return redirect('/admin_dashboard')

@app.route('/reject_job/<int:job_id>')
def reject_job(job_id):
    if session.get('role') != 'admin':
        return redirect('/login')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE jobs SET status='Rejected' WHERE id=?", (job_id,))
    conn.commit()
    conn.close()
    flash("Job rejected!")
    return redirect('/admin_dashboard')
    

@app.route('/admin_students')
def admin_students():
    if session.get('role') != 'admin':
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    students = cursor.execute("SELECT * FROM students").fetchall()
    conn.close()
    
    return render_template('admin_students.html', students=students)


@app.route('/admin_companies')
def admin_companies():
    if session.get('role') != 'admin':
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    companies = cursor.execute("SELECT * FROM companies ORDER BY status").fetchall()
    conn.close()
    
    return render_template('admin_companies.html', companies=companies)


@app.route('/admin_applications')
def admin_applications():
    if session.get('role') != 'admin':
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    applications = cursor.execute('''
        SELECT applications.*, students.name as student_name, jobs.title as job_title, companies.name as company_name
        FROM applications
        JOIN students ON applications.student_id = students.id
        JOIN jobs ON applications.job_id = jobs.id
        JOIN companies ON jobs.company_id = companies.id
        ORDER BY applications.id DESC
    ''').fetchall()
    conn.close()
    
    return render_template('admin_applications.html', applications=applications)


@app.route('/admin_jobs')
def admin_jobs():
    if session.get('role') != 'admin':
        return redirect('/login')
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    jobs = cursor.execute('''
        SELECT jobs.*, companies.name as company_name
        FROM jobs
        JOIN companies ON jobs.company_id = companies.id
        ORDER BY 
            CASE jobs.status
                WHEN 'Pending' THEN 1
                WHEN 'Approved' THEN 2
                WHEN 'Rejected' THEN 3
            END
    ''').fetchall()
    conn.close()
    
    return render_template('admin_jobs.html', jobs=jobs)


@app.route('/job_details/<int:job_id>')
def job_details(job_id):
    if 'user_id' not in session:
        return redirect('/login')
    
    student_id = session['user_id']
    
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Get job details
    cursor.execute('''
    SELECT jobs.*, companies.name 
    FROM jobs 
    JOIN companies ON jobs.company_id = companies.id 
    WHERE jobs.id=?
    ''', (job_id,))
    job = cursor.fetchone()
    
    # Check if student has already applied
    cursor.execute('''
    SELECT * FROM applications WHERE student_id=? AND job_id=?
    ''', (student_id, job_id))
    already_applied = cursor.fetchone() is not None
    
    conn.close()
    
    return render_template('job_details.html', job=job, already_applied=already_applied)

if __name__ == '__main__':
    app.run(debug=True, port=4000)