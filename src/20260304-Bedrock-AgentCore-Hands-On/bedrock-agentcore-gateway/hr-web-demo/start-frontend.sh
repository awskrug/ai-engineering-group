#!/bin/bash

echo "Starting HR Web Demo Frontend..."
echo "================================"

# Check if we're in the right directory
if [ ! -f "frontend/package.json" ]; then
    echo "Error: Please run this script from the hr-web-demo directory"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed. Please install Node.js 16+ first."
    echo "Visit: https://nodejs.org/"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "Error: npm is not installed. Please install npm first."
    exit 1
fi

# Install frontend dependencies
echo "Installing frontend dependencies..."
cd frontend
npm install

# Start the Vue.js development server
echo "Starting Vue.js development server on http://localhost:5173..."
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev