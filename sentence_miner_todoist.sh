#!/bin/bash

# Todoist to Anki Sentence Miner Runner Script
# This script activates the virtual environment and runs the main script

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Change to the project directory
cd "$SCRIPT_DIR"

# Activate the virtual environment
source venv/bin/activate

# Run the main script with todoist source
python main.py --source todoist --model "openai/gpt-oss-120b"

# Deactivate the virtual environment (optional, as the script will exit anyway)
deactivate

# Log completion with timestamp
echo "$(date '+%Y-%m-%d %H:%M:%S') - Todoist sentence miner completed" >> "$SCRIPT_DIR/cron.log"