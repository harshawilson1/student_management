from flask import Flask, Response, render_template, request, redirect, session,abort, url_for, flash,send_file
import mysql.connector
from pendulum import today
from werkzeug.security import generate_password_hash, check_password_hash
from config import MYSQL_CONFIG
import csv
from datetime import date,datetime,timedelta 
import calendar
import os
from werkzeug.utils import secure_filename
import uuid
import secrets
import json
from io import StringIO
import datetime

GENERAL_HOLIDAYS = [
    {"date": "2026-01-26", "title": "Republic Day"},
    {"date": "2026-02-15", "title": "Maha Shivratri"},
    {"date": "2026-02-19", "title": "Chhatrapati Shivaji Maharaj Jayanti"},
    {"date": "2026-03-03", "title": "Holi (Second Day)"},
    {"date": "2026-03-19", "title": "Gudi Padwa"},
    {"date": "2026-03-21", "title": "Ramzan Eid (Eid‑ul‑Fitr)"},
    {"date": "2026-03-26", "title": "Ram Navami"},
    {"date": "2026-03-31", "title": "Mahavir Janmakalyanak"},
    {"date": "2026-04-03", "title": "Good Friday"},
    {"date": "2026-04-14", "title": "Dr. Babasaheb Ambedkar Jayanti"},
    {"date": "2026-05-01", "title": "Maharashtra Day"},
    {"date": "2026-05-01", "title": "Buddha Pournima"},
    {"date": "2026-05-28", "title": "Bakri Id (Eid‑ul‑Zuha)"},
    {"date": "2026-06-26", "title": "Moharram"},
    {"date": "2026-08-15", "title": "Independence Day"},
    {"date": "2026-08-15", "title": "Parsi New Year (Shahenshahi)"},
    {"date": "2026-08-26", "title": "Id‑E‑Milad"},
    {"date": "2026-09-14", "title": "Ganesh Chaturthi"},
    {"date": "2026-10-02", "title": "Mahatma Gandhi Jayanti"},
    {"date": "2026-10-20", "title": "Dasara"},
    {"date": "2026-11-08", "title": "Diwali Amavasya (Laxmi Pujan)"},
    {"date": "2026-11-10", "title": "Diwali (Bali Pratipada)"},
    {"date": "2026-11-11", "title": "Bhaubeej"},
    {"date": "2026-11-24", "title": "Guru Nanak Jayanti"},
    {"date": "2026-12-25", "title": "Christmas"},
]


app = Flask(__name__)
app.secret_key = "secret_key"



def get_connection():
    print("MYSQL CONFIG USED:", MYSQL_CONFIG)
    return mysql.connector.connect(**MYSQL_CONFIG)

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("login.html")

# ---------------- ADMIN LOGIN ----------------
@app.route("/admin_login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_connection()
        cur = conn.cursor(dictionary=True,buffered=True)
        cur.execute("SELECT * FROM admins WHERE username=%s", (username,))
        admin = cur.fetchone()
        cur.close()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session["admin"] = username
            session["role"] = "admin"
            return redirect("/dashboard")

        return render_template("admin_login.html", error="Invalid credentials")

    return render_template("admin_login.html")

# ---------------- STUDENT LOGIN ----------------
@app.route("/student_login", methods=["GET", "POST"])
def student_login():
    if request.method == "POST":
        # Use the same name as your input field
        name = request.form.get("name")
        password = request.form.get("password")

        if not name or not password:
            return render_template("student_login.html", error="Please fill in all fields")

        conn = get_connection()
        cur = conn.cursor(dictionary=True,buffered=True)
        # Query using the correct column
        cur.execute("SELECT * FROM students WHERE name=%s", (name,))
        student = cur.fetchone()
        cur.close()
        conn.close()

        if student and check_password_hash(student["password"], password):
            session["user"] = student["name"]
            session["role"] = "student"
            session["student_id"] = student["id"]
            return redirect("/student_dashboard")

        return render_template("student_login.html", error="Invalid credentials")

    return render_template("student_login.html")


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    admin_id = session.get('admin_id')
    today = date.today()
    if session.get("role") != "admin":
        return abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    # ---------------- TOTAL COUNTS ----------------
    cur.execute("SELECT COUNT(*) AS total_students FROM students")
    total_students = cur.fetchone()["total_students"]

    cur.execute("SELECT COUNT(*) AS total_courses FROM courses")
    total_courses = cur.fetchone()["total_courses"]

    # ---------------- ATTENDANCE TREND ----------------
    cur.execute("""
        SELECT attendance_date AS day,
               SUM(attended)/NULLIF(SUM(total),0)*100 AS percentage
        FROM attendance
        GROUP BY day
        ORDER BY day ASC
        LIMIT 7
    """)
    attendance_data = cur.fetchall()
    attendance_labels = [row['day'].strftime('%Y-%m-%d') for row in attendance_data] if attendance_data else []
    attendance_values = [float(row['percentage']) for row in attendance_data] if attendance_data else []

    # ---------------- FEES TREND ----------------
    cur.execute("""
        SELECT DATE(payment_date) AS day, SUM(amount) AS total
        FROM fees_payments
        GROUP BY day
        ORDER BY day ASC
        LIMIT 7
    """)
    fees_data = cur.fetchall()
    fees_labels = [row['day'].strftime('%Y-%m-%d') for row in fees_data] if fees_data else []
    fees_values = [float(row['total']) for row in fees_data] if fees_data else []

    cur.close()
    conn.close()

    # ---------------- CALENDAR ----------------
    today_date = date.today()
    year = today_date.year
    month = today_date.month

    # Create weeks for the month
    cal = calendar.Calendar()
    weeks = []
    week = []

    for day in cal.itermonthdays(year, month):
        if day == 0:
            week.append(None)  # padding
        else:
            week.append(day)
        if len(week) == 7:
            weeks.append(week)
            week = []

    if week:  # last week padding
        while len(week) < 7:
            week.append(None)
        weeks.append(week)

    # Day names for calendar header
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Upcoming holidays
    upcoming_holidays = []
    for h in GENERAL_HOLIDAYS:
        h_day, h_month = map(int, h["date"].split("-"))
        holiday_date = date(today_date.year, h_month, h_day)
        if holiday_date >= today_date:
            upcoming_holidays.append({
                'date': holiday_date,
                'title': h['title']
            })
    
    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    cur.execute("""
        SELECT c.id AS class_id, co.name AS course_name, c.start_time, c.end_time
        FROM classes c
        JOIN courses co ON c.course_id = co.id
        WHERE c.admin_id = %s AND c.date = %s
        ORDER BY c.start_time
    """, (admin_id, today))

    todays_classes = cur.fetchall()

    cur.close()
    conn.close()

    return render_template(
        "dashboard.html",
        total_students=total_students,
        total_courses=total_courses,
        attendance_labels=attendance_labels,
        attendance_values=attendance_values,
        fees_labels=fees_labels,
        fees_values=fees_values,
        weeks=weeks,
        day_names=day_names,
        upcoming_holidays=upcoming_holidays,
        month_name=calendar.month_name[month],
        month=month,
        todays_classes=todays_classes,
        year=year
    )


# ---------------- STUDENT DASHBOARD ----------------
@app.route("/student_dashboard")
def student_dashboard():
    if "student_id" not in session:
        return redirect("/student_login")

    student_id = session["student_id"]

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    # ---- Total Courses ----
    cur.execute("""
        SELECT COUNT(*) AS total_courses
        FROM student_courses
        WHERE student_id = %s AND status='approved'
    """, (student_id,))
    total_courses = cur.fetchone()["total_courses"]

    # ---- Points per Subject ----
    cur.execute("""
        SELECT 
            c.name AS subject,
            COALESCE(p.points, 0) AS points
        FROM student_courses sc
        JOIN courses c ON sc.course_id = c.id
        LEFT JOIN points p 
            ON p.student_id = sc.student_id 
           AND p.subject_id = sc.course_id
        WHERE sc.student_id = %s AND sc.status='approved'
        ORDER BY c.name
    """, (student_id,))
    points_data = cur.fetchall()

    # ---- Attendance Percentage ----
    cur.execute("""
        SELECT 
            COALESCE(SUM(attended), 0) AS attended,
            COALESCE(SUM(total), 0) AS total
        FROM attendance
        WHERE student_id = %s
    """, (student_id,))
    attendance = cur.fetchone()
    total_attendance = round((attendance["attended"] / attendance["total"]) * 100, 2) if attendance["total"] > 0 else 0

    # ---- Fees Paid ----
    cur.execute("""
    SELECT 
        COALESCE(SUM(total_fees), 0) AS total_fees,
        COALESCE(SUM(paid_fees), 0) AS total_paid
    FROM fees
    WHERE student_id = %s
""", (student_id,))

    fees_row = cur.fetchone()
    total_fees = fees_row["total_fees"]
    total_paid = fees_row["total_paid"]
    remaining = total_fees - total_paid

    # ---- Study Materials & Course Plans per Enrolled Course ----
    cur.execute("""
        SELECT c.id AS course_id, c.name AS course_name
        FROM student_courses sc
        JOIN courses c ON sc.course_id = c.id
        WHERE sc.student_id = %s AND sc.status='approved'
    """, (student_id,))
    courses = cur.fetchall()

    course_data = []
    for course in courses:
        # Study Materials
        cur.execute("""
            SELECT title, file_path
            FROM study_materials
            WHERE course_id = %s
            ORDER BY upload_date DESC
        """, (course['course_id'],))
        materials = cur.fetchall()

        # Course Plan
        cur.execute("""
            SELECT week_no, topic, description
            FROM course_plans
            WHERE course_id = %s
            ORDER BY week_no
        """, (course['course_id'],))
        plans = cur.fetchall()

        course_data.append({
            "course": course,
            "materials": materials,
            "plans": plans
        })
    enrolled_courses = [c['course'] for c in course_data]


    cur.close()
    conn.close()

    return render_template(
        "student_dashboard.html",
        total_courses=total_courses,
        points_data=points_data,
        total_attendance=f"{total_attendance}%",
        total_fees=total_fees,
        total_paid=total_paid,
        remaining=remaining,
        course_data=course_data,
        enrolled_courses=enrolled_courses  # <-- new data for materials & plans
    )

UPLOAD_FOLDER_MATERIALS = 'static/uploads/study_materials'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'jpg', 'png'}

app.config['UPLOAD_FOLDER_MATERIALS'] = UPLOAD_FOLDER_MATERIALS

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# ---- Add Study Material ----
# Admin Add Study Material

@app.route("/admin/add_material", methods=["GET", "POST"])
def add_material():
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    # 🔹 Fetch all courses (subjects)
    cur.execute("SELECT id, name FROM courses ORDER BY name")
    courses = cur.fetchall()

    if request.method == "POST":
        course_id = request.form.get("course_id")
        title = request.form.get("title")
        file = request.files.get("file")

        if not course_id or not file:
            flash("Please select a subject and upload a file")
            return redirect(request.url)

        filename = secure_filename(file.filename)
        os.makedirs(app.config["UPLOAD_FOLDER_MATERIALS"], exist_ok=True)
        filepath = os.path.join(app.config["UPLOAD_FOLDER_MATERIALS"], filename)
        file.save(filepath)

        relative_path = f"uploads/study_materials/{filename}"

        cur.execute(
            "INSERT INTO study_materials (course_id, title, file_path) VALUES (%s, %s, %s)",
            (course_id, title, relative_path)
        )
        conn.commit()
        flash("Study material uploaded successfully")
        return redirect("/admin/add_material")

    cur.close()
    conn.close()

    return render_template(
        "admin_add_materials.html",
        courses=courses
    )

# Admin Add Course Plan

# ---------------- ADD STUDENT (ADMIN) ----------------
@app.route("/students")
def students():
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    # Join with student_courses and courses
    cur.execute("""
        SELECT s.id, s.name, s.email, 
               GROUP_CONCAT(c.name SEPARATOR ', ') AS courses
        FROM students s
        LEFT JOIN student_courses sc ON s.id = sc.student_id
        LEFT JOIN courses c ON sc.course_id = c.id
        GROUP BY s.id
        ORDER BY s.id DESC
    """)
    students = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("students.html", students=students)
@app.route("/add_student", methods=["GET", "POST"])
def add_student():
    if "admin" not in session:
        return redirect("/admin_login")

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    # Fetch all courses for dropdown
    cur.execute("SELECT id, name FROM courses")
    courses = cur.fetchall()

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        selected_courses = request.form.getlist("courses")  # getlist because multi-select

        # Insert student
        default_password = "student123"
        hashed_password = generate_password_hash(default_password)
        cur.execute(
            "INSERT INTO students (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )
        student_id = cur.lastrowid

        # Link student with courses
        for course_id in selected_courses:
            cur.execute(
                "INSERT INTO student_courses (student_id, course_id) VALUES (%s, %s)",
                (student_id, course_id)
            )

        conn.commit()
        cur.close()
        conn.close()
        return redirect("/students")

    cur.close()
    conn.close()
    return render_template("add_student.html", courses=courses)

@app.route("/edit_student/<int:student_id>", methods=["GET", "POST"])
def edit_student(student_id):
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        course = request.form.get("course")

        cur.execute("""
            UPDATE students
            SET name=%s, email=%s, course=%s
            WHERE id=%s
        """, (name, email, course, student_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/students")

    # GET request → fetch student info
    cur.execute("SELECT * FROM students WHERE id=%s", (student_id,))
    student = cur.fetchone()
    cur.close()
    conn.close()

    if not student:
        abort(404)

    return render_template("edit_student.html", student=student)
@app.route("/delete_student/<int:student_id>")
def delete_student(student_id):
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM students WHERE id=%s", (student_id,))
    conn.commit()
    cur.close()
    conn.close()
    return redirect("/students")

# ---------------- COURSES ----------------
@app.route("/courses")
def courses():
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    cur.execute("SELECT id, name, description FROM courses ORDER BY id DESC")
    courses = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("courses.html", courses=courses)


@app.route("/add_course", methods=["GET", "POST"])
def add_course():
    if session.get("role") != "admin":
        return redirect("/admin_login")

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")

        conn = get_connection()
        cur = conn.cursor()

        cur.execute("INSERT INTO courses (name, description) VALUES (%s, %s)", (name, description))
        conn.commit()
        cur.close()
        conn.close()

        return redirect("/courses")

    return render_template("add_course.html")


@app.route("/edit_course/<int:course_id>", methods=["GET", "POST"])
def edit_course(course_id):
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    if request.method == "POST":
        name = request.form.get("name")
        description = request.form.get("description")
        cur.execute("UPDATE courses SET name=%s, description=%s WHERE id=%s", (name, description, course_id))
        conn.commit()
        cur.close()
        conn.close()
        return redirect("/courses")

    cur.execute("SELECT * FROM courses WHERE id=%s", (course_id,))
    course = cur.fetchone()
    cur.close()
    conn.close()

    if not course:
        abort(404)

    return render_template("edit_course.html", course=course)


@app.route("/delete_course/<int:course_id>")
def delete_course(course_id):
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM courses WHERE id=%s", (course_id,))
    conn.commit()
    cur.close()
    conn.close()

    return redirect("/courses")

@app.route("/attendance", methods=["GET", "POST"])
def attendance():
    if session.get("role") != "admin":
        return abort(403)

    from datetime import date, datetime, timedelta
    import json
    from flask import Response

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    # ---------------- Subjects for dropdown ----------------
    cur.execute("SELECT id, name FROM courses")
    subjects = cur.fetchall()

    selected_subject = request.values.get("subject")
    attendance_date = request.values.get("date", date.today().strftime("%Y-%m-%d"))

    students = []
    if selected_subject:
        # Get students and attendance for selected date
        cur.execute("""
            SELECT s.id, s.name,
                   COALESCE(a.attended, 0) AS attended
            FROM students s
            LEFT JOIN attendance a
            ON a.student_id = s.id
            AND a.attendance_date = %s
            AND a.subject_id = %s
        """, (attendance_date, selected_subject))
        students = cur.fetchall()

    # ---------------- Download CSV ----------------
    download = request.values.get("download")
    if download and selected_subject and request.method == "GET":
        from io import StringIO
        import csv

        si = StringIO()
        cw = csv.writer(si)
        cw.writerow(["Student Name", "Present"])
        for s in students:
            cw.writerow([s['name'], "Yes" if s['attended'] else "No"])

        output = si.getvalue()
        filename = f"attendance_{attendance_date}.csv"
        cur.close()
        conn.close()

        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    # ---------------- Save attendance if POST ----------------
    if request.method == "POST" and selected_subject:
        for student in students:
            status = request.form.get(f"status_{student['id']}")
            attended = 1 if status == "Present" else 0

            cur.execute("""
                SELECT * FROM attendance
                WHERE student_id=%s AND subject_id=%s AND attendance_date=%s
            """, (student['id'], selected_subject, attendance_date))
            exists = cur.fetchone()

            if exists:
                cur.execute("""
                    UPDATE attendance SET attended=%s
                    WHERE student_id=%s AND subject_id=%s AND attendance_date=%s
                """, (attended, student['id'], selected_subject, attendance_date))
            else:
                cur.execute("""
                    INSERT INTO attendance (student_id, subject_id, attendance_date, attended, total)
                    VALUES (%s, %s, %s, %s, 1)
                """, (student['id'], selected_subject, attendance_date, attended))
        conn.commit()
        cur.close()
        conn.close()
        return redirect(request.url)

    # ---------------- Attendance Analytics ----------------
    chart_type = request.values.get("chart_type", "month")  # day, week, month
    chart_labels = []
    chart_values = []

    if selected_subject:
        if chart_type == "day":
            start_date = datetime.strptime(attendance_date, "%Y-%m-%d")
            end_date = start_date
        elif chart_type == "week":
            start_date = datetime.strptime(attendance_date, "%Y-%m-%d") - timedelta(days=6)
            end_date = datetime.strptime(attendance_date, "%Y-%m-%d")
        else:  # month
            today = datetime.strptime(attendance_date, "%Y-%m-%d")
            start_date = today.replace(day=1)
            end_date = today

        cur.execute("""
            SELECT attendance_date,
                   SUM(attended)/SUM(total)*100 AS percentage
            FROM attendance
            WHERE subject_id=%s AND attendance_date BETWEEN %s AND %s
            GROUP BY attendance_date
            ORDER BY attendance_date
        """, (selected_subject, start_date, end_date))
        chart_data = cur.fetchall()

        chart_labels = [row['attendance_date'].strftime('%Y-%m-%d') for row in chart_data]
        chart_values = [float(row['percentage']) for row in chart_data]

    cur.close()
    conn.close()

    # ---------------- Render template ----------------
    return render_template(
        "attendance.html",
        subjects=subjects,
        students=students,
        selected_subject=int(selected_subject) if selected_subject else None,
        attendance_date=attendance_date,
        chart_labels=json.dumps(chart_labels),
        chart_values=json.dumps(chart_values),
        chart_type=chart_type
    )

@app.route("/fees", methods=["GET"])
def fees():
    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    cur.execute("""
        SELECT s.id, s.name, f.total_fees, f.paid_fees
        FROM students s
        LEFT JOIN fees f ON s.id = f.student_id
        ORDER BY s.name
    """)
    students = cur.fetchall()
    for student in students:
        student['total_fees'] = student['total_fees'] or 0
        student['paid_fees'] = student['paid_fees'] or 0

    cur.close()
    conn.close()

    return render_template("fees.html", students=students)
@app.route("/fees/update/<int:student_id>", methods=["POST"])
def update_fee(student_id):
    total_fees = request.form.get("total_fees")
    paid_fees = request.form.get("paid_fees")

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO fees (student_id, total_fees, paid_fees)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE total_fees = %s, paid_fees = %s
    """, (student_id, total_fees, paid_fees, total_fees, paid_fees))

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("fees"))
@app.route("/fees/download_csv")
def download_fees():
    import csv
    from io import StringIO
    import datetime

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    cur.execute("""
        SELECT s.name, f.total_fees, f.paid_fees
        FROM students s
        LEFT JOIN fees f ON s.id = f.student_id
        ORDER BY s.name
    """)
    students = cur.fetchall()
    cur.close()
    conn.close()

    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(["Student", "Total Fee", "Paid"])
    for s in students:
        cw.writerow([s['name'], s['total_fees'] or 0, s['paid_fees'] or 0])

    output = si.getvalue()
    filename = f"fees_{datetime.date.today()}.csv"
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )

# ---------------- POINTS SYSTEM ----------------
@app.route("/points")
def points():
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)
    
    # Students with points
    cur.execute("""
        SELECT s.id, s.name, COALESCE(p.points, 0) AS points
        FROM students s
        LEFT JOIN points p ON s.id = p.student_id
        ORDER BY s.name
    """)
    students = cur.fetchall()

    # Fetch subjects for dropdown
    cur.execute("SELECT id, name FROM courses ORDER BY name")
    subjects = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("points.html", students=students, subjects=subjects)

@app.route("/update_points/<int:student_id>", methods=["POST"])
def update_points(student_id):
    if session.get("role") != "admin":
        abort(403)

    new_points = request.form.get("points")
    subject_id = request.form.get("subject_id")

    if not new_points.isdigit() or not subject_id:
        return "Points or subject not provided!", 400

    new_points = int(new_points)

    conn = get_connection()
    cur = conn.cursor()

    # Check if points exist for this student & subject
    cur.execute("SELECT * FROM points WHERE student_id=%s AND subject_id=%s", (student_id, subject_id))
    existing = cur.fetchone()

    if existing:
        cur.execute("UPDATE points SET points=%s WHERE student_id=%s AND subject_id=%s", (new_points, student_id, subject_id))
    else:
        cur.execute("INSERT INTO points (student_id, subject_id, points) VALUES (%s, %s, %s)", (student_id, subject_id, new_points))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/points")


@app.route("/top_students", methods=["GET"])
def top_students():
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True, buffered=True)

    # Fetch subjects for filter dropdown
    cur.execute("SELECT id, name FROM courses ORDER BY name")
    subjects = cur.fetchall()

    selected_subject = request.args.get("subject")

    # Base query: join points, student_courses, and courses to fetch multiple courses per student
    query = """
SELECT 
    s.id AS student_id,
    s.name AS student_name,
    c.id AS course_id,
    c.name AS course_name,
    COALESCE(p.points, 0) AS points
FROM students s
JOIN student_courses sc ON s.id = sc.student_id
JOIN courses c ON sc.course_id = c.id
LEFT JOIN points p ON s.id = p.student_id AND c.id = p.subject_id

    """
    params = []

    if selected_subject:
        query += " WHERE c.id = %s"
        params.append(selected_subject)

    #query += " GROUP BY s.id, s.name, p.points"
    query += " ORDER BY p.points DESC"

    cur.execute(query, params)
    students = cur.fetchall()

    # ---------- Ranking Logic (Handles TIES correctly) ----------
    ranked_students = []
    last_points = None
    rank = 0

    for index, student in enumerate(students):
        points = student.get("points", 0)
        if points != last_points:
            rank = index + 1
        last_points = points
        student["rank"] = rank
        ranked_students.append(student)
    cur.close()
    conn.close()

    return render_template(
        "top_students.html",
        top_students=ranked_students,
        subjects=subjects,
        selected_subject=selected_subject
    )



@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if session.get("role") != "student":
        abort(403)

    student_id = session["student_id"]

    if request.method == "POST":
        old_pass = request.form["old_password"]
        new_pass = request.form["new_password"]
        confirm_pass = request.form["confirm_password"]

        if new_pass != confirm_pass:
            return render_template("change_password.html", error="Passwords do not match!")

        conn = get_connection()
        cur = conn.cursor(dictionary=True, buffered=True)

        # Get current password hash
        cur.execute("SELECT password FROM students WHERE id=%s", (student_id,))
        student = cur.fetchone()

        if not student or not check_password_hash(student["password"], old_pass):
            cur.close()
            conn.close()
            return render_template("change_password.html", error="Old password incorrect!")

        # Update to new password
        hashed_new = generate_password_hash(new_pass)
        cur.execute("UPDATE students SET password=%s WHERE id=%s", (hashed_new, student_id))
        conn.commit()
        cur.close()
        conn.close()

        return render_template("change_password.html", success="Password updated successfully!")

    return render_template("change_password.html")

@app.route("/view_courses")
def view_courses():
    if session.get("role") != "student":
        abort(403)

    student_id = session["student_id"]

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT c.id, c.name, c.description,
               COALESCE(sc.status, 'none') AS status
        FROM courses c
        LEFT JOIN student_courses sc
        ON c.id = sc.course_id AND sc.student_id = %s
    """, (student_id,))

    courses = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("view_courses.html", courses=courses)
@app.route("/course_requests")
def course_requests():
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT sc.student_id, sc.course_id, s.name AS student, c.name AS course
        FROM student_courses sc
        JOIN students s ON sc.student_id = s.id
        JOIN courses c ON sc.course_id = c.id
        WHERE sc.status = 'pending'
    """)

    requests = cur.fetchall()
    cur.close()
    conn.close()

    return render_template("course_requests.html", requests=requests)
@app.route("/approve_course/<int:student_id>/<int:course_id>")
def approve_course(student_id, course_id):
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE student_courses
        SET status='approved'
        WHERE student_id=%s AND course_id=%s
    """, (student_id, course_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/course_requests")


@app.route("/reject_course/<int:student_id>/<int:course_id>")
def reject_course(student_id, course_id):
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE student_courses
        SET status='rejected'
        WHERE student_id=%s AND course_id=%s
    """ , (student_id, course_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/course_requests")

@app.route("/apply_course/<int:course_id>", methods=["POST"])
def apply_course(course_id):
    if session.get("role") != "student":
        abort(403)

    student_id = session["student_id"]

    conn = get_connection()
    cur = conn.cursor()

    # prevent duplicate
    cur.execute("""
        SELECT * FROM student_courses
        WHERE student_id=%s AND course_id=%s
    """, (student_id, course_id))

    if not cur.fetchone():
        cur.execute("""
            INSERT INTO student_courses (student_id, course_id, status)
            VALUES (%s, %s, 'pending')
        """, (student_id, course_id))
        conn.commit()

    cur.close()
    conn.close()

    return redirect("/view_courses")
@app.route("/drop_course/<int:course_id>", methods=["POST"])
def drop_course(course_id):
    if session.get("role") != "student":
        abort(403)

    student_id = session["student_id"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        UPDATE student_courses
        SET status='dropped'
        WHERE student_id=%s AND course_id=%s AND status='pending'
    """, (student_id, course_id))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/view_courses")


@app.route("/view_grades")
def view_grades():
    student_id = session.get("student_id")
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT 
            c.name AS subject,
            p.points
        FROM student_courses sc
        JOIN courses c ON sc.course_id = c.id
        LEFT JOIN points p 
            ON p.course_id = sc.course_id AND p.student_id = sc.student_id
        WHERE sc.student_id = %s
    """, (student_id,))

    data = cur.fetchall()
    cur.close()
    conn.close()

    # Convert points to letter grades
    grades_data = []
    for row in data:
        pts = row['points'] if row['points'] is not None else 0
        if pts >= 90:
            grade = 'A'
        elif pts >= 80:
            grade = 'B'
        elif pts >= 70:
            grade = 'C'
        elif pts >= 60:
            grade = 'D'
        else:
            grade = 'F'
        grades_data.append({'subject': row['subject'], 'grade': grade})

    return render_template("view_grades.html", grades_data=grades_data)

@app.route("/grades")
def grades():
    if session.get("role") != "admin":
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("""
        SELECT s.name AS student, c.name AS subject, g.grade
        FROM grades g
        JOIN students s ON g.student_id = s.id
        JOIN courses c ON g.subject_id = c.id
        ORDER BY s.name, c.name
    """)
    grades_data = cur.fetchall()

    cur.close()
    conn.close()

    return render_template("grades.html", grades_data=grades_data)
@app.route("/update_grade/<int:student_id>/<int:subject_id>", methods=["POST"])
def update_grade(student_id, subject_id):
    if session.get("role") != "admin":
        abort(403)

    new_grade = request.form.get("grade")

    conn = get_connection()
    cur = conn.cursor()

    # Check if grade exists
    cur.execute("SELECT * FROM grades WHERE student_id=%s AND subject_id=%s", (student_id, subject_id))
    existing = cur.fetchone()

    if existing:
        cur.execute("UPDATE grades SET grade=%s WHERE student_id=%s AND subject_id=%s", (new_grade, student_id, subject_id))
    else:
        cur.execute("INSERT INTO grades (student_id, subject_id, grade) VALUES (%s, %s, %s)", (student_id, subject_id, new_grade))

    conn.commit()
    cur.close()
    conn.close()

    return redirect("/grades")  

UPLOAD_FOLDER = 'static/uploads/profile_pic'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/student_profile", methods=["GET", "POST"])
def student_profile():
    student_id = session.get("student_id")
    if not student_id:
        abort(403)

    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    if request.method == "POST":
        # Update student info only if edit form submitted
        dob = request.form.get("dob")
        phone = request.form.get("phone")
        address = request.form.get("address")
        major = request.form.get("major")
        gpa = request.form.get("gpa")
        completed_credits = request.form.get("completed_credits")
        extracurriculars = request.form.get("extracurriculars")

        cur.execute("""
            UPDATE students
            SET dob=%s, phone=%s, address=%s, major=%s,
                gpa=%s, completed_credits=%s, extracurriculars=%s
            WHERE id=%s
        """, (dob, phone, address, major, gpa, completed_credits, extracurriculars, student_id))
        conn.commit()
        flash("Profile updated successfully!", "success")

    # Fetch latest student info
    cur.execute("SELECT * FROM students WHERE id=%s", (student_id,))
    student = cur.fetchone()

    cur.close()
    conn.close()
    return render_template("student_profile.html", student=student)


@app.route("/update_profile_pic", methods=["POST"])
def update_profile_pic():
    file = request.files.get("profile_pic")
    if file:
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(app.static_folder, "uploads/profile")
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, filename)
        file.save(save_path)

        # Save to students table
        user_id = session.get("student_id")  # Make sure this is students.id
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE students SET profile_pic=%s WHERE id=%s",
                    (f"uploads/profile/{filename}", user_id))
        conn.commit()
        cur.close()
        conn.close()

        flash("Profile picture updated!", "success")

    return redirect(url_for("student_profile"))
@app.route("/update_profile", methods=["POST"])
def update_profile():
    user_id = session.get("user_id")
    if not user_id:
        return abort(403)

    name = request.form.get("name")
    email = request.form.get("email")
    dob = request.form.get("dob")
    phone = request.form.get("phone")
    address = request.form.get("address")
    major = request.form.get("major")
    gpa = request.form.get("gpa")
    completed_credits = request.form.get("completed_credits")
    extracurriculars = request.form.get("extracurriculars")

    # Profile pic
    file = request.files.get("profile_pic")
    profile_pic_path = None
    if file:
        filename = secure_filename(file.filename)
        upload_dir = os.path.join(app.static_folder, "uploads/profile")
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, filename)
        file.save(save_path)
        profile_pic_path = f"uploads/profile/{filename}"

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE students SET name=%s, email=%s, dob=%s, phone=%s, address=%s,
                            major=%s, gpa=%s, completed_credits=%s, extracurriculars=%s
                            {} WHERE id=%s
    """.format(", profile_pic=%s" if profile_pic_path else ""),
                (name, email, dob, phone, address, major, gpa, completed_credits, extracurriculars, *( [profile_pic_path] if profile_pic_path else [] ), user_id))
    conn.commit()
    cur.close()
    conn.close()

    flash("Profile updated successfully!", "success")
    return redirect(url_for("student_profile"))



# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("student_login"))   # or student_login / admin_login
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
