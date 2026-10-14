import os
import re
import psycopg
import sqlglot
from sqlglot import exp

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "whatif_practice",
    "user": "postgres",
}

def get_metrics(conn):
    """Fetch core table counts inside the caller’s snapshot and timeout."""
    tables = ["students", "courses", "enrollments", "attendance", "marks"]
    metrics = {}
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT count(*) FROM {table}")
            metrics[table] = cur.fetchone()[0]
    return metrics


def get_academic_metrics(conn):
    """Read metrics exposed by the delivered schema without inventing CGPA."""
    with conn.cursor() as cur:
        cur.execute("SELECT student_id, course_code, attendance_percentage, exam_eligible FROM attendance_eligibility")
        attendance = [dict(zip(("student_id", "course_code", "attendance_percentage", "exam_eligible"), row)) for row in cur.fetchall()]
        cur.execute("SELECT student_id, weighted_average_score FROM student_performance")
        performance = [dict(zip(("student_id", "weighted_average_score"), row)) for row in cur.fetchall()]
    return {"attendance": attendance, "performance": performance}


def run_whatif(sql: str, password: str | None = None):
    """Simulate a supported SQL change and roll it back."""
    password = os.getenv("PGPASSWORD", "25BDS0066") if password is None else password
    statement = sql.strip().rstrip(";")

    if not statement.upper().startswith("WHAT_IF "):
        raise ValueError("Statement must begin with WHAT_IF.")

    statement = statement[8:].strip()

    if ";" in statement:
        raise ValueError("Only one SQL statement is allowed.")

    if re.search(r"\b(COMMIT|ROLLBACK|BEGIN|SAVEPOINT|VACUUM)\b", statement, re.IGNORECASE):
        raise ValueError("Transaction-control commands are not allowed.")

    try:
        parsed = sqlglot.parse(statement, read="postgres")
    except Exception as exc:
        raise ValueError(f"Could not parse SQL: {exc}") from exc

    if len(parsed) != 1 or parsed[0] is None:
        raise ValueError("Exactly one SQL statement is required.")

    node = parsed[0]
    if not isinstance(node, (exp.Update, exp.Insert, exp.Delete)):
        raise ValueError("Only UPDATE, INSERT, and DELETE are supported currently.")

    allowed_tables = {"students", "courses", "enrollments", "attendance", "marks"}
    table_names = {
        table.name.lower() for table in node.find_all(exp.Table)
    }

    if not table_names or not table_names.issubset(allowed_tables):
        raise ValueError("The statement references an unsupported table.")

    report = {
        "statement": statement,
        "tables_affected": sorted(table_names),
        "before": {},
        "after": {},
        "rolled_back": False,
    }

    # Connect outside the execution block so callers can distinguish availability
    # failures from failures after a transaction has started.
    try:
        conn = psycopg.connect(**DB_CONFIG, password=password, connect_timeout=3)
    except psycopg.OperationalError as exc:
        raise ConnectionError("PostgreSQL connection unavailable") from exc
    try:
        conn.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
        conn.execute("SET LOCAL statement_timeout = 2000")
        report["before"] = get_metrics(conn)
        report["academic_before"] = get_academic_metrics(conn)
        result = conn.execute(statement)
        report["rows_affected"] = max(result.rowcount, 0)
        report["after"] = get_metrics(conn)
        report["academic_after"] = get_academic_metrics(conn)
        report["operation"] = node.key.upper()
        target = node.this
        if isinstance(target, exp.Schema):
            target = target.this
        report["target_table"] = target.name
    finally:
        try:
            conn.rollback()
            report["rolled_back"] = True
        finally:
            conn.close()
    return report
