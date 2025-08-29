#!/bin/bash

# Sales Forecasting Backend Setup Script
# This script sets up the Docker database and configures the environment

set -e

echo "🚀 Setting up Sales Forecasting Backend..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

print_status "Docker and Docker Compose are available"

# Navigate to the Prediction Model directory to start the database
PREDICTION_MODEL_DIR="../Prediction Model"

if [ ! -d "$PREDICTION_MODEL_DIR" ]; then
    print_error "Prediction Model directory not found. Please run this script from the Backend directory."
    exit 1
fi

print_status "Starting PostgreSQL database..."

# Start the PostgreSQL database
cd "$PREDICTION_MODEL_DIR"
docker-compose up -d postgres

# Wait for the database to be ready
print_status "Waiting for database to be ready..."
sleep 10

# Check if the database is running
if docker-compose ps | grep -q "Up"; then
    print_status "PostgreSQL database is running"
else
    print_error "Failed to start PostgreSQL database"
    docker-compose logs postgres
    exit 1
fi

# Go back to Backend directory
cd - > /dev/null

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    print_status "Creating .env file with Docker database configuration..."
    cat > .env << EOF
# Database Configuration (Docker PostgreSQL)
PGHOST=localhost
PGPORT=5432
PGDATABASE=sales
PGUSER=sales_user
PGPASSWORD=sales_pass

# API Configuration (optional)
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=true
EOF
    print_status ".env file created"
else
    print_warning ".env file already exists. Please ensure it has the correct Docker database configuration."
fi

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt

print_status "Setup complete! 🎉"
echo ""
echo "Next steps:"
echo "1. Load data into the database:"
echo "   cd ../Prediction\ Model"
echo "   python save_to_postgres.py"
echo ""
echo "2. Start the API server:"
echo "   python start_server.py"
echo ""
echo "3. Access the API:"
echo "   - API: http://localhost:8000"
echo "   - Documentation: http://localhost:8000/docs"
echo "   - Sample frontend: Open plot_example.html in your browser"
echo ""
echo "To stop the database:"
echo "   cd ../Prediction\ Model && docker-compose down"
