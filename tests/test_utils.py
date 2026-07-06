import hashlib
import importlib
import sys


def test_database_helpers_work_with_temp_db(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "database").mkdir(exist_ok=True)
    sys.modules.pop("utils", None)
    utils = importlib.import_module("utils")

    utils.create_table()
    utils.cur.execute(
        "INSERT INTO credentials (uname, pswd, email, confirmed, last_ip) VALUES (?, ?, ?, ?, ?)",
        ("alice", hashlib.sha256(b"secret").hexdigest(), "alice@example.com", 1, "127.0.0.1"),
    )
    utils.con.commit()

    assert utils.check_credentials("alice", "secret") is True
    assert utils.check_credentials("missing", "secret") is False

    utils.delete_table()
    utils.create_table()
