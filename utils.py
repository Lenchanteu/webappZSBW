import sqlite3
import hashlib
con = sqlite3.connect("database/credentials.db")
cur = con.cursor()

def create_table():
    cur.execute("""
    CREATE TABLE IF NOT EXISTS credentials (
        uname TEXT PRIMARY KEY,
        pswd TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        confirmed BOOl,
        last_ip TEXT
    );
""")
    con.commit()
def check_credentials(uname, pswd):
    cur.execute("SELECT pswd FROM credentials WHERE uname=?;", (uname,))
    check = cur.fetchone()
    if check is None:
        return False  # User not found
    m = hashlib.sha256()
    m.update(pswd.encode('utf-8'))
    print(f'password is {m.hexdigest()} and check is {check[0]}')
    return m.hexdigest() == check[0]
    
def delete_table():
    cur.execute("DROP TABLE credentials")
    con.commit()

def dac(): #create and delete table
    delete_table()
    create_table()
def close():
    con.close()