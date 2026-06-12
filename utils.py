import sqlite3
import hashlib
con = sqlite3.connect("database/credentials.db")
cur = con.cursor()
data = f'("Test", {hashlib.sha256(b'test').hexdigest()})'
cur.execute("""
    CREATE TABLE IF NOT EXISTS credentials (
        uname TEXT PRIMARY KEY,
        pswd TEXT NOT NULL
    );
""")
uname = "Test"
pswd = "test"
hashed_pswd = hashlib.sha256(pswd.encode('utf-8')).hexdigest()

cur.execute("INSERT OR REPLACE INTO credentials (uname, pswd) VALUES (?, ?);", (uname, hashed_pswd))
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
    
print(check_credentials('Test', 'Test'))
con.commit()