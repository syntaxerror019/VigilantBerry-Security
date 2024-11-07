#!/bin/bash
BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the virtual environment
source "$BASE_DIR/venv/bin/activate" || { echo "Failed to activate virtual environment."; exit 1; }

# Run the Python script
python3 "$BASE_DIR/main.py" || { echo "Failed to run main.py"; exit 1; }

# Deactivate the virtual environment
deactivate
