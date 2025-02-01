class DevelopmentConfig:
    """Development configuration."""
    DEBUG = True
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///fashion_tryon.db'  # Example for SQLite

class ProductionConfig:
    """Production configuration."""
    DEBUG = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///fashion_tryon.db'  # Example for Production Database
