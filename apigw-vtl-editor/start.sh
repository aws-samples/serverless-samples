#!/bin/bash

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Store the process IDs
BACKEND_PID=""

# Function to clean up processes on exit
cleanup() {
  echo -e "\n${YELLOW}Shutting down services...${NC}"
  
  # Kill the backend process if it exists
  if [ ! -z "$BACKEND_PID" ]; then
    echo -e "${BLUE}Stopping backend API...${NC}"
    kill $BACKEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
  fi
  
  echo -e "${GREEN}All services stopped.${NC}"
  exit 0
}

# Set up trap to catch SIGINT (Ctrl+C) and SIGTERM
trap cleanup SIGINT SIGTERM

# Print welcome message
echo -e "${GREEN}=== VTL Template Browser Testing - Starting All Services ===${NC}"

# Step 1: Build the Lambda function
echo -e "\n${BLUE}Building the Lambda function...${NC}"
cd vtl-processor
mvn clean package
if [ $? -ne 0 ]; then
  echo -e "${RED}Failed to build Lambda function. Exiting.${NC}"
  exit 1
fi
cd ..

# Step 2: Start the backend API in the background
echo -e "\n${BLUE}Starting backend API on port 3000...${NC}"
sam local start-api --port 3000 --skip-pull-image &
BACKEND_PID=$!

# Wait a moment to ensure the backend is starting up
sleep 2

# Check if backend process is still running
if ! ps -p $BACKEND_PID > /dev/null; then
  echo -e "${RED}Backend API failed to start. Exiting.${NC}"
  cleanup
  exit 1
fi

echo -e "${GREEN}Backend API is starting up (PID: $BACKEND_PID)${NC}"

# Step 3: Start the frontend development server
echo -e "\n${BLUE}Starting frontend development server...${NC}"
echo -e "${YELLOW}Note: Press Ctrl+C to stop both frontend and backend services${NC}"
cd vtl-template-browser-testing
npm run dev

# If we get here, the frontend server was stopped
echo -e "\n${YELLOW}Frontend server stopped. Cleaning up...${NC}"
cleanup
