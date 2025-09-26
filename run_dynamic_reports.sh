#!/bin/bash

# NFL Dynamic Reports Launcher
# Sets up environment and starts Streamlit app

echo "🏈 Starting NFL Dynamic Reports Dashboard..."

# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_USER=postgres
export DB_PASSWORD="F1shF1sh&&"
export DB_NAME=betting_analytics
export CLAUDE_API_KEY="${CLAUDE_API_KEY:-your-claude-api-key-here}"

echo "✅ Environment variables set"

# Test database connection
echo "🔍 Testing database connection..."
python3 -c "
import psycopg2
try:
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        database='betting_analytics',
        user='postgres',
        password='F1shF1sh&&'
    )
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM games')
    games = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM spreads')
    spreads = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    print(f'✅ Database connected: {games} games, {spreads} spreads')
except Exception as e:
    print(f'❌ Database connection failed: {e}')
    exit(1)
"

echo "🚀 Starting Streamlit dashboard..."
echo "📱 App will open in your browser at: http://localhost:8501"
echo ""

# Start Streamlit
streamlit run dynamic_nfl_reports.py