#!/bin/bash
set -e

# Create data directories
mkdir -p $DATA_DIR/raw
mkdir -p $DATA_DIR/processed

# Start the application
exec "$@"
