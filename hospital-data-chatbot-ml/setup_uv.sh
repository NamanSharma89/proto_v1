#!/bin/bash
# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"

echo "Setup complete! Activate the environment with: source .venv/bin/activate"