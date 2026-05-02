import sqlite3
import os
import time

DB_PATH = "history.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print("Database not found.")
        return
    
    conn = sqlite3.connect(DB_PATH, timeout=30)
    cur = conn.cursor()
    
    try:
        # Check if actual_max_c exists
        cur.execute("PRAGMA table_info(analyses)")
        columns = [info[1] for info in cur.fetchall()]
        
        if "actual_max_c" not in columns:
            print("Adding column actual_max_c...")
            cur.execute("ALTER TABLE analyses ADD COLUMN actual_max_c REAL")
        
        if "is_resolved" not in columns:
            print("Adding column is_resolved...")
            cur.execute("ALTER TABLE analyses ADD COLUMN is_resolved INTEGER DEFAULT 0")
            
        # Check if model_biases table exists
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='model_biases'")
        if not cur.fetchone():
            print("Creating table model_biases...")
            cur.execute("CREATE TABLE model_biases (model_name TEXT, city_key TEXT, bias_sum REAL, count INTEGER, PRIMARY KEY(model_name, city_key))")
        
        conn.commit()
        print("Migration finished successfully.")
    except sqlite3.OperationalError as e:
        if "locked" in str(e):
            print("Database is locked. Please stop the application and try again.")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
