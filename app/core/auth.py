from functools import wraps
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user
from app.core.models import db, User, Store, Feature
from werkzeug.security import generate_password_hash, check_password_hash
from flask import jsonify

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'error': 'Admin privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def store_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'store':
            return jsonify({'error': 'Store privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'customer':
            return jsonify({'error': 'Customer privileges required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def check_feature_access(feature_name):
    if not current_user.is_authenticated:
        return False
    if current_user.role == 'admin':
        return True
    store = Store.query.get(current_user.store_id)
    if not store or not store.is_active:
        return False
    feature = Feature.query.filter_by(name=feature_name).first()
    if not feature or not feature.is_active:
        return False
    return store.subscription_plan >= feature.plan_required