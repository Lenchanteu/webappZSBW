#Code under a source-available license. See more info in LICENSE
#Author: Merlin Van Cranem 
#Contact: vancranemmerlin@gmail.com
#https://github.com/Lenchanteu
#Last modifications: 04/09/2026 by Merlin Van Cranem
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
    msg["To"] = 'vancranemmerlin@gmail.com'

    msg.set_content("Un nouveau rapport de bug a été envoyé depuis l'application ZSBW PrevPDF.\n\n" "Les fichiers du rapport sont joints à cet e-mail.")
    html = """ <!DOCTYPE html> <html lang="fr"> <head> <meta charset="UTF-8"> <meta name="viewport" content="width=device-width, initial-scale=1.0"> <title>Nouveau rapport de bug - ZSBW PrevPDF</title> </head> <body style=" margin: 0; padding: 0; background-color: #f4f4f4; font-family: Arial, Helvetica, sans-serif; color: #333333; "> <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color: #f4f4f4; padding: 40px 15px;"> <tr> <td align="center"> <!-- Main container --> <table width="600" cellpadding="0" cellspacing="0" border="0" style=" max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); "> <!-- Header --> <tr> <td align="center" style=" background-color: #1f2937; padding: 30px 20px; "> <h1 style=" margin: 0; color: #ffffff; font-size: 26px; font-weight: 600; "> ZSBW </h1> <p style=" margin: 8px 0 0; color: #d1d5db; font-size: 14px; "> Rapport de bug </p> </td> </tr> <!-- Content --> <tr> <td style="padding: 40px 35px;"> <h2 style=" margin: 0 0 20px; color: #1f2937; font-size: 22px; "> Nouveau rapport de bug </h2> <p style=" margin: 0 0 16px; font-size: 15px; line-height: 1.6; "> Un nouveau rapport de bug a été soumis depuis l'application <strong>ZSBW PrevPDF</strong>. </p> <p style=" margin: 0 0 25px; font-size: 15px; line-height: 1.6; "> Les fichiers associés au rapport sont joints à cet e-mail. </p> <!-- Attachment notice --> <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 25px 0;"> <tr> <td style=" background-color: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 6px; padding: 20px; "> <p style=" margin: 0; font-size: 14px; line-height: 1.5; color: #4b5563; "> <strong>Pièces jointes</strong> <br> Les fichiers du rapport de bug sont disponibles dans les pièces jointes de cet e-mail. </p> </td> </tr> </table> <p style=" margin: 30px 0 0; font-size: 15px; line-height: 1.6; "> Merci de consulter les fichiers joints afin d'analyser le problème signalé. </p> <p style=" margin: 30px 0 0; font-size: 15px; line-height: 1.6; "> <strong>Application ZSBW PrevPDF</strong> </p> </td> </tr> <!-- Footer --> <tr> <td align="center" style=" background-color: #f9fafb; border-top: 1px solid #e5e7eb; padding: 20px; "> <p style=" margin: 0; color: #888888; font-size: 11px; line-height: 1.5; "> Cet e-mail a été envoyé automatiquement par l'application ZSBW. <br> Merci de ne pas répondre à cet e-mail. </p> </td> </tr> </table> </td> </tr> </table> </body> </html> """
    msg.add_alternative(html, subtype="html")   
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
    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Confirmation de votre compte ZSBW</title>
</head>

<body style="
    margin: 0;
    padding: 0;
    background-color: #f4f4f4;
    font-family: Arial, Helvetica, sans-serif;
    color: #333333;
">

    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background-color: #f4f4f4; padding: 40px 15px;">
        <tr>
            <td align="center">

                <!-- Main container -->
                <table width="600" cellpadding="0" cellspacing="0" border="0"
                       style="
                           max-width: 600px;
                           width: 100%;
                           background-color: #ffffff;
                           border-radius: 8px;
                           overflow: hidden;
                           box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                       ">

                    <!-- Header -->
                    <tr>
                        <td align="center"
                            style="
                                background-color: #1f2937;
                                padding: 30px 20px;
                            ">
                            <h1 style="
                                margin: 0;
                                color: #ffffff;
                                font-size: 26px;
                                font-weight: 600;
                            ">
                                ZSBW
                            </h1>

                            <p style="
                                margin: 8px 0 0;
                                color: #d1d5db;
                                font-size: 14px;
                            ">
                                Confirmation de compte
                            </p>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 35px;">

                            <h2 style="
                                margin: 0 0 20px;
                                color: #1f2937;
                                font-size: 22px;
                            ">
                                Bonjour { user },
                            </h2>

                            <p style="
                                margin: 0 0 16px;
                                font-size: 15px;
                                line-height: 1.6;
                            ">
                                Vous avez créé un compte pour l'application
                                <strong>ZSBW PrevPDF</strong>.
                            </p>

                            <p style="
                                margin: 0 0 25px;
                                font-size: 15px;
                                line-height: 1.6;
                            ">
                                Afin de pouvoir utiliser l'application, veuillez
                                confirmer votre adresse e-mail en cliquant sur le
                                bouton ci-dessous.
                            </p>

                            <!-- Confirmation button -->
                            <table cellpadding="0" cellspacing="0" border="0"
                                   align="center"
                                   style="margin: 30px auto;">
                                <tr>
                                    <td align="center"
                                        style="
                                            border-radius: 6px;
                                            background-color: #2563eb;
                                        ">
                                        <a href="{ url }"
                                           style="
                                               display: inline-block;
                                               padding: 14px 28px;
                                               color: #ffffff;
                                               text-decoration: none;
                                               font-size: 15px;
                                               font-weight: bold;
                                               border-radius: 6px;
                                           ">
                                            Confirmer mon adresse e-mail
                                        </a>
                                    </td>
                                </tr>
                            </table>

                            <p style="
                                margin: 25px 0 10px;
                                font-size: 13px;
                                line-height: 1.5;
                                color: #666666;
                            ">
                                Si le bouton ne fonctionne pas, vous pouvez
                                également utiliser le lien suivant :
                            </p>

                            <p style="
                                margin: 0;
                                font-size: 12px;
                                line-height: 1.5;
                                word-break: break-all;
                            ">
                                <a href="{ url }"
                                   style="
                                       color: #2563eb;
                                       text-decoration: underline;
                                   ">
                                    { url }
                                </a>
                            </p>

                            <p style="
                                margin: 30px 0 0;
                                font-size: 15px;
                                line-height: 1.6;
                            ">
                                Merci,<br>
                                <strong>ZSBW PrevPDF</strong>
                            </p>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td align="center"
                            style="
                                background-color: #f9fafb;
                                border-top: 1px solid #e5e7eb;
                                padding: 20px;
                            ">

                            <p style="
                                margin: 0;
                                color: #888888;
                                font-size: 11px;
                                line-height: 1.5;
                            ">
                                Cet e-mail a été envoyé automatiquement par
                                l'application ZSBW.
                                <br>
                                Merci de ne pas répondre à cet e-mail.
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
    msg.set_content(f"A l'utilisateur {user},\n Vous avez créé(e) un compte pour l'application ZSBW PrevPDF. Veuillez confirmer votre addresse email pour pouvoir utiliser l'application. Pour ce faire, veuillez cliquer sur ce lien: {url}.\n Merci")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp:  # type: ignore
        smtp.login(EMAIL, PASSWORD) # type: ignore
        smtp.send_message(msg)

def send_passcode(user, email_addrs, passcode):
    msg = EmailMessage()
    msg["Subject"] = "Code pour le changement de votre mot de passe"
    msg["From"] = EMAIL
    msg["To"] = email_addrs

    html = f"""
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Changement de mot de passe - ZSBW</title>
</head>

<body style="
    margin: 0;
    padding: 0;
    background-color: #f4f4f4;
    font-family: Arial, Helvetica, sans-serif;
    color: #333333;
">

    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="background-color: #f4f4f4; padding: 40px 15px;">
        <tr>
            <td align="center">

                <!-- Main container -->
                <table width="600" cellpadding="0" cellspacing="0" border="0"
                       style="
                           max-width: 600px;
                           width: 100%;
                           background-color: #ffffff;
                           border-radius: 8px;
                           overflow: hidden;
                           box-shadow: 0 2px 8px rgba(0,0,0,0.08);
                       ">

                    <!-- Header -->
                    <tr>
                        <td align="center"
                            style="
                                background-color: #1f2937;
                                padding: 30px 20px;
                            ">
                            <h1 style="
                                margin: 0;
                                color: #ffffff;
                                font-size: 26px;
                                font-weight: 600;
                            ">
                                ZSBW
                            </h1>

                            <p style="
                                margin: 8px 0 0;
                                color: #d1d5db;
                                font-size: 14px;
                            ">
                                Sécurité du compte
                            </p>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px 35px;">

                            <h2 style="
                                margin: 0 0 20px;
                                color: #1f2937;
                                font-size: 22px;
                            ">
                                Bonjour {user},
                            </h2>

                            <p style="
                                margin: 0 0 16px;
                                font-size: 15px;
                                line-height: 1.6;
                            ">
                                Une demande de changement de mot de passe a été
                                effectuée pour votre compte ZSBW PrevPDF.
                            </p>

                            <p style="
                                margin: 0 0 25px;
                                font-size: 15px;
                                line-height: 1.6;
                            ">
                                Afin de confirmer votre identité et d'autoriser
                                le changement de mot de passe, veuillez utiliser
                                le code suivant :
                            </p>

                            <!-- Passcode -->
                            <table width="100%" cellpadding="0" cellspacing="0" border="0"
                                   style="margin: 25px 0;">
                                <tr>
                                    <td align="center"
                                        style="
                                            background-color: #f3f4f6;
                                            border: 1px solid #e5e7eb;
                                            border-radius: 6px;
                                            padding: 22px;
                                        ">
                                        <p style="
                                            margin: 0 0 8px;
                                            font-size: 12px;
                                            color: #6b7280;
                                            text-transform: uppercase;
                                            letter-spacing: 1px;
                                        ">
                                            Code de confirmation
                                        </p>

                                        <p style="
                                            margin: 0;
                                            font-size: 30px;
                                            font-weight: bold;
                                            letter-spacing: 6px;
                                            color: #1f2937;
                                        ">
                                            {passcode}
                                        </p>
                                    </td>
                                </tr>
                            </table>

                            <p style="
                                margin: 25px 0 0;
                                font-size: 15px;
                                line-height: 1.6;
                            ">
                                <strong>Vous n'êtes pas à l'origine de cette
                                demande ?</strong>
                            </p>

                            <p style="
                                margin: 10px 0 0;
                                font-size: 15px;
                                line-height: 1.6;
                            ">
                                Quelqu'un pourrait avoir obtenu votre mot de
                                passe. Nous vous recommandons de modifier
                                immédiatement votre mot de passe et de vérifier
                                les dernières connexions à votre compte.
                            </p>

                            <p style="
                                margin: 30px 0 0;
                                font-size: 15px;
                                line-height: 1.6;
                            ">
                                Merci,<br>
                                <strong>ZSBW PrevPDF</strong>
                            </p>

                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td align="center"
                            style="
                                background-color: #f9fafb;
                                border-top: 1px solid #e5e7eb;
                                padding: 20px;
                            ">

                            <p style="
                                margin: 0;
                                color: #888888;
                                font-size: 11px;
                                line-height: 1.5;
                            ">
                                Cet e-mail a été envoyé automatiquement par
                                l'application ZSBW PrevPDF.
                                <br>
                                Merci de ne pas répondre à cet e-mail.
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
    msg.set_content(f"À l'utilisateur {user}, \n Vous avez fait une demande de changement de mot de passe. Afin de confirmer votre identité, voici le code pour autoriser le changement {passcode}. \n Vous n'avez pas fait de demande de changement de mot de passe? Quelqu'un à peut-être réussi à avoir votre mot de passe, nous vous reccomendons de changer votre mot de passe et de vérifier les dernières connections à votre compte.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as smtp: #type: ignore
        smtp.login(EMAIL, PASSWORD) # type: ignore
        smtp.send_message(msg)

def send_PDF_to_brgmstr(email_addrs, file):
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


def send_PDF_to_responsable(email_addrs, file):
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
                                Madame, Monsieur,
                            </p>

                            <p style="font-size: 15px; line-height: 1.7; margin: 0 0 18px 0;">
                                Dans le cadre de la prévention incendie, la Zone de secours
                                du Brabant wallon a effectué une visite de votre
                                <strong>installation temporaire</strong>.
                            </p>

                            <p style="font-size: 15px; line-height: 1.7; margin: 0 0 25px 0;">
                                Vous trouverez en pièce jointe à ce courriel le
                                <strong>rapport de cette visite</strong>.
                            </p>

                            <p style="font-size: 15px; line-height: 1.7; margin: 25px 0 0 0;">
                                Veuillez agréer, Madame, Monsieur,
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
Madame, Monsieur, \n
Dans le cadre de la prévention incendie, la zone de secours du Brabant Wallon a fait une visite sur votre implémentation temporaire. \n
Vous pourrez trouver le rapport de cette visite attaché à cet email. \n
Veuillez agréer, Madame, Monsieur, nos salutations les plus distinguées. \n
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
    