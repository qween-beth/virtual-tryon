from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from . import admin_bp
from .services import allocate_credits_to_store, update_subscription_plan, generate_api_key, revoke_api_key
from app.core.models import Store, db, Store, Feature, User
from app.core.database import db


@admin_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """
    Render the admin dashboard with system statistics.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    # Gather statistics for the admin dashboard
    stats = {
        'total_users': User.query.count(),
        'active_stores': Store.query.filter_by(is_active=True).count(),
        'total_tryons': 1000,  # Replace with actual TryOn count if available
    }

    # Fetch all stores for the dropdown
    stores = Store.query.all()

    return render_template('admin/dashboard.html', stats=stats, stores=stores)



@admin_bp.route('/stores', methods=['GET', 'POST'])
@login_required
def stores():
    """
    View and manage all stores.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    if request.method == 'POST':
        store_id = request.form.get('store_id')
        is_active = request.form.get('is_active') == 'True'  # Compare to 'True' string to match boolean

        store = Store.query.get(store_id)
        if not store:
            flash("Store not found", "error")
        else:
            store.is_active = is_active
            db.session.commit()
            flash(f"Store {'activated' if is_active else 'deactivated'} successfully", "success")
        return redirect(url_for('admin.stores'))

    # GET: Show all stores
    stores = Store.query.all()
    return render_template('admin/stores.html', stores=stores)


@admin_bp.route('/users/change-role', methods=['POST'])
@login_required
def change_role():
    """
    Change the role of a user.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    user_id = request.form.get('user_id')
    new_role = request.form.get('role')

    user = User.query.get(user_id)
    if not user:
        flash("User not found", "error")
    else:
        user.role = new_role
        db.session.commit()
        flash("User role updated successfully", "success")

    return redirect(url_for('admin.users'))



@admin_bp.route('/features', methods=['GET', 'POST'])
@login_required
def features():
    """
    View and manage features available for stores.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    if request.method == 'POST':
        feature_id = request.form.get('feature_id')
        is_active = request.form.get('is_active') == 'true'

        # Update feature status
        feature = Feature.query.get(feature_id)
        if not feature:
            flash("Feature not found", "error")
        else:
            feature.is_active = is_active
            db.session.commit()
            flash(f"Feature {'activated' if is_active else 'deactivated'} successfully", "success")

        return redirect(url_for('admin.features'))

    # GET request: Fetch all features from the database
    features = Feature.query.all()
    return render_template('admin/features.html', features=features)



@admin_bp.route('/users', methods=['GET'])
@login_required
def users():
    """
    View and manage all users.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    # Fetch all users
    users = User.query.all()
    return render_template('admin/users.html', users=users)


@admin_bp.route('/credits', methods=['POST'])
@login_required
def allocate_credits():
    """
    Allocate credits to a specific store.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    store_id = request.form.get('store_id')
    amount = request.form.get('amount')

    if not store_id or not amount:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        amount = int(amount)
        success = allocate_credits_to_store(store_id, amount)
        if success:
            flash("Credits allocated successfully", "success")
        else:
            flash("Failed to allocate credits", "error")
    except ValueError:
        flash("Invalid credit amount", "error")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/api-keys', methods=['GET', 'POST'])
@login_required
def api_keys():
    """
    Manage API keys for stores.
    Allows generating new API keys and revoking existing ones.
    """
    if current_user.role != 'admin':
        return jsonify({'error': 'Unauthorized access'}), 403

    if request.method == 'POST':
        action = request.form.get('action')
        store_id = request.form.get('store_id')

        if action == 'generate':
            if not store_id:
                flash("Store ID is required to generate an API key", "error")
                return redirect(url_for('admin.api_keys'))

            success, api_key = generate_api_key(store_id)
            if success:
                flash(f"API Key generated: {api_key}", "success")
            else:
                flash("Failed to generate API key", "error")

        elif action == 'revoke':
            api_key = request.form.get('api_key')
            if not api_key:
                flash("API Key is required to revoke", "error")
                return redirect(url_for('admin.api_keys'))

            success = revoke_api_key(api_key)
            if success:
                flash("API Key revoked successfully", "success")
            else:
                flash("Failed to revoke API key", "error")

        return redirect(url_for('admin.api_keys'))

    # GET request: Show all API keys for all stores
    stores = Store.query.all()
    api_keys = [
        {'key': store.api_key, 'last_used': store.last_used_at, 'store_name': store.name}
        for store in stores if store.api_key
    ]
    return render_template('admin/api_keys.html', api_keys=api_keys)
