from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import sqlite3

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -----------------------
# DATABASE
# -----------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# USERS
cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE,
    password TEXT,
    role TEXT
)
""")

# LEAVES
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

    # 🚨 ONLY ONE ADMIN ALLOWED
    if role == "admin":
        existing_admin = cur.execute(
            "SELECT * FROM users WHERE role='admin'"
        ).fetchone()

        if existing_admin:
            return {"msg": "Admin already exists. Only one admin allowed."}

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
# CREATE USER (ADMIN)
# -----------------------
@app.post("/create_user")
def create_user(email: str = Form(...), password: str = Form(...), role: str = Form(...)):

    # 🚨 PREVENT MULTIPLE ADMINS
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
# APPLY LEAVE
# -----------------------
@app.post("/apply_leave")
def apply_leave(
    email: str = Form(...),
    reason: str = Form(...),
    from_date: str = Form(...),
    to_date: str = Form(...)
):
    print("DEBUG:", from_date, to_date)

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
    cur.execute(
        "UPDATE leaves SET status=? WHERE id=?",
        (action, id)
    )
    conn.commit()

    return RedirectResponse("/admin", status_code=303)

@app.get("/logout")
def logout():
    return RedirectResponse("/", status_code=303)