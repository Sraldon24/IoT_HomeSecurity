#!/bin/bash
# Auto-run script for the DomiSafe IoT HomeSecurity project

echo " Installing dependencies..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install -r requirements.txt

# --- SET YOUR ADAFRUIT IO KEY HERE ---
# Replace with your actual key or keep empty to read from an env var already set
ADAFRUIT_IO_KEY="aio_xxxREPLACE_ME"

if [ -z "$ADAFRUIT_IO_KEY" ]; then
  echo "  ADAFRUIT_IO_KEY not set!"
  echo "Edit this file and add your real key or export it manually."
  exit 1
fi

export ADAFRUIT_IO_KEY="$ADAFRUIT_IO_KEY"

echo " Starting DomiSafe..."
python3 src/domisafe_app.py
