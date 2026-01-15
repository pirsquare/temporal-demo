"""
Worker: Executes workflows and activities.
Run this in one terminal while the starter.py runs in another.
"""
import asyncio
import logging
from temporalio.client import Client
from temporalio.worker import Worker
from .workflows import ChargeWorkflow
from .activities import charge_customer

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def main():
    # Connect to Temporal server
    # The server must be running in Docker (docker-compose up)
    client = await Client.connect("localhost:7233")
    
    # Create a worker that handles workflows and activities
    # Task queue = where work items are fetched from
    worker = Worker(
        client,
        task_queue="charge-queue",  # Must match the queue used by starter.py
        workflows=[ChargeWorkflow],
        activities=[charge_customer],
    )
    
    print("✓ Worker started, listening on queue: charge-queue")
    print("✓ Temporal Server: http://localhost:7233")
    print("✓ Temporal UI: http://localhost:8080")
    print("\nPress Ctrl+C to stop the worker")
    print("=" * 60)
    
    # Run the worker forever
    # This will be interrupted if you kill the process (test scenario 1 & 2)
    try:
        await worker.run()
    except KeyboardInterrupt:
        print("\n✓ Worker stopped")
