"""
Worker wrapper: Executes workflows and activities.
Run this in one terminal while the starter.py runs in another.
"""
import asyncio
from src.worker import main

if __name__ == "__main__":
    asyncio.run(main())
