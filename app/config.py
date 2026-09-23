import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).resolve().parent.parent / '.env'
load_dotenv(dotenv_path=env_path)


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default-dev-secret-key-3918239')
    
    # Database URL
    DATABASE_URL = os.getenv('DATABASE_URL')
    db_user = os.getenv('DB_USER', 'postgres')
    db_pass = os.getenv('DB_PASSWORD', '')
    db_host = os.getenv('DB_HOST', 'localhost')
    db_port = os.getenv('DB_PORT', '5432')
    db_name = os.getenv('DB_NAME', 'appeals_db')

    if not DATABASE_URL:
        auth = f"{db_user}:{db_pass}" if db_pass else db_user
        DATABASE_URL = f"postgresql://{auth}@{db_host}:{db_port}/{db_name}"
    else:
        # Если задан DB_PASSWORD, но в DATABASE_URL пароль не указан — объединяем
        if db_pass and '@' in DATABASE_URL:
            proto_user, rest = DATABASE_URL.split('@', 1)
            if '://' in proto_user:
                proto, user_part = proto_user.split('://', 1)
                if ':' not in user_part:
                    DATABASE_URL = f"{proto}://{user_part}:{db_pass}@{rest}"

    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Built-in SuperAdmin credentials
    SUPERADMIN_USERNAME = os.getenv('SUPERADMIN_USERNAME', 'superadmin')
    SUPERADMIN_PASSWORD = os.getenv('SUPERADMIN_PASSWORD', 'SuperAdminPass2026!')
    SUPERADMIN_FULL_NAME = os.getenv('SUPERADMIN_FULL_NAME', 'Главный администратор (Встроенный)')
    
    PORT = int(os.getenv('PORT', 5000))
