#!/bin/bash

echo "HR Employee Management Gateway - Web Demo"
echo "========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "README.md" ] || [ ! -d "backend" ] || [ ! -d "frontend" ]; then
  echo "Error: Please run this script from the hr-web-demo directory"
  exit 1
fi

# Function to check if a port is in use
check_port() {
  local port=$1
  if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null ; then
      return 0  # Port is in use
  else
      return 1  # Port is free
  fi
}

# Check if backend port is available
if check_port 8000; then
  echo "Warning: Port 8000 is already in use. Please stop the service using this port."
  echo "You can find the process with: lsof -i :8000"
  echo ""
fi

# Check if frontend port is available
if check_port 5173; then
  echo "Warning: Port 5173 is already in use. Please stop the service using this port."
  echo "You can find the process with: lsof -i :5173"
  echo ""
fi

# Check if gateway is deployed
if [ ! -f "../pii-masking-gateway/deployment_info.json" ]; then
  echo "❌ Gateway deployment not found!"
  echo ""
  echo "Please deploy the HR Employee Management Gateway first:"
  echo "  Run notebook: notebook-all/01-pii-gateway-setup.ipynb"
  echo ""
  echo "Or manually:"
  echo "  cd ../pii-masking-gateway"
  echo "  source ../../venv/bin/activate"
  echo "  python3 scripts/setup.py"
  echo ""
  echo "Then come back and run this script again."
  exit 1
else
  echo "✅ Gateway deployment found"
fi

# Check virtual environment (look in parent directories)
VENV_PATH=""
if [ -d "../venv" ]; then
  VENV_PATH="$(cd ../venv && pwd)"
elif [ -d "./venv" ]; then
  VENV_PATH="$(cd ./venv && pwd)"
else
  echo "❌ Virtual environment not found!"
  echo ""
  echo "Please create a virtual environment:"
  echo "  python3 -m venv venv"
  echo "  source venv/bin/activate"
  exit 1
fi
echo "✅ Virtual environment found: $VENV_PATH"

# Check Node.js
if ! command -v node &> /dev/null; then
  echo "❌ Node.js not found!"
  echo ""
  echo "Please install Node.js 16+ from: https://nodejs.org/"
  exit 1
else
  echo "✅ Node.js found: $(node --version)"
fi

# Detect if running in SageMaker
IS_SAGEMAKER=false
if [[ "$HOSTNAME" == *"sagemaker"* ]] || [[ -d "/home/ec2-user/SageMaker" ]]; then
  IS_SAGEMAKER=true
  echo "✅ SageMaker environment detected"
fi

echo ""
echo "🚀 Starting HR Web Demo..."
echo ""

# Create a function to cleanup background processes
cleanup() {
  echo ""
  echo "🛑 Stopping demo servers..."
  jobs -p | xargs -r kill
  exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM EXIT

# Start backend in background
echo "📡 Starting backend server..."
cd backend
source $VENV_PATH/bin/activate

# Quick check: skip pip install if key packages are already importable
if python3 -c "import fastapi, uvicorn, strands, sse_starlette" 2>/dev/null; then
  echo "   ✅ Dependencies already installed, skipping..."
else
  echo "   Installing dependencies..."
  pip3 install -r requirements.txt
fi

echo "   Starting uvicorn..."
uvicorn main:app --reload --host 0.0.0.0 --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Wait for backend to start (retry up to 15 seconds)
echo "   Waiting for backend to be ready..."
for i in $(seq 1 15); do
  if check_port 8000; then
      break
  fi
  sleep 1
done

# Check if backend started successfully
if ! check_port 8000; then
  echo "❌ Backend failed to start. Check backend.log for details."
  exit 1
fi

echo "✅ Backend started on http://localhost:8000"

# Start frontend in background
echo "🎨 Starting frontend server..."
cd frontend

# Check if node_modules exists and is valid
NEEDS_REINSTALL=false

if [ ! -d "node_modules" ]; then
  echo "   node_modules not found, installing..."
  NEEDS_REINSTALL=true
elif [ ! -f "node_modules/.bin/vite" ]; then
  echo "   Vite binary missing, reinstalling..."
  NEEDS_REINSTALL=true
elif [ ! -f "node_modules/vite/dist/node/cli.js" ]; then
  echo "   Vite CLI missing, reinstalling..."
  NEEDS_REINSTALL=true
fi

# Clean install if needed
if [ "$NEEDS_REINSTALL" = true ]; then
  echo "   Cleaning corrupted dependencies..."
  rm -rf node_modules package-lock.json
  echo "   Installing fresh dependencies (this may take a minute)..."
  npm install
  if [ $? -ne 0 ]; then
      echo "❌ Failed to install frontend dependencies"
      exit 1
  fi
  echo "   ✅ Dependencies installed successfully"
else
  # Just ensure dependencies are up to date
  npm install > /dev/null 2>&1
fi

if [ "$IS_SAGEMAKER" = true ]; then
  # SageMaker: Build and serve with Python
  echo "   Building frontend for SageMaker..."
  rm -rf dist node_modules/.vite
  export VITE_BASE_PATH=/proxy/5173/
  export VITE_API_BASE_URL=/proxy/8000
  npm run build
  if [ $? -ne 0 ]; then
      echo "❌ Failed to build frontend"
      exit 1
  fi

  echo "   Starting Python HTTP server..."
  cd dist
  python3 -m http.server 5173 --bind 0.0.0.0 > ../../frontend.log 2>&1 &
  FRONTEND_PID=$!
  cd ../..
else
  # Local: Use Vite dev server
  echo "   Starting Vite dev server..."
  npm run dev > ../frontend.log 2>&1 &
  FRONTEND_PID=$!
  cd ..
fi

# Wait for frontend to start (retry up to 15 seconds)
echo "   Waiting for frontend to be ready..."
for i in $(seq 1 15); do
  if check_port 5173; then
      break
  fi
  sleep 1
done

# Check if frontend started successfully
if ! check_port 5173; then
  echo "❌ Frontend failed to start. Check frontend.log for details."
  exit 1
fi

if [ "$IS_SAGEMAKER" = true ]; then
  echo "✅ Frontend built and served on http://localhost:5173"
  echo ""
  echo "🎉 HR Web Demo is ready!"
  echo ""
  echo "📋 SageMaker Access URL:"
  echo "  • Frontend: https://<notebook-name>.<region>.sagemaker.aws/proxy/5173/"
  echo "  • Backend API: https://<notebook-name>.<region>.sagemaker.aws/proxy/8000/"
  echo ""
else
  echo "✅ Frontend started on http://localhost:5173"
  echo ""
  echo "🎉 HR Web Demo is ready!"
  echo ""
  echo "📋 Available endpoints:"
  echo "  • Frontend (Web UI): http://localhost:5173"
  echo "  • Backend API: http://localhost:8000"
  echo "  • API Documentation: http://localhost:8000/docs"
  echo ""
fi

echo "📖 How to use:"
echo "  1. Open the frontend URL in your browser"
echo "  2. Choose a role (HR Manager, Employee, or HR Admin)"
echo "  3. Click 'Login' to authenticate"
echo "  4. Explore the different tools and see PII masking in action"
echo ""
echo "🔍 What to observe:"
echo "  • HR Manager/Admin: See full employee data (no PII masking)"
echo "  • Employee: See masked PII data (emails show as {EMAIL}, etc.)"
echo "  • Different roles have access to different tools"
echo ""
echo "📝 Logs:"
echo "  • Backend logs: backend.log"
echo "  • Frontend logs: frontend.log"
echo ""
echo "Press Ctrl+C to stop all servers..."

# Wait for user to stop the demo
wait