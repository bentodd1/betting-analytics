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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
                "title": "Spread Outcomes Analysis", 
                "query": "Show me completed games with scores, spreads, and whether the favorite covered"
            },
            {
                "title": "Best Betting Lines",
                "query": "Find games where the spread was way off - show games with biggest margin vs spread difference"
            },
            {
                "title": "Team ATS Performance",
                "query": "Show me how each team has performed against the spread this season with win percentages"
            },
            {
                "title": "Bookmaker Accuracy",
                "query": "Compare DraftKings vs FanDuel spread accuracy - which bookmaker sets better lines"
            },
            {
                "title": "Upset Alert Games", 
                "query": "Show me games where the underdog won outright against the spread"
            },
            {
                "title": "Recent Game Outcomes",
                "query": "Show me the most recent completed games with scores and spread results"
            },
            {
                "title": "Line Movement Analysis",
                "query": "Find games where significant line movement indicated the right side to bet"
            },
            {
                "title": "Today's Games",
                "query": "Show me all games scheduled for today with current spreads and odds"
            },
            {
                "title": "Best Value Bets",
                "query": "Find games with the biggest spread differences between bookmakers"
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
    
    def store_query_history(self, prompt: str, sql_query: str, user_id: str = None):
        """Store prompt-query pairs for future reference"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS query_history (
                    id SERIAL PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    sql_query TEXT NOT NULL,
                    user_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sport_context VARCHAR(100),
                    execution_success BOOLEAN DEFAULT TRUE
                )
            """)
            
            # Get current sport context
            sport_context = st.session_state.get('selected_sport', 'unknown')
            
            # Insert the query history
            cursor.execute("""
                INSERT INTO query_history (prompt, sql_query, user_id, sport_context, execution_success)
                VALUES (%s, %s, %s, %s, %s)
            """, (prompt, sql_query, user_id, sport_context, True))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            # Don't fail the main workflow if history storage fails
            print(f"Warning: Could not store query history: {e}")
    
    def get_query_history(self, user_id: str = None, limit: int = 10) -> pd.DataFrame:
        """Retrieve recent query history"""
        try:
            conn = psycopg2.connect(**self.db_config)
            
            if user_id:
                query = """
                SELECT prompt, sql_query, sport_context, created_at
                FROM query_history 
                WHERE user_id = %s 
                ORDER BY created_at DESC 
                LIMIT %s
                """
                df = pd.read_sql(query, conn, params=(user_id, limit))
            else:
                query = """
                SELECT prompt, sql_query, sport_context, created_at
                FROM query_history 
                ORDER BY created_at DESC 
                LIMIT %s
                """
                df = pd.read_sql(query, conn, params=(limit,))
            
            conn.close()
            return df
            
        except Exception as e:
            print(f"Warning: Could not retrieve query history: {e}")
            return pd.DataFrame()
    
    # TODO: VISUALIZATION METHODS - TEMPORARILY DISABLED
    # These methods need debugging for proper chart rendering in Streamlit
    def smart_chart_selection(self, df: pd.DataFrame) -> dict:
        """Smart chart selection based on data structure without API calls"""
        if df.empty:
            return {"error": "No data available for visualization"}
        
        # Analyze the data structure with more flexible detection
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32', 'number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Try to detect numeric columns that are stored as objects
        for col in df.columns:
            if col not in numeric_cols and df[col].dtype == 'object':
                try:
                    sample_vals = df[col].dropna().head(10)
                    if len(sample_vals) > 0:
                        pd.to_numeric(sample_vals, errors='raise')
                        numeric_cols.append(col)
                        if col in categorical_cols:
                            categorical_cols.remove(col)
                except:
                    pass
        
        # Smart chart selection logic
        if datetime_cols and numeric_cols:
            return {
                "chart_type": "line_chart",
                "x_column": datetime_cols[0],
                "y_column": numeric_cols[0],
                "color_column": categorical_cols[0] if categorical_cols else None,
                "title": f"{numeric_cols[0]} over Time",
                "reasoning": "Time series data detected - showing trend over time"
            }
        elif categorical_cols and numeric_cols:
            return {
                "chart_type": "bar_chart", 
                "x_column": categorical_cols[0],
                "y_column": numeric_cols[0],
                "color_column": None,
                "title": f"{numeric_cols[0]} by {categorical_cols[0]}",
                "reasoning": "Categorical data with numeric values - showing comparison"
            }
        elif len(numeric_cols) >= 2:
            return {
                "chart_type": "scatter_chart",
                "x_column": numeric_cols[0], 
                "y_column": numeric_cols[1],
                "color_column": categorical_cols[0] if categorical_cols else None,
                "title": f"{numeric_cols[1]} vs {numeric_cols[0]}",
                "reasoning": "Multiple numeric columns - showing correlation"
            }
        elif numeric_cols:
            # Single numeric column - use first available categorical or index
            x_col = categorical_cols[0] if categorical_cols else df.columns[0]
            return {
                "chart_type": "bar_chart",
                "x_column": x_col,
                "y_column": numeric_cols[0],
                "color_column": None,
                "title": f"{numeric_cols[0]} Distribution",
                "reasoning": "Single numeric column - showing distribution"
            }
        else:
            return {"error": "Unable to determine appropriate visualization - no numeric data found"}
    
    def generate_streamlit_visualization(self, df: pd.DataFrame, query: str) -> dict:
        """Generate appropriate Streamlit visualization based on data and query"""
        if df.empty:
            return {"error": "No data available for visualization"}
        
        # Analyze the data structure with more flexible detection
        numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32', 'number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        # Try to detect numeric columns that are stored as objects
        for col in df.columns:
            if col not in numeric_cols and df[col].dtype == 'object':
                try:
                    # Try to convert a sample to see if it's numeric
                    sample_vals = df[col].dropna().head(10)
                    if len(sample_vals) > 0:
                        pd.to_numeric(sample_vals, errors='raise')
                        numeric_cols.append(col)
                        if col in categorical_cols:
                            categorical_cols.remove(col)
                except:
                    pass
        
        # Get column info for Claude analysis
        columns_info = []
        for col in df.columns:
            col_type = str(df[col].dtype)
            sample_values = df[col].dropna().head(3).tolist()
            columns_info.append(f"{col} ({col_type}): {sample_values}")
        
        data_sample = df.head(5).to_string()
        
        if not self.claude:
            # Fallback logic without Claude
            return self._create_default_visualization(df, numeric_cols, categorical_cols, datetime_cols)
        
        prompt = f"""
        Recommend the best Streamlit visualization for this NFL betting data. Choose from these options:
        - line_chart: for trends over time
        - bar_chart: for comparing categories
        - area_chart: for cumulative data over time  
        - scatter_chart: for correlations between variables
        - map: for geographic data
        
        Original Query: {query}
        Data Shape: {df.shape[0]} rows, {df.shape[1]} columns
        
        Available Columns:
        - Numeric: {numeric_cols}
        - Categorical: {categorical_cols} 
        - DateTime: {datetime_cols}
        
        Columns Details:
        {chr(10).join(columns_info)}
        
        Data Sample:
        {data_sample}
        
        Respond with ONLY a JSON object like:
        {{
            "chart_type": "line_chart",
            "x_column": "column_name",
            "y_column": "column_name", 
            "color_column": "column_name_or_null",
            "title": "Chart Title",
            "reasoning": "Why this chart type is best"
        }}
        """
        
        try:
            response = self.claude.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            response_text = response.content[0].text.strip()
            
            # Clean up JSON response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            viz_config = json.loads(response_text.strip())
            return viz_config
            
        except Exception as e:
            # Fallback to default logic
            return self._create_default_visualization(df, numeric_cols, categorical_cols, datetime_cols)
    
    def _create_default_visualization(self, df: pd.DataFrame, numeric_cols: list, categorical_cols: list, datetime_cols: list) -> dict:
        """Create default visualization when Claude is not available"""
        if datetime_cols and numeric_cols:
            return {
                "chart_type": "line_chart",
                "x_column": datetime_cols[0],
                "y_column": numeric_cols[0],
                "color_column": categorical_cols[0] if categorical_cols else None,
                "title": f"{numeric_cols[0]} over {datetime_cols[0]}",
                "reasoning": "Time series data detected"
            }
        elif categorical_cols and numeric_cols:
            return {
                "chart_type": "bar_chart", 
                "x_column": categorical_cols[0],
                "y_column": numeric_cols[0],
                "color_column": None,
                "title": f"{numeric_cols[0]} by {categorical_cols[0]}",
                "reasoning": "Categorical vs numeric data"
            }
        elif len(numeric_cols) >= 2:
            return {
                "chart_type": "scatter_chart",
                "x_column": numeric_cols[0], 
                "y_column": numeric_cols[1],
                "color_column": categorical_cols[0] if categorical_cols else None,
                "title": f"{numeric_cols[1]} vs {numeric_cols[0]}",
                "reasoning": "Multiple numeric columns for correlation"
            }
        else:
            return {"error": "Unable to determine appropriate visualization"}
    
    def render_streamlit_chart(self, df: pd.DataFrame, viz_config: dict):
        """Render the chart using Streamlit's native functions"""
        try:
            chart_type = viz_config.get("chart_type")
            x_col = viz_config.get("x_column")
            y_col = viz_config.get("y_column") 
            color_col = viz_config.get("color_column")
            title = viz_config.get("title", "Chart")
            
            st.write(f"**{title}**")
            
            # Debug info
            st.write(f"Chart type: {chart_type}, X: {x_col}, Y: {y_col}")
            
            # Prepare the data
            chart_data = df.copy()
            
            # Drop rows with null values in key columns
            if x_col and y_col:
                chart_data = chart_data.dropna(subset=[x_col, y_col])
            
            if chart_data.empty:
                st.warning("No data available after removing null values")
                return False
            
            if chart_type == "line_chart":
                if x_col and y_col and x_col in chart_data.columns and y_col in chart_data.columns:
                    # For line charts, sort by x column and create a simple DataFrame
                    chart_data = chart_data.sort_values(x_col)
                    display_data = chart_data[[x_col, y_col]].set_index(x_col)
                    st.line_chart(display_data, use_container_width=True)
                    
            elif chart_type == "bar_chart":
                if x_col and y_col and x_col in chart_data.columns and y_col in chart_data.columns:
                    # Group and aggregate for bar chart
                    display_data = chart_data.groupby(x_col)[y_col].sum().reset_index().set_index(x_col)
                    st.bar_chart(display_data, use_container_width=True)
                    
            elif chart_type == "area_chart":
                if x_col and y_col and x_col in chart_data.columns and y_col in chart_data.columns:
                    chart_data = chart_data.sort_values(x_col)
                    display_data = chart_data[[x_col, y_col]].set_index(x_col)
                    st.area_chart(display_data, use_container_width=True)
                    
            elif chart_type == "scatter_chart":
                if x_col and y_col and x_col in chart_data.columns and y_col in chart_data.columns:
                    st.scatter_chart(chart_data, x=x_col, y=y_col, color=color_col, use_container_width=True)
                    
            else:
                st.error(f"Unsupported chart type: {chart_type}")
                return False
            
            if viz_config.get("reasoning"):
                st.caption(f"💡 {viz_config['reasoning']}")
                
            return True
            
        except Exception as e:
            st.error(f"Error rendering chart: {str(e)}")
            st.write(f"Debug - Exception details: {e}")
            return False

def main():
    """Main Streamlit application"""
    st.set_page_config(
        page_title="Sports Betting Analytics",
        page_icon="🏆",
        layout="wide",
        initial_sidebar_state="collapsed"
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
        .sport-selector {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 8px;
            margin-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>🏆 Sports Betting Analytics Dashboard</h1>
        <p>Live Odds & AI-Powered Analysis</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Sport Selection
    st.markdown('<div class="sport-selector">', unsafe_allow_html=True)
    col_sport1, col_sport2 = st.columns([1, 3])
    
    with col_sport1:
        st.markdown("**Select Sport:**")
        
    with col_sport2:
        sport_options = {
            "🏈 NFL": "americanfootball_nfl",
            "🏈 NCAA Football": "americanfootball_ncaaf", 
            "🏀 NBA": "basketball_nba",
            "🏀 NCAA Basketball": "basketball_ncaab"
        }
        
        selected_sport_display = st.selectbox(
            "",
            options=list(sport_options.keys()),
            index=0,
            label_visibility="collapsed",
            key="sport_selector"
        )
        
        selected_sport = sport_options[selected_sport_display]
        st.session_state['selected_sport'] = selected_sport
        st.session_state['selected_sport_display'] = selected_sport_display
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.selected_sport = "americanfootball_nfl"
        st.session_state.selected_sport_display = "🏈 NFL"
    
    # Initialize app
    app = NFLReportsApp()
    
    # Quick connection check (no sidebar)
    if not app.test_database_connection():
        st.error("❌ Database Connection Failed")
        st.stop()
    
    # Main tabbed interface
    tab1, tab2 = st.tabs(["📊 Current Odds", "🧠 AI Generator"])
    
    with tab1:
        show_current_odds_tab(app)
    
    with tab2:
        show_ai_generator_tab(app)

def show_current_odds_tab(app):
    """Display current odds for the selected sport"""
    st.subheader(f"📊 Current Odds - {st.session_state.get('selected_sport_display', '🏈 NFL')}")
    
    # Refresh button
    col_refresh1, col_refresh2 = st.columns([1, 4])
    with col_refresh1:
        refresh_odds = st.button("🔄 Refresh Odds")
    
    with col_refresh2:
        st.info("💡 Live odds data from your database for the selected sport")
    
    # Query current odds from database
    if 'selected_sport' in st.session_state:
        sport = st.session_state['selected_sport']
        
        # Get latest odds for the selected sport
        try:
            query = f"""
            SELECT 
                g.commence_time,
                ht.team_name as home_team,
                at.team_name as away_team,
                bm.bookmaker_title,
                s.home_spread,
                s.away_spread,
                s.home_price,
                s.away_price,
                s.snapshot_timestamp
            FROM games g
            JOIN sports sp ON g.sport_id = sp.sport_id
            JOIN teams ht ON g.home_team_id = ht.team_id
            JOIN teams at ON g.away_team_id = at.team_id
            JOIN spreads s ON g.game_id = s.game_id
            JOIN bookmakers bm ON s.bookmaker_id = bm.bookmaker_id
            WHERE sp.sport_key = '{sport}'
              AND g.commence_time > NOW()
              AND s.snapshot_timestamp = (
                  SELECT MAX(snapshot_timestamp) 
                  FROM spreads s2 
                  WHERE s2.game_id = s.game_id AND s2.bookmaker_id = s.bookmaker_id
              )
            ORDER BY g.commence_time, ht.team_name, bm.bookmaker_title
            LIMIT 100
            """
            
            df = app.execute_sql_query(query)
            
            if not df.empty:
                # Format the data for display
                formatted_df = app.format_dataframe_for_display(df.copy())
                st.dataframe(formatted_df, use_container_width=True)
                
                # Quick stats
                col_stat1, col_stat2, col_stat3 = st.columns(3)
                with col_stat1:
                    st.metric("Upcoming Games", len(df['home_team'].unique()))
                with col_stat2:
                    st.metric("Bookmakers", len(df['bookmaker_title'].unique()))
                with col_stat3:
                    latest_update = df['snapshot_timestamp'].max()
                    st.metric("Last Update", latest_update.strftime('%m/%d %I:%M %p') if latest_update else "N/A")
                
            else:
                st.warning(f"No current odds found for {st.session_state.get('selected_sport_display', 'selected sport')}. This could mean:")
                st.write("- No upcoming games scheduled")
                st.write("- Data needs to be fetched from the odds API")
                st.write("- Sport not yet supported in database")
                
        except Exception as e:
            st.error(f"Error loading current odds: {str(e)}")
            st.write("This usually means the sport data hasn't been collected yet.")

def show_ai_generator_tab(app):
    """Display the AI-powered query generator"""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("🔍 Natural Language Query")
        
        # Query input with sport context
        sport_context = st.session_state.get('selected_sport_display', 'NFL')
        user_query = st.text_area(
            f"Ask questions about {sport_context} betting data in plain English:",
            height=100,
            placeholder=f"Example: Show me the latest spreads for {sport_context} games this week"
        )
        
        # Single action button - does everything automatically
        if st.button("🚀 Get Results", type="primary", use_container_width=True) and user_query:
            with st.spinner("Analyzing your request..."):
                # Generate SQL
                sql_query = app.generate_sql_with_claude(user_query)
                
                if sql_query:
                    # Execute immediately
                    with st.spinner("Retrieving data..."):
                        df = app.execute_sql_query(sql_query)
                        
                        if not df.empty:
                            st.session_state['query_results'] = df
                            st.session_state['last_query'] = user_query
                            st.session_state['last_sql'] = sql_query
                            
                            # Store the prompt-query pair
                            app.store_query_history(user_query, sql_query)
                            
                            st.success(f"✅ Found {len(df)} results!")
                        else:
                            st.warning("No results found for your query.")
                else:
                    st.error("❌ Could not process your request. Please try rephrasing your question.")
        
        
        # Display results
        if 'query_results' in st.session_state:
            df = st.session_state['query_results']
            
            st.subheader("📊 Results")
            
            # Format and display data
            formatted_df = app.format_dataframe_for_display(df.copy())
            st.dataframe(formatted_df, use_container_width=True)
            
            # Action buttons
            col_download, col_sql = st.columns([1, 1])
            
            with col_download:
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download CSV",
                    data=csv,
                    file_name=f"sports_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col_sql:
                if st.button("🔍 View SQL Query"):
                    st.session_state['show_sql'] = not st.session_state.get('show_sql', False)
            
            # Show SQL if requested
            if st.session_state.get('show_sql', False) and 'last_sql' in st.session_state:
                with st.expander("📝 Generated SQL Query", expanded=True):
                    st.code(st.session_state['last_sql'], language='sql')
            
            # TODO: Fix visualization functionality - currently has issues with chart rendering
            # with col_action2:
            #     generate_viz = st.button("📊 Generate Visual")
            
            # TODO: VISUALIZATION FUNCTIONALITY - TEMPORARILY DISABLED
            # Issues to fix:
            # - Chart rendering not displaying properly
            # - Y-axis column detection needs improvement  
            # - Better error handling for chart data preparation
            # - Streamlit chart compatibility with different data types
            #
            # # Generate visualization
            # if generate_viz:
            #     # Smart chart selection based on data structure (no API call needed)
            #     viz_config = app.smart_chart_selection(df)
            #     
            #     if 'error' in viz_config:
            #         st.error(viz_config['error'])
            #     else:
            #         st.session_state['viz_config'] = viz_config
            #         st.success("Chart configuration ready!")
            # 
            # # Display visualization if generated
            # if 'viz_config' in st.session_state:
            #     st.subheader("📊 Data Visualization")
            #     
            #     viz_config = st.session_state['viz_config']
            #     
            #     # Show the configuration
            #     with st.expander("View Visualization Configuration"):
            #         st.json(viz_config)
            #     
            #     # Allow manual adjustment
            #     col_viz1, col_viz2 = st.columns(2)
            #     
            #     with col_viz1:
            #         chart_types = ["line_chart", "bar_chart", "area_chart", "scatter_chart"]
            #         selected_chart_type = st.selectbox(
            #             "Chart Type:",
            #             chart_types,
            #             index=chart_types.index(viz_config.get("chart_type", "bar_chart"))
            #         )
            #         
            #         x_column = st.selectbox(
            #             "X-axis Column:",
            #             df.columns.tolist(),
            #             index=df.columns.tolist().index(viz_config.get("x_column", df.columns[0])) if viz_config.get("x_column") in df.columns else 0
            #         )
            #     
            #     with col_viz2:
            #         # Get numeric columns with more flexible detection
            #         numeric_cols = df.select_dtypes(include=['int64', 'float64', 'int32', 'float32', 'number']).columns.tolist()
            #         
            #         # If no numeric columns found, try to convert some columns
            #         if not numeric_cols:
            #             for col in df.columns:
            #                 try:
            #                     # Try to convert to numeric, excluding obvious text columns
            #                     if not col.lower() in ['team_name', 'bookmaker_title', 'status'] and df[col].dtype == 'object':
            #                         pd.to_numeric(df[col], errors='raise')
            #                         numeric_cols.append(col)
            #                 except:
            #                     pass
            #         
            #         # If still no numeric columns, use all columns as fallback
            #         if not numeric_cols:
            #             numeric_cols = df.columns.tolist()
            #             st.warning("⚠️ No numeric columns detected. Showing all columns.")
            #         
            #         st.write(f"📊 Available numeric columns: {numeric_cols}")
            #         
            #         y_column = st.selectbox(
            #             "Y-axis Column:",
            #             numeric_cols,
            #             index=numeric_cols.index(viz_config.get("y_column", numeric_cols[0])) if viz_config.get("y_column") in numeric_cols and numeric_cols else 0
            #         )
            #         
            #         categorical_cols = ["None"] + df.select_dtypes(include=['object', 'category']).columns.tolist()
            #         color_column = st.selectbox(
            #             "Color Column (optional):",
            #             categorical_cols,
            #             index=categorical_cols.index(viz_config.get("color_column")) if viz_config.get("color_column") in categorical_cols else 0
            #         )
            #     
            #     # Update configuration
            #     updated_config = {
            #         "chart_type": selected_chart_type,
            #         "x_column": x_column,
            #         "y_column": y_column,
            #         "color_column": color_column if color_column != "None" else None,
            #         "title": viz_config.get("title", "Chart"),
            #         "reasoning": viz_config.get("reasoning", "")
            #     }
            #     
            #     # Render the chart
            #     st.markdown("---")
            #     success = app.render_streamlit_chart(df, updated_config)
            #     
            #     if success:
            #         st.session_state['current_viz_config'] = updated_config
            
            # Generate insights (only once per query)
            if app.claude and 'last_query' in st.session_state:
                st.subheader("🧠 AI Insights")
                
                # Check if insights already exist for this query
                current_query_hash = hash(st.session_state['last_query'] + str(df.shape))
                
                if 'insights' not in st.session_state or st.session_state.get('insights_query_hash') != current_query_hash:
                    with st.spinner("Generating insights..."):
                        insights = app.generate_insights_with_claude(df, st.session_state['last_query'])
                        st.session_state['insights'] = insights
                        st.session_state['insights_query_hash'] = current_query_hash
                
                # Display the stored insights
                st.markdown(st.session_state['insights'])
    
    with col2:
        # Tabs for sample queries and history
        tab_samples, tab_history = st.tabs(["💡 Sample Queries", "📚 Query History"])
        
        with tab_samples:
            sample_queries = app.get_sample_queries()
            
            for query_info in sample_queries:
                with st.container():
                    st.markdown(f"""
                    <div class="query-card">
                        <strong>{query_info['title']}</strong><br>
                        <small style="color: #666;">{query_info['query']}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"Use Query: {query_info['title']}", key=f"btn_{hash(query_info['title'])}"):
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
        
        with tab_history:
            st.markdown("**Recent Queries**")
            
            # Optional user ID input for future user tracking
            user_id = st.text_input("User ID (optional):", placeholder="Enter your user ID to track personal history")
            
            # Get and display query history
            if st.button("🔄 Refresh History"):
                st.session_state['history_refresh'] = True
            
            history_df = app.get_query_history(user_id if user_id else None, limit=5)
            
            if not history_df.empty:
                for idx, row in history_df.iterrows():
                    with st.expander(f"📝 {row['prompt'][:50]}..." if len(row['prompt']) > 50 else f"📝 {row['prompt']}"):
                        st.write(f"**Sport:** {row['sport_context']}")
                        st.write(f"**Date:** {row['created_at']}")
                        st.code(row['sql_query'], language='sql')
                        
                        if st.button(f"🔄 Rerun This Query", key=f"rerun_{hash(str(row.get('prompt', '')))}_{idx}"):
                            st.session_state['generated_sql'] = row['sql_query']
                            st.session_state['last_query'] = row['prompt']
                            st.rerun()
            else:
                st.info("No query history found. Run some analyses to build your history!")

if __name__ == "__main__":
    main()