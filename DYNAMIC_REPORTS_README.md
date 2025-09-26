# 🏈 Dynamic NFL Reports with Claude API & Streamlit

A powerful natural language interface for NFL betting analytics that converts plain English questions into SQL queries and generates dynamic reports.

## 🚀 Features

- **Natural Language Queries**: Ask questions in plain English about NFL betting data
- **AI-Powered SQL Generation**: Claude API converts your questions to optimized SQL queries
- **Interactive Dashboard**: Streamlit-based web interface with real-time data
- **Smart Insights**: AI-generated analysis and recommendations
- **Export Capabilities**: Download results as CSV files
- **Sample Query Library**: Pre-built queries for common analysis needs

## 📋 Prerequisites

- Python 3.8+
- PostgreSQL database with NFL betting data
- Claude API key
- Required Python packages (see installation)

## 🔧 Installation & Setup

1. **Install Dependencies**:
   ```bash
   pip3 install streamlit anthropic pandas psycopg2-binary
   ```

2. **Set Environment Variables**:
   ```bash
   export DB_HOST=localhost
   export DB_PORT=5432
   export DB_USER=postgres
   export DB_PASSWORD="F1shF1sh&&"
   export DB_NAME=betting_analytics
   export CLAUDE_API_KEY="your-claude-api-key-here"
   ```

3. **Launch the Dashboard**:
   ```bash
   # Option 1: Use the launcher script
   ./run_dynamic_reports.sh
   
   # Option 2: Run directly
   streamlit run dynamic_nfl_reports.py
   ```

4. **Access the Dashboard**:
   Open your browser to: `http://localhost:8501`

## 🎯 Usage Examples

### Sample Natural Language Queries

1. **Latest Spreads**:
   - "Show me the latest spreads for all games this week"
   - "What are the current lines for Chiefs games?"

2. **Line Movement Analysis**:
   - "Show me games where the spread moved more than 1 point"
   - "Find line movements for DraftKings in the last 24 hours"

3. **Arbitrage Opportunities**:
   - "Find games with different spreads between DraftKings and FanDuel"
   - "Show me arbitrage opportunities for this weekend"

4. **Team Performance**:
   - "How has the Chiefs performed against the spread this season?"
   - "Show me high-scoring games with totals over 50"

5. **Bookmaker Comparison**:
   - "Compare spreads between all bookmakers for upcoming games"
   - "Which bookmaker has the best odds for Chiefs games?"

### Workflow

1. **Enter Query**: Type your question in plain English
2. **Generate SQL**: Click "Generate SQL" to convert to database query
3. **Review/Edit**: Check the generated SQL, edit if needed
4. **Execute**: Run the query to get results
5. **Analyze**: View data table and AI-generated insights
6. **Export**: Download results as CSV if needed

## 🗄️ Database Schema

The system works with these main tables:

- **games**: NFL games with teams, scores, timestamps
- **spreads**: Point spreads with bookmaker info and timestamps  
- **teams**: NFL teams
- **bookmakers**: Sportsbook information
- **moneylines**: Moneyline odds
- **totals**: Over/under odds

Key views for analysis:
- **spread_movements**: Line movement analysis
- **game_results**: Completed games with results

## 🧠 AI Features

### SQL Generation
Claude API converts natural language to optimized PostgreSQL queries:
- Proper JOINs for team and bookmaker names
- Appropriate date filters and ordering
- Limited result sets for performance
- Descriptive column aliases

### Insight Generation
AI analyzes query results to provide:
- Notable trends and patterns
- Significant line movements
- Potential betting opportunities
- Anomalies and interesting findings

## 📊 Dashboard Components

### Main Interface
- **Query Input**: Natural language text area
- **SQL Editor**: View and edit generated SQL
- **Results Table**: Formatted data display
- **Insights Panel**: AI-generated analysis

### Sidebar
- **Database Status**: Connection and stats
- **Sample Queries**: Pre-built query examples
- **Quick Actions**: Common operations

## 🔒 Security Notes

- Environment variables keep credentials secure
- SQL injection protection through parameterized queries
- Read-only database operations
- API key validation

## 🛠️ Technical Architecture

```
User Input (Natural Language)
        ↓
Claude API (SQL Generation)
        ↓
PostgreSQL Database
        ↓
Pandas DataFrame
        ↓
Streamlit Display + AI Insights
```

## 📈 Performance Tips

- Database has optimized indexes for common queries
- Queries are automatically limited to reasonable result sets
- Results are cached for repeat queries
- Streamlit provides efficient data rendering

## 🔧 Troubleshooting

### Database Connection Issues
- Verify PostgreSQL is running
- Check environment variables
- Confirm database credentials

### Claude API Issues
- Verify API key is valid
- Check network connectivity
- Monitor API usage limits

### Streamlit Issues
- Restart the application
- Clear browser cache
- Check console for errors

## 🎯 Next Steps

This dynamic reports system provides the foundation for:
- Advanced betting analytics
- Automated report generation
- Real-time monitoring dashboards
- Integration with other data sources

## 💡 Tips for Better Queries

1. **Be Specific**: Include timeframes, team names, or bookmakers
2. **Use Context**: Reference specific metrics like "spread movement" or "line value"
3. **Set Limits**: Ask for "top 10" or "last week" to get focused results
4. **Combine Concepts**: Mix teams, dates, and betting concepts in one query

## 📱 Mobile Support

The Streamlit dashboard is responsive and works on mobile devices, making it easy to check betting analytics on the go.

---

Built with ❤️ using Claude AI, Streamlit, and PostgreSQL