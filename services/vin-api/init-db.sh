#!/bin/bash

# Database Initialization Script
# This script downloads and restores the NHTSA vPIC database automatically

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
DB_NAME="${POSTGRES_DB:-vpic}"
DB_USER="${POSTGRES_USER:-vpic_user}"
DB_HOST="${POSTGRES_HOST:-postgres}"
DB_PORT="${POSTGRES_PORT:-5432}"
DOWNLOAD_URL="https://vpic.nhtsa.dot.gov/downloads/vPICList_lite_2026_01.custom.zip"
BACKUP_DIR="/backups"
BACKUP_FILE="vPICList_lite_2026_01.backup"
ZIP_FILE="vPICList_lite_2026_01.custom.zip"
RESTORE_FLAG="/backups/.db_restored"

echo -e "${BLUE}=======================================${NC}"
echo -e "${BLUE}NHTSA vPIC Database Initialization${NC}"
echo -e "${BLUE}=======================================${NC}\n"

# Check if database has already been restored
if [ -f "$RESTORE_FLAG" ]; then
    echo -e "${GREEN}✓ Database already initialized. Skipping restore.${NC}"
    echo -e "${YELLOW}  To force re-initialization, delete: $RESTORE_FLAG${NC}\n"
    exit 0
fi

# Create backups directory
mkdir -p "$BACKUP_DIR"

# Download the database backup if it doesn't exist
if [ -f "$BACKUP_DIR/$ZIP_FILE" ]; then
    echo -e "${YELLOW}✓ Database backup already exists. Skipping download.${NC}"
else
    echo -e "${BLUE}⬇ Downloading vPIC database backup (66.6 MB)...${NC}"
    if wget -q --show-progress -O "$BACKUP_DIR/$ZIP_FILE" "$DOWNLOAD_URL"; then
        echo -e "${GREEN}✓ Download complete!${NC}\n"
    else
        echo -e "${RED}✗ Download failed. Trying with curl...${NC}"
        curl -L --progress-bar -o "$BACKUP_DIR/$ZIP_FILE" "$DOWNLOAD_URL"
        echo -e "${GREEN}✓ Download complete!${NC}\n"
    fi
fi

# Extract the backup file if not already extracted
if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo -e "${YELLOW}✓ Backup file already extracted. Skipping extraction.${NC}"
else
    echo -e "${BLUE}📦 Extracting backup file...${NC}"
    unzip -q "$BACKUP_DIR/$ZIP_FILE" -d "$BACKUP_DIR"
    echo -e "${GREEN}✓ Extraction complete!${NC}\n"
fi

# Wait for PostgreSQL to be ready
echo -e "${BLUE}⏳ Waiting for PostgreSQL to be ready...${NC}"
RETRIES=30
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
    RETRIES=$((RETRIES - 1))
    if [ $RETRIES -eq 0 ]; then
        echo -e "${RED}✗ PostgreSQL did not become ready in time${NC}"
        exit 1
    fi
    echo -e "${YELLOW}  PostgreSQL is unavailable - retrying ($RETRIES attempts left)${NC}"
    sleep 2
done
echo -e "${GREEN}✓ PostgreSQL is ready!${NC}\n"

# Restore the database
echo -e "${BLUE}🔄 Restoring database backup...${NC}"
echo -e "${YELLOW}  This may take a few minutes...${NC}\n"

if PGPASSWORD=$POSTGRES_PASSWORD pg_restore \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -v \
    --no-owner \
    --no-privileges \
    "$BACKUP_DIR/$BACKUP_FILE" 2>&1 | grep -v "WARNING:"; then
    echo -e "${GREEN}✓ Database restoration complete!${NC}\n"
else
    # pg_restore may return non-zero even on success due to warnings
    # Check if the function exists to verify success
    if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
        -c "SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = 'spvindecode');" | grep -q "t"; then
        echo -e "${GREEN}✓ Database restoration complete (with warnings)!${NC}\n"
    else
        echo -e "${RED}✗ Database restoration may have failed${NC}"
        exit 1
    fi
fi

# Test the VIN decode function
echo -e "${BLUE}🧪 Testing VIN decode function...${NC}"
if PGPASSWORD=$POSTGRES_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
    -c "SELECT * FROM vpic.spVinDecode('1HGBH41JXMN109186');" 2>/dev/null | grep -q "HONDA"; then
    echo -e "${GREEN}✓ VIN decode function working correctly!${NC}\n"

    # Create restore flag to skip this on next startup
    touch "$RESTORE_FLAG"
    echo "Database initialized on $(date)" > "$RESTORE_FLAG"

    echo -e "${GREEN}=======================================${NC}"
    echo -e "${GREEN}✓ Initialization Complete!${NC}"
    echo -e "${GREEN}=======================================${NC}\n"
else
    echo -e "${RED}✗ VIN decode function test failed${NC}"
    exit 1
fi
