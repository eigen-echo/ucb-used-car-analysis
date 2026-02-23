@echo off
REM NHTSA vPIC Database Setup Script for Windows
REM This script downloads and restores the vPIC PostgreSQL database

setlocal enabledelayedexpansion

REM Configuration
set DB_NAME=vpic
set DB_USER=vpic_user
set DB_PASSWORD=vpic_password
set DB_HOST=localhost
set DB_PORT=5432
set DOWNLOAD_URL=https://vpic.nhtsa.dot.gov/downloads/vPICList_lite_2026_01.custom.zip
set BACKUP_DIR=backups
set BACKUP_FILE=vPICList_lite_2026_01.backup
set ZIP_FILE=vPICList_lite_2026_01.custom.zip

echo =====================================
echo NHTSA vPIC Database Setup
echo =====================================
echo.

REM Create backups directory if it doesn't exist
echo Creating backups directory...
if not exist "!BACKUP_DIR!" mkdir "!BACKUP_DIR!"

REM Download the database backup if it doesn't exist
if exist "!BACKUP_DIR!\!ZIP_FILE!" (
    echo Database backup already exists. Skipping download.
) else (
    echo Downloading vPIC database backup (66.6 MB^)...
    curl -L -o "!BACKUP_DIR!\!ZIP_FILE!" "!DOWNLOAD_URL!"
    echo Download complete!
    echo.
)

REM Unzip the backup file if not already unzipped
if exist "!BACKUP_DIR!\!BACKUP_FILE!" (
    echo Backup file already extracted. Skipping extraction.
) else (
    echo Extracting backup file...
    tar -xf "!BACKUP_DIR!\!ZIP_FILE!" -C "!BACKUP_DIR!"
    echo Extraction complete!
    echo.
)

REM Wait for PostgreSQL to be ready
echo Waiting for PostgreSQL to be ready...
:wait_loop
docker exec vpic-postgres pg_isready -U !DB_USER! -d !DB_NAME! >nul 2>&1
if errorlevel 1 (
    echo PostgreSQL is unavailable - sleeping
    timeout /t 2 /nobreak >nul
    goto wait_loop
)
echo PostgreSQL is ready!
echo.

REM Restore the database
echo Restoring database backup...
echo This may take a few minutes...
echo.

REM Copy backup file into container
docker cp "!BACKUP_DIR!\!BACKUP_FILE!" vpic-postgres:/tmp/!BACKUP_FILE!

REM Restore using pg_restore
docker exec -e PGPASSWORD=!DB_PASSWORD! vpic-postgres pg_restore -U !DB_USER! -d !DB_NAME! -v --no-owner --no-privileges /tmp/!BACKUP_FILE!

echo.
echo Database restoration complete!
echo.

REM Test the VIN decode function
echo Testing VIN decode function...
docker exec -e PGPASSWORD=!DB_PASSWORD! vpic-postgres psql -U !DB_USER! -d !DB_NAME! -c "SELECT * FROM vpic.spVinDecode('1HGBH41JXMN109186') LIMIT 5;"

echo.
echo =====================================
echo Setup Complete!
echo =====================================
echo.
echo You can now:
echo   1. Access the API at: http://localhost:8000
echo   2. View API docs at: http://localhost:8000/docs
echo   3. Test VIN decode: curl http://localhost:8000/decode/1HGBH41JXMN109186
echo.

endlocal
