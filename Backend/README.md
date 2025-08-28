# Sales Forecasting Backend API

This backend provides a REST API to retrieve input sales and forecasted sales data for plotting in graphs. It connects to a PostgreSQL database and provides endpoints to fetch data for specific business IDs.

## Features

- **RESTful API** built with FastAPI
- **PostgreSQL integration** for data storage
- **CORS support** for frontend integration
- **Automatic API documentation** with Swagger UI
- **Health check endpoint** for monitoring
- **Error handling** with proper HTTP status codes

## API Endpoints

### Base URL

```
http://localhost:8000
```

### Available Endpoints

1. **GET /** - API information and available endpoints
2. **GET /api/health** - Health check endpoint
3. **GET /api/businesses** - List all available business IDs
4. **GET /api/sales/{business_id}** - Get both input and forecast sales for a business
5. **GET /api/sales/{business_id}/input** - Get only input sales data
6. **GET /api/sales/{business_id}/forecast** - Get only forecast sales data

## Setup Instructions

### Prerequisites

- Python 3.8 or higher
- Docker and Docker Compose (for the PostgreSQL database)
- Data loaded using the `save_to_postgres.py` script

### Installation

#### Quick Setup (Recommended)

**For Linux/macOS:**

```bash
cd Backend
chmod +x setup.sh
./setup.sh
```

**For Windows:**

```cmd
cd Backend
setup.bat
```

#### Manual Setup

1. **Navigate to the Backend directory:**

   ```bash
   cd Backend
   ```

2. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Start the Docker PostgreSQL database:**

   ```bash
   # Navigate to the Prediction Model directory
   cd ../Prediction\ Model

   # Start the PostgreSQL database
   docker-compose up -d postgres

   # Wait for the database to be ready (check with docker-compose ps)
   docker-compose ps
   ```

4. **Set up environment variables:**
   Create a `.env` file in the Backend directory with the Docker PostgreSQL credentials:

   ```env
   PGHOST=localhost
   PGPORT=5432
   PGDATABASE=sales
   PGUSER=sales_user
   PGPASSWORD=sales_pass
   ```

5. **Run the API server:**

   ```bash
   python main.py
   ```

   Or using uvicorn directly:

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Access the API:**
   - API: http://localhost:8000
   - Interactive documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Response Formats

### Sales Record

```json
{
  "date": "2024-01-01",
  "sales": 1500.5,
  "business_id": "business_123"
}
```

### Forecast Record

```json
{
  "date": "2024-01-08",
  "predicted_sales": 1600.75,
  "lower_bound": 1440.68,
  "upper_bound": 1760.83,
  "business_id": "business_123",
  "generated_at": "2024-01-01T10:30:00Z"
}
```

### Complete Sales Data Response

```json
{
  "business_id": "business_123",
  "input_sales": [...],
  "forecast_sales": [...],
  "total_input_records": 52,
  "total_forecast_records": 12
}
```

## Usage Examples

### Using curl

1. **Get all business IDs:**

   ```bash
   curl http://localhost:8000/api/businesses
   ```

2. **Get sales data for a specific business:**

   ```bash
   curl http://localhost:8000/api/sales/business_123
   ```

3. **Get only input sales:**

   ```bash
   curl http://localhost:8000/api/sales/business_123/input
   ```

4. **Get only forecast sales:**
   ```bash
   curl http://localhost:8000/api/sales/business_123/forecast
   ```

### Using JavaScript/Fetch

```javascript
// Get sales data for plotting
async function getSalesData(businessId) {
  try {
    const response = await fetch(
      `http://localhost:8000/api/sales/${businessId}`
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();

    // Use the data for plotting
    console.log("Input sales:", data.input_sales);
    console.log("Forecast sales:", data.forecast_sales);

    return data;
  } catch (error) {
    console.error("Error fetching sales data:", error);
  }
}

// Example usage
getSalesData("business_123");
```

## Frontend Integration

A sample HTML file (`plot_example.html`) is included that demonstrates how to:

- Fetch data from the API
- Create interactive charts using Chart.js
- Handle loading states and errors
- Display both historical and forecasted sales data

To use the sample frontend:

1. Start the backend server
2. Open `plot_example.html` in a web browser
3. Select a business ID from the dropdown
4. Click "Load Data" to see the chart

## Error Handling

The API returns appropriate HTTP status codes:

- **200** - Success
- **404** - Business ID not found
- **500** - Server error (database connection, etc.)

Error responses include a `detail` field with the error message:

```json
{
  "detail": "No sales data found for business_id: invalid_id"
}
```

## Database Schema

The API expects the following PostgreSQL tables (created by `save_to_postgres.py`):

### input_sales table

```sql
CREATE TABLE input_sales (
    date DATE,
    sales NUMERIC NOT NULL,
    business_id TEXT
);
```

### forecast_sales table

```sql
CREATE TABLE forecast_sales (
    date DATE,
    predicted_sales NUMERIC NOT NULL,
    lower_bound NUMERIC NOT NULL,
    upper_bound NUMERIC NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    business_id TEXT
);
```

## Docker Setup

### Starting the Database

The backend is designed to work with the Docker PostgreSQL database defined in the `Prediction Model/docker-compose.yml` file.

1. **Start the database:**

   ```bash
   cd ../Prediction\ Model
   docker-compose up -d postgres
   ```

2. **Check database status:**

   ```bash
   docker-compose ps
   ```

3. **View database logs:**

   ```bash
   docker-compose logs postgres
   ```

4. **Stop the database:**
   ```bash
   docker-compose down
   ```

### Database Connection Details

- **Host:** localhost (or the Docker host IP)
- **Port:** 5432 (mapped from Docker container)
- **Database:** sales
- **Username:** sales_user
- **Password:** sales_pass

## Development

### Running in Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing the Setup

1. **Test database connection:**

   ```bash
   python test_connection.py
   ```

2. **Test the API endpoints:**

   ```bash
   # Health check
   curl http://localhost:8000/api/health

   # List businesses
   curl http://localhost:8000/api/businesses

   # Get sales data (replace with actual business_id)
   curl http://localhost:8000/api/sales/your_business_id
   ```

## Troubleshooting

### Common Issues

1. **Database connection failed:**

   - Check your `.env` file has correct PostgreSQL credentials
   - Ensure the Docker PostgreSQL container is running: `docker-compose ps`
   - Verify the database exists: `docker-compose exec postgres psql -U sales_user -d sales -c "\dt"`
   - Check if the port 5432 is available and not blocked by firewall

2. **Docker database not starting:**

   - Check Docker is running: `docker --version`
   - Check Docker Compose is available: `docker-compose --version`
   - View database logs: `docker-compose logs postgres`
   - Ensure port 5432 is not already in use by another PostgreSQL instance

3. **No data found:**

   - Make sure you've run `save_to_postgres.py` to load data
   - Check that the business_id exists in the database
   - Verify data was loaded: `docker-compose exec postgres psql -U sales_user -d sales -c "SELECT COUNT(*) FROM input_sales; SELECT COUNT(*) FROM forecast_sales;"`

4. **CORS errors:**
   - The API includes CORS middleware, but you may need to configure allowed origins for production

### Logs

The API will log connection errors and other issues to the console. Check the terminal output for debugging information.

## Production Deployment

For production deployment:

1. **Configure CORS properly:**

   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],
       allow_credentials=True,
       allow_methods=["GET"],
       allow_headers=["*"],
   )
   ```

2. **Use environment variables for configuration:**

   ```env
   PGHOST=your_production_db_host
   PGPORT=5432
   PGDATABASE=your_production_db
   PGUSER=your_production_user
   PGPASSWORD=your_production_password
   ```

3. **Use a production ASGI server:**

   ```bash
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

4. **Set up proper logging and monitoring**
