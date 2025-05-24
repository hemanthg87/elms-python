from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

def init_db():
    conn = sqlite3.connect('elearning.db')
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT CHECK(role IN ('student', 'faculty')) NOT NULL
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        content TEXT NOT NULL,
        faculty_id INTEGER,
        FOREIGN KEY(faculty_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER,
        question TEXT NOT NULL,
        due_date TEXT NOT NULL,
        FOREIGN KEY(course_id) REFERENCES courses(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS submissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        assignment_id INTEGER,
        student_id INTEGER,
        answer TEXT NOT NULL,
        grade TEXT,
        feedback TEXT,
        FOREIGN KEY(assignment_id) REFERENCES assignments(id),
        FOREIGN KEY(student_id) REFERENCES users(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS student_courses (
        student_id INTEGER,
        course_id INTEGER,
        FOREIGN KEY(student_id) REFERENCES users(id),
        FOREIGN KEY(course_id) REFERENCES courses(id)
    )''')

    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        conn = sqlite3.connect('elearning.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return 'Username already exists!'
        conn.close()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect('elearning.db')
        c = conn.cursor()
        c.execute("SELECT id, role FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['username'] = username  # ✅ Add this line
            session['role'] = user[1]
            if user[1] == 'student':
                return redirect(url_for('student_dashboard'))
            else:
                return redirect(url_for('faculty_dashboard'))
        else:
            return 'Invalid credentials!'
    return render_template('login.html')

@app.route('/student_dashboard')
def student_dashboard():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))
    return render_template('student_dashboard.html', username=session['username'])

@app.route('/faculty_dashboard')
def faculty_dashboard():
    if 'user_id' not in session or session.get('role') != 'faculty':
        return redirect(url_for('login'))
    return render_template('faculty_dashboard.html', username=session['username'])

@app.route('/create_course', methods=['GET', 'POST'])
def create_course():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        content = request.form['content']
        conn = sqlite3.connect('elearning.db')
        c = conn.cursor()
        c.execute("INSERT INTO courses (title, description, content, faculty_id) VALUES (?, ?, ?, ?)",
                  (title, description, content, session['user_id']))
        conn.commit()
        conn.close()
        return redirect(url_for('faculty_dashboard'))

    return render_template('create_course.html')

@app.route('/view_courses')
def view_courses():
    conn = sqlite3.connect('elearning.db')
    c = conn.cursor()
    c.execute("SELECT * FROM courses")
    courses = c.fetchall()
    conn.close()
    return render_template('view_courses.html', courses=courses)

@app.route('/create_assignment', methods=['GET', 'POST'])
def create_assignment():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))

    conn = sqlite3.connect('elearning.db')
    c = conn.cursor()
    c.execute('SELECT id, title FROM courses WHERE faculty_id = ?', (session['user_id'],))
    courses = c.fetchall()

    if request.method == 'POST':
        course_id = request.form['course_id']
        question = request.form['question']
        due_date = request.form['due_date']

        c.execute('INSERT INTO assignments (course_id, question, due_date) VALUES (?, ?, ?)',
                  (course_id, question, due_date))
        conn.commit()
        conn.close()
        return redirect(url_for('faculty_dashboard'))

    conn.close()
    return render_template('create_assignment.html', courses=courses)

@app.route('/view_assignments')
def view_assignments():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    conn = sqlite3.connect('elearning.db')
    c = conn.cursor()
    c.execute('''
        SELECT c.title, a.question, a.due_date
        FROM courses c
        JOIN assignments a ON c.id = a.course_id
    ''')
    assignments = c.fetchall()
    conn.close()
    return render_template('view_assignments.html', assignments=assignments)

@app.route('/submit_assignment', methods=['GET', 'POST'])
def submit_assignment_form():
    if 'user_id' not in session or session['role'] != 'student':
        return redirect(url_for('login'))

    conn = sqlite3.connect('elearning.db')
    c = conn.cursor()

    if request.method == 'POST':
        assignment_id = request.form['assignment_id']
        answer = request.form['answer']

        c.execute('INSERT INTO submissions (assignment_id, student_id, answer) VALUES (?, ?, ?)',
                  (assignment_id, session['user_id'], answer))
        conn.commit()
        conn.close()
        return redirect(url_for('view_assignments'))

    c.execute('SELECT id, question FROM assignments')
    assignments = c.fetchall()
    conn.close()
    return render_template('submit_assignment.html', assignments=assignments)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/view_submissions')
def view_submissions():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))

    conn = sqlite3.connect('elearning.db')
    c = conn.cursor()

    # Get all submissions for assignments in courses owned by this faculty
    c.execute('''
        SELECT s.id, u.username, a.question, s.answer, s.grade, s.feedback
        FROM submissions s
        JOIN assignments a ON s.assignment_id = a.id
        JOIN courses c ON a.course_id = c.id
        JOIN users u ON s.student_id = u.id
        WHERE c.faculty_id = ?
    ''', (session['user_id'],))

    submissions = c.fetchall()
    conn.close()

    return render_template('view_submissions.html', submissions=submissions)

@app.route('/provide_feedback/<int:submission_id>', methods=['GET', 'POST'])
def provide_feedback(submission_id):
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect(url_for('login'))

    conn = sqlite3.connect('elearning.db')
    c = conn.cursor()

    if request.method == 'POST':
        grade = request.form['grade']
        feedback = request.form['feedback']
        c.execute("UPDATE submissions SET grade = ?, feedback = ? WHERE id = ?",
                  (grade, feedback, submission_id))
        conn.commit()
        conn.close()
        return redirect(url_for('faculty_dashboard'))

    c.execute("SELECT * FROM submissions WHERE id = ?", (submission_id,))
    submission = c.fetchone()
    conn.close()
    return render_template('provide_feedback.html', submission=submission)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
