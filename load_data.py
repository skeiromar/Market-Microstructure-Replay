# /Users/omarm/My_Projects/trading/L2Replay/backend/load_data.py
import argparse
import sys
import os
from pathlib import Path

# --- Add app directory to Python path ---
# This allows importing 'database' from the 'app' directory
backend_dir = Path(__file__).resolve().parent
app_dir = backend_dir / "app"
sys.path.insert(0, str(backend_dir)) # Add backend dir first for potential relative imports
sys.path.insert(0, str(app_dir)) # Add app dir

try:
    from app.database import init_db, load_data_from_json
except ImportError as e:
    print(f"Error importing database module: {e}")
    print("Ensure this script is run from the 'backend' directory or that the 'app' directory is in the Python path.")
    sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Load market data from JSON files into SQLite DB.")
    parser.add_argument("mbp_file", help="Path to the MBP-10 JSON/JSONL file.")
    parser.add_argument("trades_file", help="Path to the Trades JSON/JSONL file.")
    parser.add_argument("--clear", action="store_true", help="Clear existing data before loading (use with caution).")

    args = parser.parse_args()

    # --- Validate file paths ---
    if not os.path.exists(args.mbp_file):
        print(f"Error: MBP file not found at {args.mbp_file}")
        sys.exit(1)
    if not os.path.exists(args.trades_file):
        print(f"Error: Trades file not found at {args.trades_file}")
        sys.exit(1)

    # --- Initialize DB ---
    init_db() # Creates table if it doesn't exist

    # --- Optional: Clear existing data ---
    if args.clear:
        print("Clearing existing data from market_events table...")
        try:
            from app.database import get_db_connection # Import here to avoid circular dependency issues if any
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM market_events;")
            conn.commit()
            conn.close()
            print("Existing data cleared.")
        except Exception as e:
            print(f"Error clearing data: {e}")
            sys.exit(1)


    # --- Load Data ---
    print("\n--- Loading MBP-10 Data ---")
    load_data_from_json(args.mbp_file, 'MBP10')

    print("\n--- Loading Trades Data ---")
    load_data_from_json(args.trades_file, 'TRADE')

    print("\nData loading process finished.")

if __name__ == "__main__":
    main()
