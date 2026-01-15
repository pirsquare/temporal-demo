# Temporal Python Demo

A complete, runnable demo showing why Temporal is superior to traditional background job systems.

## Quick Start

### 1. Start Temporal Infrastructure (Docker)

```bash
docker-compose up
```

Wait for both services to be healthy:
```
✓ temporal-server
✓ temporal-ui at http://localhost:8233
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Terminal 1: Start the Worker

```bash
python worker.py
```

Expected output:
```
✓ Worker started, listening on queue: charge-queue
✓ Temporal Server: http://localhost:7233
✓ Temporal UI: http://localhost:8233
```

### 4. Terminal 2: Start a Workflow

```bash
python starter.py
```

Follow the prompts:
- Customer ID: `customer-123` (default)
- Amount: `99.99` (default)
- Wait seconds: `10` (default)

---

## Why Temporal > Background Jobs

### Traditional Background Jobs (Redis Queue, Celery, etc.)

❌ **Problems:**
- Worker crashes → tasks re-execute → double-charge customer
- No built-in durable timers → time.sleep() blocks worker threads
- No automatic retry with exponential backoff
- No workflow state visibility → hard to debug
- Manual idempotency logic needed in every task

### Temporal Solution

✅ **Benefits:**
- **Durability**: Workflow state persisted on Temporal server, not worker
- **Fault Tolerance**: Kill worker anytime → resume from exact point
- **Idempotency**: Built-in support, prevents double execution
- **Durable Timers**: workflow.sleep() doesn't block threads
- **Automatic Retries**: Configurable retry policies with backoff
- **Full Observability**: Every workflow step logged, visible in UI
- **No Data Loss**: Temporal server maintains complete history

---

## Crash Test 1: Kill Worker During Sleep

### Scenario
A workflow is waiting 10 seconds before charging. You want to prove Temporal resumes correctly.

### Steps

1. **Start the demo normally**:
   ```bash
   # Terminal 1
   python worker.py
   
   # Terminal 2
   python starter.py
   # Input: customer-123, 99.99, 10
   ```

2. **Kill the worker** (5 seconds after starter submits):
   - In Terminal 1: `Ctrl+C`
   - The workflow is now waiting, no worker available

3. **Restart the worker**:
   ```bash
   python worker.py
   ```

### Expected Result

✅ **Charge happens exactly ONCE**
- Temporal resumed the workflow at the correct point
- Timer not "reset" — workflow waited for total 10 seconds
- No double-charge occurs
- Check UI: http://localhost:8233/namespaces/default/workflows

### Why This is Impossible with Background Jobs

With Celery/Redis, if you restart:
- The task either gets re-queued (double-charge risk)
- Or you lose the scheduled timer entirely
- Manual reconciliation needed

---

## Crash Test 2: Kill Worker During Activity Execution

### Scenario
A charge activity is being executed (simulating 5-second payment API call). Worker crashes mid-execution.

### Steps

1. **Start the demo**:
   ```bash
   # Terminal 1
   python worker.py
   
   # Terminal 2
   python starter.py
   # Input: customer-123, 99.99, 1 (short wait to reach activity fast)
   ```

2. **Kill the worker during the 5-second charge** (after seeing "Starting charge for..."):
   - In Terminal 1: `Ctrl+C`

3. **Check the database**:
   ```bash
   sqlite3 charge_store.db "SELECT * FROM charges;"
   ```
   You'll see the charge was already recorded (Temporal got into the sleep)

4. **Restart the worker**:
   ```bash
   python worker.py
   ```
   Watch the logs carefully for idempotency message

5. **Run starter.py again with SAME customer/amount**:
   ```bash
   python starter.py
   # Input: customer-123, 99.99, 1
   ```

### Expected Result

✅ **Idempotency key prevents double-charge**
- Log shows: `⚠ Idempotency detected: Charge ... already processed`
- Database has only ONE charge record, not two
- Activity ran twice (due to retry), but charge recorded once

### Why Idempotency Matters

Our idempotency key: `{customer_id}:{amount}:{workflow_id}`

Even if:
- Temporal retries the activity 3 times
- Worker crashes during activity
- Network fails and times out
- Activity logic runs multiple times

The database ensures: **Only one charge per idempotency key**

This is critical for financial systems.

---

## Project Structure

```
temporal-demo/
├── docker-compose.yml      # Run Temporal server + UI
├── requirements.txt        # Python dependencies
├── charge_store.py         # SQLite idempotency tracking
├── activities.py           # Side-effectful work (charging)
├── workflows.py            # Orchestration logic
├── worker.py              # Executes workflows/activities
├── starter.py             # Kicks off workflows
└── README.md              # This file
```

### File Purposes

- **docker-compose.yml**: Infrastructure as code. Runs Temporal server + UI.
- **requirements.txt**: Only `temporalio` — no external dependencies.
- **charge_store.py**: SQLite database with PRIMARY KEY on idempotency_key. Enforces exactly-once semantics.
- **activities.py**: `charge_customer()` simulates payment API (time.sleep = network latency).
- **workflows.py**: `ChargeWorkflow` handles sleep + activity execution with retry policy.
- **worker.py**: Connects to Temporal, registers workflows/activities, polls for work.
- **starter.py**: Client that submits workflows to Temporal server.

---

## Understanding the Code

### Workflow Sleep (Durable Timer)

```python
await workflow.sleep(timedelta(seconds=wait_seconds))
```

**Why this is special:**
- Doesn't block worker thread (can process other workflows)
- Persisted on server (crash-safe)
- Precise timing (no polling)

vs. Traditional background job:
```python
time.sleep(10)  # BLOCKS worker, not crash-safe, not observable
```

### Idempotent Activity

```python
def record_charge(self, idempotency_key: str, customer_id: str, amount: float) -> bool:
    try:
        INSERT INTO charges (idempotency_key, ...)  # PRIMARY KEY
        return True  # First execution
    except sqlite3.IntegrityError:
        return False  # Retry detected
```

**Why this works:**
- Database PRIMARY KEY on `idempotency_key` prevents duplicates
- Activity can run 3x due to retries, but charge recorded 1x
- Works across worker restarts

### Retry Policy

```python
retry_policy = RetryPolicy(
    maximum_attempts=3,
    initial_interval={"seconds": 5},
    backoff_coefficient=2.0,
)
```

**Delays between retries:**
- Attempt 1: fails
- Attempt 2: waits 5 seconds (5 * 2^0)
- Attempt 3: waits 10 seconds (5 * 2^1)
- Attempt 4: waits 20 seconds (5 * 2^2) - but max_attempts=3, so fails

This auto-retries without manual logic.

---

## Monitoring in Temporal UI

Open http://localhost:8233

**See:**
- Workflow executions (list + details)
- Activity calls (with status, duration, retries)
- Event history (every step)
- Worker connections

This visibility is free with Temporal. Try doing this with Celery+Redis — you can't.

---

## Cleanup

### Stop everything
```bash
docker-compose down
```

### Clear database (for fresh tests)
```bash
rm charge_store.db
```

### Remove Temporal volumes (full reset)
```bash
docker-compose down -v
```

---

## Real-World Applications

This pattern works for:
- **Payment processing** (idempotent charges)
- **Order fulfillment** (durable steps: pay → ship → notify)
- **Email campaigns** (retry-able, resumable batches)
- **Data migrations** (fault-tolerant, observable progress)
- **Scheduled jobs** (durable timers vs. cron)

---

## Further Reading

- [Temporal Docs](https://temporal.io/docs)
- [Python SDK](https://github.com/temporalio/sdk-python)
- [Workflow Best Practices](https://temporal.io/docs/workflows)
