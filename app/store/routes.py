from flask import render_template, request, jsonify, redirect, url_for, flash, Blueprint
from flask_login import login_required, current_user
from . import store_bp
from .services import allocate_credits_to_customer, get_customers_by_store, get_api_usage_stats
from app.core.models import CreditTransaction


@store_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """
    Render the store dashboard with credit balance and recent transactions.
    """
    if not current_user.store_id:
        return jsonify({'error': 'User is not associated with a store'}), 403

    # Fetch recent transactions
    transactions = (
        CreditTransaction.query.filter_by(to_user_id=current_user.id)
        .order_by(CreditTransaction.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template('store/dashboard.html', recent_transactions=transactions)


@store_bp.route('/customers', methods=['GET'])
@login_required
def customers():
    """
    Render the customer management page.
    """
    if not current_user.store_id:
        return jsonify({'error': 'User is not associated with a store'}), 403

    # Fetch customers associated with the store
    customers = get_customers_by_store(current_user.store_id)

    return render_template('store/customers.html', customers=customers)


@store_bp.route('/credits/customer', methods=['POST'])
@login_required
def allocate_credits():
    """
    Allocate credits to a customer.
    """
    customer_id = request.form.get('customer_id')
    amount = request.form.get('amount')

    if not customer_id or not amount:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        amount = int(amount)
        success = allocate_credits_to_customer(current_user.store_id, customer_id, amount)
        if success:
            flash("Credits allocated successfully", "success")
            return redirect(url_for('store.customers'))
        else:
            flash("Failed to allocate credits. Please check the input.", "error")
    except ValueError:
        flash("Invalid credit amount", "error")
    return redirect(url_for('store.customers'))


@store_bp.route('/api-dashboard', methods=['GET'])
@login_required
def api_dashboard():
    """
    Render the API dashboard.
    """
    if not current_user.store_id:
        return jsonify({'error': 'User is not associated with a store'}), 403

    # Fetch API usage stats
    api_usage = get_api_usage_stats(current_user.store_id)

    return render_template('store/api_dashboard.html', api_usage=api_usage)
