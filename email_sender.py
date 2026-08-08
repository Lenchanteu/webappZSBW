import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv
from flask_babel import gettext as _

load_dotenv()
EMAIL = os.getenv('SMTP_EMAIL')
PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_SERVER= os.getenv('SMTP_SERVER')
SMTP_PORT= os.getenv('SMTP_PORT')

def send_bug_report(report_folder):
    msg = EmailMessage()
    msg["Subject"] = "New Bug Report"
    msg["From"] = EMAIL
    msg["To"] = EMAIL

    msg.set_content("A new bug report has been submitted from the app.")

    # Attach every file in the report folder
    for filename in os.listdir(report_folder):
        filepath = os.path.join(report_folder, filename)

        with open(filepath, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="application",
                subtype="octet-stream",
                filename=filename
            )

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp: # pyright: ignore[reportArgumentType]
        smtp.login(EMAIL, PASSWORD) # pyright: ignore[reportArgumentType]
        smtp.send_message(msg)
        
def send_confirmation_email(user, email_addrs, url):
    msg = EmailMessage()
    msg["Subject"] = _("Confirmation of your email")
    msg["From"] = EMAIL #temporary
    msg["To"] = email_addrs
    msg.set_content(_("To user %(user)s,\n You have created an account for the ZSBW application. Please confirm your email address to use the application. To do so, please click on this link: %(url)s.\n Thank you") % {
        "user": user,
        "url": url
    })
    
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:  # type: ignore
        smtp.login(EMAIL, PASSWORD) # type: ignore
        smtp.send_message(msg)

def send_passcode(user, email_addrs, passcode):
    msg = EmailMessage()
    msg["Subject"] = _("Code to change your password")
    msg["From"] = EMAIL
    msg["To"] = email_addrs
    msg.set_content(_("To user %(user)s, You have requested a password change. To confirm your identity, here is the code to authorize the change: %(passcode)s. Didn't request a password change? Someone may have obtained your password; we recommend that you change your password and check the latest logins to your account.") % {
        "user": user,
        "passcode": passcode
    })
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp: #type: ignore
        smtp.login(EMAIL, PASSWORD) # type: ignore
        smtp.send_message(msg)