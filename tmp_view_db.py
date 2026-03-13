import sqlite3
import pandas as pd
import os

# Database Path
DB_PATH = os.path.join("data", "users.db")

def view_database():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    
    # Get all table names
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [t[0] for t in cursor.fetchall() if t[0] != 'sqlite_sequence']
    
    print("\n" + "="*50)
    print("📋 PAPERGEN AI - DATABASE INSPECTOR")
    print("="*50)
    
    if not tables:
        print("No tables found in the database.")
        return

    for table in tables:
        print(f"\n🔹 TABLE: {table}")
        try:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            if df.empty:
                print("   (Table is empty)")
            else:
                # Display first 10 rows for brevity
                print(df.head(10).to_string(index=False))
                if len(df) > 10:
                    print(f"   ... and {len(df) - 10} more rows.")
        except Exception as e:
            print(f"   Error reading table: {e}")
            
    conn.close()
    print("\n" + "="*50)
    print("💡 Tip: You can also use the 'Database Inspector' in the Admin Dashboard.")
    print("="*50 + "\n")

if __name__ == "__main__":
    view_database()
