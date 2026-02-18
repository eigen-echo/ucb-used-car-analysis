#!/usr/bin/env python3
"""
VIN Enrichment Script
Reads vehicles.csv, decodes VINs using the vPIC API, and updates vehicle information.
"""

import csv
import requests
import sys
from typing import Optional, Dict
from pathlib import Path
import time


# Configuration
API_URL = "http://localhost:8000"
INPUT_CSV = "../../data/vehicles.csv"
OUTPUT_CSV = "../../data/vehicles_enriched.csv"
BATCH_SIZE = 100  # Process in batches
RATE_LIMIT_DELAY = 0.1  # Seconds between API calls


def decode_vin(vin: str) -> Optional[Dict[str, str]]:
    """
    Decode a VIN using the vPIC API.

    Args:
        vin: 17-character Vehicle Identification Number

    Returns:
        Dictionary with make, model, and year, or None if failed
    """
    if not vin or len(vin) != 17:
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

        print(f"  ✗ No data found for {vin}", file=sys.stderr)
        return None

    except requests.exceptions.RequestException as e:
        print(f"  ✗ API error for {vin}: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ✗ Unexpected error for {vin}: {e}", file=sys.stderr)
        return None


def enrich_vehicles(input_file: str, output_file: str, max_rows: Optional[int] = None):
    """
    Read vehicles CSV, decode VINs, and write enriched data.

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

    # Statistics
    total_rows = 0
    rows_with_vin = 0
    successful_decodes = 0
    failed_decodes = 0
    skipped_rows = 0

    with open(input_path, 'r', encoding='utf-8') as infile, \
         open(output_path, 'w', encoding='utf-8', newline='') as outfile:

        reader = csv.DictReader(infile)

        # Ensure output has the same fields
        fieldnames = reader.fieldnames
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        # Find the VIN column index
        if 'VIN' not in fieldnames:
            print("✗ VIN column not found in CSV")
            sys.exit(1)

        # Process rows
        for row in reader:
            total_rows += 1

            # Check if we've hit the max rows limit
            if max_rows and total_rows > max_rows:
                print(f"\n⚠ Reached max_rows limit ({max_rows}), stopping...")
                break

            vin = row.get('VIN', '').strip()

            # Skip if no VIN
            if not vin or len(vin) != 17:
                writer.writerow(row)
                skipped_rows += 1
                continue

            rows_with_vin += 1

            # Progress indicator
            if rows_with_vin % 10 == 0:
                print(f"⏳ Processed {rows_with_vin} VINs ({successful_decodes} successful, {failed_decodes} failed)...")

            # Decode VIN
            decoded = decode_vin(vin)

            if decoded:
                # Update row with decoded data
                # Only update if the field is empty or we want to override
                if not row.get('year') or row['year'].strip() == '':
                    row['year'] = decoded['year']
                if not row.get('manufacturer') or row['manufacturer'].strip() == '':
                    row['manufacturer'] = decoded['make']
                if not row.get('model') or row['model'].strip() == '':
                    row['model'] = decoded['model']

                successful_decodes += 1
                print(f"  ✓ {vin}: {decoded['year']} {decoded['make']} {decoded['model']}")
            else:
                failed_decodes += 1

            # Write the row (updated or original)
            writer.writerow(row)

            # Rate limiting
            time.sleep(RATE_LIMIT_DELAY)

    # Final statistics
    print()
    print("=" * 60)
    print("📊 Enrichment Complete!")
    print("=" * 60)
    print(f"Total rows processed:    {total_rows:,}")
    print(f"Rows with VIN:           {rows_with_vin:,}")
    print(f"Successful decodes:      {successful_decodes:,}")
    print(f"Failed decodes:          {failed_decodes:,}")
    print(f"Rows skipped (no VIN):   {skipped_rows:,}")
    print()
    print(f"✓ Output saved to: {output_path}")

    if successful_decodes > 0:
        success_rate = (successful_decodes / rows_with_vin * 100) if rows_with_vin > 0 else 0
        print(f"✓ Success rate: {success_rate:.1f}%")


def main():
    """Main entry point."""
    global API_URL

    import argparse

    parser = argparse.ArgumentParser(
        description="Enrich vehicles.csv with VIN decode data from vPIC API"
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
