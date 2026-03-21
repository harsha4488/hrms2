from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3
import urllib.parse
from datetime import datetime
import pytz

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -----------------------
# IST TIME FUNCTION
# -----------------------
def get_ist_time():
    ist = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist)
    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M:%S")
    return date, time

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
    role TEXT,
    phone TEXT
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

cur.execute("""
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_email TEXT,
    date TEXT,
    check_in TEXT,
    check_out TEXT
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
def register(email: str = Form(...), password: str = Form(...), role: str = Form(...), phone: str = Form(...)):
    cur.execute(
        "INSERT INTO users (email,password,role,phone) VALUES (?,?,?,?)",
        (email, password, role, phone)
    )
    conn.commit()
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
    return templates.TemplateResponse("dashboard_admin.html", {"request": request, "leaves": leaves})

# -----------------------
# EMPLOYEE DASHBOARD
# -----------------------
@app.get("/employee/{email}", response_class=HTMLResponse)
def employee_dashboard(request: Request, email: str):

    leaves = cur.execute(
        "SELECT * FROM leaves WHERE employee_email=?",
        (email,)
    ).fetchall()

    attendance = cur.execute(
        "SELECT * FROM attendance WHERE employee_email=? ORDER BY date DESC",
        (email,)
    ).fetchall()

    today, _ = get_ist_time()
    today_record = cur.execute(
        "SELECT * FROM attendance WHERE employee_email=? AND date=?",
        (email, today)
    ).fetchone()

    return templates.TemplateResponse(
        "dashboard_employee.html",
        {
            "request": request,
            "email": email,
            "leaves": leaves,
            "attendance": attendance,
            "today_record": today_record
        }
    )

# -----------------------
# APPLY LEAVE
# -----------------------
@app.post("/apply_leave")
def apply_leave(email: str = Form(...), reason: str = Form(...), from_date: str = Form(...), to_date: str = Form(...)):
    cur.execute(
        "INSERT INTO leaves (employee_email, reason, from_date, to_date, status) VALUES (?, ?, ?, ?, ?)",
        (email, reason, from_date, to_date, "Pending")
    )
    conn.commit()
    return RedirectResponse(f"/employee/{email}", status_code=303)

# -----------------------
# APPROVE / REJECT
# -----------------------
@app.post("/leave_action")
def leave_action(id: int = Form(...), action: str = Form(...)):
    cur.execute("UPDATE leaves SET status=? WHERE id=?", (action, id))
    conn.commit()
    return RedirectResponse("/admin", status_code=303)

# -----------------------
# ATTENDANCE CHECK IN (IST)
# -----------------------
@app.post("/check_in")
def check_in(email: str = Form(...)):
    today, time_now = get_ist_time()

    existing = cur.execute(
        "SELECT * FROM attendance WHERE employee_email=? AND date=?",
        (email, today)
    ).fetchone()

    if not existing:
        cur.execute(
            "INSERT INTO attendance (employee_email, date, check_in) VALUES (?, ?, ?)",
            (email, today, time_now)
        )
        conn.commit()

    return RedirectResponse(f"/employee/{email}", status_code=303)

# -----------------------
# ATTENDANCE CHECK OUT (IST)
# -----------------------
@app.post("/check_out")
def check_out(email: str = Form(...)):
    today, time_now = get_ist_time()

    cur.execute(
        "UPDATE attendance SET check_out=? WHERE employee_email=? AND date=?",
        (time_now, email, today)
    )
    conn.commit()

    return RedirectResponse(f"/employee/{email}", status_code=303)

# -----------------------
# ADMIN ATTENDANCE VIEW
# -----------------------
@app.get("/admin_attendance", response_class=HTMLResponse)
def admin_attendance(request: Request):
    records = cur.execute("SELECT * FROM attendance ORDER BY date DESC").fetchall()
    return templates.TemplateResponse("admin_attendance.html", {"request": request, "records": records})