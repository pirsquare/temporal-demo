"""
Starter wrapper: Initiates workflow executions.
Run this script to start a workflow, then watch the worker process it.
"""
import asyncio
from src.starter import main

if __name__ == "__main__":
    asyncio.run(main())
