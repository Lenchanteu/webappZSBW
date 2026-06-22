from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, abort
import sqlite3
import hashlib
import secrets
import os
import uuid
import threading
from werkzeug.utils import secure_filename
from datetime import datetime
import platform
from werkzeug.middleware.proxy_fix import ProxyFix

from pdf_maker import convert_to_pdf
from worker import generate_report_job
from email_sender import send_bug_report, send_confirmation_email

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# ---------------- CONFIG ----------------
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'credentials.db')
TEMPLATE = "Rapport_de_prévention_incendie_template.docx"
DEFAULT_FILE_PATH = r"C:\ProgramData\ZSBWApp"
BUG_FOLDER = r"C:\ProgramData\ZSBWApp\BugReports"
os.makedirs(BUG_FOLDER, exist_ok=True)

jobs = {}  # in-memory job store


# ---------------- DB INIT ----------------
def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            uname TEXT PRIMARY KEY,
            pswd TEXT NOT NULL,
            email TEXT NOT NULL,
            confirmed BOOl
        );
    """)

    # test user
    cur.execute("SELECT 1 FROM credentials WHERE uname='test'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO credentials (uname, pswd, email, confirmed) VALUES (?, ?, ?, ?)",
            ("test", hashlib.sha256("test".encode()).hexdigest(), "test@test.com", True)
        )

    con.commit()
    con.close()


init_db()


# ---------------- AUTH ----------------
def check_credentials(uname, pswd):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("SELECT pswd FROM credentials WHERE uname=?", (uname,))
    row = cur.fetchone()
    cur.execute("SELECT confirmed FROM credentials WHERE uname=?", (uname,))
    confirmed = cur.fetchone()
    confirmed = confirmed[0] if confirmed  != None else None
    con.close()

    if not row:
        return False, False
    checked_hash = (hashlib.sha256(pswd.encode()).hexdigest() == row[0])
    return checked_hash, confirmed


def create_account(uname, pswd, email):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("SELECT 1 FROM credentials WHERE uname=?", (uname,))
    if cur.fetchone():
        con.close()
        return False
    cur.execute("SELECT 1 FROM credentials WHERE email=?", (email,))
    if cur.fetchone():
        con.close()
        return False

    hashed = hashlib.sha256(pswd.encode()).hexdigest()
    cur.execute("INSERT INTO credentials VALUES (?, ?, ?, ?)", (uname, hashed, email, False,))

    con.commit()
    con.close()
    return True


# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("home.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    uname = request.form.get("uname")
    pswd = request.form.get("pswd")
    print(check_credentials(uname, pswd))
    if check_credentials(uname, pswd)[0] and check_credentials(uname, pswd)[1]:
        session["logged_in"] = True
        session["uname"] = uname
        flash("Login successful!", "success")
        return redirect(url_for("dashboard"))
    elif (check_credentials(uname, pswd)[0] == True) and (check_credentials(uname, pswd)[1] == False):
        flash("User not verified, please confirm your email before login in")
        return redirect(url_for("home"))
    flash("Invalid credentials!", "error")
    return redirect(url_for("login"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html")

    uname = request.form.get("uname")
    pswd = request.form.get("pswd")
    email = request.form.get("email")
    confirm = request.form.get("confirm_pswd")

    if pswd != confirm:
        flash("Passwords do not match!", "error")
        return redirect(url_for("register"))

    if create_account(uname, pswd, email):
        flash("Account created!", "success")
        hashed_user = hashlib.sha256(uname.encode()).hexdigest() # pyright: ignore[reportOptionalMemberAccess]
        send_confirmation_email(uname, email, url_for("confirmation_email", user_code=hashed_user, _external=True))
        return redirect(url_for("login"))

    flash("Username or email already exists in the system!", "error")
    return redirect(url_for("register"))


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    return render_template("dashboard.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/rapport")
def rapport():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    user_dir = os.path.join(DEFAULT_FILE_PATH, session["uname"])
    os.makedirs(user_dir, exist_ok=True)
    
    return render_template("rapport.html")

# ---------------- ASYNC JOB SYSTEM ----------------
@app.route("/start-report", methods=["POST"])
def start_report():
    job_id = str(uuid.uuid4())

    uname = session["uname"]
    user_dir = os.path.join(DEFAULT_FILE_PATH, uname)

    os.makedirs(user_dir, exist_ok=True)

    data = request.form.to_dict()
    name = request.form.get("concerne")

    OUTPUT_DOCX = os.path.join(user_dir, f"rapport_pour_{name}.docx")
    OUTPUT_PDF = os.path.join(user_dir, f"rapport_pour_{name}.pdf")
    jobs[job_id] = {
        "status": "processing",
        "file": OUTPUT_PDF
    }

    threading.Thread(
        target=generate_report_job,
        args=(job_id, data, TEMPLATE, OUTPUT_DOCX, OUTPUT_PDF, jobs)
    ).start()

    return {"job_id": job_id}


@app.route("/job-status/<job_id>")
def job_status(job_id):
    return jobs.get(job_id, {"status": "unknown"})


@app.route("/download/<job_id>")
def download_job(job_id):
    job = jobs.get(job_id)

    if not job or job.get("status") != "done":
        return "Not ready", 400

    return send_file(job["file"], as_attachment=True)


# ---------------- LOADING PAGE -------------
@app.route("/loading/<job_id>")
def loading(job_id):
    return render_template("loading.html", job_id=job_id)


@app.route("/debug/jobs")
def debug_jobs():
    return jobs

#----------------- SAVING SYSTEM -------------
@app.route("/myfiles")
def myfiles():
    if "uname" not in session:
        return redirect(url_for("login"))

    user_folder = os.path.join(DEFAULT_FILE_PATH, session["uname"])

    if not os.path.exists(user_folder):
        os.makedirs(user_folder)

    files = []

    for file in os.listdir(user_folder):
        if file.lower().endswith(".pdf"):
            full_path = os.path.join(user_folder, file)

            files.append({
                "name": file,
                "size": round(os.path.getsize(full_path) / 1024, 1),   # KB
                "modified": os.path.getmtime(full_path)
            })

    # Sort newest first
    files.sort(key=lambda x: x["modified"], reverse=True)

    return render_template("myfiles.html", files=files)
@app.route("/downloads/<filename>")
def downloads(filename):
    if "uname" not in session:
        return redirect(url_for("login"))

    user_folder = os.path.join(DEFAULT_FILE_PATH, session["uname"])

    # Prevent directory traversal attacks
    filepath = os.path.abspath(os.path.join(user_folder, filename))

    if not filepath.startswith(os.path.abspath(user_folder)):
        abort(403)

    if not os.path.exists(filepath):
        abort(404)

    return send_from_directory(
        user_folder,
        filename,
        as_attachment=True
    )
# -----------------BUG REPORT -------------
@app.route("/report_bug", methods=["GET", "POST"])
def report_bug():
    if request.method == "POST":
        username = session.get("uname", "Unknown")
        description = request.form.get("description")
        browser = request.form.get("browser")
        

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        report_folder = os.path.join(BUG_FOLDER, f"{username}_{timestamp}")
        os.makedirs(report_folder)

        # Save report
        with open(os.path.join(report_folder, "report.txt"), "w", encoding="utf-8") as f:
            f.write(f"User: {username}\n")
            f.write(f"Date: {datetime.now()}\n")
            f.write(f"Browser: {browser}\n")
            f.write(f"Python: {platform.python_version()}\n")
            f.write(f"OS: {platform.platform()}\n")
            f.write(f"IP: {request.remote_addr}\n")
            f.write(f"User-Agent: {request.headers.get('User-Agent')}\n")
            f.write(f"URL: {request.referrer}\n\n")
            f.write(description)  # pyright: ignore[reportArgumentType]

        # Save screenshot if uploaded
        screenshot = request.files.get("screenshot")
        if screenshot and screenshot.filename:
            filename = secure_filename(screenshot.filename)
            screenshot.save(os.path.join(report_folder, filename))

        flash("Bug report submitted successfully.", "success")
        send_bug_report(report_folder)
        return redirect(url_for("home"))

    return render_template("bug_report.html")
# ---------------- Confirmation email --------------
@app.route("/confirmation_email/<user_code>", methods=["GET", "POST"])
def confirmation_email(user_code):
    if request.method == "GET":
        return render_template("confirmation_email.html")

    uname = request.form.get("uname", "none")
    pswd = request.form.get("pswd")
    if hashlib.sha256(uname.encode()).hexdigest() == user_code:

        if check_credentials(uname, pswd)[0]:
            con = sqlite3.connect(DATABASE)
            cur = con.cursor()
            cur.execute("UPDATE credentials SET confirmed=True WHERE uname=?", (uname,))
            con.commit()
            con.close()
            flash("You have succesfully confirmed your email", "info")
            return redirect(url_for("login"))
        else:
            flash("Wrong password", "error")
            return redirect(url_for("confirmation_email", user_code=user_code))
    else:
        flash("Username does not match confirmation link. Please put the right username.", "error")
        return redirect(url_for("confirmation_email", user_code=user_code))
# ---------------- RUN ---------------
if __name__ == "__main__":
    os.makedirs(DEFAULT_FILE_PATH, exist_ok=True)
    app.run(debug=True, host='0.0.0.0')