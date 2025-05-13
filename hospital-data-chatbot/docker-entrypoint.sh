#!/bin/bash
set -e

# Wait for database to be available if needed
if [ "$WAIT_FOR_DB" = "true" ]; then
    echo "Waiting for database to be available..."
    python -c "
import time
import psycopg2
from app.config.settings import AppConfig
for i in range(30):
    try:
        conn = psycopg2.connect(
            host=AppConfig.DB_HOST,
            database=AppConfig.DB_NAME,
            user=AppConfig.DB_USER,
            password=AppConfig.DB_PASSWORD,
            port=AppConfig.DB_PORT
        )
        conn.close()
        print('Database is available')
        break
    except Exception as e:
        print(f'Waiting for database... {e}')
        time.sleep(10)
"
fi

# Create data directories
mkdir -p $DATA_DIR/raw
mkdir -p $DATA_DIR/processed

# Start the application
exec "$@"