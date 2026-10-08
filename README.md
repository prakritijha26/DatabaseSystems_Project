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
├── WhatIf_Database_Review_1.pdf        # Review 1 presentation slides (PDF)
├── WhatIf_Database_Review_1.pptx       # Review 1 presentation slides (Source PPTX)
├── What-If_Database_Project_Plan.docx  # Original project plan & specifications
├── schema.sql                          # Database schema: tables, views, triggers, constraints
├── seed.sql                            # Seed data: ~30 students, 4-5 courses, attendance, marks
├── engine.py                           # Parser, transaction sandbox, baseline & diff runner
├── dependencies.py                     # PostgreSQL catalog dependency inspector (pg_depend, etc.)
├── cli.py                              # Interactive CLI for running WHAT_IF queries
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

## 📈 Progress Tracker

- [x] Review 1 Slides & Project Plan finalized
- [x] Initial repository setup & README documentation
- [ ] PostgreSQL environment setup & connectivity
- [ ] Database Schema (`schema.sql` with tables, cascades, views, triggers)
- [ ] Seed Data (`seed.sql` with ~30 students, courses, attendance, marks)
- [ ] Core Engine (`engine.py` with SQL parser, whitelist validator & rollback sandbox)
- [ ] Metric Computation & Diff Logic (Attendance %, CGPA, Eligibility)
- [ ] DDL Dependency Tracing (`dependencies.py` via `pg_depend` catalogs)
- [ ] Interactive CLI (`cli.py`)
- [ ] Test Suite & Demo Scenarios execution
