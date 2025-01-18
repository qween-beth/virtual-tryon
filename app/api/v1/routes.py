from flask import Blueprint, request, jsonify
from app.core.models import User, Store
from app.core.database import db
from werkzeug.security import generate_password_hash

api_v1 = Blueprint('api_v1', __name__, url_prefix='/api/v1')

@api_v1.route('/stores', methods=['GET'])
def get_stores():
    stores = Store.query.all()
    return jsonify([{'id': store.id, 'name': store.name} for store in stores])

@api_v1.route('/users', methods=['POST'])
def create_user():
    data = request.json
    if not data.get('email') or not data.get('password') or not data.get('role'):
        return jsonify({'error': 'Missing required fields'}), 400

    hashed_password = generate_password_hash(data['password'])
    user = User(email=data['email'], password_hash=hashed_password, role=data['role'])
    db.session.add(user)
    db.session.commit()
    return jsonify({'success': True, 'user_id': user.id})
