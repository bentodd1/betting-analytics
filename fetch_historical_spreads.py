#!/usr/bin/env python3
"""
Fetch historical NFL spreads data from The Odds API and store in PostgreSQL database
"""
import os
import sys
import requests
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
import time

# Add database module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

import psycopg2
from psycopg2.extras import RealDictCursor

class HistoricalNFLSpreadsAPI:
    """Handles historical NFL spreads data fetching and database operations"""
    
    def __init__(self, api_key: str, db_config: Dict[str, Any]):
        self.api_key = api_key
        self.base_url = "https://api.the-odds-api.com/v4"
        self.sport = "americanfootball_nfl"
        self.db_config = db_config
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def fetch_historical_odds(self, timestamp: str, markets: str = "spreads", 
                             regions: str = "us", bookmakers: Optional[str] = None,
                             date_format: str = "iso") -> Dict[Any, Any]:
        """
        Fetch historical NFL odds data from The Odds API
        
        Args:
            timestamp: ISO timestamp for historical data (e.g., "2024-01-15T18:00:00Z")
            markets: Comma-separated list of markets (spreads, h2h, totals)
            regions: Comma-separated list of regions (us, uk, au, eu)
            bookmakers: Optional comma-separated list of bookmakers
            date_format: Date format (iso or unix)
            
        Returns:
            API response as dictionary
        """
        url = f"{self.base_url}/historical/sports/{self.sport}/odds"
        
        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "date": timestamp,
            "dateFormat": date_format,
            "oddsFormat": "american"
        }
        
        if bookmakers:
            params["bookmakers"] = bookmakers
            
        print(f"🔄 Fetching historical NFL {markets} data for {timestamp}...")
        print(f"📡 URL: {url}")
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract snapshot info from response
            snapshot_info = {
                'data': data.get('data', []),
                'timestamp': data.get('timestamp'),
                'previous_timestamp': data.get('previous_timestamp'),
                'next_timestamp': data.get('next_timestamp')
            }
            
            print(f"✅ Successfully fetched {len(snapshot_info['data'])} games")
            print(f"📈 API requests remaining: {response.headers.get('x-requests-remaining', 'Unknown')}")
            print(f"🕐 Snapshot timestamp: {snapshot_info['timestamp']}")
            
            if snapshot_info['previous_timestamp']:
                print(f"⬅️  Previous: {snapshot_info['previous_timestamp']}")
            if snapshot_info['next_timestamp']:
                print(f"➡️  Next: {snapshot_info['next_timestamp']}")
                
            return snapshot_info
            
        except requests.exceptions.RequestException as e:
            print(f"❌ API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                print(f"Status code: {e.response.status_code}")
                print(f"Response: {e.response.text}")
            raise
    
    def store_api_snapshot(self, cursor, snapshot_info: Dict[str, Any]) -> int:
        """Store API snapshot metadata"""
        snapshot_timestamp = datetime.fromisoformat(snapshot_info['timestamp'].replace('Z', '+00:00'))
        
        previous_ts = None
        if snapshot_info.get('previous_timestamp'):
            previous_ts = datetime.fromisoformat(snapshot_info['previous_timestamp'].replace('Z', '+00:00'))
            
        next_ts = None  
        if snapshot_info.get('next_timestamp'):
            next_ts = datetime.fromisoformat(snapshot_info['next_timestamp'].replace('Z', '+00:00'))
        
        cursor.execute("""
            INSERT INTO api_snapshots (
                sport_key, snapshot_timestamp, previous_timestamp, 
                next_timestamp, games_count, raw_response
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (sport_key, snapshot_timestamp) 
            DO UPDATE SET
                previous_timestamp = EXCLUDED.previous_timestamp,
                next_timestamp = EXCLUDED.next_timestamp,
                games_count = EXCLUDED.games_count,
                raw_response = EXCLUDED.raw_response
            RETURNING snapshot_id
        """, (
            self.sport, snapshot_timestamp, previous_ts, next_ts,
            len(snapshot_info['data']), json.dumps(snapshot_info)
        ))
        
        return cursor.fetchone()['snapshot_id']
    
    def get_or_create_team(self, cursor, team_name: str, sport_id: int) -> int:
        """Get existing team ID or create new team"""
        cursor.execute(
            "SELECT team_id FROM teams WHERE team_name = %s AND sport_id = %s",
            (team_name, sport_id)
        )
        result = cursor.fetchone()
        
        if result:
            return result['team_id']
        
        cursor.execute(
            "INSERT INTO teams (team_name, sport_id) VALUES (%s, %s) RETURNING team_id",
            (team_name, sport_id)
        )
        return cursor.fetchone()['team_id']
    
    def get_or_create_bookmaker(self, cursor, bookmaker_key: str, bookmaker_title: str) -> int:
        """Get existing bookmaker ID or create new bookmaker"""
        cursor.execute(
            "SELECT bookmaker_id FROM bookmakers WHERE bookmaker_key = %s",
            (bookmaker_key,)
        )
        result = cursor.fetchone()
        
        if result:
            return result['bookmaker_id']
        
        cursor.execute(
            "INSERT INTO bookmakers (bookmaker_key, bookmaker_title) VALUES (%s, %s) RETURNING bookmaker_id",
            (bookmaker_key, bookmaker_title)
        )
        return cursor.fetchone()['bookmaker_id']
    
    def store_historical_spreads_data(self, snapshot_info: Dict[str, Any]) -> Dict[str, int]:
        """
        Store historical spreads data in the database
        
        Args:
            snapshot_info: Snapshot data from API including timestamp info
            
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
                'spreads': 0,
                'snapshots': 0
            }
            
            # Store API snapshot metadata
            snapshot_id = self.store_api_snapshot(cursor, snapshot_info)
            counts['snapshots'] = 1
            
            snapshot_timestamp = datetime.fromisoformat(snapshot_info['timestamp'].replace('Z', '+00:00'))
            odds_data = snapshot_info['data']
            
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
                                # Insert spread data with historical timestamp
                                cursor.execute("""
                                    INSERT INTO spreads (
                                        game_id, bookmaker_id, home_spread, home_price, 
                                        away_spread, away_price, last_update, 
                                        snapshot_timestamp, raw_outcomes, is_latest
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                                    snapshot_timestamp, json.dumps(outcomes), False  # Historical data is not latest
                                ))
                                
                                if cursor.rowcount > 0:
                                    counts['spreads'] += 1
                                    
                                print(f"   📊 {bookmaker_key}: {away_team} {away_spread:+.1f} ({away_price:+.0f}) | {home_team} {home_spread:+.1f} ({home_price:+.0f})")
            
            # Update total_odds_count in api_snapshots
            cursor.execute(
                "UPDATE api_snapshots SET total_odds_count = %s WHERE snapshot_id = %s",
                (counts['spreads'], snapshot_id)
            )
            
            # Commit transaction
            conn.commit()
            
            print(f"\n✅ Historical data stored successfully:")
            print(f"   📅 Snapshot: {snapshot_timestamp}")
            print(f"   🏈 Games: {counts['games']}")
            print(f"   📊 Spreads: {counts['spreads']}")
            
            return counts
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Database error: {e}")
            raise
        finally:
            cursor.close()
            conn.close()
    
    def fetch_historical_range(self, start_date: str, end_date: str, 
                              interval_hours: int = 24, bookmakers: Optional[str] = None) -> Dict[str, int]:
        """
        Fetch historical spreads for a date range
        
        Args:
            start_date: Start date in ISO format (e.g., "2024-01-01")
            end_date: End date in ISO format
            interval_hours: Hours between snapshots (default 24 for daily)
            bookmakers: Optional comma-separated list of bookmakers
            
        Returns:
            Dictionary with total insertion counts
        """
        start_dt = datetime.fromisoformat(start_date + "T12:00:00Z").replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_date + "T12:00:00Z").replace(tzinfo=timezone.utc)
        
        total_counts = {
            'games': 0,
            'spreads': 0,
            'snapshots': 0
        }
        
        current_dt = start_dt
        while current_dt <= end_dt:
            timestamp = current_dt.isoformat().replace('+00:00', 'Z')
            
            try:
                print(f"\n🕐 Fetching data for {timestamp}")
                snapshot_info = self.fetch_historical_odds(
                    timestamp=timestamp,
                    markets="spreads",
                    bookmakers=bookmakers
                )
                
                counts = self.store_historical_spreads_data(snapshot_info)
                
                # Add to totals
                for key in total_counts:
                    total_counts[key] += counts.get(key, 0)
                
                # Rate limiting - be nice to the API
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Failed to fetch data for {timestamp}: {e}")
                # Continue with next timestamp
                
            current_dt += timedelta(hours=interval_hours)
        
        print(f"\n🎉 Historical range complete!")
        print(f"📊 Total summary: {total_counts['snapshots']} snapshots, {total_counts['games']} games, {total_counts['spreads']} spreads")
        
        return total_counts


def main():
    """Main function to fetch historical NFL spreads"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch historical NFL spreads data')
    parser.add_argument('--timestamp', help='Specific timestamp (ISO format, e.g., 2024-01-15T18:00:00Z)')
    parser.add_argument('--start-date', help='Start date for range (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for range (YYYY-MM-DD)')
    parser.add_argument('--interval', type=int, default=24, help='Hours between snapshots (default: 24)')
    parser.add_argument('--bookmakers', help='Comma-separated bookmakers (e.g., draftkings,fanduel)')
    
    args = parser.parse_args()
    
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
    
    print("🏈 Historical NFL Spreads Data Fetcher")
    print("=" * 50)
    
    try:
        # Initialize API client
        nfl_api = HistoricalNFLSpreadsAPI(api_key, db_config)
        
        # Test database connection
        conn = nfl_api.get_connection()
        print("✅ Database connection successful")
        conn.close()
        
        if args.timestamp:
            # Fetch specific timestamp
            print(f"🕐 Fetching data for specific timestamp: {args.timestamp}")
            snapshot_info = nfl_api.fetch_historical_odds(
                timestamp=args.timestamp,
                bookmakers=args.bookmakers
            )
            counts = nfl_api.store_historical_spreads_data(snapshot_info)
            
        elif args.start_date and args.end_date:
            # Fetch date range
            print(f"📅 Fetching data from {args.start_date} to {args.end_date}")
            print(f"⏰ Interval: {args.interval} hours")
            counts = nfl_api.fetch_historical_range(
                start_date=args.start_date,
                end_date=args.end_date,
                interval_hours=args.interval,
                bookmakers=args.bookmakers
            )
            
        else:
            # Default: fetch data from 1 week ago
            one_week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')
            
            print(f"📅 No specific date provided. Fetching last week: {one_week_ago} to {today}")
            counts = nfl_api.fetch_historical_range(
                start_date=one_week_ago,
                end_date=today,
                interval_hours=24,
                bookmakers=args.bookmakers
            )
        
        print(f"\n🎉 Successfully processed historical NFL spreads data!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()