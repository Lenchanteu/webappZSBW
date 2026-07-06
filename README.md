# webappZSBW
Veuiller configurer un fichier .env sur base de ce template:

# À configurer pour chaque environnement

FLASK_DEBUG=True/False

# Clé secrète Flask (générer avec: python -c "import secrets; print(secrets.token_hex(32))")
SECRET_KEY=A_CHANGER

# Configuration Email SMTP
SMTP_EMAIL=email@gmail.com
SMTP_PASSWORD=Code
SMTP_SERVER=smtp.gmail.com (si gmail)
SMTP_PORT=465 (si gmail)

# Admin Password (générer avec: python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('votre_mot_de_passe_admin', method='pbkdf2:sha256'))")
ADMIN_PASSWORD_HASH=pbkdf2:sha256:changez_ceci

# Configuration Session
SESSION_TIMEOUT_MINUTES=900
SESSION_REFRESH_EACH_REQUEST=True

# Configuration Base de Données
DATABASE_PATH=database/credentials.db

# Configuration Fichiers
DEFAULT_FILE_PATH=/ProgramData/ZSBWApp
BUG_FOLDER=/ProgramData/ZSBWApp/BugReports
LOG_FOLDER=/ProgramData/ZSBWApp/logs

# Configuration Sécurité
REQUIRE_HTTPS=True
