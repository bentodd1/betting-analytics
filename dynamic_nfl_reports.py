#!/usr/bin/env python3
"""
Dynamic NFL Betting Reports with Claude API and Streamlit
Natural language interface for betting analytics
"""

import streamlit as st
import pandas as pd
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import psycopg2
from psycopg2.extras import RealDictCursor
from anthropic import Anthropic

# Add database module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))
from db_connection import DatabaseConnection

class NFLReportsApp:
    """Streamlit app for dynamic NFL betting reports using Claude API"""
    
    def __init__(self):
        self.claude_api_key = os.getenv('CLAUDE_API_KEY')
        
        # Database configuration
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', '5432')),
            'database': os.getenv('DB_NAME', 'betting_analytics'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', 'password')
        }
        
        self.db = DatabaseConnection()
        
        # Initialize Claude client
        if self.claude_api_key:
            self.claude = Anthropic(api_key=self.claude_api_key)
        else:
            self.claude = None
            st.error("Claude API key not found. Please set CLAUDE_API_KEY environment variable.")
    
    def get_database_schema_info(self) -> str:
        """Get database schema information for Claude context"""
        schema_info = """
        NFL Betting Analytics Database Schema:
        
        Main Tables:
        1. games - NFL games with teams, scores, timestamps
           - game_id, sport_id, commence_time, home_team_id, away_team_id, home_score, away_score, status
        
        2. spreads - Point spreads with bookmaker info and timestamps
           - spread_id, game_id, bookmaker_id, home_spread, away_spread, home_price, away_price, snapshot_timestamp
        
        3. teams - NFL teams
           - team_id, team_name, sport_id
        
        4. bookmakers - Sportsbook information
           - bookmaker_id, bookmaker_key, bookmaker_title
        
        5. moneylines - Moneyline odds
           - moneyline_id, game_id, bookmaker_id, home_price, away_price, snapshot_timestamp
        
        6. totals - Over/under odds
           - total_id, game_id, bookmaker_id, total_line, over_price, under_price, snapshot_timestamp
        
        Useful Views:
        - spread_movements: Shows line movement analysis
        - game_results: Shows completed games with results
        - moneyline_movements: Shows moneyline movement analysis
        
        Key relationships:
        - games.home_team_id -> teams.team_id
        - games.away_team_id -> teams.team_id
        - spreads.game_id -> games.game_id
        - spreads.bookmaker_id -> bookmakers.bookmaker_id
        """
        return schema_info
    
    def generate_sql_with_claude(self, natural_language_query: str) -> str:
        """Convert natural language to SQL using Claude API"""
        if not self.claude:
            return None
        
        schema_info = self.get_database_schema_info()
        
        prompt = f"""
        You are an expert SQL developer for an NFL betting analytics database. Convert the following natural language query into a PostgreSQL SQL query.

        Database Schema:
        {schema_info}

        User Request: {natural_language_query}

        Requirements:
        1. Return ONLY the SQL query, no explanations
        2. Use proper JOINs for team names and bookmaker names
        3. Include appropriate date filters and ordering
        4. Limit results to reasonable amounts (usually <= 100 rows)
        5. Use descriptive column aliases for better readability
        6. Handle time zones appropriately (data is in UTC)

        SQL Query:
        """
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            sql_query = response.content[0].text.strip()
            
            # Clean up the response - remove any markdown formatting
            if sql_query.startswith("```sql"):
                sql_query = sql_query[6:]
            if sql_query.startswith("```"):
                sql_query = sql_query[3:]
            if sql_query.endswith("```"):
                sql_query = sql_query[:-3]
            
            return sql_query.strip()
            
        except Exception as e:
            st.error(f"Error generating SQL: {str(e)}")
            return None
    
    def execute_sql_query(self, sql_query: str) -> pd.DataFrame:
        """Execute SQL query and return results as DataFrame"""
        try:
            # Use direct psycopg2 connection
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(sql_query)
            results = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if results:
                return pd.DataFrame(results)
            else:
                return pd.DataFrame()
        except Exception as e:
            st.error(f"Error executing query: {str(e)}")
            return pd.DataFrame()
    
    def test_database_connection(self) -> bool:
        """Test database connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] == 1
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            return result[0] if result else 0
        except Exception as e:
            return 0
    
    def format_dataframe_for_display(self, df: pd.DataFrame) -> pd.DataFrame:
        """Format DataFrame for better display in Streamlit"""
        if df.empty:
            return df
        
        # Convert datetime columns to readable format
        for col in df.columns:
            if df[col].dtype == 'datetime64[ns]' or 'time' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col]).dt.strftime('%m/%d %I:%M %p')
                except:
                    pass
        
        # Format decimal columns
        for col in df.columns:
            if df[col].dtype in ['float64', 'float32']:
                if 'price' in col.lower() or 'spread' in col.lower():
                    df[col] = df[col].apply(lambda x: f"{x:+.1f}" if pd.notna(x) else "")
                elif 'score' in col.lower():
                    df[col] = df[col].apply(lambda x: f"{int(x)}" if pd.notna(x) else "")
        
        return df
    
    def get_sample_queries(self) -> List[Dict[str, str]]:
        """Get sample queries for user guidance"""
        return [
            {
                "title": "Latest Spreads for This Week",
                "query": "Show me the latest spreads for all games this week with team names and bookmaker names"
            },
            {
                "title": "Line Movements",
                "query": "Show me games where the spread has moved more than 1 point with DraftKings or FanDuel"
            },
            {
                "title": "Arbitrage Opportunities",
                "query": "Find games where different bookmakers have significantly different spreads for the same game"
            },
            {
                "title": "Completed Games Analysis",
                "query": "Show me completed games from last week with final scores and spread results"
            },
            {
                "title": "Bookmaker Comparison",
                "query": "Compare spreads between DraftKings and FanDuel for upcoming games"
            },
            {
                "title": "High Scoring Games",
                "query": "Show me games with totals over 50 points and their over/under lines"
            },
            {
                "title": "Recent Line Updates",
                "query": "Show me the most recent spread updates in the last 24 hours"
            },
            {
                "title": "Team Performance",
                "query": "Show me how the Chiefs have performed against the spread this season"
            }
        ]
    
    def generate_insights_with_claude(self, df: pd.DataFrame, query: str) -> str:
        """Generate insights about the data using Claude"""
        if not self.claude or df.empty:
            return "No insights available."
        
        # Convert DataFrame to a summary for Claude
        df_summary = df.head(10).to_string()
        
        prompt = f"""
        Analyze this NFL betting data and provide 3-5 key insights. Be specific and actionable.

        Original Query: {query}
        
        Data Sample:
        {df_summary}
        
        Total Rows: {len(df)}
        
        Provide insights in bullet points focusing on:
        - Notable trends or patterns
        - Significant line movements
        - Potential betting opportunities
        - Anomalies or interesting findings
        
        Keep insights concise and relevant to NFL betting analysis.
        """
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            return f"Error generating insights: {str(e)}"

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="NFL Betting Analytics",
        page_icon="🏈",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS
    st.markdown("""
    <style>
        .main-header {
            background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 1rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 2rem;
        }
        .metric-card {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            border-left: 4px solid #007bff;
        }
        .query-card {
            background: #fff;
            padding: 1rem;
            border-radius: 8px;
            border: 1px solid #dee2e6;
            margin-bottom: 0.5rem;
            cursor: pointer;
        }
        .query-card:hover {
            background: #f8f9fa;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏈 NFL Betting Analytics Dashboard</h1>
        <p>Dynamic Reports with Natural Language Queries</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize app
    app = NFLReportsApp()
    
    # Sidebar
    st.sidebar.title("🎯 Quick Actions")
    
    # Database status
    if app.test_database_connection():
        st.sidebar.success("✅ Database Connected")
        
        # Get some quick stats
        try:
            total_games = app.get_table_count('games')
            total_spreads = app.get_table_count('spreads')
            
            st.sidebar.markdown("### 📊 Database Stats")
            st.sidebar.metric("Total Games", f"{total_games:,}")
            st.sidebar.metric("Total Spreads", f"{total_spreads:,}")
            
        except Exception as e:
            st.sidebar.warning(f"Could not load stats: {str(e)}")
    else:
        st.sidebar.error("❌ Database Connection Failed")
        st.stop()
    
    # Claude API status
    if app.claude:
        st.sidebar.success("✅ Claude API Connected")
    else:
        st.sidebar.error("❌ Claude API Not Available")
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🔍 Natural Language Query")
        
        # Query input
        user_query = st.text_area(
            "Ask questions about NFL betting data in plain English:",
            height=100,
            placeholder="Example: Show me the latest spreads for Chiefs games this week"
        )
        
        # Action buttons
        col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
        
        with col_btn1:
            generate_sql = st.button("🔄 Generate SQL", type="primary")
        
        with col_btn2:
            execute_query = st.button("▶️ Execute Query")
        
        # Query processing
        if generate_sql and user_query:
            with st.spinner("Generating SQL query..."):
                sql_query = app.generate_sql_with_claude(user_query)
                
                if sql_query:
                    st.session_state['generated_sql'] = sql_query
                    st.success("SQL generated successfully!")
                else:
                    st.error("Failed to generate SQL query")
        
        # Show generated SQL
        if 'generated_sql' in st.session_state:
            st.subheader("📝 Generated SQL")
            st.code(st.session_state['generated_sql'], language='sql')
            
            # Allow manual editing
            edited_sql = st.text_area(
                "Edit SQL if needed:",
                value=st.session_state['generated_sql'],
                height=150
            )
            st.session_state['generated_sql'] = edited_sql
        
        # Execute query
        if execute_query and 'generated_sql' in st.session_state:
            with st.spinner("Executing query..."):
                df = app.execute_sql_query(st.session_state['generated_sql'])
                
                if not df.empty:
                    st.session_state['query_results'] = df
                    st.session_state['last_query'] = user_query
                    st.success(f"Query executed successfully! Found {len(df)} rows.")
                else:
                    st.warning("Query executed but returned no results.")
        
        # Display results
        if 'query_results' in st.session_state:
            df = st.session_state['query_results']
            
            st.subheader("📊 Query Results")
            
            # Format and display data
            formatted_df = app.format_dataframe_for_display(df.copy())
            st.dataframe(formatted_df, use_container_width=True)
            
            # Download button
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"nfl_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
            
            # Generate insights
            if app.claude and 'last_query' in st.session_state:
                st.subheader("🧠 AI Insights")
                with st.spinner("Generating insights..."):
                    insights = app.generate_insights_with_claude(df, st.session_state['last_query'])
                    st.markdown(insights)
    
    with col2:
        st.subheader("💡 Sample Queries")
        
        sample_queries = app.get_sample_queries()
        
        for query_info in sample_queries:
            with st.container():
                st.markdown(f"""
                <div class="query-card">
                    <strong>{query_info['title']}</strong><br>
                    <small style="color: #666;">{query_info['query']}</small>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"Use Query: {query_info['title']}", key=f"btn_{query_info['title']}"):
                    st.session_state['sample_query'] = query_info['query']
                    st.rerun()
        
        # Handle sample query selection
        if 'sample_query' in st.session_state:
            # Update the query input with the sample query
            st.text_area(
                "Selected Query:",
                value=st.session_state['sample_query'],
                height=100,
                key="sample_display"
            )
            
            if st.button("🚀 Use This Query"):
                # Set the query and trigger SQL generation
                user_query = st.session_state['sample_query']
                with st.spinner("Generating SQL for sample query..."):
                    sql_query = app.generate_sql_with_claude(user_query)
                    if sql_query:
                        st.session_state['generated_sql'] = sql_query
                        st.rerun()

if __name__ == "__main__":
    main()