#Code under a source-available license. See more info in LICENSE
#Author: Merlin Van Cranem 
#Contact: vancranemmerlin@gmail.com
#https://github.com/Lenchanteu
#Last modifications: 01/09/2026 by Merlin Van Cranem
#------------IMPORTS------------
import smtplib
import os
from email.message import EmailMessage
from dotenv import load_dotenv

#----------VARIABLES--------- (variables come from the .env file)
load_dotenv()
EMAIL = os.getenv('SMTP_EMAIL')
PASSWORD = os.getenv('SMTP_PASSWORD')
SMTP_SERVER= os.getenv('SMTP_SERVER')
SMTP_PORT= os.getenv('SMTP_PORT')

#--------------FUNCTIONs------------
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

    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp: # pyright: ignore[reportArgumentType]
        smtp.login(EMAIL, PASSWORD) # pyright: ignore[reportArgumentType]
        smtp.send_message(msg)
        
def send_confirmation_email(user, email_addrs, url):
    msg = EmailMessage()
    msg["Subject"] = "Confirmation de l'email, App ZSBW"
    msg["From"] = EMAIL #temporary
    msg["To"] = email_addrs
    msg.set_content(f"A l'utilisateur {user},\n Vous avez créé(e) un compte pour l'application ZSBW. Veuillez confirmer votre addresse email pour pouvoir utiliser l'application. Pour ce faire, veuillez cliquer sur ce lien: {url}.\n Merci")
    
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:  # type: ignore
        smtp.login(EMAIL, PASSWORD) # type: ignore
        smtp.send_message(msg)

def send_passcode(user, email_addrs, passcode):
    msg = EmailMessage()
    msg["Subject"] = "Code pour le changement de votre mot de passe"
    msg["From"] = EMAIL
    msg["To"] = email_addrs
    msg.set_content(f"À l'utilisateur {user}, \n Vous avez fait une demande de changement de mot de passe. Afin de confirmer votre identité, voici le code pour autoriser le changement {passcode}. \n Vous n'avez pas fait de demande de changement de mot de passe? Quelqu'un à peut-être réussi à avoir votre mot de passe, nous vous reccomendons de changer votre mot de passe et de vérifier les dernières connections à votre compte.")
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp: #type: ignore
        smtp.login(EMAIL, PASSWORD) # type: ignore
        smtp.send_message(msg)

def send_PDF_to_people(email_addrs, file):
    filename = os.path.splitext(os.path.basename(file))
    filename = filename[0][13:]
    msg = EmailMessage()
    msg["Subject"] = "Rapport de prévention incendie concernant " + filename
    msg["From"] = EMAIL
    msg["To"] = email_addrs
    msg.set_content(f"Madame la Bourgmestre, Monsieur le Bourgmestre,\n Dans le cadre de la prévention incendie, la zone de secours du Brabant Wallon a fait une visite sur une implémentation temporaire. Vous pourrez trouver un rapport concernant cette visite attaché à cet email. \n Veuillez agréer, Madame la Bourgmestre, Monsieur le Bourgmestre, l'expression de nos salutations distinguées. \n Ce message à été généré automatiquement par l'application Fire PrevPDF.")
    msg.add_attachment(file)