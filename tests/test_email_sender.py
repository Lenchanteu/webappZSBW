import importlib
import sys
import types


def test_email_sender_uses_smtp(monkeypatch, tmp_path):
    class FakeSMTP:
        instances = []

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.sent_messages = []
            type(self).instances.append(self)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def login(self, email, password):
            self.logged_in = (email, password)

        def send_message(self, message):
            self.sent_messages.append(message)

    monkeypatch.setenv("SMTP_EMAIL", "from@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "secret")
    monkeypatch.setenv("SMTP_SERVER", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "465")

    fake_smtplib = types.ModuleType("smtplib")
    fake_smtplib.SMTP_SSL = FakeSMTP
    sys.modules["smtplib"] = fake_smtplib

    sys.modules.pop("email_sender", None)
    email_sender = importlib.import_module("email_sender")

    report_dir = tmp_path / "report"
    report_dir.mkdir()
    (report_dir / "details.txt").write_text("issue", encoding="utf-8")

    email_sender.send_bug_report(str(report_dir))
    assert len(FakeSMTP.instances) == 1

    email_sender.send_confirmation_email("alice", "alice@example.com", "https://example.com")
    assert len(FakeSMTP.instances) == 2

    email_sender.send_passcode("alice", "alice@example.com", "123456")
    assert len(FakeSMTP.instances) == 3
