# VIN Enrichment Guide

This guide explains how to use the VIN enrichment script to populate vehicle data (Make, Model, Year) from VINs using the NHTSA vPIC API.

## Prerequisites

1. **VIN API Running**: Make sure the VIN API service is running:
   ```bash
   cd services/vin-api
   docker-compose up -d
   ```

2. **Python 3.7+**: Ensure Python is installed with the `requests` library:
   ```bash
   pip install requests
   ```

## Quick Start

### Process First 100 Rows (Test)
```bash
python enrich_vehicles.py -n 100
```

### Process Entire CSV
```bash
python enrich_vehicles.py
```

**Note**: On Windows, you may need to set encoding:
```bash
set PYTHONIOENCODING=utf-8
python enrich_vehicles.py
```

## Usage

### Basic Usage
```bash
python enrich_vehicles.py [options]
```

### Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `-i, --input` | `data/vehicles.csv` | Input CSV file path |
| `-o, --output` | `data/vehicles_enriched.csv` | Output CSV file path |
| `-n, --max-rows` | All rows | Maximum number of rows to process |
| `--api-url` | `http://localhost:8000` | VIN API base URL |

### Examples

**Process first 50 rows:**
```bash
python enrich_vehicles.py -n 50
```

**Custom input/output files:**
```bash
python enrich_vehicles.py -i data/my_vehicles.csv -o data/output.csv
```

**Use different API URL:**
```bash
python enrich_vehicles.py --api-url http://localhost:9000
```

## How It Works

The script:

1. **Reads the CSV**: Opens the input CSV file
2. **Finds VINs**: Looks for 17-character VINs in the `VIN` column
3. **Calls API**: For each VIN, calls the vPIC API to decode vehicle information
4. **Extracts Data**: Parses the JSON response to extract:
   - **Make** (from `variable: "Make"`)
   - **Model** (from `variable: "Model"`)
   - **Year** (from `variable: "Model Year"`)
5. **Updates CSV**: Populates the `manufacturer`, `model`, and `year` columns
6. **Writes Output**: Saves the enriched data to a new CSV file

## Data Handling

- **Empty Fields Only**: Only populates fields that are empty or blank
- **Preserves Existing**: Does not overwrite existing data
- **VIN Validation**: Only processes valid 17-character VINs
- **Error Handling**: Continues processing even if some VINs fail to decode

## Output

### Console Output

```
🔍 Testing API connection...
✓ API Status: healthy
✓ Database: connected

📖 Reading from: data\vehicles.csv
📝 Writing to: data\vehicles_enriched.csv

  ✓ 3GTP1VEC4EG551563: 2014 GMC Sierra
  ✓ 1GCSCSE06AZ123805: 2010 CHEVROLET Silverado
⏳ Processed 10 VINs (9 successful, 0 failed)...
...

============================================================
📊 Enrichment Complete!
============================================================
Total rows processed:    101
Rows with VIN:           62
Successful decodes:      62
Failed decodes:          0
Rows skipped (no VIN):   38

✓ Output saved to: data\vehicles_enriched.csv
✓ Success rate: 100.0%
```

### CSV Output

The output CSV has the same structure as the input, with these columns populated from the API:

- `year` - Model year (e.g., "2014")
- `manufacturer` - Vehicle make (e.g., "GMC")
- `model` - Vehicle model (e.g., "Sierra")

## Performance

- **Rate Limiting**: 0.1 second delay between API calls (10 requests/second)
- **Processing Speed**: ~600 VINs per minute
- **Large Datasets**: For 100,000 rows with ~50,000 VINs:
  - Estimated time: ~83 minutes
  - Recommended: Process in batches using `-n` option

## Troubleshooting

### API Connection Error

```
✗ Cannot connect to API: Connection refused
```

**Solution**: Start the VIN API service:
```bash
cd services/vin-api
docker-compose up -d
```

### No VINs Found

```
Rows with VIN:           0
```

**Solution**:
- Check that your CSV has a `VIN` column
- Verify VINs are 17 characters long
- Use `-n` with a larger number to process more rows

### Unicode Encoding Error (Windows)

```
UnicodeEncodeError: 'charmap' codec can't encode character
```

**Solution**: Set UTF-8 encoding:
```bash
set PYTHONIOENCODING=utf-8
python enrich_vehicles.py
```

### Failed Decodes

If some VINs fail to decode:
- The VIN may be invalid or malformed
- The vehicle may not be in the vPIC database
- The API may have encountered an error

The script will continue processing and report statistics at the end.

## Integration with Jupyter

You can also use this as a library in your Jupyter notebook:

```python
from enrich_vehicles import decode_vin

# Decode a single VIN
result = decode_vin("1HGBH41JXMN109186")
print(result)
# {'make': 'HONDA', 'model': 'Accord', 'year': '1991'}

# Or process a DataFrame
import pandas as pd

df = pd.read_csv('data/vehicles.csv')

for idx, row in df.iterrows():
    if pd.notna(row['VIN']) and len(row['VIN']) == 17:
        decoded = decode_vin(row['VIN'])
        if decoded:
            df.at[idx, 'year'] = decoded['year']
            df.at[idx, 'manufacturer'] = decoded['make']
            df.at[idx, 'model'] = decoded['model']

df.to_csv('data/vehicles_enriched.csv', index=False)
```

## Additional Resources

- **API Documentation**: See [services/vin-api/README.md](services/vin-api/README.md)
- **API Interactive Docs**: http://localhost:8000/docs
- **Example Usage**: See [services/vin-api/example-usage.ipynb](services/vin-api/example-usage.ipynb)

## Support

For issues or questions:
1. Check the API is running: `curl http://localhost:8000/health`
2. View API logs: `cd services/vin-api && docker-compose logs -f`
3. Review the troubleshooting section above

---

**Happy Enriching! 🚗**
