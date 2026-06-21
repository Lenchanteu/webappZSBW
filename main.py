from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, abort
import sqlite3
import hashlib
import secrets
import os
import uuid
import threading
from jinja2 import Environment
from docxtpl import DocxTemplate

from pdf_maker import convert_to_pdf
from worker import generate_report_job

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# ---------------- CONFIG ----------------
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'credentials.db')
TEMPLATE = "Rapport_de_prévention_incendie_template.docx"
DEFAULT_FILE_PATH = "C:/ProgramData/ZSBWApp"

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
            email TEXT NOT NULL
        );
    """)

    # test user
    cur.execute("SELECT 1 FROM credentials WHERE uname='test'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO credentials (uname, pswd, email) VALUES (?, ?, ?)",
            ("test", hashlib.sha256("test".encode()).hexdigest(), "test@test.com")
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
    con.close()

    if not row:
        return False

    return hashlib.sha256(pswd.encode()).hexdigest() == row[0]


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
    cur.execute("INSERT INTO credentials VALUES (?, ?, ?)", (uname, hashed, email))

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

    if check_credentials(uname, pswd):
        session["logged_in"] = True
        session["uname"] = uname
        flash("Login successful!", "success")
        return redirect(url_for("dashboard"))

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


# ---------------- REPORT (SYNC VERSION) ----------------
'''@app.route("/generate-fire-report", methods=["POST"])
def generate_report():
    uname = session["uname"]
    user_dir = os.path.join(DEFAULT_FILE_PATH, uname)
    os.makedirs(user_dir, exist_ok=True)

    data = request.form.to_dict()

    # checkbox conversion
    checkbox_fields = [
        "chapiteau", "tentes", "gradins", "scene",
        "structures_aeriennes", "chauffage", "barbecue",
        "points_de_cuissons", "extincteurs",
        "eclairage_securite", "pictogrammes",
        "PV_toiles", "PV_electr", "PV_struct",
    ]

    for field in checkbox_fields:
        data[field] = field in request.form

    if "tentes_nombre" in data:
        data["tentes_nombres"] = data["tentes_nombre"]

    doc = DocxTemplate(TEMPLATE)
    doc.render(data, jinja_env=Environment(trim_blocks=True, lstrip_blocks=True))
    doc.save(OUTPUT_DOCX)

    convert_to_pdf(OUTPUT_DOCX)

    return send_file(
        OUTPUT_PDF,
        as_attachment=True,
        download_name="rapport.pdf",
        mimetype="application/pdf"
    )'''


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

# ---------------- RUN ---------------
if __name__ == "__main__":
    os.makedirs(DEFAULT_FILE_PATH, exist_ok=True)
    app.run(debug=True, host='0.0.0.0')