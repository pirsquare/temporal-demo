"""
Idempotency store using SQLite.
This ensures that even if an activity retries or is re-executed,
we never charge the same customer twice (critical for financial operations).
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = "charge_store.db"


class ChargeStore:
    """Track charges by idempotency key to prevent duplicates."""
    
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_db()
    
    def _init_db(self):
        """Create the charges table if it doesn't exist."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS charges (
                idempotency_key TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        self.conn.commit()
    
    def record_charge(self, idempotency_key: str, customer_id: str, amount: float) -> bool:
        """
        Record a charge atomically.
        Returns True if this is the first time (new charge), False if already exists.
        """
        try:
            self.conn.execute("""
                INSERT INTO charges (idempotency_key, customer_id, amount, status, created_at)
                VALUES (?, ?, ?, 'completed', ?)
            """, (idempotency_key, customer_id, amount, datetime.utcnow().isoformat()))
            self.conn.commit()
            print(f"✓ Charge recorded: {customer_id} charged ${amount}")
            return True
        except sqlite3.IntegrityError:
            # Idempotency key already exists - this is a retry/restart
            row = self.conn.execute(
                "SELECT * FROM charges WHERE idempotency_key = ?",
                (idempotency_key,)
            ).fetchone()
            print(f"⚠ Idempotency detected: Charge {idempotency_key} already processed")
            return False
    
    def get_charge(self, idempotency_key: str):
        """Retrieve a charge by idempotency key."""
        return self.conn.execute(
            "SELECT * FROM charges WHERE idempotency_key = ?",
            (idempotency_key,)
        ).fetchone()
    
    def list_charges(self):
        """List all charges (useful for debugging)."""
        return self.conn.execute("SELECT * FROM charges ORDER BY created_at DESC").fetchall()
    
    def reset(self):
        """Clear all charges (for testing)."""
        self.conn.execute("DELETE FROM charges")
        self.conn.commit()


def init_store():
    """Initialize the store."""
    store = ChargeStore()
    return store
