#!/usr/bin/env python3
"""
VIN Enrichment Script - Direct PostgreSQL version
Bypasses the HTTP API and calls vpic.spvindecode() directly via psycopg2.

Each VIN is decoded in its own transaction to avoid exhausting PostgreSQL's
max_locks_per_transaction (spvindecode creates several temp tables per call).
Parallelism comes from a thread pool of DB connections.

Enriches vehicles.csv rows that are missing make/model/year, and also captures
Base Price ($) and Transmission Style where available.

Usage:
    python enrich_vehicles_pg.py
    python enrich_vehicles_pg.py --dsn postgresql://user:pass@host:5432/vpic
    python enrich_vehicles_pg.py -i data/vehicles.csv -o data/vehicles_enriched.csv -n 1000
"""

import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

import pandas as pd
import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool


# --- Defaults (mirror the existing vin-api config) ---
DEFAULT_DSN  = "postgresql://vpic_user:vpic_password@localhost:5432/vpic"
INPUT_CSV    = "data/vehicles.csv"
OUTPUT_CSV   = "data/vehicles_enriched.csv"
MAX_WORKERS  = 8     # Parallel DB connections

# VPIC element names -> local column names
VPIC_FIELDS = {
    "Make":                "manufacturer",
    "Model":               "model",
    "Model Year":          "year",
    "Base Price ($)":      "base_price",
    "Transmission Style":  "transmission_style",
}

# Fields that only fill in gaps (skip if already populated)
FILL_IF_MISSING = {"manufacturer", "model", "year"}

# Fields that are always written (new columns not in original CSV)
ALWAYS_WRITE = {"base_price", "transmission_style"}

def decode_single(pool: ThreadedConnectionPool, vin: str) -> tuple[str, dict | None]:
    """
    Call spvindecode for one VIN in its own transaction.
    Returns (vin, result_dict) or (vin, None) on failure.
    Each call gets its own connection so temp table locks are released immediately.
    """
    conn = pool.getconn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    MAX(CASE WHEN variable = 'Make'               THEN value END)::varchar AS make,
                    MAX(CASE WHEN variable = 'Model'              THEN value END)::varchar AS model,
                    MAX(CASE WHEN variable = 'Model Year'         THEN value END)::varchar AS model_year,
                    MAX(CASE WHEN variable = 'Base Price ($)'     THEN value END)::varchar AS base_price,
                    MAX(CASE WHEN variable = 'Transmission Style' THEN value END)::varchar AS transmission_style
                FROM vpic.spvindecode(%s)
                """,
                (vin,),
            )
            row = cur.fetchone()
            if row and any(row.values()):
                return vin, {
                    "manufacturer":       row["make"]               or "",
                    "model":              row["model"]              or "",
                    "year":               row["model_year"]         or "",
                    "base_price":         row["base_price"]         or "",
                    "transmission_style": row["transmission_style"] or "",
                }
            return vin, None
    except Exception:
        conn.rollback()
        raise
    finally:
        pool.putconn(conn)


def is_missing_core_data(row: pd.Series) -> bool:
    """True if any of make / model / year is blank."""
    return (
        pd.isna(row.get("year"))         or str(row.get("year",         "")).strip() == "" or
        pd.isna(row.get("manufacturer")) or str(row.get("manufacturer", "")).strip() == "" or
        pd.isna(row.get("model"))        or str(row.get("model",        "")).strip() == ""
    )


def enrich_vehicles(
    input_file: str,
    output_file: str,
    dsn: str,
    max_rows: Optional[int] = None,
    workers: int = MAX_WORKERS,
) -> None:
    input_path  = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        print(f"Input file not found: {input_file}")
        sys.exit(1)

    # ------------------------------------------------------------------ load
    print(f"Loading {input_path} ...")
    df = pd.read_csv(input_path, dtype=str, low_memory=False)

    if max_rows:
        df = df.head(max_rows)
        print(f"Limited to first {max_rows:,} rows")

    total_rows = len(df)

    if "VIN" not in df.columns:
        print("VIN column not found in CSV")
        sys.exit(1)

    # Ensure new output columns exist
    for col in ALWAYS_WRITE:
        if col not in df.columns:
            df[col] = ""

    # --------------------------------------------------------- identify work
    df["_valid_vin"]    = df["VIN"].apply(lambda x: pd.notna(x) and len(str(x).strip()) == 17)
    df["_needs_enrich"] = df.apply(
        lambda r: bool(r["_valid_vin"]) and is_missing_core_data(r), axis=1
    )

    to_enrich = df[df["_needs_enrich"]]
    unique_vins = list({str(r).strip() for r in to_enrich["VIN"]})

    print(f"Rows total:          {total_rows:,}")
    print(f"Rows to enrich:      {len(to_enrich):,}")
    print(f"Unique VINs:         {len(unique_vins):,}")

    if not unique_vins:
        print("Nothing to enrich. All rows have make/model/year populated.")
        df.drop(columns=["_valid_vin", "_needs_enrich"]).to_csv(output_path, index=False)
        print(f"Output saved to: {output_path}")
        return

    print(f"Workers:             {workers}")
    print()

    # ---------------------------------------------------------- decode (parallel)
    # One connection per worker; each VIN decoded in its own transaction so
    # temp-table locks are released after every call.
    pool: ThreadedConnectionPool = ThreadedConnectionPool(
        minconn=2, maxconn=workers, dsn=dsn
    )
    decoded: dict[str, dict] = {}
    completed_vins = 0

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(decode_single, pool, vin): vin for vin in unique_vins}
        for future in as_completed(futures):
            vin = futures[future]
            try:
                _, result = future.result()
                if result:
                    decoded[vin] = result
            except Exception as exc:
                print(f"\n  Error decoding {vin}: {exc}", file=sys.stderr)
            completed_vins += 1
            pct = completed_vins / len(unique_vins) * 100
            print(f"  {completed_vins:>7,}/{len(unique_vins):,} VINs decoded ({pct:.1f}%)...", end="\r")

    pool.closeall()
    print(f"\nDecode complete: {len(decoded):,} VINs resolved.")

    # --------------------------------------------------------- apply to df
    successful = 0
    for idx, row in to_enrich.iterrows():
        vin    = str(row["VIN"]).strip()
        result = decoded.get(vin)
        if not result:
            continue

        # Fill-if-missing fields
        for col in FILL_IF_MISSING:
            if result.get(col) and (pd.isna(df.at[idx, col]) or str(df.at[idx, col]).strip() == ""):
                df.at[idx, col] = result[col]

        # Always-write fields (new columns)
        for col in ALWAYS_WRITE:
            if result.get(col):
                df.at[idx, col] = result[col]

        successful += 1

    df.drop(columns=["_valid_vin", "_needs_enrich"], inplace=True)

    # ------------------------------------------------------------------ save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)

    print()
    print("=" * 55)
    print("Enrichment complete")
    print("=" * 55)
    print(f"Total rows:          {total_rows:,}")
    print(f"Rows enriched:       {successful:,}")
    print(f"Output:              {output_path}")
    if len(to_enrich) > 0:
        print(f"Success rate:        {successful / len(to_enrich) * 100:.1f}%")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Enrich vehicles.csv via direct PostgreSQL connection to the vpic database."
    )
    parser.add_argument("-i", "--input",      default=INPUT_CSV,   help=f"Input CSV  (default: {INPUT_CSV})")
    parser.add_argument("-o", "--output",     default=OUTPUT_CSV,  help=f"Output CSV (default: {OUTPUT_CSV})")
    parser.add_argument("-n", "--max-rows",   type=int, default=None, help="Limit rows processed (default: all)")
    parser.add_argument("--dsn",              default=DEFAULT_DSN,
                        help="PostgreSQL DSN (default: %(default)s)")
    parser.add_argument("--workers",          type=int, default=MAX_WORKERS,
                        help=f"Parallel DB connections (default: {MAX_WORKERS})")
    args = parser.parse_args()

    # Test connection
    print(f"Connecting to: {args.dsn}")
    try:
        conn = psycopg2.connect(args.dsn)
        conn.close()
        print("DB connection OK")
    except Exception as exc:
        print(f"Cannot connect to DB: {exc}")
        sys.exit(1)

    print()
    enrich_vehicles(args.input, args.output, args.dsn, args.max_rows, args.workers)


if __name__ == "__main__":
    main()
