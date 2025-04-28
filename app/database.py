# /Users/omarm/My_Projects/trading/L2Replay/backend/app/database.py
import sqlite3
import orjson # Using orjson for speed, fallback to json if not installed
# import json # Use this if you didn't install orjson
import logging
import os
from pathlib import Path
from datetime import datetime, timezone # Import datetime and timezone

# --- Configuration ---
# Get the absolute path to the backend directory
BACKEND_DIR = Path(__file__).resolve().parent.parent
DB_DIR = BACKEND_DIR / "data"
DB_PATH = DB_DIR / "market_data.db"

# Ensure the data directory exists
os.makedirs(DB_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Database Functions ---

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row # Return rows as dictionary-like objects
        # Increase timeout if needed for large transactions
        # conn.timeout = 30.0 # seconds
        logging.debug(f"Database connection established to {DB_PATH}") # Changed to debug for less noise
        return conn
    except sqlite3.Error as e:
        logging.error(f"Database connection error: {e}")
        raise

def init_db():
    """Initializes the database and creates the market_events table if it doesn't exist."""
    logging.info("Initializing database...")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Use WAL mode for potentially better write performance and concurrency
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_events (
                timestamp INTEGER NOT NULL,    -- Nanoseconds since UNIX epoch from ts_event
                sequence INTEGER NOT NULL,     -- Sequence number from the event data
                event_type TEXT NOT NULL,      -- 'MBP10' or 'TRADE'
                data TEXT NOT NULL,            -- JSON string of the original record
                PRIMARY KEY (timestamp, sequence) -- Composite primary key
            );
        """)
        # Optional: Add an index JUST on timestamp for faster range queries if needed,
        # though the primary key might cover this depending on query patterns.
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON market_events (timestamp);")
        conn.commit()
        logging.info("Database initialized successfully. 'market_events' table ready.")

    except sqlite3.Error as e:
        logging.error(f"Error initializing database table: {e}")
    finally:
        if conn:
            conn.close()
            logging.debug("Database connection closed after initialization.") # Changed to debug

def parse_timestamp_ns(ts_string: str) -> int | None:
    """Parses an ISO 8601 timestamp string and returns nanoseconds since epoch."""
    try:
        # Handle potential 'Z' for UTC timezone
        if ts_string.endswith('Z'):
            ts_string = ts_string[:-1] + '+00:00'
        # Parse the timestamp string
        dt = datetime.fromisoformat(ts_string)
        # Ensure it's timezone-aware (assume UTC if not specified, though Z implies UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        # Convert to UNIX timestamp (seconds) and then to nanoseconds
        timestamp_ns = int(dt.timestamp() * 1_000_000_000)
        return timestamp_ns
    except (ValueError, TypeError) as e:
        logging.warning(f"Could not parse timestamp string '{ts_string}': {e}")
        return None


def load_data_from_json(json_file_path: str, event_type: str):
    """Loads data from a line-delimited JSON file (.jsonl) into the market_events table."""
    logging.info(f"Starting data load for {event_type} from {json_file_path}...")
    conn = None # Initialize conn to None
    inserted_count = 0
    skipped_invalid_ts = 0
    skipped_missing_ts = 0
    skipped_duplicate = 0
    skipped_json_error = 0
    processed_lines = 0

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Start transaction for faster inserts
        cursor.execute('BEGIN TRANSACTION')

        with open(json_file_path, 'rb') as f: # Open in binary mode for orjson
            for line in f:
                processed_lines += 1
                line = line.strip()
                if not line:
                    continue # Skip empty lines

                try:
                    record = orjson.loads(line)
                except orjson.JSONDecodeError as e:
                    logging.warning(f"Skipping invalid JSON line {processed_lines}: {e} - Line: {line[:100]}...")
                    skipped_json_error += 1
                    continue

                # --- IMPORTANT: Timestamp Handling ---
                # Access nested 'ts_event' within 'hd' object
                ts_event_str = record.get('hd', {}).get('ts_event')

                if ts_event_str is None:
                    logging.warning(f"Skipping record on line {processed_lines} due to missing 'hd.ts_event': {record}")
                    skipped_missing_ts += 1
                    continue

                # Parse the timestamp string and convert to nanoseconds
                timestamp_ns = parse_timestamp_ns(ts_event_str)

                if timestamp_ns is None:
                    logging.warning(f"Skipping record on line {processed_lines} due to invalid timestamp format '{ts_event_str}': {record}")
                    skipped_invalid_ts += 1
                    continue

                sequence = record.get('sequence') # Trades have sequence at top level
                if sequence is None:
                    # MBP-10 has sequence inside 'hd'
                    sequence = record.get('hd', {}).get('sequence')

                if sequence is None:
                    logging.warning(f"Skipping record on line {processed_lines} due to missing 'sequence': {record}")
                    # Decide how to handle missing sequence, skip for now
                    skipped_missing_seq += 1 # Add a counter for this
                    continue
                try:
                    sequence = int(sequence)
                except (ValueError, TypeError):
                    logging.warning(f"Skipping record on line {processed_lines} due to invalid 'sequence': {sequence}")
                    skipped_invalid_seq += 1 # Add a counter for this
                    continue

                # Store the entire original record as a JSON string
                # Use orjson.dumps for potentially better performance and correctness
                data_json = orjson.dumps(record).decode('utf-8')
                # data_json = json.dumps(record) # if using standard json

                cursor.execute("""
                    INSERT OR IGNORE INTO market_events (timestamp, sequence, event_type, data)
                    VALUES (?, ?, ?, ?)
                """, (timestamp_ns, sequence, event_type, data_json)) # Add sequence here

                if cursor.rowcount > 0:
                    inserted_count += 1
                else:
                    # This means the timestamp likely already existed
                    skipped_duplicate += 1
                    logging.info(f"Skipped duplicate composite key: (ts={timestamp_ns}, seq={sequence}) on line {processed_lines}")

        # Commit the transaction after processing all lines
        conn.commit()
        logging.info(f"Data loading complete for {event_type}.")
        logging.info(f"Processed Lines: {processed_lines}, Inserted: {inserted_count}")
        logging.info(f"Skipped -> Duplicates (ts+seq): {skipped_duplicate}, Missing TS: {skipped_missing_ts}, Invalid TS: {skipped_invalid_ts}, JSON Errors: {skipped_json_error}") # Add seq errors if needed

    except FileNotFoundError:
        logging.error(f"Error: JSON file not found at {json_file_path}")
    except sqlite3.Error as e:
        if conn:
            conn.rollback() # Rollback transaction on database error
        logging.error(f"Database error during data loading for {event_type}: {e}")
    except Exception as e:
        if conn:
            conn.rollback() # Rollback transaction on other errors
        logging.error(f"An unexpected error occurred during data loading for {event_type}: {e}", exc_info=True) # Log traceback
    finally:
        if conn:
            conn.close()
            logging.debug(f"Database connection closed after loading {event_type}.") # Changed to debug

# --- Data Querying Functions (Example for later use) ---

def get_events_after_timestamp(timestamp: int, limit: int = 100):
    """Retrieves events ordered by timestamp, starting after the given timestamp."""
    conn = None # Initialize conn to None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # UPDATE SELECT statement: Include sequence for potential future use, adjust ORDER BY
        cursor.execute("""
            SELECT timestamp, sequence, event_type, data
            FROM market_events
            WHERE timestamp >= ? -- Use >= to include events AT the start timestamp
            ORDER BY timestamp ASC, sequence ASC -- Order by sequence within the same timestamp
            LIMIT ?
            -- Note: Fetching strictly AFTER (>) the last processed timestamp might be complex
            -- if the last event was part of a batch with the same timestamp.
            -- Using >= and handling potential re-processing of the very last event
            -- in the engine might be simpler for now.
        """, (timestamp, limit)) # Start timestamp needs careful handling in engine now
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logging.error(f"Error querying events: {e}")
        return []
    finally:
        if conn:
            conn.close()
            logging.debug("Database connection closed after querying events.") # Changed to debug

