import sqlite3
import os
import json

db_path = ".audit_state.db"

if not os.path.exists(db_path):
    print(f"Database not found at {os.path.abspath(db_path)}")
    exit(1)

print(f"Analyzing database at {os.path.abspath(db_path)}")

try:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # Check Audit Runs
    print("\n=== Audit Runs ===")
    cursor = conn.execute("SELECT * FROM audit_runs ORDER BY started_at DESC LIMIT 5")
    runs = cursor.fetchall()
    if not runs:
        print("No audit runs found.")
    for run in runs:
        print(f"ID: {run['id']}, Status: {run['status']}, Progress: {run['completed_tools']}/{run['total_tools']}")
        print(f"  Error: {run['error']}")
    
    # Check Tool Results
    print("\n=== Tool Results (Last 10) ===")
    cursor = conn.execute("SELECT * FROM tool_results ORDER BY created_at DESC LIMIT 10")
    results = cursor.fetchall()
    if not results:
        print("No tool results found.")
    for res in results:
        # Print dictionary to see available keys
        r = dict(res)
        print(f"Result: {r}")

except Exception as e:
    print(f"Error reading DB: {e}")
finally:
    if 'conn' in locals(): conn.close()
