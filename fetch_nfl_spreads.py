#!/usr/bin/env python3
"""
Fetch NFL spreads data from The Odds API and store in PostgreSQL database
"""
import os
import sys
import requests
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

# Add database module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

import psycopg2
from psycopg2.extras import RealDictCursor

class NFLSpreadsAPI:
    """Handles NFL spreads data fetching and database operations"""
    
    def __init__(self, api_key: str, db_config: Dict[str, Any]):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "americanfootball_nfl"
        self.db_config = db_config
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def fetch_nfl_odds(self, markets: str = "spreads", regions: str = "us", 
                       bookmakers: Optional[str] = None, date_format: str = "iso") -> Dict[Any, Any]:
        """
        Fetch NFL odds data from The Odds API
        
        Args:
            markets: Comma-separated list of markets (spreads, h2h, totals)
            regions: Comma-separated list of regions (us, uk, au, eu)
            bookmakers: Optional comma-separated list of bookmakers
            date_format: Date format (iso or unix)
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/sports/{self.sport}/odds"
        
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "dateFormat": date_format,
            "oddsFormat": "american"
        }
        
        if bookmakers:
            params["bookmakers"] = bookmakers
            
        print(f"🔄 Fetching NFL {markets} data from The Odds API...")
        print(f"📡 URL: {url}")
        print(f"📊 Markets: {markets}")
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            print(f"✅ Successfully fetched {len(data)} games")
            print(f"📈 API requests remaining: {response.headers.get('x-requests-remaining', 'Unknown')}")
            
            return data
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status code: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            raise
    
    def get_or_create_team(self, cursor, team_name: str, sport_id: int) -> int:
        """Get existing team ID or create new team"""
        # Check if team exists
        cursor.execute(
            "SELECT team_id FROM teams WHERE team_name = %s AND sport_id = %s",
            (team_name, sport_id)
        )
        result = cursor.fetchone()
        
        if result:
            return result['team_id']
        
        # Create new team
        cursor.execute(
            "INSERT INTO teams (team_name, sport_id) VALUES (%s, %s) RETURNING team_id",
            (team_name, sport_id)
        )
        return cursor.fetchone()['team_id']
    
    def get_or_create_bookmaker(self, cursor, bookmaker_key: str, bookmaker_title: str) -> int:
        """Get existing bookmaker ID or create new bookmaker"""
        # Check if bookmaker exists
        cursor.execute(
            "SELECT bookmaker_id FROM bookmakers WHERE bookmaker_key = %s",
            (bookmaker_key,)
        )
        result = cursor.fetchone()
        
        if result:
            return result['bookmaker_id']
        
        # Create new bookmaker
        cursor.execute(
            "INSERT INTO bookmakers (bookmaker_key, bookmaker_title) VALUES (%s, %s) RETURNING bookmaker_id",
            (bookmaker_key, bookmaker_title)
        )
        return cursor.fetchone()['bookmaker_id']
    
    def store_spreads_data(self, odds_data: List[Dict[Any, Any]]) -> Dict[str, int]:
        """
        Store spreads data in the database
        
        Args:
            odds_data: List of game odds data from API
            
        Returns:
            Dictionary with insertion counts
        """
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get NFL sport ID
            cursor.execute("SELECT sport_id FROM sports WHERE sport_key = %s", (self.sport,))
            sport_result = cursor.fetchone()
            if not sport_result:
                raise ValueError(f"Sport {self.sport} not found in database")
            sport_id = sport_result['sport_id']
            
            counts = {
                'games': 0,
                'teams': 0,
                'bookmakers': 0,
                'spreads': 0
            }
            
            snapshot_timestamp = datetime.now(timezone.utc)
            
            for game_data in odds_data:
                game_id = game_data['id']
                commence_time = datetime.fromisoformat(game_data['commence_time'].replace('Z', '+00:00'))
                home_team = game_data['home_team']
                away_team = game_data['away_team']
                
                print(f"📋 Processing: {away_team} @ {home_team} ({game_id})")
                
                # Get or create teams
                home_team_id = self.get_or_create_team(cursor, home_team, sport_id)
                away_team_id = self.get_or_create_team(cursor, away_team, sport_id)
                
                # Insert or update game
                cursor.execute("""
                    INSERT INTO games (game_id, sport_id, commence_time, home_team_id, away_team_id, raw_data)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (game_id) DO UPDATE SET
                        commence_time = EXCLUDED.commence_time,
                        raw_data = EXCLUDED.raw_data,
                        updated_at = NOW()
                """, (game_id, sport_id, commence_time, home_team_id, away_team_id, json.dumps(game_data)))
                
                if cursor.rowcount > 0:
                    counts['games'] += 1
                
                # Process bookmakers and spreads
                for bookmaker_data in game_data.get('bookmakers', []):
                    bookmaker_key = bookmaker_data['key']
                    bookmaker_title = bookmaker_data['title']
                    last_update = datetime.fromisoformat(bookmaker_data['last_update'].replace('Z', '+00:00'))
                    
                    # Get or create bookmaker
                    bookmaker_id = self.get_or_create_bookmaker(cursor, bookmaker_key, bookmaker_title)
                    
                    # Process spreads market
                    for market in bookmaker_data.get('markets', []):
                        if market['key'] == 'spreads':
                            outcomes = market['outcomes']
                            
                            # Find home and away spreads
                            home_spread = None
                            home_price = None
                            away_spread = None
                            away_price = None
                            
                            for outcome in outcomes:
                                if outcome['name'] == home_team:
                                    home_spread = float(outcome['point'])
                                    home_price = float(outcome['price'])
                                elif outcome['name'] == away_team:
                                    away_spread = float(outcome['point'])
                                    away_price = float(outcome['price'])
                            
                            if home_spread is not None and away_spread is not None:
                                # Insert spread data
                                cursor.execute("""
                                    INSERT INTO spreads (
                                        game_id, bookmaker_id, home_spread, home_price, 
                                        away_spread, away_price, last_update, 
                                        snapshot_timestamp, raw_outcomes
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    ON CONFLICT (game_id, bookmaker_id, snapshot_timestamp) 
                                    DO UPDATE SET
                                        home_spread = EXCLUDED.home_spread,
                                        home_price = EXCLUDED.home_price,
                                        away_spread = EXCLUDED.away_spread,
                                        away_price = EXCLUDED.away_price,
                                        last_update = EXCLUDED.last_update,
                                        raw_outcomes = EXCLUDED.raw_outcomes
                                """, (
                                    game_id, bookmaker_id, home_spread, home_price,
                                    away_spread, away_price, last_update,
                                    snapshot_timestamp, json.dumps(outcomes)
                                ))
                                
                                if cursor.rowcount > 0:
                                    counts['spreads'] += 1
                                    
                                print(f"   📊 {bookmaker_key}: {away_team} {away_spread:+.1f} ({away_price:+.0f}) | {home_team} {home_spread:+.1f} ({home_price:+.0f})")
            
            # Commit transaction
            conn.commit()
            
            print(f"\n✅ Data stored successfully:")
            print(f"   Games: {counts['games']}")
            print(f"   Spreads: {counts['spreads']}")
            
            return counts
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Database error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def fetch_and_store_spreads(self, bookmakers: Optional[str] = None) -> Dict[str, int]:
        """
        Fetch NFL spreads and store in database
        
        Args:
            bookmakers: Optional comma-separated list of bookmakers
            
        Returns:
            Dictionary with insertion counts
        """
        # Fetch odds data
        odds_data = self.fetch_nfl_odds(markets="spreads", bookmakers=bookmakers)
        
        # Store in database
        counts = self.store_spreads_data(odds_data)
        
        return counts


def main():
    """Main function to fetch NFL spreads"""
    # Get API key
    api_key = os.getenv('ODDS_API_KEY')
    if not api_key:
        print("❌ ODDS_API_KEY environment variable not set")
        print("Set it with: export ODDS_API_KEY=your_api_key")
        sys.exit(1)
    
    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'betting_analytics'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }
    
    print("🏈 NFL Spreads Data Fetcher")
    print("=" * 50)
    
    try:
        # Initialize API client
        nfl_api = NFLSpreadsAPI(api_key, db_config)
        
        # Test database connection
        conn = nfl_api.get_connection()
        print("✅ Database connection successful")
        conn.close()
        
        # Fetch and store spreads data
        # You can specify specific bookmakers like: "draftkings,fanduel,betmgm"
        counts = nfl_api.fetch_and_store_spreads(bookmakers="draftkings,fanduel,betmgm,caesars")
        
        print(f"\n🎉 Successfully processed NFL spreads data!")
        print(f"📊 Summary: {counts['games']} games, {counts['spreads']} spreads")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()