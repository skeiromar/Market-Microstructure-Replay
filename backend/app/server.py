# /Users/omarm/My_Projects/trading/L2Replay/backend/app/server.py
import asyncio
import websockets
import logging
import orjson # Using orjson for faster JSON handling
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError
from functools import partial # Import partial

# Import the engine (assuming it's in the same directory)
from .replay_engine import AsyncReplayEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global Set to Keep Track of Connected Clients ---
# We need this to broadcast messages (like L2 updates or trades) to all connected frontends.
connected_clients = set()

# --- Message Structure Definitions (Conceptual) ---
# These aren't code per se, but define the JSON format we'll use.

# Outgoing Messages (Backend -> Frontend):
# L2 Update:
# {
#   "type": "l2_update",
#   "data": {
#     "timestamp": 1742860800032464619, # ts_event in nanoseconds
#     "bids": [["4.300000000", 400], ["4.290000000", 1000], ...], # List of [price_str, size_int]
#     "asks": [["4.420000000", 400], ["4.430000000", 500], ...]  # List of [price_str, size_int]
#   }
# }
# Note: Prices are kept as strings initially to avoid potential float precision issues,
#       but could be converted to floats on the frontend if needed for calculations.
#       Sizes are integers.

# New Trade:
# {
#   "type": "new_trade",
#   "data": {
#     "timestamp": 1742860802779823999, # ts_event in nanoseconds
#     "price": "4.370000000", # Trade price as string
#     "size": 200,           # Trade size as integer
#     "side": "A",           # Aggressor side ('A' for ask, 'B' for bid, 'N' for none)
#     # Optional: Add other relevant fields like 'flags', 'sequence' if needed by UI
#     "flags": 0,
#     "sequence": 298453
#   }
# }

# Incoming Messages (Frontend -> Backend):
# { "command": "play" }
# { "command": "pause" }
# { "command": "set_speed", "value": 2.0 } # value is a float

# --- WebSocket Server Logic ---

async def handle_connection(websocket, engine: AsyncReplayEngine): # Add engine type hint
    """Handles a single client connection."""
    logging.info(f"Client connected from {websocket.remote_address}")
    connected_clients.add(websocket)
    try:
        # Optional: Maybe start the engine task only when the first client connects?
        # if len(connected_clients) == 1:
        #    engine.start_replay_task() # Start the background task now

        async for message in websocket:
            logging.debug(f"Received message: {message}")
            try:
                command_data = orjson.loads(message)
                # Pass engine to handle_command
                await handle_command(engine, command_data, websocket)
            except orjson.JSONDecodeError:
                logging.warning(f"Received invalid JSON from {websocket.remote_address}: {message}")
            except Exception as e:
                logging.error(f"Error processing command: {e}", exc_info=True)

    except (ConnectionClosedOK, ConnectionClosedError) as e:
        logging.info(f"Client {websocket.remote_address} disconnected: {type(e).__name__}")
    except Exception as e:
        logging.error(f"Unhandled error in connection handler: {e}", exc_info=True)
    finally:
        connected_clients.remove(websocket)
        logging.info(f"Client {websocket.remote_address} removed. Total clients: {len(connected_clients)}")
        # Optional: Stop engine if last client disconnects?
        # if not connected_clients:
        #    logging.info("Last client disconnected, stopping engine.")
        #    engine.stop()

async def handle_command(engine: AsyncReplayEngine, command_data, websocket): # Add engine type hint
    """Processes commands received from the client by calling engine methods."""
    command = command_data.get("command")

    if command == "play":
        logging.info("Received 'play' command.")
        engine.play() # Call engine method
    elif command == "pause":
        logging.info("Received 'pause' command.")
        engine.pause() # Call engine method
    elif command == "set_speed":
        speed_value = command_data.get("value")
        if isinstance(speed_value, (int, float)):
            logging.info(f"Received 'set_speed' command with value: {speed_value}")
            engine.set_speed(float(speed_value)) # Call engine method
    elif command == "seek":
        timestamp_ns = command_data.get("timestamp_ns")
        # Basic validation for timestamp
        if isinstance(timestamp_ns, int) and timestamp_ns >= 0:
            logging.info(f"Received 'seek' command with timestamp_ns: {timestamp_ns}")
            # Call the engine's seek method (make it async if it needs to be)
            await engine.seek(timestamp_ns)

        else:
            logging.warning(f"Received 'set_speed' command with invalid value: {speed_value}")
    else:
        logging.warning(f"Received unknown command: {command}")


async def broadcast_message(message_dict):
    """Sends a JSON message to all connected clients."""
    # ... (broadcast_message remains the same) ...
    if not connected_clients:
        return

    message_json = orjson.dumps(message_dict)

    tasks = [client.send(message_json) for client in connected_clients]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed_client = list(connected_clients)[i]
            logging.error(f"Failed to send message to {failed_client.remote_address}: {result}")


async def start_server(engine: AsyncReplayEngine, host="localhost", port=8765): # Add engine type hint
    """Starts the WebSocket server, passing the engine to connection handlers."""
    logging.info(f"Starting WebSocket server on ws://{host}:{port}...")

    # Use partial to pass the engine instance to the connection handler
    connection_handler = partial(handle_connection, engine=engine)

    async with websockets.serve(connection_handler, host, port):
        await asyncio.Future()  # Run forever

# --- Main Execution (Example - can be run directly for testing) ---
# if __name__ == "__main__":
#     try:
#         asyncio.run(start_server())
#     except KeyboardInterrupt:
#         logging.info("WebSocket server stopped.")
