#Code under a source-available license. See more info in LICENSE
#Author: Merlin Van Cranem 
#Contact: vancranemmerlin@gmail.com
#https://github.com/Lenchanteu
#Last modifications: 02/09/2026 by Merlin Van Cranem
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
    html_msg = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Rapport de prévention incendie</title>
</head>

<body style="margin: 0; padding: 0; background-color: #f4f5f7; font-family: Arial, Helvetica, sans-serif; color: #333333;">

    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #f4f5f7;">
        <tr>
            <td align="center" style="padding: 35px 15px;">

                <!-- Main container -->
                <table role="presentation" width="600" cellspacing="0" cellpadding="0" border="0"
                       style="max-width: 600px; width: 100%; background-color: #ffffff; border: 1px solid #e1e4e8;">

                    <!-- Header -->
                    <tr>
                        <td style="padding: 25px 35px; border-bottom: 1px solid #e5e5e5;">
                            <div style="font-size: 20px; font-weight: bold; color: #333333;">
                                Zone de secours du Brabant wallon
                            </div>
                            <div style="font-size: 13px; color: #777777; margin-top: 5px;">
                                Service de prévention incendie
                            </div>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 35px;">

                            <p style="font-size: 15px; line-height: 1.7; margin: 0 0 22px 0;">
                                Madame la Bourgmestre, Monsieur le Bourgmestre,
                            </p>

                            <p style="font-size: 15px; line-height: 1.7; margin: 0 0 18px 0;">
                                Dans le cadre de la prévention incendie, la Zone de secours
                                du Brabant wallon a effectué une visite d'une
                                <strong>installation temporaire</strong> située sur votre territoire.
                            </p>

                            <p style="font-size: 15px; line-height: 1.7; margin: 0 0 25px 0;">
                                Vous trouverez en pièce jointe à ce courriel le
                                <strong>rapport de cette visite</strong>.
                            </p>

                            <!-- Attachment notice -->
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
                                   style="background-color: #f7f8fa; border-left: 4px solid #555555; margin: 25px 0;">
                                <tr>
                                    <td style="padding: 15px 18px;">
                                        <div style="font-size: 14px; font-weight: bold; color: #333333;">
                                            Rapport de prévention incendie
                                        </div>
                                        <div style="font-size: 13px; color: #666666; margin-top: 5px;">
                                            Le document est joint à ce courriel au format PDF.
                                        </div>
                                    </td>
                                </tr>
                            </table>

                            <p style="font-size: 15px; line-height: 1.7; margin: 25px 0 0 0;">
                                Veuillez agréer, Madame la Bourgmestre, Monsieur le Bourgmestre,
                                l'expression de nos salutations les plus distinguées.
                            </p>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="padding: 20px 35px; background-color: #f7f7f7; border-top: 1px solid #e5e5e5;">
                            <p style="font-size: 11px; line-height: 1.5; color: #888888; margin: 0;">
                                Ce message a été généré automatiquement par l'application
                                <strong>ZSBW PrevPDF</strong>.
                            </p>
                        </td>
                    </tr>

                </table>

            </td>
        </tr>
    </table>

</body>
</html>
"""
    txt_msg = """
Madame la Bourgmestre, Monsieur le Bourgmestre, \n
Dans le cadre de la prévention incendie, la zone de secours du Brabant Wallon a fait une visite sur une implémentation temporaire se situant sur votre territoire. \n
Vous pourrez trouver le rapport de cette visite attaché à cet email. \n
Veuillez agréer, Madame la Bourgmestre, Monsieur le Bourgmestre, nos salutations les plus distinguées. \n
Ce message a été généré automatiquement par l'application ZSBW PrevPDF. """
    msg.set_content(txt_msg)
    msg.add_alternative(html_msg, subtype="html")
    with open(file, "rb") as f:
        pdf_data = f.read()

    msg.add_attachment(
        pdf_data,
        maintype="application",
        subtype="pdf",
        filename=os.path.basename(file)
    )
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp: #type:ignore
        smtp.login(EMAIL, PASSWORD) #type:ignore
        smtp.send_message(msg)
    