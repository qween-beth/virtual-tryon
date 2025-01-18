from flask_sqlalchemy import SQLAlchemy

# Initialize the SQLAlchemy object
db = SQLAlchemy()

def init_db(app):
    """Initialize the database with the app."""
    db.init_app(app)
    with app.app_context():
        db.create_all()  # Create all tables if they don't exist
