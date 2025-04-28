# /Users/omarm/My_Projects/trading/L2Replay/backend/app/replay_engine.py
import asyncio
import logging
import time
import orjson # For parsing the JSON data stored in the DB
from .database import get_db_connection, DB_PATH # Import DB functions and path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s replay_engine')

class AsyncReplayEngine:
    """
    Handles replaying market events from the SQLite database with time simulation.
    """
    def __init__(self, db_path=DB_PATH, batch_size=100, on_l2_update=None, on_trade=None):
        self.db_path = db_path
        self.batch_size = batch_size # How many events to fetch from DB at a time
        self.current_replay_time_ns = 0 # Tracks the timestamp of the last processed event
        self.last_event_timestamp_ns = 0 # Timestamp of the previous event for calculating delta
        self.last_event_sequence = -1 # Track sequence within the same timestamp
        self.speed = 1.0 # Replay speed multiplier (1.0 = real-time)
        self.is_playing = False
        self._stop_requested = False
        self._replay_task = None # To hold the asyncio task
        # Store callbacks
        self.on_l2_update = on_l2_update # Async function expected
        self.on_trade = on_trade       # Async function expected


    async def _fetch_next_batch(self):
        """Fetches the next batch of events from the database."""
        conn = None
        try:
            # Use a context manager for the connection if possible, or ensure closure
            conn = get_db_connection() # Assuming this returns a connection object
            cursor = conn.cursor()
            # Fetch events strictly after the last processed timestamp
            cursor.execute("""
                SELECT timestamp, sequence, event_type, data
                FROM market_events
                WHERE (timestamp > ?) OR (timestamp = ? AND sequence > ?)
                ORDER BY timestamp ASC, sequence ASC
                LIMIT ?
            """, (self.last_event_timestamp_ns, self.last_event_timestamp_ns, self.last_event_sequence, self.batch_size))
            rows = cursor.fetchall()
            logging.debug(f"Fetched {len(rows)} events after timestamp {self.last_event_timestamp_ns}")
            # Convert rows to list of dictionaries
            return [dict(row) for row in rows]
        except Exception as e:
            logging.error(f"Error fetching batch from database: {e}", exc_info=True)
            return [] # Return empty list on error
        finally:
            if conn:
                conn.close()

    async def _process_event(self, event):
        """Parses a single event and calls the appropriate callback."""
        try:
            logging.info(f"Processing event type: {event.get('event_type')}, Timestamp: {event.get('timestamp')}")
            event_data = orjson.loads(event['data'])
            event_timestamp_ns = event['timestamp'] # Already an integer from DB

            if event['event_type'] == 'MBP10':
                if self.on_l2_update:
                    # Extract and format L2 data
                    levels = event_data.get('levels', [])
                    bids = []
                    asks = []
                    for level in levels:
                        # Ensure price is string, size is int, skip if price/size is None/invalid
                        bid_px = level.get('bid_px')
                        bid_sz = level.get('bid_sz')
                        ask_px = level.get('ask_px')
                        ask_sz = level.get('ask_sz')
                        if bid_px is not None and bid_sz is not None and bid_sz > 0:
                            bids.append([str(bid_px), int(bid_sz)])
                        if ask_px is not None and ask_sz is not None and ask_sz > 0:
                            asks.append([str(ask_px), int(ask_sz)])

                    l2_update_msg = {
                        "type": "l2_update",
                        "data": {
                            "timestamp": event_timestamp_ns,
                            "bids": bids,
                            "asks": asks
                        }
                    }
                    # Await the callback (which should be broadcast_message)
                    await self.on_l2_update(l2_update_msg)

            elif event['event_type'] == 'TRADE':
                logging.info(f"Entered TRADE processing block for timestamp: {event_timestamp_ns}")

                if self.on_trade:
                    # Extract trade data
                    trade_data = {
                        "timestamp": event_timestamp_ns,
                        "price": str(event_data.get('price', 'N/A')), # Ensure price is string
                        "size": int(event_data.get('size', 0)),     # Ensure size is int
                        "side": event_data.get('side', 'N'),        # Aggressor side
                        "flags": event_data.get('flags'),
                        "sequence": event_data.get('sequence')
                        # Add other fields as needed by frontend
                    }
                    trade_msg = {
                        "type": "new_trade",
                        "data": trade_data
                    }
                    logging.info(f"Calling on_trade callback with message: {trade_msg}")

                    # Await the callback
                    await self.on_trade(trade_msg)

        except orjson.JSONDecodeError as e:
            logging.warning(f"Failed to parse event data JSON: {e}. Data: {event['data'][:100]}...")
        except Exception as e:
            logging.error(f"Error processing event: {e}", exc_info=True)



    async def _replay_loop(self):
        """The main asynchronous loop for replaying events."""
        logging.info("Replay loop started.")
        self.last_event_timestamp_ns = 0 # Reset timestamp at the start of a replay
        self._stop_requested = False

        while not self._stop_requested:
            if not self.is_playing:
                # If paused, wait briefly before checking again
                await asyncio.sleep(0.1)
                continue

            # Fetch the next batch of events
            batch = await self._fetch_next_batch()

            if not batch:
                # No more events found or error occurred
                if self.last_event_timestamp_ns > 0: # Avoid logging completion if we never started
                    logging.info("No more events found in the database. Replay finished.")
                else:
                    logging.warning("No events found in the database to replay.")
                self.pause() # Stop playing
                # self._stop_requested = True # Exit loop
                # break
                continue

            # Process events in the batch
            for event in batch:
                if self._stop_requested:
                    logging.info("Stop requested during batch processing.")
                    break # Exit inner loop if stop requested

                if not self.is_playing:
                    # If paused mid-batch, wait until resumed
                    while not self.is_playing and not self._stop_requested:
                        await asyncio.sleep(0.1)
                    if self._stop_requested: # Check again after pause
                         logging.info("Stop requested after pause.")
                         break

                event_timestamp_ns = event['timestamp']
                event_sequence = event['sequence']
                self.current_replay_time_ns = event_timestamp_ns # Update current time

                # Calculate time delta from the previous event
                if self.last_event_timestamp_ns > 0:
                    delta_ns = event_timestamp_ns - self.last_event_timestamp_ns
                    if delta_ns < 0:
                        logging.warning(f"Negative time delta detected: {delta_ns}ns. Skipping delay.")
                        delta_ns = 0 # Avoid negative sleep

                    # Calculate sleep duration based on speed
                    if self.speed > 0:
                        sleep_duration_sec = delta_ns / (1_000_000_000 * self.speed)
                        if sleep_duration_sec > 0:
                            max_sleep = 5.0
                            await asyncio.sleep(min(sleep_duration_sec, max_sleep))
                    # If speed is 0 or less, process as fast as possible (no sleep)

                # --- Process the event ---
                await self._process_event(event)

                # Update the timestamp of the last processed event
                self.last_event_timestamp_ns = event_timestamp_ns
                self.last_event_sequence = event_sequence

            if self._stop_requested: # Exit outer loop if stop requested
                break

            # End of batch processing, loop continues to fetch next batch unless finished

        logging.info("Replay loop stopped or paused.")
        self._replay_task = None # Clear task reference

    def start_replay_task(self):
        """Creates and starts the replay loop task if not already running."""
        if self._replay_task and not self._replay_task.done():
            logging.warning("Replay task already running.")
            return False

        logging.info("Creating replay task...")
        self.is_playing = False # Start in paused state
        self._stop_requested = False
        loop = asyncio.get_event_loop()
        self._replay_task = loop.create_task(self._replay_loop())
        return True

    def start_replay(self):
        """Starts the replay process in a background task."""
        if self._replay_task and not self._replay_task.done():
            logging.warning("Replay task already running.")
            return

        logging.info("Starting replay...")
        self.is_playing = True
        self._stop_requested = False
        # Create and run the replay loop as an asyncio task
        loop = asyncio.get_event_loop()
        self._replay_task = loop.create_task(self._replay_loop())

    def play(self):
        """Starts or resumes the replay."""
        # Ensure the task exists and is running first
        if not self._replay_task or self._replay_task.done():
             self.start_replay_task() # Create the task if needed

        if not self.is_playing:
            logging.info("Playing replay...")
            self.is_playing = True

    def pause(self):
        """Pauses the replay."""
        if self.is_playing:
            logging.info("Pausing replay...")
            self.is_playing = False

    def set_speed(self, speed_multiplier: float):
        """Sets the replay speed multiplier."""
        if speed_multiplier <= 0:
            logging.warning("Replay speed set to 0 or negative. Events will process without simulated delay.")
            self.speed = 0 # Treat 0 or negative as max speed
        else:
            logging.info(f"Setting replay speed to {speed_multiplier}x")
            self.speed = speed_multiplier

    def stop(self):
        """Requests the replay loop to stop gracefully."""
        # ... (stop remains the same)
        logging.info("Requesting replay stop...")
        self._stop_requested = True
        self.is_playing = False # Ensure it stops waiting if paused

    # Optional: Add a method to get the current status
    def get_status(self):
        # ... (get_status remains the same)
        return {
            "is_playing": self.is_playing,
            "speed": self.speed,
            "current_replay_time_ns": self.current_replay_time_ns,
            "last_event_timestamp_ns": self.last_event_timestamp_ns,
            "last_event_sequence": self.last_event_sequence,
            "is_running": self._replay_task is not None and not self._replay_task.done()
        }
