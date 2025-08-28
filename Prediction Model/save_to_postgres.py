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
    """Create tables if they do not exist and ensure unique constraints for upserts."""
    schema_prefix = f'"{schema}".' if schema else ""

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema_prefix}"input_sales" (
            date DATE PRIMARY KEY,
            sales NUMERIC NOT NULL
        );
    """)

    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema_prefix}"forecast_sales" (
            date DATE PRIMARY KEY,
            predicted_sales NUMERIC NOT NULL,
            lower_bound NUMERIC NOT NULL,
            upper_bound NUMERIC NOT NULL,
            generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
        );
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


def normalize_input_records(records):
    """Map input JSON to (date, sales)."""
    normalized = []
    for rec in records:
        # Find date-like and sales-like keys
        date_key = next((k for k in rec.keys() if "date" in k.lower() or "week" in k.lower()), None)
        sales_key = next((k for k in rec.keys() if "sales" in k.lower() or "revenue" in k.lower()), None)
        if not date_key or not sales_key:
            continue
        date_str = str(rec[date_key])
        sales_val = rec[sales_key]
        normalized.append((date_str, sales_val))
    return normalized


def normalize_forecast_records(records):
    """Map forecast JSON to (date, predicted_sales, lower_bound, upper_bound)."""
    normalized = []
    for rec in records:
        # forecast.py exports keys: date, predicted_sales, lower_bound, upper_bound
        date_str = rec.get("date") or rec.get("ds")
        yhat = rec.get("predicted_sales") or rec.get("yhat")
        lb = rec.get("lower_bound") or rec.get("yhat_lower")
        ub = rec.get("upper_bound") or rec.get("yhat_upper")
        if date_str is None or yhat is None or lb is None or ub is None:
            continue
        normalized.append((date_str, yhat, lb, ub))
    return normalized


def upsert_input_sales(cur, rows, schema: str | None = None):
    schema_prefix = f'"{schema}".' if schema else ""
    sql = f"""
        INSERT INTO {schema_prefix}"input_sales" (date, sales)
        VALUES (%s::date, %s)
        ON CONFLICT (date) DO UPDATE SET
            sales = EXCLUDED.sales
    """
    execute_batch(cur, sql, rows, page_size=1000)


def upsert_forecast_sales(cur, rows, schema: str | None = None, generated_at: datetime | None = None):
    schema_prefix = f'"{schema}".' if schema else ""
    # Include generated_at if provided; otherwise default will be used
    if generated_at is None:
        sql = f"""
            INSERT INTO {schema_prefix}"forecast_sales" (date, predicted_sales, lower_bound, upper_bound)
            VALUES (%s::date, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
                predicted_sales = EXCLUDED.predicted_sales,
                lower_bound = EXCLUDED.lower_bound,
                upper_bound = EXCLUDED.upper_bound,
                generated_at = NOW()
        """
        params = rows
    else:
        sql = f"""
            INSERT INTO {schema_prefix}"forecast_sales" (date, predicted_sales, lower_bound, upper_bound, generated_at)
            VALUES (%s::date, %s, %s, %s, %s)
            ON CONFLICT (date) DO UPDATE SET
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
    args = parser.parse_args()

    # Resolve to absolute paths for clarity
    input_path = os.path.abspath(args.input_json)
    forecast_path = os.path.abspath(args.forecast_json)

    input_records = load_json_records(input_path)
    forecast_records = load_json_records(forecast_path)

    input_rows = normalize_input_records(input_records)
    forecast_rows = normalize_forecast_records(forecast_records)

    if not input_rows:
        raise RuntimeError("No valid input rows parsed from input JSON")
    if not forecast_rows:
        raise RuntimeError("No valid forecast rows parsed from forecast JSON")

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                ensure_tables(cur, schema=args.schema)
                upsert_input_sales(cur, input_rows, schema=args.schema)
                upsert_forecast_sales(cur, forecast_rows, schema=args.schema)
        print(f"Loaded {len(input_rows)} input rows and {len(forecast_rows)} forecast rows into Postgres")
    finally:
        conn.close()


if __name__ == "__main__":
    main() 