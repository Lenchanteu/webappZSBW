import os
from unittest.mock import patch, MagicMock

import email_sender


@patch("email_sender.smtplib.SMTP_SSL")
def test_send_confirmation_email(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    email_sender.send_confirmation_email(
        "Merlin",
        "test@example.com",
        "https://example.com/confirm/test"
    )

    # SMTP connection was created
    mock_smtp.assert_called_once_with(
        email_sender.SMTP_SERVER,
        email_sender.SMTP_PORT
    )

    # Login was attempted
    mock_server.login.assert_called_once_with(
        email_sender.EMAIL,
        email_sender.PASSWORD
    )

    # An email was sent
    mock_server.send_message.assert_called_once()

    # Get the actual EmailMessage
    message = mock_server.send_message.call_args.args[0]

    assert message["Subject"] == "Confirmation de l'email, App ZSBW"
    assert message["From"] == email_sender.EMAIL
    assert message["To"] == "test@example.com"

    assert "Merlin" in message.get_content()
    assert "https://example.com/confirm/test" in message.get_content()


@patch("email_sender.smtplib.SMTP_SSL")
def test_send_passcode(mock_smtp):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    email_sender.send_passcode(
        "Merlin",
        "test@example.com",
        "123456"
    )

    mock_smtp.assert_called_once_with(
        email_sender.SMTP_SERVER,
        email_sender.SMTP_PORT
    )

    mock_server.login.assert_called_once_with(
        email_sender.EMAIL,
        email_sender.PASSWORD
    )

    mock_server.send_message.assert_called_once()

    message = mock_server.send_message.call_args.args[0]

    assert message["Subject"] == "Code pour le changement de votre mot de passe"
    assert message["From"] == email_sender.EMAIL
    assert message["To"] == "test@example.com"

    assert "Merlin" in message.get_content()
    assert "123456" in message.get_content()


@patch("email_sender.smtplib.SMTP_SSL")
def test_send_bug_report(mock_smtp, tmp_path):
    mock_server = MagicMock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    # Create fake report files
    report_file_1 = tmp_path / "report.txt"
    report_file_1.write_text("This is a test report.")

    report_file_2 = tmp_path / "log.txt"
    report_file_2.write_text("This is a test log.")

    email_sender.send_bug_report(str(tmp_path))

    mock_smtp.assert_called_once_with(
        email_sender.SMTP_SERVER,
        email_sender.SMTP_PORT
    )

    mock_server.login.assert_called_once_with(
        email_sender.EMAIL,
        email_sender.PASSWORD
    )

    mock_server.send_message.assert_called_once()

    message = mock_server.send_message.call_args.args[0]

    assert message["Subject"] == "New Bug Report"
    assert message["From"] == email_sender.EMAIL
    assert message["To"] == email_sender.EMAIL

    # Check attachments
    attachments = list(message.iter_attachments())

    assert len(attachments) == 2

    filenames = {
        attachment.get_filename()
        for attachment in attachments
    }

    assert filenames == {
        "report.txt",
        "log.txt"
    }