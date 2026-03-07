#!/bin/bash
set -e

echo "Waiting for database..."
sleep 5

echo "Running migrations..."
if alembic upgrade head; then
    echo "✓ Migrations applied successfully."
else
    echo "𐄂 Failed to apply migrations. Exiting."
    exit 1
fi

echo "Creating root user..."
python create_root_user.py