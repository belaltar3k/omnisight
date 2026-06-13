import sys
import os
from sqlalchemy import text

# Add the root directory to the python path so we can import 'app'
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import engine

def initialize_database():
    sql_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "init_timescaledb.sql")
    
    if not os.path.exists(sql_file_path):
        print(f"❌ SQL file not found at: {sql_file_path}")
        return

    print("Reading SQL script...")
    with open(sql_file_path, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # Split script into individual SQL statements by semicolon, avoiding splitting inside functions or blocks if possible.
    # For timescaledb script, standard splitting or executing the block is fine.
    # Running the whole script block in SQLAlchemy can sometimes fail if it has multiple statements depending on the driver,
    # but with psycopg2, we can execute the whole text block as one raw command.
    print("Executing SQL script to initialize database...")
    try:
        with engine.connect() as connection:
            # Wrap in transaction
            with connection.begin():
                connection.execute(text(sql_content))
        print("✅ TimescaleDB tables and hypertables initialized successfully!")
    except Exception as e:
        print(f"❌ Error executing SQL script: {e}")

if __name__ == "__main__":
    initialize_database()
