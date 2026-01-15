"""
Starter: Initiates workflow executions.
Run this script to start a workflow, then watch the worker process it.
"""
import asyncio
import uuid
from temporalio.client import Client
from .workflows import ChargeWorkflow
from .charge_store import ChargeStore

# Optional: clear the charge store for fresh tests
# Uncomment to reset:
# ChargeStore().reset()


async def main():
    # Connect to Temporal server
    client = await Client.connect("localhost:7233")
    
    # Generate a unique workflow ID for tracking
    workflow_id = f"charge-workflow-{uuid.uuid4()}"
    
    # Get input parameters
    customer_id = input("Enter customer ID (default: customer-123): ").strip() or "customer-123"
    amount_input = input("Enter amount to charge (default: 99.99): ").strip() or "99.99"
    wait_input = input("Enter wait seconds (default: 10): ").strip() or "10"
    
    try:
        amount = float(amount_input)
        wait_seconds = int(wait_input)
    except ValueError:
        print("❌ Invalid input")
        return
    
    print(f"\n{'='*60}")
    print(f"Starting workflow...")
    print(f"  Workflow ID: {workflow_id}")
    print(f"  Customer: {customer_id}")
    print(f"  Amount: ${amount}")
    print(f"  Wait before charge: {wait_seconds} seconds")
    print(f"  Queue: charge-queue")
    print(f"\n⚠ TEST SCENARIO INSTRUCTIONS:")
    print(f"  1. SLEEP TEST: Kill worker DURING the {wait_seconds}sec sleep")
    print(f"     → Restart worker BEFORE charge happens")
    print(f"     → Charge should execute exactly ONCE (at correct time)")
    print(f"\n  2. ACTIVITY TEST: Kill worker DURING the 5sec charge activity")
    print(f"     → Restart worker immediately")
    print(f"     → Idempotency key prevents double-charge (check logs)")
    print(f"{'='*60}\n")
    
    # Start the workflow
    handle = await client.start_workflow_class(
        ChargeWorkflow,
        customer_id,
        amount,
        wait_seconds,
        id=workflow_id,
        task_queue="charge-queue",
    )
    
    print(f"✓ Workflow {workflow_id} submitted")
    print(f"✓ Check Temporal UI: http://localhost:8080")
    print(f"\nWaiting for workflow to complete...")
    
    # Wait for workflow to complete
    result = await handle.result()
    print(f"\n✓ Workflow completed!")
    print(f"✓ Result: {result}")
    
    # Show all charges in the database
    store = ChargeStore()
    charges = store.list_charges()
    
    print(f"\n{'='*60}")
    print(f"All charges in database:")
    print(f"{'='*60}")
    for charge in charges:
        print(f"  Customer: {charge['customer_id']}")
        print(f"  Amount: ${charge['amount']}")
        print(f"  Status: {charge['status']}")
        print(f"  Created: {charge['created_at']}")
        print()
