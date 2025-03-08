from flask_login import UserMixin
from .database import db
from datetime import datetime

# Define allowed roles
USER_ROLES = ['admin', 'store', 'customer']

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Roles: admin, store, customer
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=True)  # Nullable for general customers
    credit_balance = db.Column(db.Integer, default=0)  # Added credit balance for all users
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    # Role validation
    def set_role(self, role):
        if role not in USER_ROLES:
            raise ValueError(f"Invalid role: {role}. Allowed roles: {USER_ROLES}")
        self.role = role

    def is_admin(self):
        return self.role == 'admin'

    def is_store(self):
        return self.role == 'store'

    def is_customer(self):
        return self.role == 'customer'

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    subscription_plan = db.Column(db.String(20), default='basic')  # Plan types: basic, premium
    is_active = db.Column(db.Boolean, default=True)
    credit_balance = db.Column(db.Integer, default=0)
    
    users = db.relationship('User', backref='store', lazy=True)

class CreditTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    to_user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    amount = db.Column(db.Integer, nullable=False)
    transaction_type = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Feature(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    plan_required = db.Column(db.String(20), nullable=False)  # basic or premium
    is_active = db.Column(db.Boolean, default=True)

class TryOn(db.Model):
    """Model for storing virtual try-on records"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # The customer who tried it on
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=True)  # Nullable for general customers
    model_image = db.Column(db.String(255), nullable=False)  # Image of the model
    garment_image = db.Column(db.String(255), nullable=False)  # Image of the clothing
    result_image = db.Column(db.String(255), nullable=False)  # Output try-on result
    category = db.Column(db.String(50), nullable=False)  # Clothing category
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    credits_source = db.Column(db.String(20), nullable=False, default='user')

    # Relationships
    user = db.relationship('User', backref=db.backref('tryons', lazy=True))
    store = db.relationship('Store', backref=db.backref('tryons', lazy=True))