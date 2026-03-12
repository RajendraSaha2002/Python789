# ============================================================
# config.py — App & Database Configuration
# ============================================================

class Config:
    # Flask
    SECRET_KEY = "parrot_os_dashboard_secret_2026"
    DEBUG = True
    HOST = "0.0.0.0"
    PORT = 5000

    # PostgreSQL — Change these to your credentials
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_NAME = "parrot_dashboard"
    DB_USER = "postgres"
    DB_PASS = "varrie75"

    # Connection string
    DATABASE_URL = (
        f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )