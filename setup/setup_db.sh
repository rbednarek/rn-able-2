#!/bin/bash

# Database setup script for rnable_db
# Sets up database 'rnable_db' with user 'rnable_user'

set -e  # Exit on any error

# Configuration
DB_NAME="rnable_db"
DB_USER="rnable_user"
DB_PASSWORD="rnablepass"

echo "Setting up database: $DB_NAME"
echo "User: $DB_USER"
echo ""

# Step 1: Check if the database exists, if not create it
echo "Step 1: Checking if database '$DB_NAME' exists..."
if psql -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
    echo "✓ Database '$DB_NAME' already exists"
else
    echo "Creating database '$DB_NAME'..."
    createdb "$DB_NAME"
    echo "✓ Database '$DB_NAME' created successfully"
fi

# Step 2: Check if the user exists, if not create it with the specified password
echo ""
echo "Step 2: Checking if user '$DB_USER' exists..."
if psql -d "$DB_NAME" -tAc "SELECT 1 FROM pg_roles WHERE rolname='$DB_USER';" | grep -q 1; then
    echo "✓ User '$DB_USER' already exists"
else
    echo "Creating user '$DB_USER'..."
    psql -d "$DB_NAME" -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
    echo "✓ User '$DB_USER' created successfully"
fi

# Step 3: Check if the user owns the database, if not make it so
echo ""
echo "Step 3: Checking if user '$DB_USER' owns database '$DB_NAME'..."
CURRENT_OWNER=$(psql -d "$DB_NAME" -tAc "SELECT pg_catalog.pg_get_userbyid(d.datdba) FROM pg_catalog.pg_database d WHERE d.datname='$DB_NAME';")

if [ "$CURRENT_OWNER" = "$DB_USER" ]; then
    echo "✓ User '$DB_USER' already owns database '$DB_NAME'"
else
    echo "Transferring ownership of database '$DB_NAME' to user '$DB_USER'..."
    psql -d "$DB_NAME" -c "ALTER DATABASE $DB_NAME OWNER TO $DB_USER;"
    echo "✓ Database '$DB_NAME' ownership transferred to '$DB_USER'"
fi

# Step 4: Ensure the user owns the public schema (required for Django migrations)
echo ""
echo "Step 4: Ensuring user '$DB_USER' owns schema 'public'..."
psql -d "$DB_NAME" -c "ALTER SCHEMA public OWNER TO $DB_USER;"
echo "✓ Schema 'public' ownership set to '$DB_USER'"

echo ""
echo "🎉 Database setup completed successfully!"
echo "Database: $DB_NAME"
echo "Owner: $DB_USER"
echo "Connection string: postgresql://$DB_USER:$DB_PASSWORD@localhost/$DB_NAME"
