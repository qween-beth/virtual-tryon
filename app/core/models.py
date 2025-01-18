from flask_login import UserMixin
from .database import db
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    subscription_plan = db.Column(db.String(20), default='basic')
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
    plan_required = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=True)

class TryOn(db.Model):
    """Model for storing try-on records"""
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id'), nullable=False)
    model_image = db.Column(db.String(255), nullable=False)
    garment_image = db.Column(db.String(255), nullable=False)
    result_image = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    store = db.relationship('Store', backref=db.backref('tryons', lazy=True))
