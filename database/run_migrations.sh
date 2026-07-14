#!/bin/sh

set -eu

for migration_file in /database/migrations/*.sql; do
    if [ ! -f "$migration_file" ]; then
        continue
    fi

    echo "Applying database migration: $(basename "$migration_file")"
    psql \
        --set ON_ERROR_STOP=1 \
        --single-transaction \
        --file "$migration_file"
done

echo "Database migrations completed successfully."
