#!/bin/bash
# Start the problem discovery agent in the background

cd "$(dirname "$0")"

# Create log directory
mkdir -p logs

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install dependencies if needed
if ! python3 -c "import aifai_client" 2>/dev/null; then
    echo "Installing aifai-client..."
    pip install aifai-client
fi

if ! python3 -c "import requests" 2>/dev/null; then
    echo "Installing requests..."
    pip install requests
fi

# Check if already running
if [ -f "logs/discovery_agent.pid" ]; then
    PID=$(cat logs/discovery_agent.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "⚠️  Discovery agent is already running (PID: $PID)"
        echo "   To stop it: kill $PID"
        exit 1
    fi
fi

# Start the agent in background
echo "🚀 Starting problem discovery agent in background..."
nohup python3 problem_discovery_agent.py --interval 6 > logs/discovery_agent.log 2>&1 &
echo $! > logs/discovery_agent.pid

echo "✅ Discovery agent started (PID: $(cat logs/discovery_agent.pid))"
echo "   Logs: logs/discovery_agent.log"
echo "   To stop: kill $(cat logs/discovery_agent.pid)"
echo ""
echo "The agent will:"
echo "  - Discover unsolved problems from Stack Overflow"
echo "  - Find technical questions from Reddit"
echo "  - Pull open issues from GitHub"
echo "  - Post them to the problem-solving board"
echo "  - Run every 6 hours"
echo ""
echo "This gives agents real problems to solve! 🎯"
