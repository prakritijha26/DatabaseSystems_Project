# What-If Database: Impact Analysis for University Databases

**Course:** BACSE202 – Database Management Systems  
**Institution:** Vellore Institute of Technology (VIT)  
**Semester:** Fall Semester 2026  


---

## 📌 Project Overview

Testing what-if scenarios on production or operational databases typically requires cloning the database, manual before/after query scripting, or setting up complex branching systems. 

**What-If Database** is a lightweight middleware layer built on top of **PostgreSQL** that introduces a custom `WHAT_IF` SQL command:

```sql
WHAT_IF DELETE FROM attendance WHERE student_id = 1042;
```

It executes the hypothetical modification within a sandbox transaction that is **always rolled back**, evaluates derived metrics before and after the modification, and produces an exact **Impact Report** detailing:
- Affected tables and rows changed (including foreign key cascades and triggers).
- Attendance percentage shifts and exam eligibility status flips.
- Cumulative Grade Point Average (CGPA) deltas.
- For schema changes (e.g. `DROP COLUMN`): system catalog-derived lists of broken views, foreign keys, triggers, and failing metric queries.

> **Important Framing:** This system performs **exact simulation**, not predictive modelling, statistical estimation, or machine learning. The real database is guaranteed to remain untouched.

---

## 🏗️ Architecture & Pipeline

The execution follows a strict 6-step transactional pipeline:

```
[WHAT_IF SQL Input]
         │
         ▼
 1. Parse & Validate ──────► [sqlglot: AST check & statement whitelist]
         │
         ▼
 2. Baseline Metrics ──────► [Compute initial CGPA, Attendance %, Eligibility]
         │
         ▼
 3. Transaction Sandbox ───► [BEGIN ISOLATION LEVEL REPEATABLE READ]
         │                   [Execute statement (cascades & triggers fire)]
         ▼
 4. Re-run & Diff ─────────► [Savepoints per metric query; compute delta]
         │
         ▼
 5. Guaranteed Rollback ───► [ROLLBACK in finally block — zero persistent side-effects]
         │
         ▼
 6. Impact Report ─────────► [Format and return JSON / CLI summary]
```

### Key Technical Pillars
- **Snapshot Isolation (`REPEATABLE READ`):** Ensures a consistent snapshot view during simulation, preventing dirty reads and isolation anomalies.
- **Savepoints for Fault Tolerance:** Each post-change metric runs inside an isolated savepoint so that a failure in one metric query does not abort the entire simulation.
- **System Catalog Inspection:** Queries PostgreSQL internals (`pg_depend`, `pg_rewrite`, `pg_constraint`, `information_schema`) to identify schema dependencies that would break under hypothetical DDL.

---

## 🎯 Scope & Boundaries

### In Scope
- **Data Statements:** `INSERT`, `UPDATE`, `DELETE`.
- **Allowed Schema Changes (DDL):** `DROP COLUMN`, `ALTER COLUMN TYPE`, `DROP TABLE`, `DROP CONSTRAINT`, `RENAME`.
- **Cascades & Business Logic:** Foreign key `ON DELETE CASCADE` actions and trigger executions inside the transaction.
- **Exact Metric Comparison:** Before vs. After comparison of student attendance, CGPA, and exam eligibility (e.g., < 75% attendance threshold).
- **Single-User Operational Environment:** University academic database prototype.

### Out of Scope
- Machine learning, forecasting, or statistical approximations.
- Multi-user concurrent simulation and lock contention management.
- Arbitrary DDL outside the allowed whitelist.
- Deep application-code tracing outside the database engine.
- Production-grade access control and auth infrastructure.

---

## 🛡️ Safety & Validation Rules

- **Strict Command Whitelist:** Only permitted DML and listed DDL statements are processed.
- **Rejection of Control Commands:** Explicitly rejects `COMMIT`, `ROLLBACK`, transaction control, and multi-statement queries.
- **Rejection of Non-Transactional Statements:** Forbids commands that cannot run inside a standard transaction block (e.g., `CREATE INDEX CONCURRENTLY`, `VACUUM`).
- **Pristine State Guarantee:** Every run executes inside a `try ... finally: conn.rollback()` block. Automated verification tests ensure the live database state remains identical before and after invocation.

---

## 📂 Project Structure

```text
DatabaseSystems_Project/
├── README.md                           # Project documentation and progress tracking
├── app.py                              # Web interface server (FastAPI/Bottle HTTP server)
├── web/                                # Web UI frontend assets
│   ├── index.html                      # Single-page UI with terminal & dashboard
│   ├── style.css                       # Modern dark developer workbench stylesheet
│   └── app.js                          # Client-side terminal & interactive logic
├── cli.py                              # Interactive CLI for running WHAT_IF queries
├── demo.py                             # Automated evaluation runner for 6 review scenarios
├── mock_engine.py                      # Contract-compliant offline simulation mock
├── schema.sql                          # Database schema: tables, views, triggers, constraints
├── seed.sql                            # Seed data: ~30 students, 4-5 courses, attendance, marks
├── engine.py                           # Parser, transaction sandbox, baseline & diff runner
├── dependencies.py                     # PostgreSQL catalog dependency inspector (pg_depend, etc.)
├── tests/                              # Automated test suite
│   ├── test_parser.py                  # Parser and validation tests
│   ├── test_rollback.py                # State immutability & rollback guarantee tests
│   └── test_scenarios.py               # End-to-end verification of demo scenarios
└── docker-compose.yml                  # PostgreSQL container service definition (optional)
```

---

## 📊 Standard Impact Report Interface

The engine returns an agreed JSON `ImpactReport` contract:

```json
{
  "statement": "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;",
  "statement_type": "DML",
  "status": "SIMULATED",
  "tables_affected": [
    {"table": "attendance", "rows_changed": 14}
  ],
  "metrics": [
    {
      "metric": "attendance_percentage",
      "student_id": 1042,
      "before": 78.5,
      "after": 64.2,
      "change": -14.3
    },
    {
      "metric": "exam_eligibility",
      "student_id": 1042,
      "before": "ELIGIBLE",
      "after": "INELIGIBLE",
      "change": "FLIPPED_TO_NO"
    }
  ],
  "broken_dependencies": []
}
```

---

## 🧪 Demo Scenarios

The system is evaluated against 6 core scenarios:

1. **Attendance Drop & Eligibility Flip:** Delete attendance records for a student; attendance drops below 75% and exam eligibility flips from `ELIGIBLE` to `INELIGIBLE`.
2. **Mark Change & CGPA Impact:** Update internal/exam marks; credit-weighted CGPA recalculated and difference displayed.
3. **Course Deregistration Cascade:** Drop an enrollment record; cascading foreign keys automatically clean up marks and attendance.
4. **Hypothetical DDL Impact:** Run `WHAT_IF ALTER TABLE marks DROP COLUMN score;`; report lists broken `student_cgpa_view` and failed dependent metrics without executing destructive changes on disk.
5. **Safety Violation Rejection:** Attempt invalid inputs like `WHAT_IF COMMIT;` or SQL injection multi-statements, verifying prompt rejection.
6. **Data Immutability Verification:** Run regular `SELECT` queries across all affected tables immediately after simulations to verify the live database is 100% pristine.

---

## 🛠️ Tech Stack & Requirements

- **Database:** PostgreSQL 14+ (Required for transactional DDL and dependency catalogs `pg_depend`, `pg_rewrite`)
- **Language:** Python 3.10+
- **Database Driver:** `psycopg` (v3)
- **SQL Parser:** `sqlglot`
- **Testing:** `pytest`

---

## 🚀 Running the System (Part C: Interface & Demo)

### 1. Launch Interactive Web UI (With On-Screen Terminal & Live Impact Dashboard)
```bash
python3 app.py
```
Open [http://localhost:8000](http://localhost:8000) in your browser. Features:
- Embedded interactive shell for typing `WHAT_IF` statements.
- One-click preset buttons for all 6 review scenarios.
- Side-by-side visual diff cards for attendance thresholds, exam eligibility badges, CGPA deltas, and broken schema dependencies.

### 2. Launch Interactive Terminal CLI
```bash
# Start interactive shell:
python3 cli.py

# Or evaluate a one-shot query directly:
python3 cli.py "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;"
```

### 3. Run Automated Review Scenario Demo Suite
```bash
# Python runner:
python3 demo.py
# or with interactive pauses:
python3 demo.py --interactive
```
Executes all 6 official review scenarios with commentary and formats the resulting impact reports.

### 4. TypeScript & Bun Workflow
```bash
# Bundle frontend client:
bun run build

# Native TypeScript CLI:
bun run cli "WHAT_IF DELETE FROM attendance WHERE student_id = 1042;"

# Automated TypeScript Demo Suite:
bun run demo
# or interactive:
bun run demo --interactive
```

---

## 📈 Progress Tracker

- [x] Review 1 Slides & Project Plan finalized
- [x] Initial repository setup & README documentation
- [x] Contract-compliant mock engine (`mock_engine.py`) for offline testing & demo
- [x] Interactive CLI with formatted tables (`cli.py`)
- [x] Web Interface with on-screen terminal & visual impact dashboard (`app.py`, `web/`)
- [x] Automated review demo script for all 6 scenarios (`demo.py`)
- [x] TypeScript migration for frontend & CLI drivers (`src/app.ts`, `src/cli.ts`, `src/demo.ts`)
- [ ] PostgreSQL environment setup & connectivity
- [ ] Database Schema (`schema.sql` with tables, cascades, views, triggers)
- [ ] Seed Data (`seed.sql` with ~30 students, courses, attendance, marks)
- [ ] Core Engine (`engine.py` with SQL parser, whitelist validator & rollback sandbox)
- [ ] Metric Computation & Diff Logic (Attendance %, CGPA, Eligibility)
- [ ] DDL Dependency Tracing (`dependencies.py` via `pg_depend` catalogs)
- [ ] Unit Test Suite (`tests/`)

### Integrated web interface

Start `python3 app.py` and open `http://127.0.0.1:8000`. Rebuild the browser client with `bun run build` after changing `src/app.ts`.

HTTP and both CLIs use the `app.run_whatif` adapter. If `psycopg`/`sqlglot` are missing or the database connection cannot be opened, reports explicitly identify **offline fixture data**. SQL validation and execution failures do not trigger mock fallback.

For the live engine, install `psycopg[binary]` and `sqlglot` in your Python environment and set `PGPASSWORD`. An explicit `engine.run_whatif(sql, password=...)` argument overrides the environment; the course demo password is the final local fallback. The database connection settings remain in `engine.DB_CONFIG`.

Select **Delivered schema** in the interface for enrollment-based DML examples compatible with `schema.sql` and `seed.sql`. The original review examples target a different schema. The delivered engine supports UPDATE, INSERT, and DELETE only: DDL dependency tracing and verification SELECT return rejection reports in live mode. Its academic view exposes weighted score, not institutional CGPA; the UI preserves that distinction. Rollback confirmation means transaction changes were discarded, not that PostgreSQL performed zero physical writes or reversed sequence advances.

Verification:

```sh
python3 -m unittest discover -s tests -v
python3 handoff/tests/verify_contract.py
bun run demo
python3 demo.py
bun run build
```

Engine lifecycle tests require the live Python dependencies; otherwise those tests are reported as skipped. They exercise connection doubles and do not replace an integration test against an initialized PostgreSQL database.
