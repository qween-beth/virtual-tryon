from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import login_user, logout_user, current_user  # Added logout_user import
from werkzeug.security import check_password_hash, generate_password_hash
from app.core.models import User, Store
from app.core.database import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for(f'{user.role}.dashboard'))  # Redirect based on role
        
        flash('Invalid email or password')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    flash('You have been logged out successfully')
    return redirect(url_for('auth.login'))

# @auth_bp.route('/register', methods=['GET', 'POST'])
# def register():
#     if current_user.is_authenticated:
#         return redirect(url_for(f'{current_user.role}.dashboard'))  # Redirect to the appropriate dashboard if already logged in
    
#     if request.method == 'POST':
#         email = request.form.get('email')
#         password = request.form.get('password')
#         confirm_password = request.form.get('confirm_password')
#         role = request.form.get('role')  # Role is selected on the registration form
        
#         # Validation checks
#         if role not in ['customer', 'store']:
#             flash('Invalid role selected')
#             return redirect(url_for('auth.register'))
        
#         if not all([email, password, confirm_password, role]):
#             flash('All fields are required')
#             return redirect(url_for('auth.register'))
        
#         if password != confirm_password:
#             flash('Passwords do not match')
#             return redirect(url_for('auth.register'))
        
#         if User.query.filter_by(email=email).first():
#             flash('Email already registered')
#             return redirect(url_for('auth.register'))
        
#         # Create new user
#         new_user = User(
#             email=email,
#             password_hash=generate_password_hash(password),
#             role=role
#         )
        
#         # Additional logic for 'store' role
#         if role == 'store':
#             store_name = request.form.get('store_name')
#             if not store_name:
#                 flash('Store name is required for store registration')
#                 return redirect(url_for('auth.register'))
#             store = Store(name=store_name)
#             db.session.add(store)
#             db.session.flush()  # Ensure the store is added to the database and the ID is generated
#             new_user.store_id = store.id  # Associate store ID with the user
        
#         try:
#             db.session.add(new_user)
#             db.session.commit()
#             login_user(new_user)  # Log the user in after successful registration
#             return redirect(url_for(f'{role}.dashboard'))  # Redirect to the correct dashboard based on role
#         except Exception as e:
#             db.session.rollback()  # Rollback in case of error
#             flash(f'Registration failed: {str(e)}')  # Provide a user-friendly error message
#             return redirect(url_for('auth.register'))
    
#     return render_template('auth/register.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    # If the user is already logged in, redirect to their dashboard
    if current_user.is_authenticated:
        flash('You are already logged in.')
        return redirect(url_for(f'{current_user.role}.dashboard'))

    if request.method == 'POST':
        # Retrieve form data
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role')  # Role selected during registration

        # Validation checks
        errors = []
        if not email:
            errors.append('Email is required.')
        if not password:
            errors.append('Password is required.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        if role not in ['customer', 'store']:
            errors.append('Invalid role selected.')
        if User.query.filter_by(email=email).first():
            errors.append('Email is already registered.')

        # If there are validation errors, show them to the user
        if errors:
            for error in errors:
                flash(error)
            return redirect(url_for('auth.register'))

        # Create new user
        new_user = User(
            email=email,
            password_hash=generate_password_hash(password),
            role=role
        )

        # Additional logic for store role
        if role == 'store':
            store_name = request.form.get('store_name')
            if not store_name:
                flash('Store name is required for store registration.')
                return redirect(url_for('auth.register'))
            try:
                store = Store(name=store_name)
                db.session.add(store)
                db.session.flush()  # Ensure the store ID is generated
                new_user.store_id = store.id
            except Exception as e:
                db.session.rollback()
                flash(f'Store creation failed: {str(e)}')
                return redirect(url_for('auth.register'))

        # For customers, optionally associate a default store or leave store_id as None
        if role == 'customer':
            # Example: Associate a default store (optional)
            default_store = Store.query.filter_by(name='Default Store').first()
            if default_store:
                new_user.store_id = default_store.id

        # Save the new user and handle any errors
        try:
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)  # Log the user in after registration
            flash('Registration successful!')
            return redirect(url_for(f'{role}.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f'Registration failed: {str(e)}')
            return redirect(url_for('auth.register'))

    return render_template('auth/register.html')


