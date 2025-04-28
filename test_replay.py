# /Users/omarm/My_Projects/trading/L2Replay/backend/test_replay.py
import asyncio
import sys
from pathlib import Path
import time

# --- Add app directory to Python path ---
# This allows importing from the 'app' directory
backend_dir = Path(__file__).resolve().parent
app_dir = backend_dir / "app"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(app_dir))

try:
    from app.replay_engine import AsyncReplayEngine
    from app.database import DB_PATH, init_db # Import DB path and init function
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Ensure this script is run from the 'backend' directory or that the 'app' directory is in the Python path.")
    sys.exit(1)

async def main():
    print("Initializing database (checking table existence)...")
    # Ensure the DB and table exist before starting
    init_db()

    print(f"Creating replay engine with database: {DB_PATH}")
    engine = AsyncReplayEngine(db_path=DB_PATH, batch_size=50) # Smaller batch for testing visibility

    print("Starting replay engine...")
    engine.start_replay() # Starts the loop in the background

    # Let the replay run for a bit
    try:
        start_time = time.time()
        while True:
            status = engine.get_status()
            print(f"Engine Status: Playing={status['is_playing']}, Speed={status['speed']:.1f}x, Running={status['is_running']}")

            if not status['is_running'] and (time.time() - start_time) > 5: # Exit if finished and waited 5s
                 print("Engine task finished.")
                 break

            await asyncio.sleep(5) # Print status every 5 seconds

            # --- Example Controls (Uncomment to test) ---
            if time.time() - start_time > 10 and status['is_playing']:
                print("\n--- Pausing Engine ---\n")
                engine.pause()
                await asyncio.sleep(5)
                print("\n--- Resuming Engine ---\n")
                engine.play()
                await asyncio.sleep(5)
                print("\n--- Setting Speed to 2x ---\n")
                engine.set_speed(2.0)
                await asyncio.sleep(10)
                print("\n--- Setting Speed to 0.5x ---\n")
                engine.set_speed(0.5)
                await asyncio.sleep(10)
                print("\n--- Stopping Engine ---\n")
                engine.stop()
                break # Exit after stopping

    except KeyboardInterrupt:
        print("\nKeyboardInterrupt received, stopping engine...")
        engine.stop()
        # Wait briefly for the task to hopefully finish cleanup
        await asyncio.sleep(1)
    finally:
        # Ensure stop is called if loop exits unexpectedly
        if engine.get_status()['is_running']:
             engine.stop()
             await asyncio.sleep(0.5) # Short wait
        print("Test script finished.")


if __name__ == "__main__":
    asyncio.run(main())
