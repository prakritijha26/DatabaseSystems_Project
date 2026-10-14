import traceback
import psycopg
from engine import DB_CONFIG, get_metrics

print("1. Starting debug script...")
try:
    print("2. Connecting to database...")
    conn = psycopg.connect(
        **DB_CONFIG,
        password="25BDS0066",
        connect_timeout=5,
        autocommit=True
    )
    print("3. Connected successfully!")

    print("4. Testing get_metrics()...")
    metrics = get_metrics(conn)
    print("5. Metrics retrieved successfully:", list(metrics.keys()))

    print("6. Starting transaction...")
    with conn.transaction():
        print("7. Inside transaction block, executing update...")
        cursor = conn.execute("UPDATE marks SET score = 100 WHERE enrollment_id = 1")
        print("8. Update executed, rowcount:", cursor.rowcount)

        print("9. Fetching metrics after update...")
        after_metrics = get_metrics(conn)
        print("10. After-metrics retrieved successfully!")

        print("11. Rolling back...")
        conn.rollback()
        print("12. Rollback complete!")

    conn.close()
    print("13. Done successfully!")
except Exception as e:
    print("\n--- CAUGHT EXCEPTION ---")
    traceback.print_exc()