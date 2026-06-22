import smtplib
import os
from email.message import EmailMessage

EMAIL = "vancranemmerlin@gmail.com"
PASSWORD = "fpex zjuh fikt iuop"   # Gmail password for app.

def send_bug_report(report_folder):
    msg = EmailMessage()
    msg["Subject"] = "New Bug Report"
    msg["From"] = EMAIL
    msg["To"] = EMAIL

    msg.set_content("A new bug report has been submitted from the ZSBW app.")

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

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL, PASSWORD)
        smtp.send_message(msg)
        
def send_confirmation_email(user, email_addrs, url):
    msg = EmailMessage()
    msg["Subject"] = "Confirmation de l'email, App ZSBW"
    msg["From"] = EMAIL #temporary
    msg["To"] = email_addrs
    msg.set_content(f"A l'utilisateur {user},\n Vous avez créé(e) un compte pour l'application ZSBW. Veuillez confirmer votre addresse email pour pouvoir utiliser l'application. Pour ce faire, veuillez cliquer sur ce lien: {url}.\n Merci")
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL, PASSWORD)
        smtp.send_message(msg)