import engine

def main():
    print("Starting What-If simulation test...")
    sql = "WHAT_IF UPDATE marks SET score = 95 WHERE enrollment_id = 1"
    try:
        result = engine.run_whatif(sql, "25BDS0066")
        print("Simulation successfully completed!")
        print("Tables affected:", result["tables_affected"])
        print("Rows affected:", result.get("rows_affected"))
        print("Rolled back:", result["rolled_back"])
    except Exception as e:
        print("Simulation failed with error:", e)

if __name__ == "__main__":
    main()