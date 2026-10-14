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
    """Safely fetch basic counts from core tables with a local statement timeout."""
    tables = ["students", "courses", "enrollments", "attendance", "marks"]
    metrics = {}
    with conn.cursor() as cur:
        try:
            cur.execute("SET LOCAL statement_timeout = 2000;")
        except Exception:
            pass
            
        for table in tables:
            try:
                cur.execute(f"SELECT count(*) FROM {table}")
                row = cur.fetchone()
                metrics[table] = row[0] if row else 0
            except Exception:
                metrics[table] = 0
    return metrics

def run_whatif(sql: str, password: str):
    """Simulate a supported SQL change and roll it back."""
    print("-> INSIDE run_whatif: Parsing statement...")
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

    print("-> INSIDE run_whatif: Connecting to database...")
    try:
        with psycopg.connect(
            **DB_CONFIG,
            password=password,
            connect_timeout=10,
        ) as conn:
            print("-> INSIDE run_whatif: Connected! Getting 'before' metrics...")
            report["before"] = get_metrics(conn)
            
            print("-> INSIDE run_whatif: Executing statement...")
            result = conn.execute(statement)
            report["rows_affected"] = result.rowcount
            
            print("-> INSIDE run_whatif: Getting 'after' metrics...")
            report["after"] = get_metrics(conn)
            
            print("-> INSIDE run_whatif: Rolling back...")
            conn.rollback()
            report["rolled_back"] = True
            print("-> INSIDE run_whatif: Rollback complete.")

    except Exception as e:
        print(f"-> DATABASE ERROR EXCEPTION: {e}")
        raise e

    return report