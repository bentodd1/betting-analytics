# NFL Betting Analytics Platform - Claude Instructions

## 🎯 Project Overview
This is a comprehensive NFL betting analytics platform that collects historical and current spreads data, stores it in PostgreSQL, and provides interactive dashboards for analysis. The goal is to eventually create an LLM app for dynamic reports and visualizations using natural language.

## 🗂️ Core Components (Keep These)

### Database & Data Collection
- **`database/`** - PostgreSQL schema and connection utilities
  - `schema.sql` - Complete database schema with spreads, games, teams, bookmakers
  - `db_connection.py` - Database connection and utility functions
- **`fetch_nfl_spreads.py`** - Fetches current NFL spreads from The Odds API
- **`fetch_historical_spreads.py`** - Fetches historical data with timestamps
- **`fetch_nfl_seasons.py`** - Bulk historical data collection for multiple seasons

### Reporting & Analysis
- **`weekly_analysis.py`** - Comprehensive weekly report generator with line movements
- **`quick_weekly_report.py`** - Simplified weekly reports
- **`nfl_tables_dashboard.html`** - Clean table-based dashboard (BEST UI)

### Configuration
- **`requirements.txt`** - Python dependencies
- **`docker-compose.yml`** - PostgreSQL container setup

## 🗑️ Files to Delete (Outdated/Experimental)
- `test_db.py` - Basic connection test (functionality now in db_connection.py)
- `interactive_spotlight_charts.py` - Chart version with UI issues
- `dynamic_betting_dashboard.py` - Problematic f-string version
- `simple_dynamic_dashboard.py` - Mock data version
- `enhanced_dynamic_dashboard.py` - Complex chart version
- All generated HTML files except `nfl_tables_dashboard.html`
- Generated report TXT files (can be regenerated)

## 🏗️ Database Setup
1. **Start PostgreSQL:**
   ```bash
   docker-compose up -d postgres
   # OR if PostgreSQL installed locally, ensure it's running
   ```

2. **Set Environment Variables:**
   ```bash
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_USER=postgres
   export DB_PASSWORD="F1shF1sh&&"
   export DB_NAME=betting_analytics
   export ODDS_API_KEY=c2684e376927153aefc7aa730cca2d27
   ```

3. **Initialize Database:**
   ```bash
   python3 database/db_connection.py
   ```

## 📊 Current Data Status
- **NFL Seasons:** 2024 season with 337 games, 5,976 spreads
- **Time Range:** August 2024 - January 2025
- **Bookmakers:** DraftKings, FanDuel (primary), BetMGM, Caesars
- **Data Points:** 62 API snapshots across 61 unique dates

## 🚀 Usage Examples

### Fetch Current Week Data
```bash
python3 fetch_nfl_spreads.py
```

### Fetch Historical Data
```bash
python3 fetch_historical_spreads.py --timestamp "2024-12-20T18:00:00Z" --bookmakers "draftkings,fanduel"
```

### Generate Weekly Report
```bash
python3 weekly_analysis.py --week-start "2024-12-23" --week-end "2024-12-30"
```

### View Dashboard
Open `nfl_tables_dashboard.html` in browser for clean table interface

## 📋 Database Schema Summary
- **`games`** - NFL games with teams, scores, timestamps
- **`spreads`** - Point spreads with bookmaker info and timestamps
- **`teams`** - NFL teams linked to games
- **`bookmakers`** - Sportsbook information
- **`api_snapshots`** - Track historical data collection
- **Views:** `spread_movements`, `game_results` for analysis

## 🎯 Next Steps Toward LLM App
1. **Natural Language Query Interface** - Convert English questions to SQL
2. **Dynamic Report Generation** - Generate reports from text prompts
3. **Automated Insights** - AI-powered trend detection
4. **API Endpoints** - REST API for LLM integration

## 🔧 Key Commands for New Claude Instance
```bash
# Check database status
python3 -c "from database.db_connection import get_database_status; print(get_database_status())"

# List available weeks
python3 weekly_analysis.py --list-weeks

# Generate quick report
python3 quick_weekly_report.py --start "2024-12-23" --end "2024-12-30"

# View best dashboard
open nfl_tables_dashboard.html
```

## 📊 Data Quality Metrics
- **Coverage:** 61 unique dates with data
- **Richness:** Average 21 snapshots per week
- **Bookmaker Coverage:** 2-4 bookmakers per game
- **Movement Detection:** 15% of spreads show line movements
- **API Credits Used:** ~50 of 4.8M available

## 🎛️ Environment Setup for New Claude
When starting fresh:
1. Confirm PostgreSQL is running with credentials above
2. Verify Python dependencies: `pip3 install -r requirements.txt`
3. Test database: `python3 database/db_connection.py`
4. Check latest data: `python3 weekly_analysis.py --list-weeks`
5. Open dashboard: `nfl_tables_dashboard.html`

This platform is ready for LLM integration to create natural language betting analysis!