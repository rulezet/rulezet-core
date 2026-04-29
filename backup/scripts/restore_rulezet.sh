#!/bin/bash
set -e

# --- Config ---
DB_NAME="rulezet"
DB_USER="$(whoami)"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
BACKUP_DIR="$PROJECT_ROOT/backup/dumps"

# --- List available backups ---
mapfile -t BACKUPS < <(ls -t "$BACKUP_DIR"/*.dump 2>/dev/null | xargs -I{} basename {})

if [ ${#BACKUPS[@]} -eq 0 ]; then
    echo "No backups found in $BACKUP_DIR"
    exit 1
fi

# --- If no argument, show interactive selection ---
if [ -z "$1" ]; then
    echo "Available backups (newest first):"
    echo ""
    for i in "${!BACKUPS[@]}"; do
        echo "  [$((i+1))] ${BACKUPS[$i]}"
    done
    echo ""
    read -rp "Select a backup number (or press Enter to cancel): " SELECTION

    if [ -z "$SELECTION" ]; then
        echo "Cancelled."
        exit 0
    fi

    if ! [[ "$SELECTION" =~ ^[0-9]+$ ]] || [ "$SELECTION" -lt 1 ] || [ "$SELECTION" -gt "${#BACKUPS[@]}" ]; then
        echo "Error: invalid selection '$SELECTION'"
        exit 1
    fi

    BACKUP_FILE="$BACKUP_DIR/${BACKUPS[$((SELECTION-1))]}"
else
    BACKUP_FILE="$BACKUP_DIR/$1"
    if [ ! -f "$BACKUP_FILE" ]; then
        echo "Error: backup file '$BACKUP_FILE' not found in $BACKUP_DIR!"
        exit 1
    fi
fi

# --- Confirm ---
echo ""
echo "You are about to restore: $(basename "$BACKUP_FILE")"
read -rp "Are you sure? This will DROP the current database. [y/N] " CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# --- Restore ---
echo ""
echo "Starting restoration of database '$DB_NAME' from '$(basename "$BACKUP_FILE")'..."
echo "Dropping existing database '$DB_NAME'..."
dropdb -U "$DB_USER" --if-exists "$DB_NAME"

echo "Creating new empty database '$DB_NAME'..."
createdb -U "$DB_USER" "$DB_NAME"

echo "Restoring backup..."
pg_restore -U "$DB_USER" -d "$DB_NAME" "$BACKUP_FILE"

echo "Database '$DB_NAME' successfully restored from '$(basename "$BACKUP_FILE")'."