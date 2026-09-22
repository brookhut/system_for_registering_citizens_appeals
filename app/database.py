from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, scoped_session, sessionmaker
from app.config import Config

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI, pool_pre_ping=True)
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()


def init_db():
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    ensure_superadmin()


def ensure_superadmin():
    from app.models import User
    from werkzeug.security import generate_password_hash

    username = Config.SUPERADMIN_USERNAME
    user = db_session.query(User).filter_by(username=username).first()
    
    if not user:
        # Create built-in superadmin
        admin_user = User(
            username=username,
            password_hash=generate_password_hash(Config.SUPERADMIN_PASSWORD),
            full_name=Config.SUPERADMIN_FULL_NAME,
            role='superadmin',
            is_builtin=True,
            is_active=True
        )
        db_session.add(admin_user)
        db_session.commit()
    else:
        # Ensure built-in superadmin attributes remain protected and in sync with .env
        changed = False
        if not user.is_builtin:
            user.is_builtin = True
            changed = True
        if not user.is_active:
            user.is_active = True
            changed = True
        if user.role != 'superadmin':
            user.role = 'superadmin'
            changed = True
        # Always update password from .env if needed
        if not user.check_password(Config.SUPERADMIN_PASSWORD):
            user.password_hash = generate_password_hash(Config.SUPERADMIN_PASSWORD)
            changed = True
        if changed:
            db_session.commit()
