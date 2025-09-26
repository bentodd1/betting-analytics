#!/usr/bin/env python3
"""
Quick NFL Weekly Report Generator
"""
import os
import sys
sys.path.append('./database')
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

def generate_quick_report(start_date, end_date):
    """Generate a quick weekly report"""
    
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        user='postgres',
        password='F1shF1sh&&',
        database='betting_analytics'
    )
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Get games for the week
    cursor.execute('''
        SELECT 
            g.game_id,
            g.commence_time,
            ht.team_name as home_team,
            at.team_name as away_team,
            g.home_score,
            g.away_score,
            g.status,
            COUNT(sp.spread_id) as spread_count,
            COUNT(DISTINCT sp.bookmaker_id) as bookmaker_count,
            COUNT(DISTINCT sp.snapshot_timestamp) as snapshot_count
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id
        JOIN teams at ON g.away_team_id = at.team_id
        LEFT JOIN spreads sp ON g.game_id = sp.game_id
        WHERE g.commence_time >= %s AND g.commence_time < %s
        GROUP BY g.game_id, g.commence_time, ht.team_name, at.team_name, g.home_score, g.away_score, g.status
        ORDER BY g.commence_time
    ''', (start_date, end_date))
    
    games = cursor.fetchall()
    
    # Get latest spreads comparison
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
                sp.away_price
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
        LIMIT 50
    ''', (start_date, end_date))
    
    spreads = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Generate report
    report_lines = []
    report_lines.append("🏈 NFL WEEKLY SPOTLIGHT REPORT")
    report_lines.append("=" * 60)
    report_lines.append(f"📅 Week: {start_date} to {end_date}")
    report_lines.append(f"📊 Data Summary: {len(games)} games")
    report_lines.append("")
    
    report_lines.append("🎯 GAMES OVERVIEW")
    report_lines.append("=" * 60)
    
    for game in games:
        status_icon = "✅" if game['status'] == 'completed' else "🔄" if game['status'] == 'in_progress' else "⏰"
        score_text = f" ({game['away_score']}-{game['home_score']})" if game['away_score'] is not None else ""
        
        report_lines.append(f"{status_icon} {game['away_team']} @ {game['home_team']}{score_text}")
        report_lines.append(f"   📅 {game['commence_time'].strftime('%m/%d %I:%M %p')} | 📊 {game['spread_count']} spreads | 📸 {game['snapshot_count']} snapshots")
        report_lines.append("")
    
    # Group spreads by game
    game_spreads = {}
    for spread in spreads:
        game_key = f"{spread['away_team']} @ {spread['home_team']}"
        if game_key not in game_spreads:
            game_spreads[game_key] = []
        game_spreads[game_key].append(spread)
    
    if game_spreads:
        report_lines.append("📊 LATEST SPREADS COMPARISON")
        report_lines.append("=" * 60)
        
        for game_key, game_spreads_list in list(game_spreads.items())[:5]:
            report_lines.append(f"🏈 {game_key}:")
            
            for spread in game_spreads_list:
                away_spread_str = f"{spread['away_spread']:+.1f}" if spread['away_spread'] is not None else "N/A"
                home_spread_str = f"{spread['home_spread']:+.1f}" if spread['home_spread'] is not None else "N/A"
                away_price_str = f"({spread['away_price']:+.0f})" if spread['away_price'] is not None else "(N/A)"
                home_price_str = f"({spread['home_price']:+.0f})" if spread['home_price'] is not None else "(N/A)"
                
                report_lines.append(f"   {spread['bookmaker_title']:12} | Away: {away_spread_str} {away_price_str} | Home: {home_spread_str} {home_price_str}")
            
            report_lines.append("")
    
    # Find potential arbitrage
    arbitrage_opportunities = []
    for game_key, game_spreads_list in game_spreads.items():
        if len(game_spreads_list) >= 2:
            best_away_price = max([s['away_price'] for s in game_spreads_list if s['away_price'] is not None] + [-1000])
            best_home_price = max([s['home_price'] for s in game_spreads_list if s['home_price'] is not None] + [-1000])
            
            if best_away_price > -200 and best_home_price > -200:  # Reasonable odds
                # Simple arbitrage check
                if best_away_price > 0:
                    away_implied = 100 / (best_away_price + 100)
                else:
                    away_implied = abs(best_away_price) / (abs(best_away_price) + 100)
                
                if best_home_price > 0:
                    home_implied = 100 / (best_home_price + 100)
                else:
                    home_implied = abs(best_home_price) / (abs(best_home_price) + 100)
                
                total_implied = away_implied + home_implied
                
                if total_implied < 0.98:  # Potential arbitrage (allowing for margin)
                    profit_margin = (1 - total_implied) * 100
                    arbitrage_opportunities.append((game_key, profit_margin, best_away_price, best_home_price))
    
    if arbitrage_opportunities:
        arbitrage_opportunities.sort(key=lambda x: x[1], reverse=True)
        
        report_lines.append("💰 POTENTIAL ARBITRAGE OPPORTUNITIES")
        report_lines.append("=" * 60)
        
        for game, profit, away_price, home_price in arbitrage_opportunities[:3]:
            report_lines.append(f"🎯 {game}")
            report_lines.append(f"   💡 Potential {profit:.2f}% profit")
            report_lines.append(f"   📊 Best Away: {away_price:+.0f} | Best Home: {home_price:+.0f}")
            report_lines.append("")
    
    report_lines.append("=" * 60)
    report_lines.append(f"📊 Report generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return "\n".join(report_lines)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2024-12-23', help='Start date')
    parser.add_argument('--end', default='2024-12-30', help='End date')
    
    args = parser.parse_args()
    
    report = generate_quick_report(args.start, args.end)
    print(report)
    
    # Save to file
    filename = f"nfl_report_{args.start}_to_{args.end}.txt"
    with open(filename, 'w') as f:
        f.write(report)
    
    print(f"\n💾 Report saved to: {filename}")