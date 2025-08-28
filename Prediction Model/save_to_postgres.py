import os
import json
import argparse
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_batch


def get_db_connection():
    """Create a Postgres connection from environment variables."""
    host = os.getenv("PGHOST", "localhost")
    port = int(os.getenv("PGPORT", "5432"))
    dbname = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")

    missing = [k for k, v in {
        "PGDATABASE": dbname,
        "PGUSER": user,
        "PGPASSWORD": password,
    }.items() if not v]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

    return psycopg2.connect(
        host=host,
        port=port,
        dbname=dbname,
        user=user,
        password=password,
    )


def ensure_tables(cur, schema: str | None = None):
    """Create/prepare tables and indexes for business-aware upserts.

    - Ensure tables exist
    - Ensure business_id column exists
    - Ensure unique index on (business_id, date) to support ON CONFLICT
    """
    schema_prefix = f'"{schema}".' if schema else ""

    # Create base tables if missing (legacy minimal schema)
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema_prefix}"input_sales" (
            date DATE,
            sales NUMERIC NOT NULL
        );
    """)

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema_prefix}"forecast_sales" (
            date DATE,
            predicted_sales NUMERIC NOT NULL,
            lower_bound NUMERIC NOT NULL,
            upper_bound NUMERIC NOT NULL,
            generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
    """)

    # Add business_id column if not exists (kept nullable for backward compatibility)
    cur.execute(f"ALTER TABLE {schema_prefix}\"input_sales\" ADD COLUMN IF NOT EXISTS business_id TEXT;")
    cur.execute(f"ALTER TABLE {schema_prefix}\"forecast_sales\" ADD COLUMN IF NOT EXISTS business_id TEXT;")

    # Create unique indexes to support ON CONFLICT (business_id, date)
    cur.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS input_sales_business_date_idx
        ON {schema_prefix}"input_sales" (business_id, date)
    """)
    cur.execute(f"""
        CREATE UNIQUE INDEX IF NOT EXISTS forecast_sales_business_date_idx
        ON {schema_prefix}"forecast_sales" (business_id, date)
    """)


def load_json_records(path: str):
    """Load a JSON file and return a list of records (dicts)."""
    with open(path, "r") as f:
        data = json.load(f)

    # Accept either list of records or an object with a single key
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # Try common container key
        for key in ("sales_data", "data", "records", "items"):
            if key in data and isinstance(data[key], list):
                return data[key]
        # Fallback: wrap dict as one record
        return [data]
    raise ValueError(f"Unsupported JSON structure in {path}")


def normalize_input_records(records, default_business_id: str | None = None):
    """Map input JSON to (business_id, date, sales)."""
    normalized = []
    for rec in records:
        # Keys
        date_key = next((k for k in rec.keys() if "date" in k.lower() or "week" in k.lower()), None)
        sales_key = next((k for k in rec.keys() if "sales" in k.lower() or "revenue" in k.lower()), None)
        biz_id = rec.get("business_id") or default_business_id
        if not date_key or not sales_key or not biz_id:
            continue
        date_str = str(rec[date_key])
        sales_val = rec[sales_key]
        normalized.append((biz_id, date_str, sales_val))
    return normalized


def normalize_forecast_records(records, default_business_id: str | None = None):
    """Map forecast JSON to (business_id, date, predicted_sales, lower_bound, upper_bound)."""
    normalized = []
    for rec in records:
        date_str = rec.get("date") or rec.get("ds")
        yhat = rec.get("predicted_sales") or rec.get("yhat")
        lb = rec.get("lower_bound") or rec.get("yhat_lower")
        ub = rec.get("upper_bound") or rec.get("yhat_upper")
        biz_id = rec.get("business_id") or default_business_id
        if biz_id is None or date_str is None or yhat is None or lb is None or ub is None:
            continue
        normalized.append((biz_id, date_str, yhat, lb, ub))
    return normalized


def purge_business_data(cur, business_ids: list[str], schema: str | None = None):
    """Delete existing rows for given business_ids from both tables."""
    if not business_ids:
        return
    schema_prefix = f'"{schema}".' if schema else ""
    # Use IN with unique ids
    cur.execute(
        f"DELETE FROM {schema_prefix}\"forecast_sales\" WHERE business_id = ANY(%s)",
        (business_ids,)
    )
    cur.execute(
        f"DELETE FROM {schema_prefix}\"input_sales\" WHERE business_id = ANY(%s)",
        (business_ids,)
    )


def upsert_input_sales(cur, rows, schema: str | None = None):
    schema_prefix = f'"{schema}".' if schema else ""
    sql = f"""
        INSERT INTO {schema_prefix}"input_sales" (business_id, date, sales)
        VALUES (%s, %s::date, %s)
        ON CONFLICT (business_id, date) DO UPDATE SET
            sales = EXCLUDED.sales
    """
    execute_batch(cur, sql, rows, page_size=1000)


def upsert_forecast_sales(cur, rows, schema: str | None = None, generated_at: datetime | None = None):
    schema_prefix = f'"{schema}".' if schema else ""
    # Include generated_at if provided; otherwise default will be used
    if generated_at is None:
        sql = f"""
            INSERT INTO {schema_prefix}"forecast_sales" (business_id, date, predicted_sales, lower_bound, upper_bound)
            VALUES (%s, %s::date, %s, %s, %s)
            ON CONFLICT (business_id, date) DO UPDATE SET
                predicted_sales = EXCLUDED.predicted_sales,
                lower_bound = EXCLUDED.lower_bound,
                upper_bound = EXCLUDED.upper_bound,
                generated_at = NOW()
        """
        params = rows
    else:
        sql = f"""
            INSERT INTO {schema_prefix}"forecast_sales" (business_id, date, predicted_sales, lower_bound, upper_bound, generated_at)
            VALUES (%s, %s::date, %s, %s, %s, %s)
            ON CONFLICT (business_id, date) DO UPDATE SET
                predicted_sales = EXCLUDED.predicted_sales,
                lower_bound = EXCLUDED.lower_bound,
                upper_bound = EXCLUDED.upper_bound,
                generated_at = EXCLUDED.generated_at
        """
        params = [(*r, generated_at) for r in rows]
    execute_batch(cur, sql, params, page_size=1000)


def main():
    parser = argparse.ArgumentParser(description="Load input and forecast JSONs into Postgres")
    parser.add_argument("--input-json", default="weekly_sales_data.json", help="Path to input JSON (historical)")
    parser.add_argument("--forecast-json", default=os.path.join("output", "sales_forecast.json"), help="Path to forecast JSON")
    parser.add_argument("--schema", default=None, help="Optional Postgres schema name")
    parser.add_argument("--business-id", dest="business_id", default=None, help="Optional business_id fallback/override for rows without it")
    args = parser.parse_args()

    # Resolve to absolute paths for clarity
    input_path = os.path.abspath(args.input_json)
    forecast_path = os.path.abspath(args.forecast_json)

    input_records = load_json_records(input_path)
    forecast_records = load_json_records(forecast_path)

    input_rows = normalize_input_records(input_records, default_business_id=args.business_id)
    forecast_rows = normalize_forecast_records(forecast_records, default_business_id=args.business_id)

    if not input_rows:
        raise RuntimeError("No valid input rows parsed from input JSON (ensure business_id/date/sales present or pass --business-id)")
    if not forecast_rows:
        raise RuntimeError("No valid forecast rows parsed from forecast JSON (ensure business_id/date/prediction keys or pass --business-id)")

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                ensure_tables(cur, schema=args.schema)
                # Determine target business_ids to purge
                biz_ids = sorted({r[0] for r in input_rows} | {r[0] for r in forecast_rows})
                purge_business_data(cur, biz_ids, schema=args.schema)
                upsert_input_sales(cur, input_rows, schema=args.schema)
                upsert_forecast_sales(cur, forecast_rows, schema=args.schema)
        print(f"Purged and loaded business_ids={biz_ids}; input rows={len(input_rows)}, forecast rows={len(forecast_rows)}")
    finally:
        conn.close()


if __name__ == "__main__":
    main() 