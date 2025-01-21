# this is just a test
import json
import time

from flask import Flask, Response, jsonify
from flask_cors import CORS

from .sensor import SensorData


app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})  # Svelte dev server
sensor = SensorData()


@app.route("/")
def root():
    return jsonify({"message": "Welcome to the Sensor Dashboard API"})


@app.route("/current")
def get_current_reading():
    """Get the current sensor reading."""
    return jsonify(sensor.generate_reading())


@app.route("/stream")
def stream_data():
    """Stream sensor data using server-sent events."""
    def generate():
        while True:
            data = sensor.generate_reading()
            yield f"event: sensor_update\ndata: {json.dumps(data)}\n\n"
            time.sleep(2)  # Update every 2 seconds

    return Response(generate(), mimetype="text/event-stream")
