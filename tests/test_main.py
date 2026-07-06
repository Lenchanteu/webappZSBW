import importlib
import sys
import types

import pytest


@pytest.fixture
def main_module(monkeypatch, tmp_path):
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "credentials.db"))
    monkeypatch.setenv("DEFAULT_FILE_PATH", str(tmp_path / "reports"))
    monkeypatch.setenv("BUG_FOLDER", str(tmp_path / "bugs"))
    monkeypatch.setenv("LOG_FOLDER", str(tmp_path / "logs"))
    monkeypatch.setenv("REQUIRE_HTTPS", "False")
    monkeypatch.setenv("FLASK_DEBUG", "False")
    monkeypatch.setenv("SESSION_TIMEOUT_MINUTES", "90")
    monkeypatch.setenv("SESSION_REFRESH_EACH_REQUEST", "False")
    monkeypatch.setenv("CREATE_TEST_USER", "False")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "pbkdf2:sha256:dummy")
    monkeypatch.setenv("SMTP_EMAIL", "test@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_SERVER", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "465")

    fake_docxtpl = types.ModuleType("docxtpl")

    class FakeDocxTemplate:
        def __init__(self, template):
            self.template = template

        def render(self, data):
            self.data = data

        def save(self, output):
            self.output = output

    fake_docxtpl.DocxTemplate = FakeDocxTemplate
    sys.modules["docxtpl"] = fake_docxtpl

    fake_pdf_maker = types.ModuleType("pdf_maker")
    fake_pdf_maker.convert_to_pdf = lambda path: None
    sys.modules["pdf_maker"] = fake_pdf_maker

    sys.modules.pop("main", None)
    module = importlib.import_module("main")
    return importlib.reload(module)


def test_home_page_renders(main_module):
    client = main_module.app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"ZSBW" in response.data


def test_account_creation_and_login_flow(main_module):
    assert main_module.create_account("alice", "secret123", "alice@example.com") is True
    assert main_module.create_account("alice", "another", "other@example.com") is False

    with main_module.app.app_context():
        ok, confirmed = main_module.check_credentials("alice", "secret123")

    assert ok is True
    assert confirmed in (False, 0)
