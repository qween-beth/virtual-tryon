from app import create_app
from flask import Flask, render_template, request, url_for, send_from_directory, jsonify, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from app.core.models import db, User, Store, Feature
from werkzeug.security import generate_password_hash, check_password_hash
import asyncio
import fal_client
import requests
from base64 import b64encode
from dotenv import load_dotenv
from datetime import datetime
from dotenv import load_dotenv
import os
from hypercorn.config import Config
from hypercorn.asyncio import serve


# Load environment variables
load_dotenv()

# Check for required environment variables
REQUIRED_ENV_VARS = {
    'FAL_KEY': 'FAL API key for image processing',
    'DATABASE_URL': 'Database connection string',
    'SECRET_KEY': 'Flask application secret key'
}

missing_vars = []
for var, description in REQUIRED_ENV_VARS.items():
    if not os.getenv(var):
        missing_vars.append(f"{var} ({description})")

if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

def seed_database(app):
    """
    Seed the database with initial data.
    
    Args:
        app: Flask application instance
    """
    try:
        with app.app_context():
            db.create_all()

            # Create default admin user if it doesn't exist
            admin = User.query.filter_by(email='admin@example.com').first()
            if not admin:
                admin = User(
                    email='admin@example.com',
                    password_hash=generate_password_hash('admin'),
                    role='admin'
                )
                db.session.add(admin)
                print("Created admin user")

            # Create default store if needed
            default_store = Store.query.filter_by(name='Default Store').first()
            if not default_store:
                default_store = Store(
                    name='Default Store',
                    subscription_plan='premium',
                    credit_balance=100
                )
                db.session.add(default_store)
                db.session.commit()  # Commit to get the store ID
                print("Created default store")

            # Create default store user if needed
            store_user = User.query.filter_by(email='user@example.com').first()
            if not store_user:
                store_user = User(
                    email='user@example.com',
                    password_hash=generate_password_hash('user'),
                    role='store',
                    store_id=default_store.id
                )
                db.session.add(store_user)
                print("Created store user")

            # Add default features if needed
            default_features = [
                {'name': 'basic_generation', 'plan_required': 'basic', 'description': 'Basic image generation capabilities'},
                {'name': 'advanced_generation', 'plan_required': 'premium', 'description': 'Advanced AI-powered generation'},
                {'name': 'bulk_operations', 'plan_required': 'premium', 'description': 'Process multiple items at once'}
            ]

            for feature_data in default_features:
                existing_feature = Feature.query.filter_by(name=feature_data['name']).first()
                if not existing_feature:
                    new_feature = Feature(
                        name=feature_data['name'],
                        plan_required=feature_data['plan_required'],
                        description=feature_data.get('description'),
                        is_active=True
                    )
                    db.session.add(new_feature)
                    print(f"Created feature: {feature_data['name']}")

            db.session.commit()
            print("Database seeding completed successfully")

    except Exception as e:
        print(f"Error seeding database: {str(e)}")
        raise

async def main():
    """
    Main application entry point.
    Sets up and runs the application server.
    """
    try:
        # Configure Hypercorn
        config = Config()
        config.bind = ["localhost:5000"]
        
        # Initialize app
        app = create_app()
        
        # Seed the database
        seed_database(app)
        
        print("Starting server on http://localhost:5000")
        await serve(app, config)
        
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())