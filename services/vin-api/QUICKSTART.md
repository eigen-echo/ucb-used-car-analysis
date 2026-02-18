# Quick Start Guide

Get the VIN Decoder API running with **ONE command!** ✨

## Start Everything (Automatic Setup)

```bash
cd services/vin-api
docker-compose up -d
```

**That's it!** The setup will automatically:
1. ✅ Start PostgreSQL database
2. ✅ Download NHTSA vPIC database (66.6 MB) - *only on first run*
3. ✅ Restore database to PostgreSQL - *only on first run*
4. ✅ Start the API service

⏱️ **Time:**
- First run: ~5-10 minutes (downloads and restores database)
- Subsequent runs: ~10 seconds (database is cached)

### Watch the Progress

```bash
docker-compose logs -f db-init
```

You'll see the download, extraction, and restore progress in real-time.

## Test the API

Once initialization is complete (watch for "Initialization Complete!" in logs):

**Open your browser:**
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

**Or use curl:**
```bash
curl http://localhost:8000/decode/1HGBH41JXMN109186
```

## Use from Jupyter Notebook

```python
import requests

# Decode a VIN
response = requests.get("http://localhost:8000/decode/1HGBH41JXMN109186")
print(response.json())
```

## Common Commands

**View all logs:**
```bash
docker-compose logs -f
```

**View init logs only:**
```bash
docker-compose logs -f db-init
```

**Stop services:**
```bash
docker-compose down
```

**Restart services:**
```bash
docker-compose restart
```

**Force database re-initialization:**
```bash
# Delete the restore flag and backups
rm -rf backups/.db_restored backups/vPICList_lite_2026_01.*

# Restart everything
docker-compose down
docker-compose up -d
```

## Alternative: Manual Setup

If you prefer to control the initialization manually, you can still use the standalone scripts:

**Linux/Mac:**
```bash
docker-compose up -d postgres  # Start only PostgreSQL
./setup-database.sh            # Run manual setup
docker-compose up -d vin-api   # Start API
```

**Windows:**
```cmd
docker-compose up -d postgres
setup-database.bat
docker-compose up -d vin-api
```

## Need Help?

See the full [README.md](README.md) for:
- Detailed documentation
- API endpoint reference
- Jupyter notebook examples
- Troubleshooting guide

---

**Ready to use!** The API will remember the database even if you stop and restart Docker.
