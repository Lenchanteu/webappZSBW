#Code under a source-available license. See more info in LICENSE
#Author: Merlin Van Cranem 
#Contact: vancranemmerlin@gmail.com
#https://github.com/Lenchanteu
#Last modifications: 04/09/2026 by Merlin Van Cranem
#------------------- IMPORTS ------------------
import json

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, abort, current_app
import sqlite3
import hashlib
import secrets
import os
import uuid
import threading
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import platform
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import check_password_hash
import logging
from logging.config import dictConfig
from functools import partial
import shutil
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import argon2
from argon2.exceptions import VerifyMismatchError
import email_config

from worker import generate_report_job
from email_sender import send_bug_report, send_confirmation_email, send_passcode


# ---------------- CONFIG ----------------
def parse_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off", ""}:
        return False
    return default


load_dotenv(".env")
ph = argon2.PasswordHasher()
DATABASE = os.getenv('DATABASE_PATH', os.path.join(os.getcwd(), 'database', 'credentials.db'))
TEMPLATE = "Rapport_de_prévention_incendie_template.docx"
DEFAULT_FILE_PATH = os.getenv('DEFAULT_FILE_PATH', os.path.join(os.getcwd(), 'instance', 'reports'))
BUG_FOLDER = os.getenv('BUG_FOLDER', os.path.join(DEFAULT_FILE_PATH, 'BugReports'))
LOG_FOLDER = os.getenv('LOG_FOLDER', os.path.join(DEFAULT_FILE_PATH, 'logs'))
FLASK_DEBUG = parse_bool(os.getenv('FLASK_DEBUG', 'False'), False)
REQUIRE_HTTPS = parse_bool(os.getenv('REQUIRE_HTTPS', 'True'), True)
SESSION_REFRESH_EACH_REQUEST = parse_bool(os.getenv('SESSION_REFRESH_EACH_REQUEST', 'True'), True)
CREATE_TEST_USER = parse_bool(os.getenv('CREATE_TEST_USER', 'False'), False)
SESSION_COOKIE_SECURE = not FLASK_DEBUG
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
BOURG_EMAILS = email_config.EMAILS

os.makedirs(DEFAULT_FILE_PATH, exist_ok=True)
os.makedirs(BUG_FOLDER, exist_ok=True)
os.makedirs(LOG_FOLDER, exist_ok=True)
LOG_FILE = os.path.join(LOG_FOLDER, f'log_{datetime.today().strftime("%Y-%m-%d")}.log')
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, 'w') as fp:
        pass

jobs = {}  # in-memory job store

#------------ APP FACTORY ------------
# Configure logging using dictConfig
dictConfig(
    {
		    # Specify the logging configuration version
        "version": 1,
        "formatters": {
		        # Define a formatter named 'default'
            "default": {
		            # Specify log message format
                "format": "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
            }
        },
        "handlers": {
            # Define a console handler configuration
            "console": {
		            # Use StreamHandler to log to stdout
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                # Use 'default' formatter for this handler
                "formatter": "default",
            },
            "file": {
                "class": "logging.FileHandler",
                "filename": LOG_FILE,
                "formatter": "default",
                "level": "DEBUG",
            }
        },
        # Configure the root logger
        "root": {
        # Set root logger level to DEBUG
        "level": "DEBUG",
        # Attach 'file' handler to the root logger 
        "handlers": ["file", "console"]},
    }
)
app = Flask(__name__)
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY missing")
app.secret_key = SECRET_KEY
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
csrf = CSRFProtect(app)
app.config.update({
    'PERMANENT_SESSION_LIFETIME': timedelta(minutes=int(os.getenv('SESSION_TIMEOUT_MINUTES', 90))),
    'SESSION_REFRESH_EACH_REQUEST': SESSION_REFRESH_EACH_REQUEST,
    'SESSION_COOKIE_HTTPONLY': SESSION_COOKIE_HTTPONLY,
    'SESSION_COOKIE_SECURE': SESSION_COOKIE_SECURE,
    'SESSION_COOKIE_SAMESITE': SESSION_COOKIE_SAMESITE,
    'MAX_CONTENT_LENGTH': int(os.getenv('MAX_CONTENT_LENGTH_BYTES', 16 * 1024 * 1024)),
})
app.logger.info(f"NEW LOG: timestamp: {datetime.now().strftime('%Y/%m/%d, %H:%M:%S')}\n\n")
app.logger.debug(f"Current environment: {os.getenv('ENVIRONMENT', 'production')}")
# Create a StreamHandler to handle file output

handler = logging.FileHandler(LOG_FILE)
# Define A Custom Log Message Format
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
# Assign The Formatter To The Handler
handler.setFormatter(formatter)
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.WARNING)
app.logger.info(f"PID is {os.getpid()}")
# ---------------- DB INIT ----------------
def init_db():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            uname TEXT PRIMARY KEY,
            pswd TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            confirmed BOOL,
            last_ip TEXT
        );
    """)
    app.logger.info("Database was created")
    if CREATE_TEST_USER:
        cur.execute("SELECT 1 FROM credentials WHERE uname='test'")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO credentials (uname, pswd, email, confirmed, last_ip) VALUES (?, ?, ?, ?, ?)",
                ("test", ph.hash("test"), "test@test.com", True, "0.0.0.0")
            )
            app.logger.info("Test user was created")
    else:
        app.logger.info("Test user creation skipped")
    con.commit()
    con.close()


init_db()

# ---------------- AUTH functions ----------------
def check_credentials(uname, pswd):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute(
        "SELECT pswd, confirmed FROM credentials WHERE uname=?",
        (uname,)
    )
    row = cur.fetchone()
    con.close()

    current_app.logger.info("Checking user credentials")

    if row is None:
        return False, False

    password_hash, confirmed = row

    try:
        ph.verify(password_hash, pswd)

        if ph.check_needs_rehash(password_hash):
            change_password_func(uname, pswd)

        return True, confirmed

    except VerifyMismatchError:
        return False, confirmed

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

    hashed = ph.hash(pswd)
    cur.execute("INSERT INTO credentials VALUES (?, ?, ?, ?, ?)", (uname, hashed, email, False, "0.0.0.0", ))

    con.commit()
    con.close()
    return True

def modify_lastIP(ip, uname):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("UPDATE credentials SET last_ip=? WHERE uname=?", (ip, uname,))
    con.commit()
    con.close()

# ---------------- Functions --------------
def dispatchCommands(command_table, command_name, args):
    if command_name not in command_table:
        raise ValueError(f"Command {command_name} not found in command table.")
    current_app.logger.debug(f"Command received. Name: {command_name}, args: {args}")
    entry = command_table[command_name]
    func = entry["name"]
    arg_names = entry["args"]

    resolved_args = []

    for arg in arg_names:
        if arg in args:
            resolved_args.append(args[arg])
        elif hasattr(entry, arg):
            resolved_args.append(getattr(entry, arg))
        else:
            raise ValueError(f"Missing some argument: {arg} ")
    return partial(func, *resolved_args)

def debugMessage():
    app.logger.debug("Debug message: Does everything work?")

def del_rapport(user):
    directory = os.path.join(DEFAULT_FILE_PATH, user, "RAPPORTS")
    try:
        shutil.rmtree(directory)
    except OSError as e:
        current_app.logger.error(f"Could not delete repports from user {user}. Error info: {e}")
    return None

def del_user(user):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("DELETE FROM credentials WHERE uname=?", (user,))
    con.commit()
    con.close()

def change_password_func(user, password):
    hash = ph.hash(password)
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("UPDATE credentials SET pswd=? WHERE uname=?", (hash, user,))
    con.commit()
    con.close()


def verify_admin_password(provided_password, configured_hash):
    if not provided_password or not configured_hash:
        return False

    if provided_password == configured_hash:
        return True

    if configured_hash.startswith("sha256:"):
        expected_hash = configured_hash.split(":", 1)[1]
        return hashlib.sha256(provided_password.encode("utf-8")).hexdigest() == expected_hash

    if len(configured_hash) == 64 and all(ch in "0123456789abcdefABCDEF" for ch in configured_hash):
        return hashlib.sha256(provided_password.encode("utf-8")).hexdigest() == configured_hash

    try:
        return check_password_hash(configured_hash, provided_password)
    except Exception:
        return False
# ---------------- COMMAND TABLE ------------
COMMAND_TABLE = {
                "DEBUG": 
                {"name": debugMessage, 
                "args": []},
                "DELETE_RAPPORT":
                {"name": del_rapport,
                 "args": ["user"]}
                        }
# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return render_template("home.html")

@app.before_request
def enforce_https():
    if not request.is_secure and not app.debug and REQUIRE_HTTPS:
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    uname = request.form.get("uname")
    pswd = request.form.get("pswd")
    ip = request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']

    if check_credentials(uname, pswd)[0] and check_credentials(uname, pswd)[1]:
        session["logged_in"] = True
        session["uname"] = uname
        current_app.logger.info(f"User {uname} has successfully logged in")
        modify_lastIP(ip, uname)
        flash("Login successful!", "success")
        return redirect(url_for("dashboard"))
    
    elif (check_credentials(uname, pswd)[0] == True) and (check_credentials(uname, pswd)[1] == False):
        current_app.logger.warning(f"User {uname} tried to log in but hasn't confirmed their email address.")
        flash("User not verified, please confirm your email before login in")
        modify_lastIP(ip, uname)
        return redirect(url_for("home"))

    current_app.logger.warning(f"Someone with ip address {ip} tried to connect to the account named {uname} with the wrong password")
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
    ip = request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']

    if pswd != confirm:
        current_app.logger.info(f"A new user tried to create an account with the name {uname} but did not input the same password.")
        flash("Passwords do not match!", "error")
        return redirect(url_for("register"))

    if create_account(uname, pswd, email):
        current_app.logger.info(f"A new user with username {uname} has been created.")
        modify_lastIP(ip, uname)
        flash("Account created!", "success")
        hashed_user = hashlib.sha256(uname.encode()).hexdigest() # pyright: ignore[reportOptionalMemberAccess]
        send_confirmation_email(uname, email, url_for("confirmation_email", user_code=hashed_user, _external=True))
        current_app.logger.info(f"A confirmation email has been send to user {uname} at the email address {email}.")
        return redirect(url_for("login"))
    
    current_app.logger.warning(f"Someone with IP address {ip} tried creating an account that already existed")
    flash("Username or email already exists in the system!", "error")
    return redirect(url_for("register"))


@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        abort(403)
    
    return render_template("dashboard.html")

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("logged_in"):
        abort(403)
    if request.method == "GET":
        return render_template("settings.html")
    if request.method == "POST":
        id = request.form.get("id", "")
        if id == "delete_account":
            flash(f"Votre compte avec le nom d'utilisateur {session['uname']} a été supprimé", "info")
            del_user(session['uname'])
            session["logged_in"] = False
            return redirect(url_for("home"))
        if id == "change_password":
            return redirect(url_for("change_password"))
    return redirect(url_for("home"))

@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if not session.get("logged_in"):
        abort(403)
    uname = session["uname"]
    if request.method == "GET":
        passcode = str(secrets.randbelow(1000000)).zfill(6)
        session["passcode"] = passcode
        con = sqlite3.connect(DATABASE)
        cur = con.cursor()
        cur.execute("SELECT email FROM credentials WHERE uname=?", (uname,))
        email = cur.fetchone()[0]
        send_passcode(uname, email, passcode)
        return render_template("change_password.html")
    if request.method == "POST":
        code = request.form.get("code")
        new_pass = request.form.get("new")
        if code == session.get("passcode") and new_pass != None:
            change_password_func(uname, new_pass)
            session["logged_in"] = False
            flash("Mot de passe changé, utilisateur déconnecté.")
            session.pop("passcode", None)
            return redirect(url_for("login"))
        elif code != session.get("passcode"): 
            flash("Mauvais code")
            session.pop("passcode", None)
            return redirect(url_for("login"))
        elif new_pass == None:
            flash("Veuillez entrer un mot de passe.")
        else:
            flash("Erreur.")
            session.pop("passcode", None)
            return redirect(url_for("home"))
    return redirect(url_for("home"))
@app.route("/logout")
def logout():
    current_app.logger.info(f"User {session['uname']} has logged out.")
    session.clear()
    return redirect(url_for("home"))


@app.route("/rapport")
def rapport():
    if not session.get("logged_in"):
        abort(403)

    user_dir = os.path.join(DEFAULT_FILE_PATH, session["uname"])
    os.makedirs(user_dir, exist_ok=True)
    current_app.logger.info(f"User {session['uname']} is creating a rapport.")
    return render_template("rapport.html", email_addrs=BOURG_EMAILS)

@app.route("/edit/<report_name>")
def edit(report_name):
    if not session.get("logged_in"):
        abort(403)

    uname = session["uname"]

    # Remove the extension from the filename
    name = os.path.splitext(report_name)[0]

    user_dir = os.path.join(
        DEFAULT_FILE_PATH,
        uname,
        "RAPPORTS"
    )

    report = os.path.join(
        user_dir,
        f"{name}.json"
    )

    if not os.path.exists(report):
        abort(404)

    with open(report, "r", encoding="utf-8") as file:
        data = json.load(file)

    return render_template(
        "rapport.html",
        email_addrs=BOURG_EMAILS,
        report=data
    )
# ---------------- ASYNC JOB SYSTEM ----------------
@app.route("/start-report", methods=["POST"])
def start_report():
    job_id = str(uuid.uuid4())
    try:
        current_app.logger.info(f"A new job with job_id {job_id} has been created for user {session['uname']}.")
        uname = session["uname"]
    except Exception as e:
        current_app.logger.error(f"An error has occured. Exception in /start repport while trying to get session[uname]. Exception: {e}")
        abort(401)
    user_dir = os.path.join(DEFAULT_FILE_PATH, uname, "RAPPORTS")

    os.makedirs(user_dir, exist_ok=True)

    data = request.form.to_dict()
    data.pop("csrf_token", None)
    name = request.form.get("concerne")
    commune = request.form.get("commune")
    send_to_bourg = request.form.get("copie_bourgmestre")
    send_to_people = request.form.get("copie_manifestation")
    email_responsable = request.form.get("email_envoi_rapport")
    status = request.form.get("V_fin")
    if not status:
        send_to_bourg = False
    if not status:
        send_to_people = False

    OUTPUT_DOCX = os.path.join(user_dir, f"rapport_pour_{name}.docx")
    OUTPUT_PDF = os.path.join(user_dir, f"rapport_pour_{name}.pdf")
    OUTPUT_JSON = os.path.join(user_dir, f"rapport_pour_{name}.json")

    with open(OUTPUT_JSON, 'w') as file:
        json.dump(data, file)

    jobs[job_id] = {
        "status": "processing",
        "file": OUTPUT_PDF
    }

    threading.Thread(
        target=generate_report_job,
        args=(job_id, data, TEMPLATE, OUTPUT_DOCX, OUTPUT_PDF, jobs, commune, send_to_bourg)
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
    current_app.logger.info(f"The job with job_id {job_id} for user {session['uname']} has been finished.")
    return send_file(job["file"], as_attachment=True)


# ---------------- LOADING PAGE -------------
@app.route("/loading/<job_id>")
def loading(job_id):
    return render_template("loading.html", job_id=job_id)


@app.route("/debug/jobs")
def debug_jobs():
    if not session.get("admin_logged_in"):
        abort(403)

    current_app.logger.warning(f"Someone is trying to access a debug tool at /debug/jobs. IP address is {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']}.")
    return jobs


#----------------- SAVING SYSTEM -------------
@app.route("/myfiles")
def myfiles():
    if not session.get("logged_in"):
        abort(403)
    user_folder = os.path.join(DEFAULT_FILE_PATH, session.get("uname", "test"), "RAPPORTS")

    if not os.path.exists(user_folder):
        current_app.logger.info(f"created a new user folder for user {session['uname']} while viewing files at /myfiles.")
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

@app.route("/downloads/<uname>/<filename>")
def downloads(filename, uname):
    if not session.get("logged_in"):
        abort(403)
    if uname == None:
        uname = session["uname"]
    user_folder = os.path.join(DEFAULT_FILE_PATH, uname, "RAPPORTS")

    # Prevent directory traversal attacks
    filepath = os.path.abspath(os.path.join(user_folder, filename))

    if not filepath.startswith(os.path.abspath(user_folder)):
        current_app.logger.error(f"User {session['uname']} tried to download a saved file named {filename} at {filepath} but couldn't. Reason: filepath.startswith(os.path.join(user_folder)) not True. Error 403")
        abort(403)

    if not os.path.exists(filepath):
        current_app.logger.error(f"User {session['uname']}tried to download a saved file named {filename} at {filepath} but couldn't. Reason: os.path.exists(filepath) not True. Error 404")
        abort(404)

    current_app.logger.info(f"User {session['uname']} has successfuly downloaded a file named {filename} at {filepath}.")
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
        current_app.logger.warning(f"Someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} submitted a bug report on the {timestamp}. Please review bug report.")
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
    current_app.logger.info(f"A user named {uname} is trying to confirm their email.")
    if hashlib.sha256(uname.encode()).hexdigest() == user_code:

        if check_credentials(uname, pswd)[0]:
            con = sqlite3.connect(DATABASE)
            cur = con.cursor()
            cur.execute("UPDATE credentials SET confirmed=True WHERE uname=?", (uname,))
            con.commit()
            con.close()
            flash("You have succesfully confirmed your email", "info")
            current_app.logger.info(f"User {uname} has confirmed their email address.")
            session['uname'] = uname
            session['logged_in'] = True
            current_app.logger.info(f"User {uname} has logged in.")
            return redirect(url_for("dashboard"))
        else:
            current_app.logger.warning(f"Someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has tried to confirm the email address of {uname} with a wrong password.")
            flash("Wrong password", "error")
            return redirect(url_for("confirmation_email", user_code=user_code))
    else:
        current_app.logger.warning(f"Someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has tried to confirm their email with a wrong link. ")
        flash("Username does not match confirmation link. Please put the right username.", "error")
        return redirect(url_for("confirmation_email", user_code=user_code))
    
@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        current_app.logger.warning(f"Someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} is trying to get admin access.")
        return render_template("admin_login.html")
    
    code = request.form.get("code", "None")
    admin_password_hash = os.getenv('ADMIN_PASSWORD_HASH', '')
    if verify_admin_password(code, admin_password_hash):
        session["admin_logged_in"] = True
        current_app.logger.warning(f"Someone with IP {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has gotten admin access. Shut down server?")
        return redirect(url_for("admin"))
    current_app.logger.warning(f"Someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has unsuccessfully tried to get admin access.")
    flash("Wrong password")
    return redirect(url_for("home"))

@app.route("/admin_logged_in", methods=["GET", "POST"])
def admin():
    if not session.get("admin_logged_in"):
        abort(403)

    # Read the log file
    try:
        with open(LOG_FILE, "r", encoding="cp1252") as f:
            logs = f.read()
    except FileNotFoundError:
        logs = "No log file found."

    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("SELECT uname FROM credentials")
    usersname  = [row[0] for row in cur.fetchall()]
    users = []
    for user in usersname:
        users.append({
            "name": user
        })
    
    if request.method == "POST":
        form_id = request.form.get("form_id")
        if form_id == "comm":
            code = request.form.get("code", "")
            args = {
    "user": request.form.get("args", "")
            }

            try:
                func = dispatchCommands(COMMAND_TABLE, code, args)
                func()
                flash("Command executed.", "success")
            except Exception as e:
                app.logger.exception("Admin command failed")
                flash(f"Error: {e}", "error")
        if form_id == "del_u_rep":
            user = request.form.get("args")
            try:
                func = dispatchCommands(COMMAND_TABLE, "DELETE_RAPPORT", {"user": user})
                func()
                app.logger.info(f"Deleting the user repports of user {user} has been succesfull.")
                flash("Success", "info")
            except Exception as e:
                app.logger.exception(f"Deleting the user repports of user {user} has failed.")
                flash(f"Error: {e} ", "error")
        # Reload the log after the command executes
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.read()
    
    return render_template("admin.html", logs=logs, users=users)
@app.route("/user/<uname>")
def user(uname):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("SELECT * FROM credentials WHERE uname=?", (uname,))
    user_data = cur.fetchone()
    user = {
    "uname": user_data[0],
    "email": user_data[2],
    "confirmation": user_data[3],
    "last_ip": user_data[4]
}
    user_folder = os.path.join(DEFAULT_FILE_PATH, uname, "RAPPORTS")

    if not os.path.exists(user_folder):
        current_app.logger.info(f"created a new user folder for user {session['uname']} while viewing files at /user.")
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

    
    return render_template("user.html", user=user, rapports=files)

@app.route("/admn_del_user/<uname>", methods=["GET", "POST"])
def admn_del_user(uname):
    if not session.get("admin_logged_in"):
        abort(403)
    del_user(uname)
    flash("User deleted", "Info")
    return redirect(url_for("admin"))

@app.route("/KillSwitch", methods=["GET"])
def killSwitch():
    if not session.get("admin_logged_in"):
        abort(403)
    current_app.logger.critical(f"Kill switch activated by someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']}")
    os._exit(1)
    return 0


@app.route("/admin/logs")
def admin_logs():
    if not session.get("admin_logged_in"):
        abort(403)

    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        return f.read(), 200, {"Content-Type": "text/plain"}
#----------------- ERROR HANDLING ---------------
@app.errorhandler(401)
def e_401(error):
    return render_template("401.html"), 401
@app.errorhandler(404)
def e_404(error):
    return render_template("404.html"), 404
@app.errorhandler(403)
def e_403(error):
    return render_template("403.html"), 403
#------------------ COOKIES EXPLAINATION ----------
@app.route("/cookies")
def cookies():
    return render_template("cookies.html")
@app.route("/download_collected_data", methods=["GET", "POST"])
def download_data():
    if not session.get("logged_in"):
        abort(403)
    if request.method == "GET":
        return render_template("download_data.html")
    
    uname = request.form.get("uname")
    pswd = request.form.get("pswd")
    ip = request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']

    if check_credentials(uname, pswd)[0] and check_credentials(uname, pswd)[1]:
        con = sqlite3.connect(DATABASE)
        con.row_factory = sqlite3.Row

        cur = con.cursor()

        cur.execute("""
            SELECT email, confirmed, last_ip
            FROM credentials
            WHERE uname = ?
        """, (uname,))

        row = cur.fetchone()

        if row:
            email = row["email"]
            confirmed = row["confirmed"]
            last_ip = row["last_ip"]
        else:
            email = None
            confirmed = None
            last_ip = None
        session["uname"] = uname
        current_app.logger.info(f"User {uname} has successfully logged in to get their info")
        modify_lastIP(ip, uname)
        user_folder = os.path.join(DEFAULT_FILE_PATH, session["uname"], "DATA")
        os.makedirs(user_folder, exist_ok=True)
        filepath = os.path.abspath(os.path.join(user_folder, "data.txt"))
        with open(filepath, "w", encoding="utf-8") as file:
            file.write(
                f"""Données collectées de l'utilisateur {uname}

        1. Nom d'utilisateur : {uname}
        2. Adresse e-mail : {email}
        3. Adresse e-mail confirmée : {confirmed}
        4. Dernière adresse IP de connection : {last_ip}
        """
            )

        current_app.logger.info(f"User {uname} downloaded their personal data.")

        return send_file(filepath, as_attachment=True)
    elif (check_credentials(uname, pswd)[0] == True) and (check_credentials(uname, pswd)[1] == False):
        current_app.logger.warning(f"User {uname} tried to get their data but hasn't confirmed their email address.")
        flash("Votre addresse e-mail n'a pas été confirmée. Afin de nous assurer de la sécurité de vos données, veuillez confirmer votre addresse e-mail avant.")
        modify_lastIP(ip, uname)
        return redirect(url_for("home"))

    current_app.logger.warning(f"Someone with ip address {ip} tried to connect to the account named {uname} with the wrong password to collect their data")
    flash("Données de connection invalides!", "error")
    return redirect(url_for("download_data"))
@app.route("/delete_data", methods=["POST"])
def delete_data():
    if not session.get("logged_in"):
        abort(403)
    uname = request.form.get("uname")
    pswd = request.form.get("pswd")
    ip = request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']

    if check_credentials(uname, pswd)[0] and check_credentials(uname, pswd)[1]:
        modify_lastIP(None, uname)
        current_app.logger.info(f"User {uname} deleted their non essential personal data.")
        flash("Vous avez supprimé vos données non essentielles.", "info")
        return redirect(url_for("download_data"))
    elif (check_credentials(uname, pswd)[0] == True) and (check_credentials(uname, pswd)[1] == False):
        current_app.logger.warning(f"User {uname} tried to delete their data but hasn't confirmed their email address.")
        flash("Votre addresse e-mail n'a pas été confirmée. Afin de nous assurer de la sécurité de vos données, veuillez confirmer votre addresse e-mail avant.", "info")
        modify_lastIP(ip, uname)
        return redirect(url_for("home"))

    current_app.logger.warning(f"Someone with ip address {ip} tried to connect to the account named {uname} with the wrong password to delete their data")
    flash("Données de connection invalides!", "error")
    return redirect(url_for("download_data"))
# ---------------- RUN ---------------

if __name__ == "__main__":
    os.makedirs(DEFAULT_FILE_PATH, exist_ok=True)
    app.run(debug=FLASK_DEBUG, host='0.0.0.0')
