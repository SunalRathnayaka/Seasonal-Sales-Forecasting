@echo off
REM Sales Forecasting Backend Setup Script for Windows
REM This script sets up the Docker database and configures the environment

echo 🚀 Setting up Sales Forecasting Backend...

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not installed. Please install Docker Desktop first.
    pause
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker Compose is not installed. Please install Docker Compose first.
    pause
    exit /b 1
)

echo [INFO] Docker and Docker Compose are available

REM Navigate to the Prediction Model directory to start the database
set PREDICTION_MODEL_DIR=..\Prediction Model

if not exist "%PREDICTION_MODEL_DIR%" (
    echo [ERROR] Prediction Model directory not found. Please run this script from the Backend directory.
    pause
    exit /b 1
)

echo [INFO] Starting PostgreSQL database...

REM Start the PostgreSQL database
cd "%PREDICTION_MODEL_DIR%"
docker-compose up -d postgres

REM Wait for the database to be ready
echo [INFO] Waiting for database to be ready...
timeout /t 10 /nobreak >nul

REM Check if the database is running
docker-compose ps | findstr "Up" >nul
if errorlevel 1 (
    echo [ERROR] Failed to start PostgreSQL database
    docker-compose logs postgres
    pause
    exit /b 1
) else (
    echo [INFO] PostgreSQL database is running
)

REM Go back to Backend directory
cd /d "%~dp0"

REM Create .env file if it doesn't exist
if not exist ".env" (
    echo [INFO] Creating .env file with Docker database configuration...
    (
        echo # Database Configuration ^(Docker PostgreSQL^)
        echo PGHOST=localhost
        echo PGPORT=5432
        echo PGDATABASE=sales
        echo PGUSER=sales_user
        echo PGPASSWORD=sales_pass
        echo.
        echo # API Configuration ^(optional^)
        echo API_HOST=0.0.0.0
        echo API_PORT=8000
        echo API_RELOAD=true
    ) > .env
    echo [INFO] .env file created
) else (
    echo [WARNING] .env file already exists. Please ensure it has the correct Docker database configuration.
)

REM Install Python dependencies
echo [INFO] Installing Python dependencies...
pip install -r requirements.txt

echo [INFO] Setup complete! 🎉
echo.
echo Next steps:
echo 1. Load data into the database:
echo    cd ..\Prediction Model
echo    python save_to_postgres.py
echo.
echo 2. Start the API server:
echo    python start_server.py
echo.
echo 3. Access the API:
echo    - API: http://localhost:8000
echo    - Documentation: http://localhost:8000/docs
echo    - Sample frontend: Open plot_example.html in your browser
echo.
echo To stop the database:
echo    cd ..\Prediction Model ^&^& docker-compose down
echo.
pause
