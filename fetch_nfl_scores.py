#!/usr/bin/env python3
"""
NFL Scores Data Integration
Fetches game scores from nflverse and updates our database
"""

import os
import sys
import pandas as pd
import requests
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import psycopg2
from psycopg2.extras import RealDictCursor

# Add database module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

class NFLScoresIntegrator:
    """Integrates NFL scores data with our betting analytics database"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        self.nflverse_url = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
        
        # Team mapping from nflverse abbreviations to our team names
        self.team_mapping = {
            'ARI': 'Arizona Cardinals', 'ATL': 'Atlanta Falcons', 'BAL': 'Baltimore Ravens',
            'BUF': 'Buffalo Bills', 'CAR': 'Carolina Panthers', 'CHI': 'Chicago Bears',
            'CIN': 'Cincinnati Bengals', 'CLE': 'Cleveland Browns', 'DAL': 'Dallas Cowboys',
            'DEN': 'Denver Broncos', 'DET': 'Detroit Lions', 'GB': 'Green Bay Packers',
            'HOU': 'Houston Texans', 'IND': 'Indianapolis Colts', 'JAX': 'Jacksonville Jaguars',
            'KC': 'Kansas City Chiefs', 'LV': 'Las Vegas Raiders', 'LAC': 'Los Angeles Chargers',
            'LAR': 'Los Angeles Rams', 'LA': 'Los Angeles Rams', 'MIA': 'Miami Dolphins', 'MIN': 'Minnesota Vikings',
            'NE': 'New England Patriots', 'NO': 'New Orleans Saints', 'NYG': 'New York Giants',
            'NYJ': 'New York Jets', 'PHI': 'Philadelphia Eagles', 'PIT': 'Pittsburgh Steelers',
            'SF': 'San Francisco 49ers', 'SEA': 'Seattle Seahawks', 'TB': 'Tampa Bay Buccaneers',
            'TEN': 'Tennessee Titans', 'WAS': 'Washington Commanders',
            
            # Historical team names
            'OAK': 'Las Vegas Raiders', 'SD': 'Los Angeles Chargers', 'STL': 'Los Angeles Rams'
        }
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def fetch_nfl_scores_data(self, season_filter: Optional[int] = None) -> pd.DataFrame:
        """Fetch NFL scores data from nflverse"""
        print(f"🔄 Fetching NFL scores data from: {self.nflverse_url}")
        
        try:
            response = requests.get(self.nflverse_url)
            response.raise_for_status()
            
            # Read CSV data
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            print(f"✅ Fetched {len(df):,} games from nflverse")
            print(f"📅 Data covers seasons: {df['season'].min()} - {df['season'].max()}")
            
            # Filter by season if specified
            if season_filter:
                df = df[df['season'] == season_filter]
                print(f"🎯 Filtered to {season_filter} season: {len(df):,} games")
            
            return df
            
        except Exception as e:
            print(f"❌ Error fetching NFL scores data: {e}")
            return pd.DataFrame()
    
    def get_existing_games(self) -> pd.DataFrame:
        """Get existing games from our database"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT 
                    g.game_id,
                    g.commence_time,
                    ht.team_name as home_team_name,
                    at.team_name as away_team_name,
                    g.home_score as current_home_score,
                    g.away_score as current_away_score,
                    g.status
                FROM games g
                JOIN teams ht ON g.home_team_id = ht.team_id
                JOIN teams at ON g.away_team_id = at.team_id
                ORDER BY g.commence_time
            ''')
            
            results = cursor.fetchall()
            df = pd.DataFrame(results)
            
            print(f"📊 Found {len(df)} existing games in database")
            return df
            
        finally:
            cursor.close()
            conn.close()
    
    def map_team_name(self, nflverse_abbrev: str) -> str:
        """Map nflverse team abbreviation to our full team name"""
        return self.team_mapping.get(nflverse_abbrev, nflverse_abbrev)
    
    def find_game_matches(self, nfl_scores: pd.DataFrame, existing_games: pd.DataFrame) -> List[Dict[str, Any]]:
        """Find matches between nflverse games and our database games"""
        matches = []
        
        print("🔍 Matching games between nflverse and database...")
        
        for _, nfl_game in nfl_scores.iterrows():
            # Convert nflverse team abbreviations to full names
            nfl_home_team = self.map_team_name(nfl_game['home_team'])
            nfl_away_team = self.map_team_name(nfl_game['away_team'])
            
            # Convert gameday to date for comparison
            nfl_date = pd.to_datetime(nfl_game['gameday']).date()
            
            # Find matching games in our database
            # Match by teams and date (within a reasonable window)
            for _, db_game in existing_games.iterrows():
                db_date = pd.to_datetime(db_game['commence_time']).date()
                
                # Check if teams match and dates are close (same day or within 1 day)
                if (nfl_home_team == db_game['home_team_name'] and 
                    nfl_away_team == db_game['away_team_name'] and
                    abs((nfl_date - db_date).days) <= 1):
                    
                    matches.append({
                        'nfl_game_id': nfl_game['game_id'],
                        'db_game_id': db_game['game_id'],
                        'nfl_home_score': nfl_game['home_score'],
                        'nfl_away_score': nfl_game['away_score'],
                        'current_home_score': db_game['current_home_score'],
                        'current_away_score': db_game['current_away_score'],
                        'teams': f"{nfl_away_team} @ {nfl_home_team}",
                        'date': nfl_date,
                        'needs_update': (
                            pd.isna(db_game['current_home_score']) or 
                            pd.isna(db_game['current_away_score']) or
                            db_game['current_home_score'] != nfl_game['home_score'] or
                            db_game['current_away_score'] != nfl_game['away_score']
                        )
                    })
                    break
        
        print(f"🎯 Found {len(matches)} game matches")
        updates_needed = sum(1 for m in matches if m['needs_update'])
        print(f"📝 {updates_needed} games need score updates")
        
        return matches
    
    def update_game_scores(self, matches: List[Dict[str, Any]], dry_run: bool = False) -> int:
        """Update game scores in database"""
        if dry_run:
            print("🔍 DRY RUN - No actual database updates will be made")
            updates_needed = [m for m in matches if m['needs_update']]
            for match in updates_needed[:10]:  # Show first 10
                print(f"  Would update: {match['teams']} - {match['nfl_away_score']}-{match['nfl_home_score']}")
            if len(updates_needed) > 10:
                print(f"  ... and {len(updates_needed) - 10} more games")
            return len(updates_needed)
        
        updates_made = 0
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            for match in matches:
                if match['needs_update']:
                    cursor.execute('''
                        UPDATE games 
                        SET 
                            home_score = %s,
                            away_score = %s,
                            status = 'completed',
                            updated_at = NOW()
                        WHERE game_id = %s
                    ''', (
                        match['nfl_home_score'],
                        match['nfl_away_score'],
                        match['db_game_id']
                    ))
                    
                    updates_made += 1
                    
                    if updates_made % 50 == 0:
                        print(f"  📝 Updated {updates_made} games...")
            
            conn.commit()
            print(f"✅ Successfully updated {updates_made} game scores")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error updating scores: {e}")
            
        finally:
            cursor.close()
            conn.close()
        
        return updates_made
    
    def analyze_spread_outcomes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Analyze spread betting outcomes for completed games"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                WITH latest_spreads AS (
                    SELECT DISTINCT ON (game_id, bookmaker_id)
                        game_id,
                        bookmaker_id,
                        home_spread,
                        away_spread,
                        snapshot_timestamp
                    FROM spreads
                    ORDER BY game_id, bookmaker_id, snapshot_timestamp DESC
                )
                SELECT 
                    g.game_id,
                    ht.team_name as home_team,
                    at.team_name as away_team,
                    g.home_score,
                    g.away_score,
                    g.commence_time,
                    ls.home_spread,
                    ls.away_spread,
                    b.bookmaker_title,
                    ls.snapshot_timestamp,
                    -- Calculate actual margin
                    (g.home_score - g.away_score) as actual_margin,
                    -- Calculate spread outcome
                    CASE 
                        WHEN g.home_score IS NULL OR g.away_score IS NULL THEN 'No Result'
                        WHEN (g.home_score - g.away_score) > ABS(ls.home_spread) THEN 'Home Cover'
                        WHEN (g.home_score - g.away_score) < -ABS(ls.home_spread) THEN 'Away Cover'
                        ELSE 'Push'
                    END as spread_outcome
                FROM games g
                JOIN teams ht ON g.home_team_id = ht.team_id
                JOIN teams at ON g.away_team_id = at.team_id
                JOIN latest_spreads ls ON g.game_id = ls.game_id
                JOIN bookmakers b ON ls.bookmaker_id = b.bookmaker_id
                WHERE g.home_score IS NOT NULL 
                  AND g.away_score IS NOT NULL
                ORDER BY g.commence_time DESC
                LIMIT %s
            ''', (limit,))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
        finally:
            cursor.close()
            conn.close()
    
    def generate_score_summary(self) -> Dict[str, Any]:
        """Generate summary of score data integration"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get basic counts
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN home_score IS NOT NULL THEN 1 END) as games_with_scores,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_games
                FROM games
            ''')
            basic_stats = cursor.fetchone()
            
            # Get spread outcome statistics
            cursor.execute('''
                WITH latest_spreads AS (
                    SELECT DISTINCT ON (game_id, bookmaker_id)
                        game_id,
                        bookmaker_id,
                        home_spread,
                        away_spread
                    FROM spreads
                    ORDER BY game_id, bookmaker_id, snapshot_timestamp DESC
                )
                SELECT 
                    CASE 
                        WHEN g.home_score IS NULL OR g.away_score IS NULL THEN 'No Result'
                        WHEN (g.home_score - g.away_score) > ABS(ls.home_spread) THEN 'Home Cover'
                        WHEN (g.home_score - g.away_score) < -ABS(ls.home_spread) THEN 'Away Cover'
                        ELSE 'Push'
                    END as outcome,
                    COUNT(*) as count
                FROM games g
                JOIN latest_spreads ls ON g.game_id = ls.game_id
                GROUP BY 1
                ORDER BY count DESC
            ''')
            spread_outcomes = cursor.fetchall()
            
            return {
                'total_games': basic_stats['total_games'],
                'games_with_scores': basic_stats['games_with_scores'],
                'completed_games': basic_stats['completed_games'],
                'score_percentage': round(basic_stats['games_with_scores'] / basic_stats['total_games'] * 100, 1),
                'spread_outcomes': [dict(row) for row in spread_outcomes]
            }
            
        finally:
            cursor.close()
            conn.close()


def main():
    """Main function for NFL scores integration"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Integrate NFL scores with betting analytics database')
    parser.add_argument('--season', type=int, help='Specific season to fetch (e.g., 2024)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    parser.add_argument('--analyze', action='store_true', help='Analyze spread outcomes for completed games')
    parser.add_argument('--summary', action='store_true', help='Show score integration summary')
    
    args = parser.parse_args()
    
    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'betting_analytics'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }
    
    try:
        integrator = NFLScoresIntegrator(db_config)
        
        if args.summary:
            # Show summary of current score data
            summary = integrator.generate_score_summary()
            print("📊 NFL Scores Integration Summary:")
            print("=" * 50)
            print(f"Total Games: {summary['total_games']:,}")
            print(f"Games with Scores: {summary['games_with_scores']:,} ({summary['score_percentage']}%)")
            print(f"Completed Games: {summary['completed_games']:,}")
            print("\nSpread Outcomes:")
            for outcome in summary['spread_outcomes']:
                print(f"  {outcome['outcome']}: {outcome['count']:,}")
            return
        
        if args.analyze:
            # Analyze spread outcomes
            print("🎯 Analyzing Spread Outcomes for Recent Games:")
            print("=" * 60)
            outcomes = integrator.analyze_spread_outcomes(20)
            
            for outcome in outcomes:
                margin = outcome['actual_margin']
                spread = outcome['home_spread']
                result = outcome['spread_outcome']
                
                print(f"{outcome['away_team']} @ {outcome['home_team']}")
                print(f"  Score: {outcome['away_score']}-{outcome['home_score']} (Margin: {margin:+d})")
                print(f"  Spread: {spread:+.1f} | Outcome: {result}")
                print(f"  Bookmaker: {outcome['bookmaker_title']}")
                print()
            return
        
        # Fetch NFL scores data
        nfl_scores = integrator.fetch_nfl_scores_data(args.season)
        if nfl_scores.empty:
            print("❌ No NFL scores data available")
            return
        
        # Get existing games
        existing_games = integrator.get_existing_games()
        if existing_games.empty:
            print("❌ No existing games found in database")
            return
        
        # Find matches
        matches = integrator.find_game_matches(nfl_scores, existing_games)
        
        if not matches:
            print("❌ No matching games found")
            return
        
        # Update scores
        updates_made = integrator.update_game_scores(matches, dry_run=args.dry_run)
        
        if not args.dry_run:
            print("\n📊 Score Integration Complete!")
            summary = integrator.generate_score_summary()
            print(f"✅ {summary['games_with_scores']:,} of {summary['total_games']:,} games now have scores ({summary['score_percentage']}%)")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()