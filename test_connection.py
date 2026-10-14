
import getpass
import psycopg

print("A: Script started", flush=True)

password = getpass.getpass("PostgreSQL password: ")

print("B: Connecting to database...", flush=True)

with psycopg.connect(
    host="127.0.0.1",
    port=5432,
    dbname="whatif_practice",
    user="postgres",
    password=password,
    connect_timeout=5,
    autocommit=True,
    options="-c statement_timeout=5000"
) as conn:

    print("C: Connected successfully!", flush=True)

    # Display database connection details
    details = conn.execute("""
        SELECT current_database(), current_schema(), current_user;
    """).fetchone()

    print("\nDatabase:", details[0], flush=True)
    print("Schema:", details[1], flush=True)
    print("User:", details[2], flush=True)

    # List only project tables in the public schema
    print("\nD: Checking project tables...", flush=True)

    tables = conn.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """).fetchall()

    print("\nProject tables found:", len(tables), flush=True)

    for table in tables:
        print("-", table[0], flush=True)

    # Count students if the students table exists
    table_names = [table[0] for table in tables]

    if "students" in table_names:
        student_count = conn.execute(
            "SELECT COUNT(*) FROM public.students;"
        ).fetchone()

        print(
            "\nTotal students:",
            student_count[0],
            flush=True
        )
    else:
        print(
            "\nThe students table was not found in the public schema.",
            flush=True
        )

print("\nE: Connection closed successfully!", flush=True)
print("F: Finished successfully!", flush=True)
