import uuid
from app.core.database import db
from app.core.models import Store, CreditTransaction


def allocate_credits_to_store(store_id, amount):
    """
    Allocate credits to a store.
    :param store_id: ID of the store
    :param amount: Number of credits to allocate
    :return: True if successful, False otherwise
    """
    try:
        store = Store.query.get(store_id)
        if not store:
            return False

        store.credit_balance += amount

        # Log the credit transaction
        transaction = CreditTransaction(
            from_user_id=None,  # Admin transaction
            to_user_id=None,  # Not tied to a user
            amount=amount,
            transaction_type='admin_allocation'
        )
        db.session.add(transaction)

        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error allocating credits to store: {str(e)}")
        return False


def update_subscription_plan(store_id, plan):
    """
    Update a store's subscription plan.
    :param store_id: ID of the store
    :param plan: New subscription plan
    :return: True if successful, False otherwise
    """
    try:
        store = Store.query.get(store_id)
        if not store:
            return False

        store.subscription_plan = plan
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error updating subscription plan: {str(e)}")
        return False


def generate_api_key(store_id):
    """
    Generate a new API key for a store.
    :param store_id: ID of the store
    :return: (True, api_key) if successful, (False, None) otherwise
    """
    try:
        store = Store.query.get(store_id)
        if not store:
            return False, None

        new_api_key = str(uuid.uuid4())
        store.api_key = new_api_key
        db.session.commit()
        return True, new_api_key
    except Exception as e:
        db.session.rollback()
        print(f"Error generating API key: {str(e)}")
        return False, None


def revoke_api_key(api_key):
    """
    Revoke an API key for a store.
    :param api_key: API key to revoke
    :return: True if successful, False otherwise
    """
    try:
        store = Store.query.filter_by(api_key=api_key).first()
        if not store:
            return False

        store.api_key = None
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        print(f"Error revoking API key: {str(e)}")
        return False
