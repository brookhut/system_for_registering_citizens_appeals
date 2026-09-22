import os
from flask import Flask
from flask_login import LoginManager
from app.config import Config
from app.database import db_session, init_db
from app.models import User

login_manager = LoginManager()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask-Login
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Пожалуйста, войдите в систему для доступа к этой странице.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db_session.get(User, int(user_id))

    # Teardown database session
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.appeals import appeals_bp
    from app.routes.admin import admin_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(appeals_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Jinja template filters and globals
    from datetime import date
    @app.context_processor
    def inject_now():
        return {
            'current_date': date.today(),
            'current_date_str': date.today().strftime('%Y-%m-%d'),
            'current_date_eur': date.today().strftime('%d.%m.%Y'),
        }

    # Ensure DB is initialized
    with app.app_context():
        init_db()

    return app
