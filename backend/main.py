# /Users/omarm/My_Projects/trading/L2Replay/backend/main.py
import asyncio
import logging
import sys
from pathlib import Path

# --- Add app directory to Python path ---
backend_dir = Path(__file__).resolve().parent
app_dir = backend_dir / "app"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(app_dir))

try:
    from app.database import init_db, DB_PATH
    from app.replay_engine import AsyncReplayEngine
    from app.server import start_server, broadcast_message # Import server components
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Ensure this script is run from the 'backend' directory or that the 'app' directory is in the Python path.")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    logging.info("Application starting...")

    # 1. Initialize Database (check table)
    logging.info("Initializing database...")
    init_db()

    # 2. Create Replay Engine Instance
    #    Pass the broadcast_message function from the server module as the callback
    #    for both L2 updates and trades. The message type ('l2_update' or 'new_trade')
    #    will differentiate them on the frontend.
    logging.info("Creating replay engine...")
    engine = AsyncReplayEngine(
        db_path=DB_PATH,
        on_l2_update=broadcast_message,
        on_trade=broadcast_message
    )

    # 3. Start the replay engine task in the background (it will wait for 'play')
    #    Alternatively, start it when the first client connects (see server.py comment)
    engine.start_replay_task()

    # 4. Start WebSocket Server and run forever
    #    Pass the engine instance to the server.
    await start_server(engine, host="localhost", port=8765)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Application stopped by user.")
    except Exception as e:
        logging.error(f"Unhandled exception in main: {e}", exc_info=True)
    finally:
        logging.info("Application shutdown.")
