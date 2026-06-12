from flask import Flask, render_template, request, redirect, url_for
import flask
import sqlite3
import hashlib

app = Flask(__name__)

con = sqlite3.connect("database/credentials.db")
cur = con.cursor()
def check_credentials(pswd, uname):
    check = cur.execute("SELECT pswd FROM credentials WHERE uname=?;", uname)
    m = hashlib.sha256()
    m.update(pswd)
    if m.hexdigest() == check:
        return True
    else: 
        return False

@app.route("/hello_world")
def hello_world():
    return "hello_world"
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template('login.html')
    uname = request.form.get('uname')
    pswd = request.form.get('pswd')
    check = check_credentials('test', uname)
    if check == True:






    return redirect(url_for('home'))

@app.route("/", methods=["POST", "GET"])  # pyright: ignore[reportArgumentType]
def home():
    return render_template('home.html'), 'index'

if __name__ == '__main__':
    app.run(debug=True)