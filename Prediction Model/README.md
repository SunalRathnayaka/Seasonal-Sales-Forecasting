python3 -m venv .venv
source ".venv/bin/activate"
pip install -r requirements.txt

# Run Postgres with Docker
# From this directory (Prediction Model)
# cp .env.example .env  # then edit if needed
# docker compose up -d
# Wait for healthy status: docker compose ps

# Run forecasting
python forecast.py

# Environment variables for Postgres (host-side)
# Required: PGDATABASE, PGUSER, PGPASSWORD
# Optional: PGHOST (default localhost), PGPORT (default 5432)

# If you used .env.example without changes, you can export:
# export PGDATABASE=sales
# export PGUSER=sales_user
# export PGPASSWORD=sales_pass
# export PGHOST=localhost
# export PGPORT=5432

# Load data into Postgres (after forecast has generated output/sales_forecast.json)
python save_to_postgres.py \
  --input-json weekly_sales_data.json \
  --forecast-json output/sales_forecast.json