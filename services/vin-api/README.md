# NHTSA vPIC VIN Decoder API

A RESTful API service for decoding Vehicle Identification Numbers (VINs) using the NHTSA vPIC PostgreSQL database.

## Overview

This service provides a Python FastAPI-based REST API that exposes VIN lookup functionality from the NHTSA (National Highway Traffic Safety Administration) vPIC database running in a PostgreSQL Docker container.

### Features

- ✅ **Fast VIN Decoding**: Decode 17-character VINs to retrieve vehicle information
- ✅ **RESTful API**: Simple HTTP endpoints (GET and POST)
- ✅ **Auto Documentation**: Interactive API docs with Swagger UI and ReDoc
- ✅ **Docker-based**: Easy deployment with Docker Compose
- ✅ **Health Checks**: Monitor API and database status
- ✅ **CORS Enabled**: Ready for consumption from Jupyter notebooks and web applications

## Prerequisites

- **Docker** and **Docker Compose** installed
- **curl** or **wget** for downloading database files
- **unzip** or **tar** for extracting archives
- At least **500 MB** of free disk space

## Quick Start

### 🚀 One-Command Setup (Automatic)

```bash
cd services/vin-api
docker-compose up -d
```

**That's it!** Docker Compose will automatically:
1. Start PostgreSQL database
2. Download the NHTSA vPIC database (66.6 MB) - *first run only*
3. Restore the database - *first run only*
4. Start the API service

⏱️ **First run:** ~5-10 minutes | **Subsequent runs:** ~10 seconds

#### Watch Progress
```bash
docker-compose logs -f db-init
```

### 🌐 Access the API

Once the initialization completes (watch for "Initialization Complete!" in logs):

- **API Base URL**: http://localhost:8000
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### 🔧 Alternative: Manual Setup

If you prefer manual control over the initialization:

**For Linux/Mac:**
```bash
docker-compose up -d postgres    # Start only PostgreSQL
chmod +x setup-database.sh
./setup-database.sh              # Manual setup
docker-compose up -d vin-api     # Start API
```

**For Windows:**
```cmd
docker-compose up -d postgres
setup-database.bat
docker-compose up -d vin-api
```

## API Endpoints

### Health Check

Check if the API and database are running:

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "message": "API is running and database is accessible"
}
```

### Decode VIN (GET)

Decode a VIN using a GET request:

```bash
curl http://localhost:8000/decode/1HGBH41JXMN109186
```

### Decode VIN (POST)

Decode a VIN using a POST request:

```bash
curl -X POST http://localhost:8000/decode \
  -H "Content-Type: application/json" \
  -d '{"vin": "1HGBH41JXMN109186"}'
```

**Response:**
```json
{
  "vin": "1HGBH41JXMN109186",
  "data": [
    {
      "variable": "Make",
      "value": "HONDA"
    },
    {
      "variable": "Model",
      "value": "Accord"
    },
    ...
  ],
  "count": 136,
  "success": true,
  "message": "VIN decoded successfully"
}
```

## Usage from Jupyter Notebook

### Install requests library (if not already installed)

```python
!pip install requests
```

### Example: Decode a Single VIN

```python
import requests

# API endpoint
API_URL = "http://localhost:8000"

# Decode a VIN
vin = "1HGBH41JXMN109186"
response = requests.get(f"{API_URL}/decode/{vin}")

# Check response
if response.status_code == 200:
    data = response.json()
    print(f"VIN: {data['vin']}")
    print(f"Records found: {data['count']}")

    # Display results
    for item in data['data']:
        print(f"{item['variable']}: {item['value']}")
else:
    print(f"Error: {response.status_code}")
```

### Example: Decode Multiple VINs

```python
import requests
import pandas as pd

API_URL = "http://localhost:8000"

# List of VINs to decode
vins = [
    "1HGBH41JXMN109186",
    "2HGFG12668H542570",
    "1FTFW1EF8DFC10312"
]

# Decode all VINs
results = []
for vin in vins:
    response = requests.get(f"{API_URL}/decode/{vin}")
    if response.status_code == 200:
        results.append(response.json())

# Convert to DataFrame for analysis
df = pd.DataFrame(results)
print(df[['vin', 'count', 'success']])
```

### Example: Extract Specific Fields

```python
import requests

API_URL = "http://localhost:8000"
vin = "1HGBH41JXMN109186"

response = requests.get(f"{API_URL}/decode/{vin}")
data = response.json()

# Extract specific fields
vehicle_info = {}
for item in data['data']:
    vehicle_info[item['variable']] = item['value']

# Access specific attributes
print(f"Make: {vehicle_info.get('Make')}")
print(f"Model: {vehicle_info.get('Model')}")
print(f"Year: {vehicle_info.get('Model Year')}")
print(f"Body Class: {vehicle_info.get('Body Class')}")
```

## Architecture

### Runtime Architecture
```
┌─────────────────────┐
│  Jupyter Notebook   │
│   (Client)          │
└──────────┬──────────┘
           │ HTTP
           ▼
┌─────────────────────┐
│   FastAPI           │
│   REST API          │
│   (Port 8000)       │
└──────────┬──────────┘
           │ SQL
           ▼
┌─────────────────────┐
│   PostgreSQL 17     │
│   vPIC Database     │
│   (Port 5432)       │
└─────────────────────┘
```

### Initialization Flow (First Run Only)
```
docker-compose up
       │
       ├──> postgres (starts)
       │         │
       │         └──> Health check passes
       │                    │
       ├──> db-init ────────┘
       │      │
       │      ├──> Download vPIC database
       │      ├──> Extract backup
       │      ├──> Restore to PostgreSQL
       │      ├──> Test VIN decode
       │      └──> Create .db_restored flag
       │
       └──> vin-api (starts after db-init completes)
```

## Project Structure

```
services/vin-api/
├── docker-compose.yml          # Docker services configuration
├── Dockerfile                  # API container definition
├── requirements.txt            # Python dependencies
├── init-db.sh                  # Automatic database initialization (used by Docker)
├── setup-database.sh           # Manual database setup script (Linux/Mac)
├── setup-database.bat          # Manual database setup script (Windows)
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── README.md                   # This file
├── QUICKSTART.md               # Quick start guide
├── example-usage.ipynb         # Jupyter usage examples
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration settings
│   ├── database.py             # Database connection handling
│   └── models.py               # Pydantic models
└── backups/                    # Database backup files (auto-created)
    └── .db_restored            # Flag file indicating DB is initialized
```

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and modify if needed:

```bash
cp .env.example .env
```

**Available variables:**
- `DATABASE_URL`: PostgreSQL connection string
- `API_HOST`: API host (default: 0.0.0.0)
- `API_PORT`: API port (default: 8000)

### Database Connection

**From host machine:**
```bash
psql -h localhost -p 5432 -U vpic_user -d vpic
# Password: vpic_password
```

**Test VIN decode in PostgreSQL:**
```sql
SELECT * FROM vpic.spVinDecode('1HGBH41JXMN109186');
```

## Management Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# API only
docker-compose logs -f vin-api

# Database only
docker-compose logs -f postgres

# Database initialization (first run)
docker-compose logs -f db-init
```

### Restart Services
```bash
docker-compose restart
```

### Force Database Re-initialization
```bash
# Remove the restore flag and cached files
rm -rf backups/.db_restored backups/vPICList_lite_2026_01.*

# Restart to trigger re-initialization
docker-compose down
docker-compose up -d
```

### Remove All Data (including database)
```bash
docker-compose down -v
rm -rf backups/
```

## Troubleshooting

### Port Already in Use

If ports 5432 or 8000 are already in use, modify `docker-compose.yml`:

```yaml
ports:
  - "5433:5432"  # Change 5432 to 5433
  # or
  - "8001:8000"  # Change 8000 to 8001
```

### Database Connection Errors

1. Check if PostgreSQL is running:
```bash
docker ps | grep vpic-postgres
```

2. Check PostgreSQL logs:
```bash
docker-compose logs postgres
```

3. Test connection:
```bash
docker exec vpic-postgres pg_isready -U vpic_user -d vpic
```

### API Not Responding

1. Check if API container is running:
```bash
docker ps | grep vin-api
```

2. Check API logs:
```bash
docker-compose logs vin-api
```

3. Restart the API:
```bash
docker-compose restart vin-api
```

## Database Information

- **Source**: NHTSA vPIC (Vehicle Product Information Catalog)
- **Version**: January 2026 (vPICList_lite_2026_01)
- **PostgreSQL Version**: 17
- **Schema**: `vpic` and `vpiclist_lite`
- **Main Function**: `vpic.spVinDecode(vin_text)`
- **Update Frequency**: Monthly (check https://vpic.nhtsa.dot.gov/downloads/)

## Limitations

- **VIN Decoding Only**: This database is limited to VIN decoding functionality
- **No Make/Model Lookups**: For other queries (makes, models, variables), use the vPIC web API
- **17-Character VINs**: Only standard 17-character VINs are supported
- **US Vehicles**: Primarily focused on vehicles sold in the United States

## Performance

- **Database Size**: ~66.6 MB (compressed), ~200 MB (uncompressed)
- **VIN Decode Speed**: < 100ms per request
- **Concurrent Requests**: Supports multiple simultaneous requests
- **Caching**: No built-in caching (can be added with Redis if needed)

## Security Notes

⚠️ **This is a development setup. For production use:**

1. Change default passwords in `docker-compose.yml`
2. Use environment variables for sensitive data
3. Enable SSL/TLS for API endpoints
4. Restrict CORS origins in `main.py`
5. Add authentication/authorization
6. Use a reverse proxy (nginx, traefik)
7. Implement rate limiting

## License

This API wrapper is provided as-is for educational and research purposes. The NHTSA vPIC database is public domain.

## Resources

- **NHTSA vPIC API**: https://vpic.nhtsa.dot.gov/api/
- **Database Downloads**: https://vpic.nhtsa.dot.gov/downloads/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/

## Support

For issues related to:
- **This API wrapper**: Check logs and troubleshooting section
- **NHTSA vPIC data**: Contact NHTSA or check their FAQ
- **Docker issues**: Refer to Docker documentation

---

**Built with FastAPI and PostgreSQL** | **Powered by NHTSA vPIC Data**
