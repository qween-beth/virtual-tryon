from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from app.core.database import db  # Import the db object
from app.api.errors import register_error_handlers
from app.admin import admin_bp
from app.store import store_bp
from app.customer import customer_bp
from app.auth.routes import auth_bp
from app.main import main_bp  # Add this line


# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    from app.core.models import User
    return User.query.get(int(user_id))

def create_app(config_name='config.DevelopmentConfig'):
    """
    Factory function to create and configure the Flask app.
    """
    app = Flask(__name__)
    app.config.from_object(config_name)
    app.secret_key = '123ertg6yu5665'

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    Migrate(app, db)


    # Register blueprints
    app.register_blueprint(main_bp)  # No URL prefix for main blueprint
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(store_bp, url_prefix='/store')
    app.register_blueprint(customer_bp, url_prefix='/customer')


    # Register error handlers
    register_error_handlers(app)

    return app