from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import hashlib
import secrets
from docxtpl import DocxTemplate
import os
from pdf_maker import convert_to_pdf
from jinja2 import Environment
from docxtpl import DocxTemplate


app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Path to database file
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'credentials.db')
TEMPLATE = "Rapport_de_prévention_incendie_template.docx"
OUTPUT_DOCX = "generated_report.docx"
OUTPUT_PDF = "generated_report.pdf"



def init_db():
    """Initialize the database with required tables"""
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS credentials (
            uname TEXT PRIMARY KEY,
            pswd TEXT NOT NULL
        );
    """)
    # Insert test user if not exists
    cur.execute("SELECT 1 FROM credentials WHERE uname='test'")
    if not cur.fetchone():
        test_user = ("test", hashlib.sha256("test".encode('utf-8')).hexdigest())
        cur.execute("INSERT INTO credentials (uname, pswd) VALUES (?, ?)", test_user)
    con.commit()
    con.close()

# Initialize database
init_db()

def check_credentials(uname, pswd):
    """Check if username and password match"""
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()
    cur.execute("SELECT pswd FROM credentials WHERE uname=?;", (uname,))
    check = cur.fetchone()
    con.close()

    if check is None:
        return False  # User not found

    # Hash the input password
    hashed_pswd = hashlib.sha256(pswd.encode('utf-8')).hexdigest()
    # Compare with stored hash
    return hashed_pswd == check[0]

def create_account(uname, pswd):
    """Create a new user account"""
    con = sqlite3.connect(DATABASE)
    cur = con.cursor()

    # Check if username already exists
    cur.execute("SELECT 1 FROM credentials WHERE uname=?;", (uname,))
    if cur.fetchone():
        con.close()
        return False  # Username already exists

    # Hash the password
    hash_obj = hashlib.sha256()
    hash_obj.update(pswd.encode('utf-8'))
    hashed_pswd = hash_obj.hexdigest()

    # Insert the new user
    cur.execute("INSERT INTO credentials (uname, pswd) VALUES (?, ?)", (uname, hashed_pswd))
    con.commit()
    con.close()
    return True  # Registration successful

@app.route("/")
def home():
    return render_template('home.html')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('login.html')

    uname = request.form.get('uname')
    pswd = request.form.get('pswd')

    if check_credentials(uname, pswd):
        session['logged_in'] = True
        session['uname'] = uname
        flash('Login successful!', 'success')
        return redirect(url_for('dashboard'))
    else:
        flash('Invalid credentials!', 'error')
        return redirect(url_for('login'))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template('register.html')

    uname = request.form.get('uname')
    pswd = request.form.get('pswd')
    confirm_pswd = request.form.get('confirm_pswd')

    # Validate password match
    if pswd != confirm_pswd:
        flash('Passwords do not match!', 'error')
        return redirect(url_for('register'))

    # Register the user
    if create_account(uname, pswd):
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    else:
        flash('Username already exists! Please choose a different username.', 'error')
        return redirect(url_for('register'))

@app.route("/dashboard")
def dashboard():
    if not session.get('logged_in'):
        flash('Please log in to access this page.', 'error')
        return redirect(url_for("login"))
    return render_template('dashboard.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('uname', None)
    flash('You were logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/rapport')
def rapport():
    return render_template('rapport.html')

@app.route("/generate-fire-report", methods=["POST"])
def generate_report():
    data = request.form.to_dict()
    doc = DocxTemplate(TEMPLATE)
    doc.render(
    data,
    jinja_env=Environment(
        trim_blocks=True,
        lstrip_blocks=True
    )
)
    # List of checkbox fields
    checkboxes = [
        "chapiteau",
        "tentes",
        "gradins",
        "scene",
        "structures_aeriennes",
        "chauffage",
        "barbecue",
        "points_de_cuissons",
        "extincteurs",
        "eclairage_securite",
        "pictogrammes",
        "PV_toiles",
        "PV_electr",
        "PV_struct",
    ]

    # Add all prescription checkboxes
    for letter in "BCDEFGHIJKLMNPQR":
        for i in range(1, 20):
            checkboxes.append(f"it_3{letter}{i}")

    # Convert HTML checkboxes to Python booleans
    for field in checkboxes:
        data[field] = field in request.form

    # Fix template naming mismatch
    if "tentes_nombre" in data:
        data["tentes_nombres"] = data["tentes_nombre"]

    # Load DOCX template
    doc = DocxTemplate(TEMPLATE)

    # Replace all Jinja variables
    doc.render(data)

    # Save DOCX
    doc.save(OUTPUT_DOCX)

    # Convert to PDF
    convert_to_pdf(OUTPUT_DOCX)

    return send_file(
        OUTPUT_PDF,
        as_attachment=True,
        download_name="rapport_prevention_incendie.pdf",
        mimetype="application/pdf"
    )


if __name__ == '__main__':
    app.run(debug=True)
