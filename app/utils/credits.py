def can_allocate_credits(store, amount):
    return store and store.credit_balance >= amount

def deduct_credits(store, amount):
    if can_allocate_credits(store, amount):
        store.credit_balance -= amount
        return True
    return False
