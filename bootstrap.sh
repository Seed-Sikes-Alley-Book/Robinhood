cd ..#!/usr/bin/env bash
set -e

PROJECT_NAME="ROBINHOOD"
VENV_DIR=".venv"
REQ_FILE="requirements.txt"

echo "=== Bootstrapping Python project: $PROJECT_NAME ==="

# Ensure Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Install it first."
    exit 1
fi

# Ensure venv module exists
if ! python3 -m venv --help &> /dev/null; then
    echo "python3-venv is missing. Installing..."
    sudo apt update && sudo apt install -y python3-venv
fi

# Create virtual environment
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
else
    echo "Virtual environment already exists."
fi

# Activate environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
if [ -f "$REQ_FILE" ]; then
    echo "Installing dependencies from $REQ_FILE..."
    pip install -r "$REQ_FILE"
else
    echo "No requirements.txt found. Skipping dependency install."
fi

# Show installed versions
echo "=== Installed Packages ==="
pip freeze

echo "=== Bootstrap complete. Environment ready. ==="
