#!/usr/bin/env python3
"""
Test script to verify database connection and check data availability
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

def test_database_connection():
    """Test the database connection and check for data."""
    
    # Load environment variables
    load_dotenv()
    
    # Get database configuration
    host = os.getenv("PGHOST", "localhost")
    port = int(os.getenv("PGPORT", "5432"))
    dbname = os.getenv("PGDATABASE")
    user = os.getenv("PGUSER")
    password = os.getenv("PGPASSWORD")
    
    print("🔍 Testing database connection...")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {dbname}")
    print(f"User: {user}")
    print("-" * 50)
    
    # Check for missing environment variables
    missing = [k for k, v in {
        "PGDATABASE": dbname,
        "PGUSER": user,
        "PGPASSWORD": password,
    }.items() if not v]
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        print("Please create a .env file with the correct database configuration.")
        return False
    
    try:
        # Test connection
        conn = psycopg2.connect(
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
            cursor_factory=RealDictCursor
        )
        
        print("✅ Database connection successful!")
        
        with conn.cursor() as cur:
            # Check if tables exist
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name IN ('input_sales', 'forecast_sales')
            """)
            tables = [row['table_name'] for row in cur.fetchall()]
            
            print(f"📋 Found tables: {', '.join(tables) if tables else 'None'}")
            
            # Check data counts
            if 'input_sales' in tables:
                cur.execute("SELECT COUNT(*) as count FROM input_sales")
                input_count = cur.fetchone()['count']
                print(f"📊 Input sales records: {input_count}")
                
                # Get unique business IDs
                cur.execute("SELECT DISTINCT business_id FROM input_sales WHERE business_id IS NOT NULL")
                business_ids = [row['business_id'] for row in cur.fetchall()]
                print(f"🏢 Business IDs: {', '.join(business_ids) if business_ids else 'None'}")
            
            if 'forecast_sales' in tables:
                cur.execute("SELECT COUNT(*) as count FROM forecast_sales")
                forecast_count = cur.fetchone()['count']
                print(f"🔮 Forecast sales records: {forecast_count}")
            
            # Check if we have any data
            if 'input_sales' in tables and input_count > 0:
                print("✅ Data is available for the API!")
                return True
            else:
                print("⚠️  No data found. Please run the forecasting pipeline first:")
                print("   cd ../Prediction\\ Model")
                print("   python forecast.py")
                print("   python save_to_postgres.py")
                return False
                
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure the Docker database is running:")
        print("   cd ../Prediction\\ Model && docker-compose ps")
        print("2. Start the database if it's not running:")
        print("   cd ../Prediction\\ Model && docker-compose up -d postgres")
        print("3. Check the database logs:")
        print("   cd ../Prediction\\ Model && docker-compose logs postgres")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = test_database_connection()
    sys.exit(0 if success else 1)
