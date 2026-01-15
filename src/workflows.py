"""
Workflow definitions: orchestration logic that's durable and fault-tolerant.
Workflows are replayed from history, not re-executed from the start.
"""
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy
from .activities import charge_customer


@workflow.defn
class ChargeWorkflow:
    """
    A workflow that waits N seconds, then charges a customer.
    
    WHY THIS IS POWERFUL:
    - The sleep is DURABLE: if the worker crashes, it resumes at the right time
    - The charge is IDEMPOTENT: retrying never double-charges
    - The whole flow is OBSERVABLE: every step is logged to Temporal server
    - No background job queue needed: Temporal handles all orchestration
    """
    
    @workflow.run
    async def run(self, customer_id: str, amount: float, wait_seconds: int = 10) -> str:
        """
        Main workflow logic.
        
        Args:
            customer_id: Customer to charge
            amount: Amount to charge
            wait_seconds: How long to wait before charging (default 10 seconds)
        
        Returns:
            Result message
        """
        workflow.logger.info(f"Workflow started for {customer_id}")
        
        # DURABLE SLEEP: This doesn't block the worker thread
        # If worker crashes, Temporal remembers this sleep and resumes at exactly the right time
        # This is why Temporal is better than background jobs with time.sleep()
        workflow.logger.info(f"Sleeping for {wait_seconds} seconds...")
        await workflow.sleep(timedelta(seconds=wait_seconds))
        
        workflow.logger.info(f"Sleep completed, now charging {customer_id}...")
        
        # Define retry policy: retry up to 3 times with 5 second backoff
        # WHY: If activity fails (network error, timeout), Temporal auto-retries
        # Meanwhile, the idempotency key ensures we never actually charge twice
        retry_policy = RetryPolicy(
            maximum_attempts=3,  # Retry 3 times max
            initial_interval=timedelta(seconds=5),  # Wait 5 seconds before first retry
            backoff_coefficient=2.0,  # Exponential backoff
        )
        
        # Execute the activity with retry policy
        # Idempotency key = customer_id + amount, ensuring uniqueness per charge request
        result = await workflow.execute_activity(
            charge_customer,
            customer_id,
            amount,
            f"{customer_id}:{amount}:{id(self)}",  # Unique idempotency key
            start_to_close_timeout=timedelta(minutes=5),  # Activity timeout
            retry_policy=retry_policy,
        )
        
        workflow.logger.info(f"Workflow completed: {result}")
        return f"Charged {customer_id} ${amount} successfully"
