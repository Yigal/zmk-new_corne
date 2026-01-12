#!/bin/bash

# Extract port from config.json, default to 5000 if not found
PORT=$(grep -o '"port": [0-9]*' config.json | awk '{print $2}')
if [ -z "$PORT" ]; then
    PORT=5000
fi

# Find PID using the port and kill it
PID=$(lsof -ti :$PORT)
if [ -n "$PID" ]; then
  echo "Killing existing process $PID on port $PORT..."
  kill -9 $PID
fi

# Install dependencies if needed (quietly)
pip install -q flask

# Run the app in developer mode using FLASK_ENV
echo "Starting ZMK Configurator on port $PORT (Debug Mode)..."
export FLASK_APP=app.py
export FLASK_DEBUG=1
python3 -m flask run --port=$PORT --host=0.0.0.0
