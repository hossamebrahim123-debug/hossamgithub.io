from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import sqlite3
import csv
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "school_dashboard_secret_2026"
DB = "school.db"

#DATABASE SETUP
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'teacher'
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            year_group INTEGER NOT NULL,
            gender TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            subject TEXT NOT NULL,
            grade INTEGER NOT NULL,
            attendance INTEGER NOT NULL,
            pass_fail TEXT NOT NULL,
            teacher TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
    """)
    conn.commit()

    # Load CSV data if students table is empty
    c.execute("SELECT COUNT(*) FROM students")
    if c.fetchone()[0] == 0:
        df = pd.read_csv('school_performance.csv')
        students = df[['Student_Name', 'Year_Group', 'Gender']].drop_duplicates()
        for _, row in students.iterrows():
            c.execute("INSERT INTO students (name, year_group, gender) VALUES (?, ?, ?)",
                      (row['Student_Name'], int(row['Year_Group']), row['Gender']))
            student_id = c.lastrowid
            student_grades = df[df['Student_Name'] == row['Student_Name']]
            for _, g in student_grades.iterrows():
                c.execute("""
                    INSERT INTO grades (student_id, subject, grade, attendance, pass_fail, teacher)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student_id, g['Subject'], int(g['Grade']), int(g['Attendance_Percentage']),
                      g['Pass_Fail'], g['Teacher']))
        conn.commit()
    conn.close()

init_db()

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def get_chart(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
    buf.seek(0)
    img = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_dataframe():
    conn = get_db()
    df = pd.read_sql_query("""
        SELECT s.name as Student_Name, s.year_group as Year_Group, s.gender as Gender,
               g.subject as Subject, g.grade as Grade, g.attendance as Attendance_Percentage,
               g.pass_fail as Pass_Fail, g.teacher as Teacher, s.id as student_id
        FROM students s JOIN grades g ON s.id = g.student_id
    """, conn)
    conn.close()
    return df

# CHARTS
def chart_pass_fail_all_years(df):
    extract = df.groupby(['Year_Group', 'Pass_Fail'])['Pass_Fail'].count().unstack()
    fig, ax = plt.subplots(figsize=(8, 4))
    extract.plot(kind='bar', color=['red', 'green'], edgecolor='black', ax=ax)
    ax.set_title('Pass/Fail Results by Year Group', fontsize=13, fontweight='bold')
    ax.set_xlabel('Year Group')
    ax.set_ylabel('Number of Students')
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.legend(['Fail', 'Pass'])
    ax.tick_params(axis='x', rotation=0)
    fig.tight_layout()
    return get_chart(fig)

def chart_pass_fail_year(df, year):
    year_data = df[df['Year_Group'] == year]
    extract = year_data.groupby('Pass_Fail')['Pass_Fail'].count()
    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ['red' if x == 'Fail' else 'green' for x in extract.index]
    extract.plot(kind='bar', color=colors, edgecolor='black', ax=ax)
    ax.set_title(f'Pass/Fail Results for Year {year}', fontsize=13, fontweight='bold')
    ax.set_xlabel('Result')
    ax.yaxis.set_major_locator(plt.MaxNLocator(integer=True))
    ax.set_ylabel('Number of Students')
    ax.tick_params(axis='x', rotation=0)
    fig.tight_layout()
    return get_chart(fig)

def chart_average_grades(df):
    extract = df.groupby('Subject')['Grade'].mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    extract.plot(kind='bar', color='steelblue', edgecolor='black', ax=ax)
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.1f}', (p.get_x() + p.get_width() / 2, p.get_height()),
                    ha='center', va='bottom', fontsize=9)
    ax.set_title('Average Grade per Subject', fontsize=13, fontweight='bold')
    ax.set_xlabel('Subject')
    ax.set_ylabel('Average Grade')
    ax.tick_params(axis='x', rotation=0)
    fig.tight_layout()
    return get_chart(fig)

def chart_attendance(df):
    extract = df.groupby('Year_Group')['Attendance_Percentage'].mean()
    fig, ax = plt.subplots(figsize=(8, 4))
    colors = ['#2ecc71' if v >= 80 else '#e74c3c' for v in extract.values]
    extract.plot(kind='bar', color=colors, edgecolor='black', ax=ax)
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.1f}%', (p.get_x() + p.get_width() / 2, p.get_height()),
                    ha='center', va='bottom', fontsize=9)
    ax.set_title('Average Attendance by Year Group', fontsize=13, fontweight='bold')
    ax.set_xlabel('Year Group')
    ax.set_ylabel('Attendance %')
    ax.tick_params(axis='x', rotation=0)
    fig.tight_layout()
    return get_chart(fig)

def chart_top_subjects(df):
    extract = df.groupby('Subject')['Grade'].mean().sort_values(ascending=False)
    colors = ['gold', 'silver', 'peru', 'steelblue', 'steelblue']
    fig, ax = plt.subplots(figsize=(8, 4))
    extract.plot(kind='bar', color=colors, edgecolor='black', ax=ax)
    for p in ax.patches:
        ax.annotate(f'{p.get_height():.1f}', (p.get_x() + p.get_width() / 2, p.get_height()),
                    ha='center', va='bottom', fontsize=9)
    ax.set_title('Top Performing Subjects', fontsize=13, fontweight='bold')
    ax.set_xlabel('Subject')
    ax.set_ylabel('Average Grade')
    ax.tick_params(axis='x', rotation=0)
    fig.tight_layout()
    return get_chart(fig)

def chart_student_grades(student_df):
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = ['green' if pf == 'Pass' else 'red' for pf in student_df['Pass_Fail']]
    ax.bar(student_df['Subject'], student_df['Grade'], color=colors, edgecolor='black')
    ax.set_title('Grade by Subject', fontsize=13, fontweight='bold')
    ax.set_xlabel('Subject')
    ax.set_ylabel('Grade')
    ax.set_ylim(0, 110)
    for i, (g, pf) in enumerate(zip(student_df['Grade'], student_df['Pass_Fail'])):
        ax.annotate(f'{g}', (i, g), ha='center', va='bottom', fontsize=9)
    ax.tick_params(axis='x', rotation=0)
    fig.tight_layout()
    return get_chart(fig)

#AUTH
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        flash("Invalid email or password", "error")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed = generate_password_hash(password)
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                         (name, email, hashed))
            conn.commit()
            conn.close()
            flash("Account created! Please log in.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already exists", "error")
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# DASHBOARD
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    df = get_dataframe()
    year_groups = sorted(df['Year_Group'].unique().tolist())
    selected_year = int(request.form.get('year_group', year_groups[0]))

    # Stats
    total_students = df['Student_Name'].nunique()
    pass_rate = round((df[df['Pass_Fail'] == 'Pass'].shape[0] / df.shape[0]) * 100, 1)
    avg_attendance = round(df.groupby('Student_Name')['Attendance_Percentage'].first().mean(), 1)
    top_subject = df.groupby('Subject')['Grade'].mean().idxmax()

    # Flags
    student_attendance = df.groupby('Student_Name')['Attendance_Percentage'].first()
    low_attendance = student_attendance[student_attendance < 50].index.tolist()
    failing = df[df['Pass_Fail'] == 'Fail']['Student_Name'].unique().tolist()
    flags = list(set(low_attendance + failing))

    return render_template('dashboard.html',
        chart1=chart_pass_fail_all_years(df),
        chart2=chart_pass_fail_year(df, selected_year),
        chart3=chart_average_grades(df),
        chart4=chart_attendance(df),
        chart5=chart_top_subjects(df),
        year_groups=year_groups,
        selected_year=selected_year,
        total_students=total_students,
        pass_rate=pass_rate,
        avg_attendance=avg_attendance,
        top_subject=top_subject,
        flags=flags,
        low_attendance=low_attendance,
        failing=failing
    )

# STUDENT SEARCH
@app.route('/search')
@login_required
def search():
    query = request.args.get('q', '').strip()
    results = []
    if query:
        conn = get_db()
        students = conn.execute(
            "SELECT id, name, year_group FROM students WHERE name LIKE ?",
            (f'%{query}%',)
        ).fetchall()
        conn.close()
        results = students
    return render_template('search.html', query=query, results=results)

@app.route('/student/<int:student_id>')
@login_required
def student_profile(student_id):
    df = get_dataframe()
    student_df = df[df['student_id'] == student_id]
    if student_df.empty:
        flash("Student not found", "error")
        return redirect(url_for('search'))

    name = student_df['Student_Name'].iloc[0]
    year = student_df['Year_Group'].iloc[0]
    gender = student_df['Gender'].iloc[0]
    avg_grade = round(student_df['Grade'].mean(), 1)
    attendance = student_df['Attendance_Percentage'].iloc[0]
    pass_count = (student_df['Pass_Fail'] == 'Pass').sum()
    fail_count = (student_df['Pass_Fail'] == 'Fail').sum()

    flags = []
    if attendance < 50:
        flags.append(f"Low attendance: {attendance}%")
    if fail_count > 0:
        flags.append(f"Failing {fail_count} subject(s)")
    if avg_grade < 50:
        flags.append(f"Low average grade: {avg_grade}")

    chart = chart_student_grades(student_df)

    return render_template('student.html',
        name=name, year=year, gender=gender,
        avg_grade=avg_grade, attendance=attendance,
        pass_count=pass_count, fail_count=fail_count,
        grades=student_df.to_dict('records'),
        chart=chart, flags=flags, student_id=student_id
    )

# ADD STUDENT
@app.route('/add_student', methods=['GET', 'POST'])
@login_required
def add_student():
    if request.method == 'POST':
        name = request.form['name']
        year = int(request.form['year_group'])
        gender = request.form['gender']
        subjects = ['Maths', 'English', 'Science', 'History', 'Geography']

        conn = get_db()
        conn.execute("INSERT INTO students (name, year_group, gender) VALUES (?, ?, ?)",
                     (name, year, gender))
        student_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        for subject in subjects:
            grade = int(request.form.get(f'grade_{subject}', 50))
            attendance = int(request.form.get('attendance', 90))
            teacher = request.form.get(f'teacher_{subject}', 'TBC')
            pass_fail = 'Pass' if grade >= 50 else 'Fail'
            conn.execute("""
                INSERT INTO grades (student_id, subject, grade, attendance, pass_fail, teacher)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (student_id, subject, grade, attendance, pass_fail, teacher))

        conn.commit()
        conn.close()
        flash(f"Student {name} added successfully!", "success")
        return redirect(url_for('student_profile', student_id=student_id))

    return render_template('add_student.html')

#  EDIT STUDENT
@app.route('/edit_student/<int:student_id>', methods=['GET', 'POST'])
@login_required
def edit_student(student_id):
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    grades = conn.execute("SELECT * FROM grades WHERE student_id = ?", (student_id,)).fetchall()

    if request.method == 'POST':
        name = request.form['name']
        year = int(request.form['year_group'])
        gender = request.form['gender']
        conn.execute("UPDATE students SET name=?, year_group=?, gender=? WHERE id=?",
                     (name, year, gender, student_id))
        for grade in grades:
            new_grade = int(request.form.get(f'grade_{grade["subject"]}', grade['grade']))
            new_attendance = int(request.form.get('attendance', grade['attendance']))
            new_teacher = request.form.get(f'teacher_{grade["subject"]}', grade['teacher'])
            pass_fail = 'Pass' if new_grade >= 50 else 'Fail'
            conn.execute("""
                UPDATE grades SET grade=?, attendance=?, pass_fail=?, teacher=?
                WHERE id=?
            """, (new_grade, new_attendance, pass_fail, new_teacher, grade['id']))
        conn.commit()
        conn.close()
        flash("Student updated successfully!", "success")
        return redirect(url_for('student_profile', student_id=student_id))

    conn.close()
    return render_template('edit_student.html', student=student, grades=grades)

#EXPORT
@app.route('/export/<int:year_group>')
@login_required
def export(year_group):
    df = get_dataframe()
    year_df = df[df['Year_Group'] == year_group]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Year Group', 'Subject', 'Grade', 'Attendance %', 'Pass/Fail', 'Teacher'])
    for _, row in year_df.iterrows():
        writer.writerow([row['Student_Name'], row['Year_Group'], row['Subject'],
                         row['Grade'], row['Attendance_Percentage'], row['Pass_Fail'], row['Teacher']])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='text/csv',
        headers={"Content-Disposition": f"attachment;filename=year_{year_group}_report.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)
