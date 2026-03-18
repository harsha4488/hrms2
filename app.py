from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import smtplib
from email.mime.text import MIMEText
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -----------------------
# EMAIL CONFIG (USE ENV IN RENDER)
# -----------------------
EMAIL = os.getenv("EMAIL") 
PASSWORD = os.getenv("PASSWORD") 

def send_email(to_email, subject, message):
    try:
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = EMAIL
        msg["To"] = to_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL, PASSWORD)
            server.send_message(msg)

    except Exception as e:
        print("Email error:", e)

# -----------------------
# DATABASE
# -----------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS leaves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_email TEXT,
    reason TEXT,
    from_date TEXT,
    to_date TEXT,
    status TEXT
)
""")

conn.commit()

# -----------------------
# LOGIN PAGE
# -----------------------
@app.get("/", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

# -----------------------
# REGISTER PAGE
# -----------------------
@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

# -----------------------
# REGISTER USER
# -----------------------
@app.post("/register")
def register(email: str = Form(...), password: str = Form(...), role: str = Form(...)):

    # 🚨 ONLY ONE ADMIN
    if role == "admin":
        existing_admin = cur.execute(
            "SELECT * FROM users WHERE role='admin'"
        ).fetchone()

        if existing_admin:
            return {"msg": "Admin already exists. Only one allowed."}

    try:
        cur.execute(
            "INSERT INTO users (email,password,role) VALUES (?,?,?)",
            (email, password, role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return {"msg": "User already exists"}

    return RedirectResponse("/", status_code=303)

# -----------------------
# LOGIN
# -----------------------
@app.post("/login")
def login(email: str = Form(...), password: str = Form(...)):
    user = cur.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    ).fetchone()

    if not user:
        return {"msg": "Invalid login"}

    if user["role"] == "admin":
        return RedirectResponse("/admin", status_code=303)
    else:
        return RedirectResponse(f"/employee/{email}", status_code=303)

# -----------------------
# LOGOUT
# -----------------------
@app.get("/logout")
def logout():
    return RedirectResponse("/", status_code=303)

# -----------------------
# ADMIN DASHBOARD
# -----------------------
@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request):
    leaves = cur.execute("SELECT * FROM leaves").fetchall()
    return templates.TemplateResponse(
        "dashboard_admin.html",
        {"request": request, "leaves": leaves}
    )

# -----------------------
# CREATE USER
# -----------------------
@app.post("/create_user")
def create_user(email: str = Form(...), password: str = Form(...), role: str = Form(...)):

    if role == "admin":
        existing_admin = cur.execute(
            "SELECT * FROM users WHERE role='admin'"
        ).fetchone()

        if existing_admin:
            return {"msg": "Only one admin allowed"}

    try:
        cur.execute(
            "INSERT INTO users (email,password,role) VALUES (?,?,?)",
            (email, password, role)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return {"msg": "User already exists"}

    return RedirectResponse("/admin", status_code=303)

# -----------------------
# EMPLOYEE DASHBOARD
# -----------------------
@app.get("/employee/{email}", response_class=HTMLResponse)
def employee_dashboard(request: Request, email: str):
    leaves = cur.execute(
        "SELECT * FROM leaves WHERE employee_email=?",
        (email,)
    ).fetchall()

    return templates.TemplateResponse(
        "dashboard_employee.html",
        {"request": request, "email": email, "leaves": leaves}
    )

# -----------------------
# APPLY LEAVE + EMAIL ADMIN
# -----------------------
@app.post("/apply_leave")
def apply_leave(
    email: str = Form(...),
    reason: str = Form(...),
    from_date: str = Form(...),
    to_date: str = Form(...)
):
    cur.execute(
        "INSERT INTO leaves (employee_email, reason, from_date, to_date, status) VALUES (?, ?, ?, ?, ?)",
        (email, reason, from_date, to_date, "Pending")
    )
    conn.commit()

    # 📧 EMAIL ADMIN
    admin = cur.execute(
        "SELECT email FROM users WHERE role='admin'"
    ).fetchone()

    if admin:
        send_email(
            admin["email"],
            "New Leave Request",
            f"""
Employee: {email}
From: {from_date}
To: {to_date}
Reason: {reason}
Status: Pending
"""
        )

    return RedirectResponse(f"/employee/{email}", status_code=303)

# -----------------------
# APPROVE / REJECT + EMAIL EMPLOYEE
# -----------------------
@app.post("/leave_action")
def leave_action(id: int = Form(...), action: str = Form(...)):

    leave = cur.execute(
        "SELECT * FROM leaves WHERE id=?",
        (id,)
    ).fetchone()

    cur.execute(
        "UPDATE leaves SET status=? WHERE id=?",
        (action, id)
    )
    conn.commit()

    # 📧 EMAIL EMPLOYEE
    if leave:
        send_email(
            leave["employee_email"],
            "Leave Status Update",
            f"""
Your leave request has been {action}

From: {leave['from_date']}
To: {leave['to_date']}
Reason: {leave['reason']}
"""
        )

    return RedirectResponse("/admin", status_code=303)