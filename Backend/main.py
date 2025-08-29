import os
import json
from datetime import datetime, date
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Add OpenAI client import
try:
	from openai import OpenAI
except Exception:
	OpenAI = None

# Load environment variables (.env next to this file), fallback to process env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"), override=False)

app = FastAPI(
    title="Sales Forecasting API",
    description="API for retrieving input sales and forecasted sales data for plotting",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for response
class SalesRecord(BaseModel):
    date: str
    sales: float
    business_id: Optional[str] = None

class ForecastRecord(BaseModel):
    date: str
    predicted_sales: float
    lower_bound: float
    upper_bound: float
    business_id: Optional[str] = None
    generated_at: Optional[str] = None

class SalesDataResponse(BaseModel):
    business_id: str
    input_sales: List[SalesRecord]
    forecast_sales: List[ForecastRecord]
    total_input_records: int
    total_forecast_records: int

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
        raise HTTPException(
            status_code=500, 
            detail=f"Missing required environment variables: {', '.join(missing)}"
        )

    try:
        return psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            cursor_factory=RealDictCursor
        )
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database connection failed: {str(e)}"
        )

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Sales Forecasting API",
        "version": "1.0.0",
        "endpoints": {
            "get_sales_data": "/api/sales/{business_id}",
            "get_input_sales": "/api/sales/{business_id}/input",
            "get_forecast_sales": "/api/sales/{business_id}/forecast",
            "list_businesses": "/api/businesses"
        }
    }

@app.get("/api/businesses", response_model=List[str])
async def list_businesses():
    """Get a list of all available business IDs."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get unique business IDs from both tables
            cur.execute("""
                SELECT DISTINCT business_id 
                FROM input_sales 
                WHERE business_id IS NOT NULL
                UNION
                SELECT DISTINCT business_id 
                FROM forecast_sales 
                WHERE business_id IS NOT NULL
                ORDER BY business_id
            """)
            results = cur.fetchall()
            return [row['business_id'] for row in results]
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        conn.close()

@app.get("/api/sales/{business_id}/input", response_model=List[SalesRecord])
async def get_input_sales(business_id: str):
    """Get input sales data for a specific business ID."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT date, sales, business_id
                FROM input_sales 
                WHERE business_id = %s
                ORDER BY date
            """, (business_id,))
            results = cur.fetchall()
            
            if not results:
                raise HTTPException(
                    status_code=404,
                    detail=f"No input sales data found for business_id: {business_id}"
                )
            
            return [
                SalesRecord(
                    date=row['date'].isoformat(),
                    sales=float(row['sales']),
                    business_id=row['business_id']
                )
                for row in results
            ]
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        conn.close()

@app.get("/api/sales/{business_id}/forecast", response_model=List[ForecastRecord])
async def get_forecast_sales(business_id: str):
    """Get forecast sales data for a specific business ID."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT date, predicted_sales, lower_bound, upper_bound, 
                       business_id, generated_at
                FROM forecast_sales 
                WHERE business_id = %s
                ORDER BY date
            """, (business_id,))
            results = cur.fetchall()
            
            if not results:
                raise HTTPException(
                    status_code=404,
                    detail=f"No forecast sales data found for business_id: {business_id}"
                )
            
            return [
                ForecastRecord(
                    date=row['date'].isoformat(),
                    predicted_sales=float(row['predicted_sales']),
                    lower_bound=float(row['lower_bound']),
                    upper_bound=float(row['upper_bound']),
                    business_id=row['business_id'],
                    generated_at=row['generated_at'].isoformat() if row['generated_at'] else None
                )
                for row in results
            ]
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        conn.close()

@app.get("/api/sales/{business_id}", response_model=SalesDataResponse)
async def get_sales_data(business_id: str):
    """Get both input sales and forecast sales data for a specific business ID."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Get input sales data
            cur.execute("""
                SELECT date, sales, business_id
                FROM input_sales 
                WHERE business_id = %s
                ORDER BY date
            """, (business_id,))
            input_results = cur.fetchall()
            
            # Get forecast sales data
            cur.execute("""
                SELECT date, predicted_sales, lower_bound, upper_bound, 
                       business_id, generated_at
                FROM forecast_sales 
                WHERE business_id = %s
                ORDER BY date
            """, (business_id,))
            forecast_results = cur.fetchall()
            
            if not input_results and not forecast_results:
                raise HTTPException(
                    status_code=404,
                    detail=f"No sales data found for business_id: {business_id}"
                )
            
            # Convert input sales data
            input_sales = [
                SalesRecord(
                    date=row['date'].isoformat(),
                    sales=float(row['sales']),
                    business_id=row['business_id']
                )
                for row in input_results
            ]
            
            # Convert forecast sales data
            forecast_sales = [
                ForecastRecord(
                    date=row['date'].isoformat(),
                    predicted_sales=float(row['predicted_sales']),
                    lower_bound=float(row['lower_bound']),
                    upper_bound=float(row['upper_bound']),
                    business_id=row['business_id'],
                    generated_at=row['generated_at'].isoformat() if row['generated_at'] else None
                )
                for row in forecast_results
            ]
            
            return SalesDataResponse(
                business_id=business_id,
                input_sales=input_sales,
                forecast_sales=forecast_sales,
                total_input_records=len(input_sales),
                total_forecast_records=len(forecast_sales)
            )
    except psycopg2.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )
    finally:
        conn.close()

@app.get("/api/sales/{business_id}/overview")
async def get_sales_overview(business_id: str):
    """Generate a trend overview for a business by sending input and forecast data to OpenAI."""
    # Check OpenAI availability and config
    if OpenAI is None:
        raise HTTPException(status_code=500, detail="OpenAI SDK is not installed on the server")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if not openai_api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY environment variable is missing")

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # Fetch input sales
            cur.execute(
                """
                SELECT date, sales
                FROM input_sales
                WHERE business_id = %s
                ORDER BY date
                """,
                (business_id,),
            )
            input_rows = cur.fetchall()

            # Fetch forecast sales
            cur.execute(
                """
                SELECT date, predicted_sales, lower_bound, upper_bound
                FROM forecast_sales
                WHERE business_id = %s
                ORDER BY date
                """,
                (business_id,),
            )
            forecast_rows = cur.fetchall()

            if not input_rows and not forecast_rows:
                raise HTTPException(status_code=404, detail=f"No sales data found for business_id: {business_id}")

        # Prepare compact data payloads (limit to keep prompt size small)
        def serialize_input(rows, limit=150):
            items = []
            for row in rows[-limit:]:
                items.append({
                    "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                    "sales": float(row["sales"]),
                })
            return items

        def serialize_forecast(rows, limit=150):
            items = []
            for row in rows[-limit:]:
                items.append({
                    "date": row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                    "predicted_sales": float(row["predicted_sales"]),
                    "lower_bound": float(row["lower_bound"]),
                    "upper_bound": float(row["upper_bound"]),
                })
            return items

        input_payload = serialize_input(input_rows)
        forecast_payload = serialize_forecast(forecast_rows)

        # Build prompt/messages
        system_msg = (
            "You are a data analyst. Analyze historical weekly sales and forecast data. "
            "Identify key trends, seasonality, growth/decline, anomalies, and forecast outlook. "
            "Be concise and actionable. Use plain language. Include 3 bullets and a 1-sentence summary."
        )
        user_msg = {
            "business_id": business_id,
            "input_sales_sample_count": len(input_payload),
            "forecast_sample_count": len(forecast_payload),
            "input_sales": input_payload,
            "forecast_sales": forecast_payload,
        }

        client = OpenAI(api_key=openai_api_key)
        try:
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": json.dumps(user_msg)},
                ],
                temperature=0.2,
                max_tokens=500,
            )
            overview_text = completion.choices[0].message.content if completion and completion.choices else None
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"OpenAI request failed: {str(e)}")

        if not overview_text:
            raise HTTPException(status_code=502, detail="OpenAI did not return a response")

        return {
            "business_id": business_id,
            "overview": overview_text,
            "input_records_used": len(input_payload),
            "forecast_records_used": len(forecast_payload),
            "model": model,
        }
    except psycopg2.Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        conn.close()

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
