#!/bin/bash
set -e

execute_sql() {
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -c "$1"
}

# Check if the user exists; create it if not.
USER_EXISTS=$(psql -U "$POSTGRES_USER" -tAc "SELECT 1 FROM pg_catalog.pg_roles WHERE rolname = '$FAMILY_DB_USER'")
if [ "$USER_EXISTS" != "1" ]; then
    execute_sql "CREATE USER $FAMILY_DB_USER WITH PASSWORD '$FAMILY_DB_PASSWORD';"
fi

# Check if the database exists; create it if not.
DB_EXISTS=$(psql -U "$POSTGRES_USER" -tAc "SELECT 1 FROM pg_database WHERE datname = '$FAMILY_POSTGRES_DB'")
if [ "$DB_EXISTS" != "1" ]; then
    execute_sql "CREATE DATABASE $FAMILY_POSTGRES_DB;"
    execute_sql "ALTER DATABASE $FAMILY_POSTGRES_DB OWNER TO $FAMILY_DB_USER;"
else
    execute_sql "ALTER DATABASE $FAMILY_POSTGRES_DB OWNER TO $FAMILY_DB_USER;"
fi

# Grant all privileges on the database to the user
execute_sql "GRANT ALL PRIVILEGES ON DATABASE $FAMILY_POSTGRES_DB TO $FAMILY_DB_USER;"
