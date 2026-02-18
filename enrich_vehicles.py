#!/usr/bin/env python3
"""
VIN Enrichment Script
Reads vehicles.csv, decodes VINs using the vPIC API, and updates vehicle information.
Only processes rows where make, model, or year is missing.
"""

import pandas as pd
import requests
import sys
from typing import Optional, Dict
from pathlib import Path
import time


# Configuration
API_URL = "http://localhost:8000"
INPUT_CSV = "data/vehicles.csv"
OUTPUT_CSV = "data/vehicles_enriched.csv"
RATE_LIMIT_DELAY = 0.1  # Seconds between API calls


def decode_vin(vin: str) -> Optional[Dict[str, str]]:
    """
    Decode a VIN using the vPIC API.

    Args:
        vin: 17-character Vehicle Identification Number

    Returns:
        Dictionary with make, model, and year, or None if failed
    """
    if not vin or len(str(vin)) != 17:
        return None

    try:
        response = requests.get(f"{API_URL}/decode/{vin}", timeout=10)

        if response.status_code != 200:
            print(f"  ✗ Failed to decode {vin}: HTTP {response.status_code}", file=sys.stderr)
            return None

        data = response.json()

        # Extract make, model, and year from the response
        result = {
            'make': '',
            'model': '',
            'year': ''
        }

        for item in data.get('data', []):
            variable = item.get('variable', '')
            value = item.get('value', '')

            if variable == 'Make':
                result['make'] = value
            elif variable == 'Model':
                result['model'] = value
            elif variable == 'Model Year':
                result['year'] = value

        # Only return if we got at least some data
        if result['make'] or result['model'] or result['year']:
            return result

        print(f"  ⚠ No data found for {vin}", file=sys.stderr)
        return None

    except requests.exceptions.RequestException as e:
        print(f"  ✗ API error for {vin}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ✗ Unexpected error for {vin}: {e}", file=sys.stderr)
        return None


def is_missing_data(row: pd.Series) -> bool:
    """
    Check if a row is missing year, manufacturer, or model data.

    Args:
        row: DataFrame row

    Returns:
        True if any of the fields is missing
    """
    return (
        pd.isna(row.get('year')) or str(row.get('year', '')).strip() == '' or
        pd.isna(row.get('manufacturer')) or str(row.get('manufacturer', '')).strip() == '' or
        pd.isna(row.get('model')) or str(row.get('model', '')).strip() == ''
    )


def enrich_vehicles(input_file: str, output_file: str, max_rows: Optional[int] = None):
    """
    Read vehicles CSV, decode VINs with missing data, and write enriched data.

    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV
        max_rows: Maximum number of rows to process (None for all)
    """
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"✗ Input file not found: {input_file}")
        sys.exit(1)

    print(f"📖 Reading from: {input_path}")
    print(f"📝 Writing to: {output_path}")
    print()

    # Read CSV into DataFrame
    print("⏳ Loading CSV into DataFrame...")
    df = pd.read_csv(input_path, dtype=str, low_memory=False)

    if max_rows:
        df = df.head(max_rows)
        print(f"⚠ Limited to first {max_rows} rows")

    total_rows = len(df)
    print(f"✓ Loaded {total_rows:,} rows")
    print()

    # Check for VIN column
    if 'VIN' not in df.columns:
        print("✗ VIN column not found in CSV")
        sys.exit(1)

    # Find rows that need enrichment (have VIN but missing data)
    df['_has_valid_vin'] = df['VIN'].apply(lambda x: pd.notna(x) and len(str(x).strip()) == 17)
    df['_needs_enrichment'] = df.apply(lambda row: row['_has_valid_vin'] and is_missing_data(row), axis=1)

    rows_to_process = df[df['_needs_enrichment']].copy()
    rows_with_vin = df['_has_valid_vin'].sum()
    rows_needing_enrichment = len(rows_to_process)

    print("📊 Data Analysis:")
    print(f"  Total rows:                {total_rows:,}")
    print(f"  Rows with valid VIN:       {rows_with_vin:,}")
    print(f"  Rows needing enrichment:   {rows_needing_enrichment:,}")
    print(f"  Rows to skip (complete):   {rows_with_vin - rows_needing_enrichment:,}")
    print()

    if rows_needing_enrichment == 0:
        print("✓ No rows need enrichment. All data is complete!")
        # Still save the output
        df.drop(columns=['_has_valid_vin', '_needs_enrichment'], inplace=True)
        df.to_csv(output_path, index=False)
        print(f"✓ Output saved to: {output_path}")
        return

    # Statistics
    successful_decodes = 0
    failed_decodes = 0
    processed = 0

    print("🔄 Processing VINs with missing data...")
    print()

    # Process each row that needs enrichment
    for idx, row in rows_to_process.iterrows():
        vin = str(row['VIN']).strip()
        processed += 1

        # Progress indicator
        if processed % 10 == 0:
            print(f"⏳ Processed {processed}/{rows_needing_enrichment} VINs ({successful_decodes} successful, {failed_decodes} failed)...")

        # Decode VIN
        decoded = decode_vin(vin)

        if decoded:
            # Update only missing fields
            if pd.isna(row['year']) or str(row['year']).strip() == '':
                df.at[idx, 'year'] = decoded['year']
            if pd.isna(row['manufacturer']) or str(row['manufacturer']).strip() == '':
                df.at[idx, 'manufacturer'] = decoded['make']
            if pd.isna(row['model']) or str(row['model']).strip() == '':
                df.at[idx, 'model'] = decoded['model']

            successful_decodes += 1
            print(f"  ✓ {vin}: {decoded['year']} {decoded['make']} {decoded['model']}")
        else:
            failed_decodes += 1

        # Rate limiting
        time.sleep(RATE_LIMIT_DELAY)

    # Remove helper columns
    df.drop(columns=['_has_valid_vin', '_needs_enrichment'], inplace=True)

    # Save enriched DataFrame
    print()
    print("💾 Saving enriched data...")
    df.to_csv(output_path, index=False)

    # Final statistics
    print()
    print("=" * 60)
    print("📊 Enrichment Complete!")
    print("=" * 60)
    print(f"Total rows:                  {total_rows:,}")
    print(f"Rows with VIN:               {rows_with_vin:,}")
    print(f"Rows needing enrichment:     {rows_needing_enrichment:,}")
    print(f"Successful decodes:          {successful_decodes:,}")
    print(f"Failed decodes:              {failed_decodes:,}")
    print()
    print(f"✓ Output saved to: {output_path}")

    if successful_decodes > 0 and rows_needing_enrichment > 0:
        success_rate = (successful_decodes / rows_needing_enrichment * 100)
        print(f"✓ Success rate: {success_rate:.1f}%")


def main():
    """Main entry point."""
    global API_URL

    import argparse

    parser = argparse.ArgumentParser(
        description="Enrich vehicles.csv with VIN decode data from vPIC API (only for rows with missing data)"
    )
    parser.add_argument(
        '-i', '--input',
        default=INPUT_CSV,
        help=f"Input CSV file (default: {INPUT_CSV})"
    )
    parser.add_argument(
        '-o', '--output',
        default=OUTPUT_CSV,
        help=f"Output CSV file (default: {OUTPUT_CSV})"
    )
    parser.add_argument(
        '-n', '--max-rows',
        type=int,
        default=None,
        help="Maximum number of rows to process (default: all)"
    )
    parser.add_argument(
        '--api-url',
        default=API_URL,
        help=f"API base URL (default: {API_URL})"
    )

    args = parser.parse_args()

    # Update API_URL if specified
    API_URL = args.api_url

    # Test API connection
    print("🔍 Testing API connection...")
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✓ API Status: {health.get('status')}")
            print(f"✓ Database: {health.get('database')}")
            print()
        else:
            print(f"✗ API returned status {response.status_code}")
            print("  Make sure the API is running: cd services/vin-api && docker-compose up -d")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Cannot connect to API: {e}")
        print("  Make sure the API is running: cd services/vin-api && docker-compose up -d")
        sys.exit(1)

    # Run enrichment
    enrich_vehicles(args.input, args.output, args.max_rows)


if __name__ == "__main__":
    main()
