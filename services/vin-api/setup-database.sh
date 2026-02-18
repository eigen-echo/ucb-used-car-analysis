#!/bin/bash

# NHTSA vPIC Database Setup Script
# This script downloads and restores the vPIC PostgreSQL database

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
DB_NAME="vpic"
DB_USER="vpic_user"
DB_PASSWORD="vpic_password"
DB_HOST="localhost"
DB_PORT="5432"
DOWNLOAD_URL="https://vpic.nhtsa.dot.gov/downloads/vPICList_lite_2026_01.custom.zip"
BACKUP_DIR="./backups"
BACKUP_FILE="vPICList_lite_2026_01.backup"
ZIP_FILE="vPICList_lite_2026_01.custom.zip"

echo -e "${GREEN}=====================================${NC}"
echo -e "${GREEN}NHTSA vPIC Database Setup${NC}"
echo -e "${GREEN}=====================================${NC}\n"

# Create backups directory if it doesn't exist
echo -e "${YELLOW}Creating backups directory...${NC}"
mkdir -p "$BACKUP_DIR"

# Download the database backup if it doesn't exist
if [ -f "$BACKUP_DIR/$ZIP_FILE" ]; then
    echo -e "${YELLOW}Database backup already exists. Skipping download.${NC}"
else
    echo -e "${YELLOW}Downloading vPIC database backup (66.6 MB)...${NC}"
    curl -L -o "$BACKUP_DIR/$ZIP_FILE" "$DOWNLOAD_URL"
    echo -e "${GREEN}Download complete!${NC}\n"
fi

# Unzip the backup file if not already unzipped
if [ -f "$BACKUP_DIR/$BACKUP_FILE" ]; then
    echo -e "${YELLOW}Backup file already extracted. Skipping extraction.${NC}"
else
    echo -e "${YELLOW}Extracting backup file...${NC}"
    unzip -o "$BACKUP_DIR/$ZIP_FILE" -d "$BACKUP_DIR"
    echo -e "${GREEN}Extraction complete!${NC}\n"
fi

# Wait for PostgreSQL to be ready
echo -e "${YELLOW}Waiting for PostgreSQL to be ready...${NC}"
until docker exec vpic-postgres pg_isready -U "$DB_USER" -d "$DB_NAME" > /dev/null 2>&1; do
    echo -e "${YELLOW}PostgreSQL is unavailable - sleeping${NC}"
    sleep 2
done
echo -e "${GREEN}PostgreSQL is ready!${NC}\n"

# Restore the database
echo -e "${YELLOW}Restoring database backup...${NC}"
echo -e "${YELLOW}This may take a few minutes...${NC}\n"

# Copy backup file into container
docker cp "$BACKUP_DIR/$BACKUP_FILE" vpic-postgres:/tmp/$BACKUP_FILE

# Restore using pg_restore
docker exec -e PGPASSWORD="$DB_PASSWORD" vpic-postgres \
    pg_restore \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -v \
    --no-owner \
    --no-privileges \
    /tmp/$BACKUP_FILE

echo -e "\n${GREEN}Database restoration complete!${NC}\n"

# Test the VIN decode function
echo -e "${YELLOW}Testing VIN decode function...${NC}"
docker exec -e PGPASSWORD="$DB_PASSWORD" vpic-postgres \
    psql -U "$DB_USER" -d "$DB_NAME" \
    -c "SELECT * FROM vpic.spVinDecode('1HGBH41JXMN109186') LIMIT 5;"

echo -e "\n${GREEN}=====================================${NC}"
echo -e "${GREEN}Setup Complete!${NC}"
echo -e "${GREEN}=====================================${NC}"
echo -e "\nYou can now:"
echo -e "  1. Access the API at: ${GREEN}http://localhost:8000${NC}"
echo -e "  2. View API docs at: ${GREEN}http://localhost:8000/docs${NC}"
echo -e "  3. Test VIN decode: ${GREEN}curl http://localhost:8000/decode/1HGBH41JXMN109186${NC}\n"
