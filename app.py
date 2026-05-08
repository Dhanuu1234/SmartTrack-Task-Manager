"""
SmartTrack — Employee Task Management System
=============================================
Tech Stack : Python · Flask · SQLite · Bootstrap 5
Features   : Role-Based Login (Admin/Employee) · CRUD Tasks · Search/Filter · Dashboard
Author     : Dhanshree Zagde
GitHub     : github.com/dhanshree-zagde
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from datetime import datetime, date
import sqlite3, hashlib, os

app = Flask(__name__)
app.secret_key = "smarttrack_dhanshree_2024"

DB = os.path.join(os.path.dirname(__file__), "instance", "smarttrack.db")

# ── DATABASE SETUP ─────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT NOT NULL,
            email      TEXT UNIQUE NOT NULL,
            password   TEXT NOT NULL,
            role       TEXT DEFAULT 'employee',
            dept       TEXT,
            avatar     TEXT DEFAULT 'U',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            title        TEXT NOT NULL,
            description  TEXT,
            assigned_to  INTEGER REFERENCES users(id),
            assigned_by  INTEGER REFERENCES users(id),
            priority     TEXT DEFAULT 'Medium',
            status       TEXT DEFAULT 'Pending',
            due_date     TEXT,
            category     TEXT DEFAULT 'General',
            created_at   TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at   TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS activity_log (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER REFERENCES users(id),
            action     TEXT,
            detail     TEXT,
            timestamp  TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Seed demo users
    def pwd(p): return hashlib.sha256(p.encode()).hexdigest()

    users = [
        ("Admin User",      "admin@smarttrack.com",  pwd("admin123"),    "admin",    "Management", "A"),
        ("Dhanshree Zagde", "dhanshree@smarttrack.com", pwd("pass123"), "employee", "IT",         "D"),
        ("Rahul Sharma",    "rahul@smarttrack.com",   pwd("pass123"),    "employee", "IT",         "R"),
        ("Priya Patil",     "priya@smarttrack.com",   pwd("pass123"),    "employee", "HR",         "P"),
        ("Amit Verma",      "amit@smarttrack.com",    pwd("pass123"),    "employee", "Finance",    "A"),
    ]
    for u in users:
        try:
            cursor.execute("INSERT INTO users (name,email,password,role,dept,avatar) VALUES (?,?,?,?,?,?)", u)
        except: pass

    # Seed demo tasks
    tasks = [
        ("Build Login Module",        "Implement JWT auth for mobile app",        2, 1, "High",   "In Progress", "2025-08-15", "Development"),
        ("Design Database Schema",    "Create ERD and SQL schema for v2",         3, 1, "High",   "Completed",   "2025-07-30", "Database"),
        ("Write Unit Tests",          "Achieve 80% code coverage",               2, 1, "Medium", "Pending",     "2025-08-20", "Testing"),
        ("Deploy to AWS EC2",         "Setup production server and CI/CD",        3, 1, "High",   "Pending",     "2025-08-25", "Cloud"),
        ("API Documentation",         "Document all REST endpoints in Swagger",   4, 1, "Low",    "In Progress", "2025-08-18", "Documentation"),
        ("Performance Optimization",  "Reduce query response time by 30%",        2, 1, "Medium", "Pending",     "2025-09-01", "Database"),
        ("HR Portal Integration",     "Connect employee data via REST API",       4, 1, "Medium", "Completed",   "2025-07-25", "Integration"),
        ("Mobile UI Redesign",        "Update dashboard for Android 14",          2, 1, "High",   "In Progress", "2025-08-10", "Design"),
        ("Security Audit",            "Run OWASP top 10 checks",                  5, 1, "High",   "Pending",     "2025-08-28", "Security"),
        ("Monthly Report",            "Generate Q3 analytics report",             5, 1, "Low",    "Pending",     "2025-09-05", "Reporting"),
    ]
    for t in tasks:
        try:
            cursor.execute("""INSERT INTO tasks
                (title,description,assigned_to,assigned_by,priority,status,due_date,category)
                VALUES (?,?,?,?,?,?,?,?)""", t)
        except: pass

    conn.commit()
    conn.close()

# ── HELPERS ────────────────────────────────────────────────────
def log_activity(user_id, action, detail=""):
    conn = get_db()
    conn.execute("INSERT INTO activity_log (user_id,action,detail) VALUES (?,?,?)",
                 (user_id, action, detail))
    conn.commit(); conn.close()

def current_user():
    if "user_id" not in session: return None
    conn = get_db()
    u = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return u

# ── AUTH ───────────────────────────────────────────────────────
@app.route("/", methods=["GET","POST"])
def login():
    if "user_id" in session: return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form["email"]
        pwd   = hashlib.sha256(request.form["password"].encode()).hexdigest()
        conn  = get_db()
        user  = conn.execute("SELECT * FROM users WHERE email=? AND password=?",
                             (email, pwd)).fetchone()
        conn.close()
        if user:
            session["user_id"] = user["id"]
            session["role"]    = user["role"]
            session["name"]    = user["name"]
            log_activity(user["id"], "LOGIN", f"{user['name']} logged in")
            return redirect(url_for("dashboard"))
        flash("Invalid email or password", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    if "user_id" in session:
        log_activity(session["user_id"], "LOGOUT", f"{session['name']} logged out")
    session.clear()
    return redirect(url_for("login"))

# ── DASHBOARD ──────────────────────────────────────────────────
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session: return redirect(url_for("login"))
    conn = get_db()
    uid  = session["user_id"]
    role = session["role"]

    if role == "admin":
        tasks   = conn.execute("""
            SELECT t.*, u.name as assignee_name, u.dept
            FROM tasks t JOIN users u ON t.assigned_to=u.id
            ORDER BY t.created_at DESC LIMIT 10
        """).fetchall()
        stats = {
            "total":       conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0],
            "pending":     conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending'").fetchone()[0],
            "in_progress": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='In Progress'").fetchone()[0],
            "completed":   conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Completed'").fetchone()[0],
            "employees":   conn.execute("SELECT COUNT(*) FROM users WHERE role='employee'").fetchone()[0],
            "high_priority": conn.execute("SELECT COUNT(*) FROM tasks WHERE priority='High' AND status!='Completed'").fetchone()[0],
        }
    else:
        tasks = conn.execute("""
            SELECT t.*, u.name as assignee_name
            FROM tasks t JOIN users u ON t.assigned_to=u.id
            WHERE t.assigned_to=?
            ORDER BY t.created_at DESC LIMIT 10
        """, (uid,)).fetchall()
        stats = {
            "total":       conn.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=?", (uid,)).fetchone()[0],
            "pending":     conn.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='Pending'", (uid,)).fetchone()[0],
            "in_progress": conn.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='In Progress'", (uid,)).fetchone()[0],
            "completed":   conn.execute("SELECT COUNT(*) FROM tasks WHERE assigned_to=? AND status='Completed'", (uid,)).fetchone()[0],
        }

    activity = conn.execute("""
        SELECT al.*, u.name FROM activity_log al
        JOIN users u ON al.user_id=u.id ORDER BY al.timestamp DESC LIMIT 6
    """).fetchall()
    conn.close()
    return render_template("dashboard.html", tasks=tasks, stats=stats, activity=activity)

# ── TASKS ──────────────────────────────────────────────────────
@app.route("/tasks")
def tasks():
    if "user_id" not in session: return redirect(url_for("login"))
    conn = get_db()
    uid  = session["user_id"]
    role = session["role"]

    status   = request.args.get("status", "")
    priority = request.args.get("priority", "")
    search   = request.args.get("search", "")
    category = request.args.get("category", "")

    base  = "SELECT t.*, u.name as assignee_name FROM tasks t JOIN users u ON t.assigned_to=u.id WHERE 1=1"
    params = []

    if role != "admin":
        base += " AND t.assigned_to=?"; params.append(uid)
    if status:
        base += " AND t.status=?"; params.append(status)
    if priority:
        base += " AND t.priority=?"; params.append(priority)
    if category:
        base += " AND t.category=?"; params.append(category)
    if search:
        base += " AND (t.title LIKE ? OR t.description LIKE ?)"; params += [f"%{search}%", f"%{search}%"]

    base += " ORDER BY CASE t.priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, t.due_date"
    task_list = conn.execute(base, params).fetchall()

    employees  = conn.execute("SELECT id,name FROM users WHERE role='employee'").fetchall()
    categories = ["Development","Testing","Database","Cloud","Design","Documentation","Security","Reporting","Integration","General"]
    conn.close()
    return render_template("tasks.html", tasks=task_list, employees=employees, categories=categories,
                           filters={"status":status,"priority":priority,"search":search,"category":category})

@app.route("/tasks/add", methods=["POST"])
def add_task():
    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))
    conn = get_db()
    conn.execute("""
        INSERT INTO tasks (title,description,assigned_to,assigned_by,priority,status,due_date,category)
        VALUES (?,?,?,?,?,?,?,?)
    """, (request.form["title"], request.form["description"],
          request.form["assigned_to"], session["user_id"],
          request.form["priority"], "Pending",
          request.form["due_date"], request.form["category"]))
    conn.commit()
    log_activity(session["user_id"], "TASK CREATED", f"Task '{request.form['title']}' assigned")
    flash("Task created successfully!", "success")
    conn.close()
    return redirect(url_for("tasks"))

@app.route("/tasks/update/<int:tid>", methods=["POST"])
def update_task(tid):
    if "user_id" not in session: return redirect(url_for("login"))
    conn  = get_db()
    uid   = session["user_id"]
    role  = session["role"]
    task  = conn.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()

    if role == "admin":
        conn.execute("""UPDATE tasks SET title=?,description=?,assigned_to=?,
                        priority=?,status=?,due_date=?,category=?,updated_at=CURRENT_TIMESTAMP
                        WHERE id=?""",
                     (request.form["title"], request.form["description"], request.form["assigned_to"],
                      request.form["priority"], request.form["status"], request.form["due_date"],
                      request.form["category"], tid))
    else:
        if task["assigned_to"] != uid:
            flash("Access denied!", "danger"); conn.close(); return redirect(url_for("tasks"))
        conn.execute("UPDATE tasks SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                     (request.form["status"], tid))

    conn.commit()
    log_activity(uid, "TASK UPDATED", f"Task ID {tid} updated")
    flash("Task updated!", "success")
    conn.close()
    return redirect(url_for("tasks"))

@app.route("/tasks/delete/<int:tid>")
def delete_task(tid):
    if "user_id" not in session or session["role"] != "admin":
        flash("Admin access required", "danger"); return redirect(url_for("tasks"))
    conn = get_db()
    task = conn.execute("SELECT title FROM tasks WHERE id=?", (tid,)).fetchone()
    conn.execute("DELETE FROM tasks WHERE id=?", (tid,))
    conn.commit()
    log_activity(session["user_id"], "TASK DELETED", f"Task '{task['title']}' deleted")
    flash("Task deleted.", "warning")
    conn.close()
    return redirect(url_for("tasks"))

# ── API ────────────────────────────────────────────────────────
@app.route("/api/stats")
def api_stats():
    if "user_id" not in session: return jsonify({"error":"unauthorized"}), 401
    conn = get_db()
    data = {
        "pending":     conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending'").fetchone()[0],
        "in_progress": conn.execute("SELECT COUNT(*) FROM tasks WHERE status='In Progress'").fetchone()[0],
        "completed":   conn.execute("SELECT COUNT(*) FROM tasks WHERE status='Completed'").fetchone()[0],
    }
    conn.close()
    return jsonify(data)

# ── EMPLOYEES (Admin only) ──────────────────────────────────────
@app.route("/employees")
def employees():
    if "user_id" not in session or session["role"] != "admin":
        flash("Admin access required","danger"); return redirect(url_for("dashboard"))
    conn  = get_db()
    emps  = conn.execute("""
        SELECT u.*, COUNT(t.id) as task_count,
               SUM(CASE WHEN t.status='Completed' THEN 1 ELSE 0 END) as completed_count
        FROM users u LEFT JOIN tasks t ON u.id=t.assigned_to
        WHERE u.role='employee' GROUP BY u.id
    """).fetchall()
    conn.close()
    return render_template("employees.html", employees=emps)

if __name__ == "__main__":
    init_db()
    print("\n" + "="*50)
    print("  SmartTrack — Task Management System")
    print("  Author : Dhanshree Zagde")
    print("  URL    : http://localhost:5000")
    print("  Login  : admin@smarttrack.com / admin123")
    print("="*50 + "\n")
    app.run(debug=True, port=5000)
