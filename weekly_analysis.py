#!/usr/bin/env python3
"""
Weekly NFL Analysis and Report Generator
Creates comprehensive reports and visualizations for specific NFL weeks
"""
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd

# Add database module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

import psycopg2
from psycopg2.extras import RealDictCursor

class NFLWeeklyAnalysis:
    """Comprehensive NFL weekly analysis and reporting"""
    
    def __init__(self, db_config: Dict[str, Any]):
        self.db_config = db_config
        
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def get_available_weeks(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get list of available weeks with data richness metrics"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT 
                    DATE_TRUNC('week', g.commence_time) as week_start,
                    COUNT(DISTINCT g.game_id) as games,
                    COUNT(s.spread_id) as total_spreads,
                    COUNT(DISTINCT s.bookmaker_id) as bookmakers,
                    COUNT(DISTINCT s.snapshot_timestamp) as snapshots,
                    MIN(g.commence_time) as first_game,
                    MAX(g.commence_time) as last_game,
                    (COUNT(s.spread_id) * COUNT(DISTINCT s.snapshot_timestamp)) as richness_score
                FROM games g
                LEFT JOIN spreads s ON g.game_id = s.game_id
                WHERE g.commence_time >= '2024-08-01'
                GROUP BY DATE_TRUNC('week', g.commence_time)
                HAVING COUNT(DISTINCT g.game_id) >= 5  -- Weeks with meaningful data
                ORDER BY richness_score DESC
                LIMIT %s
            ''', (limit,))
            
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_week_games(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get all games for a specific week"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT 
                    g.game_id,
                    g.commence_time,
                    s.sport_title,
                    ht.team_name as home_team,
                    at.team_name as away_team,
                    g.home_score,
                    g.away_score,
                    g.status,
                    -- Latest spreads info
                    COUNT(DISTINCT sp.bookmaker_id) as bookmaker_count,
                    COUNT(sp.spread_id) as spread_count,
                    COUNT(DISTINCT sp.snapshot_timestamp) as snapshot_count
                FROM games g
                JOIN sports s ON g.sport_id = s.sport_id
                JOIN teams ht ON g.home_team_id = ht.team_id
                JOIN teams at ON g.away_team_id = at.team_id
                LEFT JOIN spreads sp ON g.game_id = sp.game_id
                WHERE g.commence_time >= %s AND g.commence_time < %s
                GROUP BY g.game_id, g.commence_time, s.sport_title, ht.team_name, at.team_name, g.home_score, g.away_score, g.status
                ORDER BY g.commence_time
            ''', (start_date, end_date))
            
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def get_game_spreads_timeline(self, game_id: str) -> List[Dict[str, Any]]:
        """Get spread timeline for a specific game"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            cursor.execute('''
                SELECT 
                    sp.snapshot_timestamp,
                    sp.recorded_at,
                    b.bookmaker_title,
                    b.bookmaker_key,
                    sp.home_spread,
                    sp.home_price,
                    sp.away_spread,
                    sp.away_price,
                    sp.is_latest,
                    ht.team_name as home_team,
                    at.team_name as away_team
                FROM spreads sp
                JOIN bookmakers b ON sp.bookmaker_id = b.bookmaker_id
                JOIN games g ON sp.game_id = g.game_id
                JOIN teams ht ON g.home_team_id = ht.team_id
                JOIN teams at ON g.away_team_id = at.team_id
                WHERE sp.game_id = %s
                ORDER BY sp.snapshot_timestamp, b.bookmaker_title
            ''', (game_id,))
            
            return cursor.fetchall()
            
        finally:
            cursor.close()
            conn.close()
    
    def calculate_line_movements(self, game_id: str) -> Dict[str, Any]:
        """Calculate line movement statistics for a game"""
        spreads = self.get_game_spreads_timeline(game_id)
        
        if not spreads:
            return {}
        
        # Group by bookmaker
        bookmaker_movements = {}
        
        for spread in spreads:
            bm_key = spread['bookmaker_key']
            if bm_key not in bookmaker_movements:
                bookmaker_movements[bm_key] = {
                    'bookmaker': spread['bookmaker_title'],
                    'spreads': [],
                    'movements': []
                }
            
            bookmaker_movements[bm_key]['spreads'].append({
                'timestamp': spread['snapshot_timestamp'],
                'home_spread': spread['home_spread'],
                'away_spread': spread['away_spread'],
                'home_price': spread['home_price'],
                'away_price': spread['away_price']
            })
        
        # Calculate movements for each bookmaker
        for bm_key, data in bookmaker_movements.items():
            spreads_list = sorted(data['spreads'], key=lambda x: x['timestamp'])
            
            for i in range(1, len(spreads_list)):
                prev = spreads_list[i-1]
                curr = spreads_list[i]
                
                home_movement = curr['home_spread'] - prev['home_spread']
                away_movement = curr['away_spread'] - prev['away_spread']
                
                data['movements'].append({
                    'timestamp': curr['timestamp'],
                    'home_movement': home_movement,
                    'away_movement': away_movement,
                    'home_price_change': curr['home_price'] - prev['home_price'],
                    'away_price_change': curr['away_price'] - prev['away_price']
                })
        
        return bookmaker_movements
    
    def get_bookmaker_comparison(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Compare bookmaker spreads for the week"""
        conn = self.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Get latest spreads for each game/bookmaker combo
            cursor.execute('''
                WITH latest_spreads AS (
                    SELECT DISTINCT ON (g.game_id, b.bookmaker_id)
                        g.game_id,
                        ht.team_name as home_team,
                        at.team_name as away_team,
                        b.bookmaker_title,
                        b.bookmaker_key,
                        sp.home_spread,
                        sp.away_spread,
                        sp.home_price,
                        sp.away_price,
                        sp.snapshot_timestamp
                    FROM games g
                    JOIN teams ht ON g.home_team_id = ht.team_id
                    JOIN teams at ON g.away_team_id = at.team_id
                    JOIN spreads sp ON g.game_id = sp.game_id
                    JOIN bookmakers b ON sp.bookmaker_id = b.bookmaker_id
                    WHERE g.commence_time >= %s AND g.commence_time < %s
                    ORDER BY g.game_id, b.bookmaker_id, sp.snapshot_timestamp DESC
                )
                SELECT * FROM latest_spreads
                ORDER BY game_id, bookmaker_title
            ''', (start_date, end_date))
            
            results = cursor.fetchall()
            
            # Group by game
            games_comparison = {}
            for row in results:
                game_key = f"{row['away_team']} @ {row['home_team']}"
                if game_key not in games_comparison:
                    games_comparison[game_key] = {
                        'game_id': row['game_id'],
                        'matchup': game_key,
                        'bookmakers': {}
                    }
                
                games_comparison[game_key]['bookmakers'][row['bookmaker_key']] = {
                    'bookmaker': row['bookmaker_title'],
                    'home_spread': row['home_spread'],
                    'away_spread': row['away_spread'],
                    'home_price': row['home_price'],
                    'away_price': row['away_price']
                }
            
            return games_comparison
            
        finally:
            cursor.close()
            conn.close()
    
    def find_arbitrage_opportunities(self, bookmaker_comparison: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Find potential arbitrage opportunities"""
        opportunities = []
        
        for game_key, game_data in bookmaker_comparison.items():
            bookmakers = game_data['bookmakers']
            
            if len(bookmakers) < 2:
                continue
            
            # Find best odds for each side
            best_home = {'bookmaker': None, 'spread': None, 'price': float('-inf')}
            best_away = {'bookmaker': None, 'spread': None, 'price': float('-inf')}
            
            for bm_key, bm_data in bookmakers.items():
                if bm_data['home_price'] > best_home['price']:
                    best_home = {
                        'bookmaker': bm_data['bookmaker'],
                        'spread': bm_data['home_spread'],
                        'price': bm_data['home_price']
                    }
                
                if bm_data['away_price'] > best_away['price']:
                    best_away = {
                        'bookmaker': bm_data['bookmaker'],
                        'spread': bm_data['away_spread'],
                        'price': bm_data['away_price']
                    }
            
            # Calculate implied probability and potential arbitrage
            if best_home['price'] > 0 and best_away['price'] > 0:
                home_implied = 100 / (best_home['price'] + 100)
                away_implied = 100 / (best_away['price'] + 100)
            else:
                home_implied = abs(best_home['price']) / (abs(best_home['price']) + 100)
                away_implied = abs(best_away['price']) / (abs(best_away['price']) + 100)
            
            total_implied = home_implied + away_implied
            
            if total_implied < 1.0:  # Potential arbitrage
                opportunities.append({
                    'game': game_key,
                    'profit_margin': (1 - total_implied) * 100,
                    'home_bet': best_home,
                    'away_bet': best_away,
                    'total_implied_prob': total_implied * 100
                })
        
        return sorted(opportunities, key=lambda x: x['profit_margin'], reverse=True)
    
    def generate_weekly_report(self, start_date: str, end_date: str) -> str:
        """Generate comprehensive weekly report"""
        
        # Get basic week info
        games = self.get_week_games(start_date, end_date)
        bookmaker_comparison = self.get_bookmaker_comparison(start_date, end_date)
        arbitrage_ops = self.find_arbitrage_opportunities(bookmaker_comparison)
        
        # Generate report
        report = f"""
🏈 NFL WEEKLY ANALYSIS REPORT
{'=' * 60}
📅 Week: {start_date[:10]} to {end_date[:10]}
📊 Data Summary: {len(games)} games, {sum(g['spread_count'] for g in games)} total spreads

🎯 KEY HIGHLIGHTS
{'=' * 60}
"""
        
        if games:
            total_snapshots = sum(g['snapshot_count'] for g in games)
            avg_bookmakers = sum(g['bookmaker_count'] for g in games) / len(games)
            
            report += f"""
📈 Data Coverage:
   • {total_snapshots:,} total snapshots across all games
   • Average {avg_bookmakers:.1f} bookmakers per game
   • Most tracked game: {max(games, key=lambda x: x['spread_count'])['away_team']} @ {max(games, key=lambda x: x['spread_count'])['home_team']} ({max(g['spread_count'] for g in games)} spreads)

🏈 Games Overview:
"""
            
            for game in games[:10]:  # Show first 10 games
                status_icon = "✅" if game['status'] == 'completed' else "🔄" if game['status'] == 'in_progress' else "⏰"
                score_text = f" ({game['away_score']}-{game['home_score']})" if game['away_score'] is not None else ""
                
                report += f"""   {status_icon} {game['away_team']} @ {game['home_team']}{score_text}
      📅 {game['commence_time'].strftime('%m/%d %I:%M %p')} | 📊 {game['spread_count']} spreads | 📸 {game['snapshot_count']} snapshots
"""
        
        # Arbitrage opportunities
        if arbitrage_ops:
            report += f"""
💰 ARBITRAGE OPPORTUNITIES
{'=' * 60}
"""
            for i, arb in enumerate(arbitrage_ops[:5], 1):
                report += f"""
{i}. {arb['game']} - {arb['profit_margin']:.2f}% potential profit
   🏠 Home: {arb['home_bet']['bookmaker']} {arb['home_bet']['spread']:+.1f} ({arb['home_bet']['price']:+d})
   ✈️  Away: {arb['away_bet']['bookmaker']} {arb['away_bet']['spread']:+.1f} ({arb['away_bet']['price']:+d})
   📊 Total Implied Probability: {arb['total_implied_prob']:.1f}%
"""
        
        # Bookmaker comparison section
        report += f"""
📊 BOOKMAKER COMPARISON
{'=' * 60}
"""
        
        for game_key, game_data in list(bookmaker_comparison.items())[:5]:
            report += f"""
🏈 {game_key}:
"""
            bookmakers = game_data['bookmakers']
            for bm_key, bm_data in bookmakers.items():
                report += f"""   {bm_data['bookmaker']:12} | Away: {bm_data['away_spread']:+.1f} ({bm_data['away_price']:+4d}) | Home: {bm_data['home_spread']:+.1f} ({bm_data['home_price']:+4d})
"""
        
        # Line movement spotlights
        report += f"""
📈 LINE MOVEMENT SPOTLIGHTS
{'=' * 60}
"""
        
        # Find games with significant line movements
        movement_games = []
        for game in games[:5]:  # Check first 5 games for movements
            movements = self.calculate_line_movements(game['game_id'])
            if movements:
                total_movement = 0
                for bm_key, bm_data in movements.items():
                    if bm_data['movements']:
                        max_movement = max([abs(m['home_movement']) for m in bm_data['movements']] + [0])
                        total_movement += max_movement
                
                if total_movement > 0.5:  # Significant movement threshold
                    movement_games.append({
                        'game': f"{game['away_team']} @ {game['home_team']}",
                        'movement': total_movement,
                        'details': movements
                    })
        
        movement_games.sort(key=lambda x: x['movement'], reverse=True)
        
        for movement in movement_games[:3]:
            report += f"""
🔥 {movement['game']} - {movement['movement']:.1f} point total movement
"""
            for bm_key, bm_data in movement['details'].items():
                if bm_data['movements']:
                    latest_movement = bm_data['movements'][-1]
                    report += f"""   {bm_data['bookmaker']:12} | Home moved {latest_movement['home_movement']:+.1f} | Away moved {latest_movement['away_movement']:+.1f}
"""
        
        report += f"""
{'=' * 60}
📊 Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return report


def main():
    """Main function for weekly analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate NFL weekly analysis report')
    parser.add_argument('--week-start', help='Week start date (YYYY-MM-DD)')
    parser.add_argument('--week-end', help='Week end date (YYYY-MM-DD)')
    parser.add_argument('--list-weeks', action='store_true', help='List available weeks')
    parser.add_argument('--auto-best', action='store_true', help='Automatically select best week')
    
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
        analyzer = NFLWeeklyAnalysis(db_config)
        
        if args.list_weeks:
            # List available weeks
            weeks = analyzer.get_available_weeks(15)
            
            print("📅 Available NFL Weeks for Analysis:")
            print("=" * 60)
            
            for i, week in enumerate(weeks, 1):
                week_start = week['first_game'].strftime('%b %d')
                week_end = week['last_game'].strftime('%b %d, %Y')
                
                print(f"{i:2}. {week_start} - {week_end}")
                print(f"    📊 {week['games']} games | {week['total_spreads']} spreads | {week['bookmakers']} bookmakers | {week['snapshots']} snapshots")
                print(f"    🎯 Richness Score: {week['richness_score']:,}")
                print()
            
            return
        
        if args.auto_best:
            # Automatically select the best week
            weeks = analyzer.get_available_weeks(1)
            if not weeks:
                print("❌ No weeks available for analysis")
                return
            
            best_week = weeks[0]
            start_date = best_week['week_start'].strftime('%Y-%m-%d')
            end_date = (best_week['week_start'] + timedelta(days=7)).strftime('%Y-%m-%d')
            
            print(f"🎯 Auto-selected best week: {best_week['first_game'].strftime('%b %d')} - {best_week['last_game'].strftime('%b %d, %Y')}")
            
        elif args.week_start and args.week_end:
            start_date = args.week_start
            end_date = args.week_end
        else:
            # Default to most recent week with good data
            weeks = analyzer.get_available_weeks(1)
            if not weeks:
                print("❌ No weeks available for analysis")
                return
            
            best_week = weeks[0]
            start_date = best_week['week_start'].strftime('%Y-%m-%d')
            end_date = (best_week['week_start'] + timedelta(days=7)).strftime('%Y-%m-%d')
        
        # Generate and display report
        print("🔄 Generating weekly analysis report...")
        report = analyzer.generate_weekly_report(start_date, end_date)
        print(report)
        
        # Save report to file
        filename = f"nfl_weekly_report_{start_date}_to_{end_date.replace('-', '')}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        
        print(f"\n💾 Report saved to: {filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()