#!/bin/bash

echo "Starting HR Web Demo Backend..."
echo "================================"

# Check if we're in the right directory
if [ ! -f "backend/main.py" ]; then
    echo "Error: Please run this script from the hr-web-demo directory"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "Error: Virtual environment not found. Please ensure you have a virtual environment set up."
    echo "You can create one with: python3 -m venv ../venv"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source ../venv/bin/activate

# Install backend dependencies
echo "Installing backend dependencies..."
cd backend
pip install -r requirements.txt

# Check if deployment info exists
if [ ! -f "../../pii-masking-gateway/deployment_info.json" ]; then
    echo "Warning: Gateway deployment info not found!"
    echo "Please run the gateway setup first:"
    echo "  cd ../pii-masking-gateway"
    echo "  python3 scripts/setup.py"
    echo ""
    echo "Continuing anyway (backend will show errors until gateway is deployed)..."
fi

# Start the FastAPI server
echo "Starting FastAPI server on http://localhost:8000..."
echo "Press Ctrl+C to stop the server"
echo ""

uvicorn main:app --reload --host 0.0.0.0 --port 8000