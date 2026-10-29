# What-If Database

Preview SQL changes to a university database and inspect attendance, GPA, row counts and catalog dependencies. Hypothetical changes roll back; explicit `APPLY` commands commit. BACSE202 Database Management Systems, VIT, Fall 2026.

## Requirements

- Git and Python 3.11 or 3.12 (recommended).
- PostgreSQL 15, through Docker Compose or a native installation.
- Optional [Bun](https://bun.sh/docs/installation) for TypeScript CLI/builds/tests. The browser bundle is included, so Python alone runs the web app and Python CLI.

Use a dedicated local sample database. The password below is a public development default. The app has no authentication: keep the web server on loopback, not exposed publicly.

## Windows — PowerShell

Install [Python](https://www.python.org/downloads/windows/), [Git](https://git-scm.com/downloads/win) and [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/). Start Docker Desktop with Linux containers enabled. Open PowerShell:

```powershell
git clone https://github.com/prakritijha26/DatabaseSystems_Project.git
cd DatabaseSystems_Project
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose up -d --wait
$env:WHATIF_REQUIRE_LIVE = "1"
.\.venv\Scripts\python.exe app.py
```

Open **http://127.0.0.1:8000**. Keep the terminal running; Ctrl+C stops it. Direct use of the virtual-environment executable avoids PowerShell activation-policy changes.

In a second terminal, from the project folder:

```powershell
$env:WHATIF_REQUIRE_LIVE = "1"
.\.venv\Scripts\python.exe cli.py "SELECT COUNT(*) FROM students;"
.\.venv\Scripts\python.exe demo.py
```

## Linux — Bash

On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install git python3 python3-venv python3-pip
```

Install [Docker Engine](https://docs.docker.com/engine/install/) and the [Compose plugin](https://docs.docker.com/compose/install/linux/), then start Docker. Other distributions should use their corresponding Python packages.

```bash
git clone https://github.com/prakritijha26/DatabaseSystems_Project.git
cd DatabaseSystems_Project
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
docker compose up -d --wait
export WHATIF_REQUIRE_LIVE=1
.venv/bin/python app.py
```

Open **http://127.0.0.1:8000**; Ctrl+C stops the app. If Docker requires administrative access, use `sudo docker compose ...` for Docker only, not Python or pip.

In a second terminal, from the project folder:

```bash
export WHATIF_REQUIRE_LIVE=1
.venv/bin/python cli.py "SELECT COUNT(*) FROM students;"
.venv/bin/python demo.py
```

## PostgreSQL through Docker

Compose starts `postgres:15-alpine` as `whatif_postgres`, creates `whatif_practice`, then imports `schema.sql` and `seed.sql`. A named volume retains data.

```bash
docker compose ps
docker compose exec postgres psql -U postgres -d whatif_practice -c "SELECT COUNT(*) FROM students;"
docker compose stop
docker compose up -d --wait
```

Expect **30 students**, five courses, and 150 rows each in enrollments, attendance and marks. `docker compose down` removes the container/network but retains the named volume.

Initialization scripts run only on an empty data directory; restarts do not reseed or reset existing passwords. See the [official image documentation](https://hub.docker.com/_/postgres). **Adding `-v` to `down` deletes the database volume.**

Do not run native and Docker PostgreSQL on the same port. If 5432 is occupied, change Compose's port mapping to `"5433:5432"` and set `PGPORT=5433` in the application terminal.

## Native PostgreSQL instead of Docker

Complete the Python setup above, skipping Docker commands. Initialize a new dedicated database: `schema.sql` recreates project objects and is not a migration for valuable existing data.

### Windows

Install PostgreSQL 15 and command-line tools using the [Windows installer](https://www.postgresql.org/download/windows/). Remember the postgres password and ensure the Windows service is running. From the project folder:

```powershell
$env:Path = "C:\Program Files\PostgreSQL\15\bin;" + $env:Path
$env:PGHOST = "127.0.0.1"
$env:PGPORT = "5432"
$env:PGUSER = "postgres"
$env:PGPASSWORD = Read-Host "PostgreSQL password"
psql -d postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE whatif_practice;"
psql -d whatif_practice -v ON_ERROR_STOP=1 -f schema.sql
psql -d whatif_practice -v ON_ERROR_STOP=1 -f seed.sql
$env:PGDATABASE = "whatif_practice"
$env:WHATIF_REQUIRE_LIVE = "1"
.\.venv\Scripts\python.exe app.py
```

Adjust the PostgreSQL installation path as necessary. Read-Host here takes a plain string for the process environment. If the database already exists, inspect it before importing.

### Linux (Ubuntu/Debian)

Use the [PostgreSQL packages for your distribution](https://www.postgresql.org/download/linux/). The distribution default may be newer than 15; Docker supplies the reproducible project version.

```bash
sudo apt install postgresql postgresql-client
sudo systemctl start postgresql
sudo -u postgres psql -c "CREATE DATABASE whatif_practice;"
sudo -u postgres psql -c '\password postgres'
```

The last command prompts for a new password. From the project folder, use that same password:

```bash
export PGHOST=127.0.0.1 PGPORT=5432 PGUSER=postgres PGDATABASE=whatif_practice
read -rsp 'PostgreSQL password: ' PGPASSWORD; echo
export PGPASSWORD
psql -v ON_ERROR_STOP=1 -f schema.sql
psql -v ON_ERROR_STOP=1 -f seed.sql
export WHATIF_REQUIRE_LIVE=1
.venv/bin/python app.py
```

Without systemd, use your distribution's service manager. These connections use TCP authentication without changing local peer-authentication rules.

## Configuration

Set variables in the terminal that launches the app. **The application does not automatically load .env files.**

| Variable | Default | Purpose |
| --- | --- | --- |
| PGHOST | localhost | Database host |
| PGPORT | 5432 | Database port |
| PGDATABASE | whatif_practice | Dedicated database |
| PGUSER | postgres | Database user |
| PGPASSWORD | 25BDS0066 | Public demo password; override for native installs |
| WHATIF_REQUIRE_LIVE | unset | Set to 1 to reject unavailable PostgreSQL instead of using fixtures |
| WHATIF_PYTHON | python3 | Bun CLI subprocess interpreter |
| WHATIF_API_URL | http://127.0.0.1:8000/api/whatif | Bun CLI HTTP endpoint |

Pass `--port 8001` to app.py to change the web port; update WHATIF_API_URL for Bun clients. Missing engine dependencies or unavailable PostgreSQL otherwise select labeled offline fixtures. Mock results do not prove live execution or persist APPLY changes.

## Usage

Run cli.py without arguments for an interactive prompt, or pass one quoted statement. Add `--json` for the report. The browser uses the same adapter through POST /api/whatif with JSON `{"sql":"..."}`.

```sql
WHAT_IF DELETE FROM attendance WHERE enrollment_id = 1;
WHAT_IF UPDATE marks SET score = 45 WHERE enrollment_id = 1;
WHAT_IF DELETE FROM enrollments WHERE enrollment_id = 1;
WHAT_IF ALTER TABLE marks DROP COLUMN score;
SELECT student_id, weighted_average_score, weighted_gpa FROM student_performance WHERE student_id = 1001;
```

The six demonstrations are defined in scenarios.json. demo.py also demonstrates rejection of `WHAT_IF COMMIT;`.

Supported mutations: INSERT, UPDATE, DELETE, DROP COLUMN and DROP TABLE on approved university tables. SELECT is restricted to approved relations/functions. Multiple statements, transaction control and unsupported SQL are rejected.

### Saving changes deliberately

```sql
WHAT_IF UPDATE marks SET score = 50 WHERE enrollment_id = 1;
APPLY UPDATE marks SET score = 50 WHERE enrollment_id = 1;
SELECT score FROM marks WHERE enrollment_id = 1;
```

WHAT_IF rolls back; successful live APPLY commits. These are separate transactions: the preview does not reserve its snapshot for a later commit. DDL previews may explore CASCADE after RESTRICT fails; APPLY never automatically commits that expanded cascade.

`RESEED;` (alias `RESET;`) transactionally replaces sample tables/views/audit function and restores seed data. It discards applied changes and can remove dependent objects through CASCADE. Use only in the dedicated sample database. After a lost APPLY response, inspect data before retrying: the commit may already have succeeded.

## Architecture and limitations

Browser/CLI → app.py report adapter → engine.py validation and transaction → PostgreSQL.

The engine captures before/after metrics inside REPEATABLE READ, uses savepoints for recoverable probes and rolls back hypothetical changes. dependencies.py inspects catalogs for views, triggers and constraints. verification.py fingerprints logical data/catalog state for tests.

Students and courses connect through enrollments; attendance and marks reference enrollments with cascading foreign keys. attendance_eligibility applies the 75% threshold, student_performance calculates weighted score and demonstration GPA, and trg_log_mark_change logs score updates.

GPA bands are a demonstration policy, not official VIT grading rules. Rollback protects transactional logical state in the trusted sample schema; it does not imply zero physical disk/WAL writes or safety for arbitrary external triggers.

## Development and tests

Linux:

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python demo.py
```

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe demo.py
```

Use a disposable seeded test database. Live scenario tests can **skip** if the database is unavailable or unsuitable; passing with skips is not live verification. They generate ignored Review-2/evidence.json. Inspect report backend/status as well as exit codes when demonstrating strict live mode.

Optional Bun commands:

```bash
bun run build  # rebuild web/app.js after TypeScript changes
bun run dev    # watch and rebuild
bun test
bun run cli
bun run demo
```

Set the Bun interpreter on Linux with `export WHATIF_PYTHON="$PWD/.venv/bin/python"`. On Windows PowerShell use `$env:WHATIF_PYTHON = (Resolve-Path .\.venv\Scripts\python.exe).Path`. Keep database variables consistent between server and CLI.

## Repository layout

| Files | Purpose |
| --- | --- |
| app.py, engine.py, dependencies.py, mock_engine.py | HTTP interface, live execution, catalog inspection, fixtures |
| cli.py, demo.py, scenarios.json | Python CLI and shared demonstrations |
| schema.sql, seed.sql, docker-compose.yml | Schema, sample data, PostgreSQL deployment |
| requirements.txt | Pinned Python dependencies |
| src/, web/, package.json, tsconfig.json | TypeScript source, prebuilt browser files, build configuration |
| tests/, verification.py | Regression tests and logical-state checks |
| start_demo.sh, start_postgres.sh, whatif.sh | Optional Bash helpers; cross-platform instructions use Python/Compose directly |
| docs/ | Implementation decisions and known limitations |

Coursework decks, reports, personal tool caches and old debug scripts are not required to run the app. Generated evidence and local environments are ignored. Keep web/app.js in version control so running the browser interface does not require Bun.

## Troubleshooting

- Connection refused: start PostgreSQL; check Compose status, PGHOST and PGPORT.
- Authentication failure: match PGPASSWORD to the existing database user. Changing Compose configuration does not change an initialized volume's password.
- Missing tables/wrong results: verify PGDATABASE and schema/seed initialization. Restarting does not reseed.
- Port 8000 busy: use --port 8001 without killing unrelated processes.
- Import errors: install requirements with the same virtual-environment Python used to launch the app.
- Bun cannot find Python: set WHATIF_PYTHON or use the Python CLI.
- Unexpected mock results: set WHATIF_REQUIRE_LIVE=1 and resolve the connection/dependency error.

## Contributors

Prakriti Prakash Jha (25BDS0066), Kahill Manuel Alvares (25BCE2873), Himali Agarwal (25BAI0012).
