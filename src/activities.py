"""
Activity definitions: actual business logic that executes on workers.
Activities are where side effects happen (API calls, DB writes, etc).
"""
import time
from temporalio import activity
from .charge_store import ChargeStore


@activity.defn
async def charge_customer(customer_id: str, amount: float, idempotency_key: str) -> dict:
    """
    Charge a customer money (simulating a payment processor call).
    
    WHY THIS MATTERS:
    - This is side-effectful (modifies DB, charges money)
    - It has a built-in delay simulating network latency
    - The idempotency_key ensures we never charge twice, even if activity retries
    
    Args:
        customer_id: Who to charge
        amount: How much to charge
        idempotency_key: Unique key for this charge (prevents double-charging on retry)
    
    Returns:
        dict with charge result
    """
    store = ChargeStore()
    
    activity.logger.info(f"Starting charge for {customer_id}: ${amount}")
    
    # Simulate slow external API call (payment processor)
    # If worker is killed here, Temporal will retry when it comes back
    time.sleep(5)
    
    # Record the charge atomically with idempotency
    # Even if this is the 10th retry attempt, we only charge ONCE
    is_new = store.record_charge(idempotency_key, customer_id, amount)
    
    if is_new:
        activity.logger.info(f"✓ Charge succeeded: {customer_id} charged ${amount}")
    else:
        activity.logger.info(f"⚠ Charge already processed (idempotency): {idempotency_key}")
    
    return {
        "customer_id": customer_id,
        "amount": amount,
        "idempotency_key": idempotency_key,
        "is_new": is_new,
        "status": "completed"
    }
