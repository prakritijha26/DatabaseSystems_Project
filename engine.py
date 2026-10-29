"""Bounded hypothetical SQL on the trusted Review 2 PostgreSQL schema."""
import os
import re
from pathlib import Path

import psycopg
from psycopg import sql as pgsql
import sqlglot
from sqlglot import exp

from dependencies import find_broken_dependencies

DB_CONFIG = {"host": "localhost", "port": 5432, "dbname": "whatif_practice", "user": "postgres"}
TABLES = {"students", "courses", "enrollments", "attendance", "marks"}
READ_TABLES = TABLES | {"mark_change_log", "attendance_eligibility", "student_performance"}
SAFE_FUNCTIONS = {"COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND", "COALESCE", "NULLIF", "ABS"}


def connect_database(password=None):
    config = dict(DB_CONFIG)
    for key, env in (("host", "PGHOST"), ("port", "PGPORT"), ("dbname", "PGDATABASE"), ("user", "PGUSER")):
        if os.getenv(env):
            config[key] = os.environ[env]
    try:
        return psycopg.connect(**config, password=os.getenv("PGPASSWORD", "25BDS0066") if password is None else password, connect_timeout=3)
    except psycopg.OperationalError as exc:
        raise ConnectionError("PostgreSQL connection unavailable") from exc


def validate_statement(sql):
    """Return normalized SQL, AST and optional DDL target. No database access."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("Enter one SQL statement.")
    statement = sql.strip()
    hypothetical = bool(re.match(r"WHAT_IF\s+", statement, re.I))
    is_apply = bool(re.match(r"APPLY\s+", statement, re.I))
    if hypothetical or is_apply:
        statement = re.sub(r"^(?:WHAT_IF|APPLY)\s+", "", statement, count=1, flags=re.I)
    try:
        parsed = sqlglot.parse(statement, read="postgres")
    except sqlglot.errors.ParseError as exc:
        raise ValueError("Invalid PostgreSQL syntax.") from exc
    if len(parsed) != 1 or parsed[0] is None:
        raise ValueError("Exactly one SQL statement is required.")
    node = parsed[0]
    if not isinstance(node, (exp.Update, exp.Insert, exp.Delete, exp.Select, exp.Alter, exp.Drop)):
        raise ValueError("Only WHAT_IF/APPLY DML, DROP COLUMN / DROP TABLE and read-only SELECT are permitted.")
    if not isinstance(node, exp.Select) and not (hypothetical or is_apply):
        raise ValueError("Changes must begin with WHAT_IF (to simulate) or APPLY (to commit).")
    if is_apply and isinstance(node, exp.Select):
        raise ValueError("APPLY requires a mutation; use SELECT without APPLY to read data.")
    # Do not allow hidden writes, session effects, function side effects, or custom casts.
    for child in node.walk():
        column_drop = isinstance(node, exp.Alter) and isinstance(child, exp.Drop) and child.parent is node and child.args.get("kind") == "COLUMN"
        if child is not node and not column_drop and isinstance(child, (exp.Update, exp.Insert, exp.Delete, exp.Alter, exp.Drop)):
            raise ValueError("Nested modifying statements are not supported.")
        if isinstance(child, (exp.Into, exp.Lock, exp.Cast, exp.Command)):
            raise ValueError("SELECT INTO, locks, casts and commands are not supported.")
        if isinstance(child, exp.Func) and (isinstance(child, exp.Anonymous) or child.sql_name() not in SAFE_FUNCTIONS):
            raise ValueError("Only approved read-only aggregate/scalar functions are supported.")
    tables = list(node.find_all(exp.Table))
    if not tables or any(t.name not in READ_TABLES or t.catalog or t.db not in ("", "public") for t in tables):
        raise ValueError("Only public university tables and views are supported.")
    ddl = None
    if isinstance(node, exp.Alter):
        match = re.fullmatch(r"ALTER\s+TABLE\s+(?:public\.)?([a-z_][a-z_0-9]*)\s+DROP\s+COLUMN\s+([a-z_][a-z_0-9]*)\s*;?", statement, re.I)
        if not match or match[1].lower() not in TABLES:
            raise ValueError("Allowed DDL: WHAT_IF ALTER TABLE <table> DROP COLUMN <column>.")
        ddl = (match[1].lower(), match[2].lower())
    elif isinstance(node, exp.Drop):
        match = re.fullmatch(r"DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?(?:public\.)?([a-z_][a-z_0-9]*)\s*;?", statement, re.I)
        if not match or match[1].lower() not in TABLES:
            raise ValueError("Allowed DDL: WHAT_IF DROP TABLE <table>.")
        ddl = (match[1].lower(), None)
    elif not isinstance(node, exp.Select):
        target = node.this.this if isinstance(node.this, exp.Schema) else node.this
        if not isinstance(target, exp.Table) or target.name not in TABLES:
            raise ValueError("Only core university tables may be modified.")
    return node.sql(dialect="postgres"), node, ddl


def optional_rows(conn, query):
    """Read telemetry while permitting objects removed by supported DDL."""
    conn.execute("SAVEPOINT telemetry_read")
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            rows = cur.fetchall()
    except (psycopg.errors.UndefinedTable, psycopg.errors.UndefinedColumn):
        conn.execute("ROLLBACK TO SAVEPOINT telemetry_read")
        rows = []
    conn.execute("RELEASE SAVEPOINT telemetry_read")
    return rows


def get_metrics(conn):
    counts = {}
    for table in sorted(TABLES | {"mark_change_log"}):
        rows = optional_rows(conn, pgsql.SQL("SELECT count(*) FROM public.{}").format(pgsql.Identifier(table)))
        counts[table] = rows[0][0] if rows else 0
    return counts


def get_academic_metrics(conn):
    attendance = optional_rows(conn, "SELECT student_id, course_code, attendance_percentage, exam_eligible FROM public.attendance_eligibility")
    performance = optional_rows(conn, "SELECT student_id, weighted_average_score, weighted_gpa FROM public.student_performance")
    return {
        "attendance": [dict(zip(("student_id", "course_code", "attendance_percentage", "exam_eligible"), row)) for row in attendance],
        "performance": [dict(zip(("student_id", "weighted_average_score", "weighted_gpa"), row)) for row in performance],
    }


def reseed_database(password=None):
    """Atomically restore the dedicated demo's named objects, including damaged schema."""
    root = Path(__file__).resolve().parent
    schema = (root / "schema.sql").read_text()
    seed = (root / "seed.sql").read_text()
    conn = connect_database(password)
    try:
        conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
        conn.execute("SET LOCAL search_path = public, pg_catalog")
        conn.execute("SET LOCAL lock_timeout = 1000")
        conn.execute("SET LOCAL statement_timeout = 10000")
        conn.execute("DROP VIEW IF EXISTS public.student_performance, public.attendance_eligibility CASCADE")
        for table in sorted(TABLES | {"mark_change_log"}):
            conn.execute(pgsql.SQL("DROP TABLE IF EXISTS public.{} CASCADE").format(pgsql.Identifier(table)))
        conn.execute("DROP FUNCTION IF EXISTS public.log_mark_change() CASCADE")
        conn.execute(schema)
        conn.execute(seed)
        after = get_metrics(conn)
        conn.commit()
        return {"statement_type": "DML", "operation": "RESET", "status": "COMMITTED",
                "committed": True, "commit_scope": "postgresql", "rolled_back": False,
                "after": after, "message": "Database restored to initial seed state.",
                "logs": ["[RESET] Sample schema and seed data rebuilt in one transaction.",
                         "[COMMIT] Database restored to initial seed state."]}
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def run_whatif(sql: str, password: str | None = None):
    if isinstance(sql, str) and re.fullmatch(r"\s*(?:RESEED|RESET)\s*;?\s*", sql, re.I):
        return reseed_database(password)
    statement, node, ddl = validate_statement(sql)
    is_apply = bool(re.match(r"\s*APPLY\s+", sql, re.I))
    readonly = isinstance(node, exp.Select)
    report = {"statement": statement, "statement_type": "VERIFICATION_SELECT" if readonly else "DDL_SCHEMA_CHANGE" if ddl else "DML",
              "tables_affected": [], "before": {}, "after": {}, "rows_affected": 0,
              "broken_dependencies": [], "rolled_back": False, "committed": False, "logs": ["[PARSE] Single supported AST validated."]}
    conn = connect_database(password)
    try:
        conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ" + (" READ ONLY" if readonly else ""))
        conn.execute("SET LOCAL search_path = public, pg_catalog")
        conn.execute("SET LOCAL statement_timeout = 3000")
        conn.execute("SET LOCAL lock_timeout = 1000")
        report["logs"].append("[SNAPSHOT] REPEATABLE READ; bounded statement and lock timeouts.")
        if readonly:
            result = conn.execute(statement)
            rows = result.fetchmany(501)
            report["query_columns"] = [column.name for column in result.description]
            report["query_rows"] = [[float(v) if hasattr(v, "as_tuple") else str(v) if v is not None and not isinstance(v, (str, int, float, bool)) else v for v in row] for row in rows[:500]]
            report["query_truncated"] = len(rows) > 500
            report["logs"].append("[VERIFY] Read-only SELECT completed. Cross-run immutability is established by the fingerprint test suite.")
        elif ddl:
            report["before"] = get_metrics(conn)
            report["academic_before"] = get_academic_metrics(conn)
            table, column = ddl
            report["broken_dependencies"] = find_broken_dependencies(conn, table, column)
            report["tables_affected"] = [table]
            report["target_table"] = table
            report["operation"] = "DROP_COLUMN" if column else "DROP_TABLE"
            conn.execute("SAVEPOINT whatif_exec")
            report["logs"].append("[CATALOG] pg_depend / pg_rewrite / pg_trigger / pg_constraint inspected before DDL.")
            if column:
                command = pgsql.SQL("ALTER TABLE public.{} DROP COLUMN {}").format(pgsql.Identifier(table), pgsql.Identifier(column))
            else:
                command = pgsql.SQL("DROP TABLE public.{}").format(pgsql.Identifier(table))
            try:
                conn.execute(command)
                report["ddl_mode"] = "RESTRICT"
            except psycopg.errors.DependentObjectsStillExist:
                if is_apply:
                    raise
                conn.execute("ROLLBACK TO SAVEPOINT whatif_exec")
                report["ddl_mode"] = "CASCADE_PREVIEW"
                report["logs"].append("[DDL] Original RESTRICT blocked; explicitly expanded to a hypothetical CASCADE preview.")
                conn.execute(command + pgsql.SQL(" CASCADE"))
            report["logs"].append("[DDL] Schema modification executed; unavailable dependent metrics are omitted.")
            report["after"] = get_metrics(conn)
            report["academic_after"] = get_academic_metrics(conn)
            if not is_apply:
                conn.execute("ROLLBACK TO SAVEPOINT whatif_exec")
                report["logs"].append("[SAVEPOINT] Schema restored before full transaction rollback.")
        else:
            target = node.this.this if isinstance(node.this, exp.Schema) else node.this
            report["target_table"] = target.name
            report["tables_affected"] = [target.name]
            report["operation"] = node.key.upper()
            report["before"] = get_metrics(conn)
            report["academic_before"] = get_academic_metrics(conn)
            conn.execute("SAVEPOINT whatif_exec")
            result = conn.execute(statement)
            report["rows_affected"] = max(result.rowcount, 0)
            report["after"] = get_metrics(conn)
            report["academic_after"] = get_academic_metrics(conn)
            report["logs"].append("[DIFF] Baseline/after counts, attendance, eligibility and demonstration GPA captured.")
        report["logs"].append("[EVALUATE] Execution and telemetry completed.")
        if is_apply:
            conn.commit()
            report["committed"] = True
            report["commit_scope"] = "postgresql"
            report["status"] = "COMMITTED"
            report["logs"].append("[COMMIT] Changes permanently committed to PostgreSQL storage.")
    finally:
        try:
            if not report["committed"]:
                conn.rollback()
                report["rolled_back"] = True
                report["status"] = "VERIFIED_PRISTINE" if readonly else "SIMULATED"
                report["logs"].append("[ROLLBACK] Acknowledged; no transaction changes committed.")
        finally:
            conn.close()
    return report
