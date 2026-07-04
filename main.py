#------------------- IMPORTS ------------------
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, send_from_directory, abort, current_app
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
import logging
from logging.config import dictConfig
from functools import partial

from pdf_maker import convert_to_pdf
from worker import generate_report_job
from email_sender import send_bug_report, send_confirmation_email


# ---------------- CONFIG ----------------
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'credentials.db')
TEMPLATE = "Rapport_de_prévention_incendie_template.docx"
DEFAULT_FILE_PATH = r"C:\ProgramData\ZSBWApp"
BUG_FOLDER = r"C:\ProgramData\ZSBWApp\BugReports"
LOG_FOLDER = os.path.join(DEFAULT_FILE_PATH, 'logs')
os.makedirs(BUG_FOLDER, exist_ok=True)
os.makedirs(os.path.join(LOG_FOLDER), exist_ok=True)
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
app.secret_key = secrets.token_hex(32)
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.logger.info(f"NEW LOG: timestamp: {datetime.now().strftime("%Y/%m/%d, %H:%M:%S")}\n\n")
app.logger.debug(f"Current environment: {os.getenv('ENVIRONMENT')}")
# Create a StreamHandler to handle file output

handler = logging.FileHandler(LOG_FILE)
# Define A Custom Log Message Format
formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
# Assign The Formatter To The Handler
handler.setFormatter(formatter)
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.setLevel(logging.WARNING)
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
            confirmed BOOl,
            last_ip TEXT
        );
    """)
    app.logger.info("Database was created")
    # test user
    cur.execute("SELECT 1 FROM credentials WHERE uname='test'")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO credentials (uname, pswd, email,    confirmed, last_ip) VALUES (?, ?, ?, ?, ?)",
            ("test", hashlib.sha256("test".encode()).hexdigest(), "test@test.com", True, "0.0.0.0")
        )
    app.logger.info("Test user was created")
    con.commit()
    con.close()


init_db()

# ---------------- AUTH functions ----------------
def check_credentials(uname, pswd):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("SELECT pswd FROM credentials WHERE uname=?", (uname,))
    row = cur.fetchone()
    cur.execute("SELECT confirmed FROM credentials WHERE uname=?", (uname,))
    confirmed = cur.fetchone()
    confirmed = confirmed[0] if confirmed  != None else None
    
    current_app.logger.info("Checking a user credentials")
    if not row:
        return False, False
    checked_hash = (hashlib.sha256(pswd.encode()).hexdigest() == row[0])
    con.close()
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

def modify_lastIP(ip, uname):
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    cur.execute("UPDATE credentials SET last_ip=? WHERE uname=?", (ip, uname,))
    con.commit()
    con.close

# ---------------- Functions --------------
def dispatchCommands(command_table, command_name, args):
    if command_name not in command_table:
        raise ValueError(f"Command {command_name} not found in command table.")
    
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
# ---------------- COMMAND TABLE ------------
COMMAND_TABLE = {
                "DEBUG": 
                {"name": debugMessage, 
                "args": []}
                        }
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
        ip = request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']
        current_app.logger.warning(f"A user with IP address {ip} has tried to access the dashboard without logging in. Sending them to login.")
        return redirect(url_for("login"))
    
    return render_template("dashboard.html")


@app.route("/logout")
def logout():
    current_app.logger.info(f"User {session['uname']} has logged out.")
    session.clear()
    return redirect(url_for("home"))


@app.route("/rapport")
def rapport():
    if not session.get("logged_in"):
        ip = request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']
        current_app.logger.warning(f"Someone with IP address {ip} has tried to access page /rapport while not being logged in. Sending them to login")
        return redirect(url_for("login"))

    user_dir = os.path.join(DEFAULT_FILE_PATH, session["uname"])
    os.makedirs(user_dir, exist_ok=True)
    current_app.logger.info(f"User {session['uname']} is creating a rapport.")
    return render_template("rapport.html")

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
    current_app.logger.info(f"The job with job_id {job_id} for user {session['uname']} has been finished.")
    return send_file(job["file"], as_attachment=True)


# ---------------- LOADING PAGE -------------
@app.route("/loading/<job_id>")
def loading(job_id):
    return render_template("loading.html", job_id=job_id)


@app.route("/debug/jobs")
def debug_jobs():
    current_app.logger.warning(f"Someone is trying to access a debug tool at /debug/jobs. IP address is {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']}.")
    return jobs

#----------------- SAVING SYSTEM -------------
@app.route("/myfiles")
def myfiles():
    if "uname" not in session:
        current_app.logger.warning(f"Someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has tried to access page /myfiles while not being logged in. Sending them to login")
        return redirect(url_for("login"))

    user_folder = os.path.join(DEFAULT_FILE_PATH, session["uname"])

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

@app.route("/downloads/<filename>")
def downloads(filename):
    if "uname" not in session:
        current_app.logger.warning(f"Someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has tried to access page /dowloads/{filename} while not being logged in. Sending them to login")
        return redirect(url_for("login"))

    user_folder = os.path.join(DEFAULT_FILE_PATH, session["uname"])

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
    current_app.logger.debug(f"Received: {repr(code)}")
    if hashlib.sha256(code.encode()).hexdigest() == "8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918":
        session["admin_logged_in"] = True
        current_app.logger.warning(f"Someone with IP {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has gotten admin access. Shut down server?")
        return redirect(url_for("admin"))
    current_app.logger.warning(f"Someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has unsuccessfully tried to get admin access.")
    flash("Wrong password")
    return redirect(url_for("home"))

@app.route("/admin_logged_in", methods=["GET", "POST"])
def admin():
    if not session.get("admin_logged_in"):
        flash("You are not allowed here", "error")
        return redirect(url_for("home"))

    # Read the log file
    try:
        with open(LOG_FILE, "r", encoding="cp1252") as f:
            logs = f.read()
    except FileNotFoundError:
        logs = "No log file found."

    if request.method == "POST":
        code = request.form.get("code", "")
        args = {}

        try:
            func = dispatchCommands(COMMAND_TABLE, code, args)
            func()
            flash("Command executed.", "success")
        except Exception as e:
            app.logger.exception("Admin command failed")
            flash(f"Error: {e}", "error")

        # Reload the log after the command executes
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            logs = f.read()

    return render_template("admin.html", logs=logs)


@app.route("/KillSwitch", methods=["GET"])
def killSwitch():
    if session["admin_logged_in"]:
        current_app.logger.critical(f"Kill switch activated by someone with IP address {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']}")
        os._exit(1)
        return 0
    current_app.logger.warning(f"Someone with IP adress {request.environ.get('HTTP_X_FORWARDED_FOR') if request.environ.get('HTTP_X_FORWARDED_FOR') != None else request.environ['REMOTE_ADDR']} has tried to use the kill switch whitout being admin.")
    flash("You are not allowed here.", "error")
    return(url_for("home"))

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
#------------------ COOKIES EXPLAINATION ----------
@app.route("/cookies")
def cookies():
    return render_template("cookies.html")
@app.route("/download_collected_data", methods=["GET", "POST"])
def download_data():
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
    app.run(debug=True, host='0.0.0.0')