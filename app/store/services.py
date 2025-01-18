from app.core.models import Store, User, CreditTransaction
from app.core.database import db


def allocate_credits_to_customer(store_id, customer_id, amount):
    """
    Allocate credits from a store to a customer.
    :param store_id: ID of the store
    :param customer_id: ID of the customer
    :param amount: Number of credits to allocate
    :return: True if successful, False otherwise
    """
    try:
        store = Store.query.get(store_id)
        customer = User.query.get(customer_id)

        if not store or not customer or store.id != customer.store_id:
            return False  # Store or customer doesn't exist, or they aren't linked.

        if store.credit_balance < amount:
            return False  # Insufficient credits.

        # Deduct credits from the store.
        store.credit_balance -= amount

        # Log the transaction.
        transaction = CreditTransaction(
            from_user_id=None,  # Not linked to a user (store-level transaction).
            to_user_id=customer_id,
            amount=amount,
            transaction_type='store_allocation'
        )
        db.session.add(transaction)
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error allocating credits to customer: {str(e)}")
        return False


def get_customers_by_store(store_id):
    """
    Retrieve all customers associated with a given store.
    :param store_id: ID of the store
    :return: List of customers
    """
    return User.query.filter_by(store_id=store_id, role='customer').all()


def get_api_usage_stats(store_id):
    """
    Mocked function to return API usage statistics for a store.
    :param store_id: ID of the store
    :return: List of API usage stats
    """
    # Replace this with actual API usage stats from your logging system.
    return [
        {'endpoint': '/api/v1/tryon', 'requests': 120, 'last_used': '2025-01-03'},
        {'endpoint': '/api/v1/customers', 'requests': 75, 'last_used': '2025-01-02'},
    ]
