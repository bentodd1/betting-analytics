#!/usr/bin/env python3
"""
Fetch comprehensive NFL spreads data for multiple seasons (2021-2025)
This script handles bulk historical data collection for NFL seasons
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Tuple, Optional
import time

# Add database module to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from fetch_historical_spreads import HistoricalNFLSpreadsAPI

class NFLSeasonsDataCollector:
    """Handles bulk NFL seasons data collection"""
    
    def __init__(self, api_key: str, db_config: Dict[str, str]):
        self.api = HistoricalNFLSpreadsAPI(api_key, db_config)
        self.seasons = self._define_nfl_seasons()
        
    def _define_nfl_seasons(self) -> List[Dict[str, str]]:
        """Define NFL season date ranges"""
        return [
            {
                'name': '2021 NFL Season',
                'start_date': '2021-08-01',
                'end_date': '2022-02-28',
                'year': 2021
            },
            {
                'name': '2022 NFL Season', 
                'start_date': '2022-08-01',
                'end_date': '2023-02-28',
                'year': 2022
            },
            {
                'name': '2023 NFL Season',
                'start_date': '2023-08-01', 
                'end_date': '2024-02-29',
                'year': 2023
            },
            {
                'name': '2024 NFL Season',
                'start_date': '2024-08-01',
                'end_date': '2025-02-28', 
                'year': 2024
            },
            {
                'name': '2025 NFL Season',
                'start_date': '2025-08-01',
                'end_date': '2026-02-28',
                'year': 2025
            }
        ]
    
    def calculate_fetch_strategy(self, start_date: str, end_date: str, 
                               interval_hours: int = 24) -> Dict[str, int]:
        """Calculate how many API calls will be needed"""
        start_dt = datetime.fromisoformat(start_date + "T12:00:00Z").replace(tzinfo=timezone.utc)
        end_dt = datetime.fromisoformat(end_date + "T12:00:00Z").replace(tzinfo=timezone.utc)
        
        total_hours = (end_dt - start_dt).total_seconds() / 3600
        total_calls = int(total_hours / interval_hours) + 1
        
        return {
            'total_calls': total_calls,
            'total_days': int(total_hours / 24),
            'estimated_credits': total_calls * 10,  # 10 credits per historical call
            'estimated_time_minutes': total_calls * 2  # ~2 seconds per call with rate limiting
        }
    
    def fetch_season_data(self, season: Dict[str, str], 
                         interval_hours: int = 24,
                         bookmakers: Optional[str] = None,
                         dry_run: bool = False) -> Dict[str, int]:
        """
        Fetch data for a complete NFL season
        
        Args:
            season: Season definition dict
            interval_hours: Hours between snapshots (24 = daily, 12 = twice daily)
            bookmakers: Comma-separated bookmaker list
            dry_run: If True, only calculate strategy without fetching
        """
        print(f"\n🏈 {season['name']} ({season['start_date']} to {season['end_date']})")
        print("=" * 60)
        
        # Calculate strategy
        strategy = self.calculate_fetch_strategy(
            season['start_date'], 
            season['end_date'], 
            interval_hours
        )
        
        print(f"📊 Fetch Strategy:")
        print(f"   📅 Total days: {strategy['total_days']}")
        print(f"   📡 API calls: {strategy['total_calls']}")
        print(f"   💳 Estimated credits: {strategy['estimated_credits']:,}")
        print(f"   ⏱️  Estimated time: {strategy['estimated_time_minutes']:.0f} minutes")
        
        if dry_run:
            print("   🔍 DRY RUN - No actual data fetching")
            return strategy
        
        # Ask for confirmation for large requests
        if strategy['total_calls'] > 100:
            print(f"\n⚠️  This will use {strategy['estimated_credits']:,} API credits!")
            response = input("Continue? (y/N): ")
            if response.lower() != 'y':
                print("❌ Cancelled by user")
                return {'cancelled': True}
        
        # Fetch the data
        print(f"\n🚀 Starting data collection for {season['name']}...")
        start_time = time.time()
        
        try:
            counts = self.api.fetch_historical_range(
                start_date=season['start_date'],
                end_date=season['end_date'], 
                interval_hours=interval_hours,
                bookmakers=bookmakers
            )
            
            elapsed_time = (time.time() - start_time) / 60
            
            print(f"\n✅ {season['name']} completed in {elapsed_time:.1f} minutes")
            print(f"📊 Results: {counts['snapshots']} snapshots, {counts['games']} games, {counts['spreads']} spreads")
            
            return counts
            
        except Exception as e:
            print(f"❌ Error fetching {season['name']}: {e}")
            return {'error': str(e)}
    
    def fetch_all_seasons(self, interval_hours: int = 24, 
                         bookmakers: Optional[str] = None,
                         start_year: Optional[int] = None,
                         end_year: Optional[int] = None,
                         dry_run: bool = False) -> Dict[str, Dict]:
        """
        Fetch data for all NFL seasons
        
        Args:
            interval_hours: Hours between snapshots
            bookmakers: Comma-separated bookmaker list
            start_year: Start from this year (inclusive)
            end_year: End at this year (inclusive)
            dry_run: If True, only show strategy without fetching
        """
        print("🏈 NFL Multi-Season Data Collection")
        print("=" * 60)
        
        # Filter seasons by year range
        seasons_to_fetch = self.seasons
        if start_year:
            seasons_to_fetch = [s for s in seasons_to_fetch if s['year'] >= start_year]
        if end_year:
            seasons_to_fetch = [s for s in seasons_to_fetch if s['year'] <= end_year]
        
        print(f"📅 Seasons to process: {len(seasons_to_fetch)}")
        
        # Calculate total strategy
        total_strategy = {
            'total_calls': 0,
            'estimated_credits': 0,
            'estimated_time_minutes': 0
        }
        
        for season in seasons_to_fetch:
            strategy = self.calculate_fetch_strategy(
                season['start_date'], 
                season['end_date'], 
                interval_hours
            )
            total_strategy['total_calls'] += strategy['total_calls']
            total_strategy['estimated_credits'] += strategy['estimated_credits']
            total_strategy['estimated_time_minutes'] += strategy['estimated_time_minutes']
        
        print(f"\n📊 Total Strategy:")
        print(f"   📡 Total API calls: {total_strategy['total_calls']:,}")
        print(f"   💳 Total credits: {total_strategy['estimated_credits']:,}")
        print(f"   ⏱️  Total time: {total_strategy['estimated_time_minutes']/60:.1f} hours")
        
        if dry_run:
            print("\n🔍 DRY RUN - Showing individual season strategies:")
            results = {}
            for season in seasons_to_fetch:
                results[season['name']] = self.fetch_season_data(
                    season, interval_hours, bookmakers, dry_run=True
                )
            return results
        
        # Execute data collection
        results = {}
        overall_start_time = time.time()
        
        for i, season in enumerate(seasons_to_fetch, 1):
            print(f"\n🔄 Processing {i}/{len(seasons_to_fetch)}: {season['name']}")
            
            result = self.fetch_season_data(
                season, interval_hours, bookmakers, dry_run=False
            )
            results[season['name']] = result
            
            # Rate limiting between seasons
            if i < len(seasons_to_fetch):
                print("⏸️  Pausing 10 seconds between seasons...")
                time.sleep(10)
        
        overall_elapsed = (time.time() - overall_start_time) / 60
        
        print(f"\n🎉 All seasons completed in {overall_elapsed:.1f} minutes!")
        print("\n📊 Final Summary:")
        
        total_snapshots = sum(r.get('snapshots', 0) for r in results.values())
        total_games = sum(r.get('games', 0) for r in results.values())
        total_spreads = sum(r.get('spreads', 0) for r in results.values())
        
        print(f"   📅 Snapshots: {total_snapshots:,}")
        print(f"   🏈 Games: {total_games:,}")
        print(f"   📊 Spreads: {total_spreads:,}")
        
        return results


def main():
    """Main function for NFL seasons data collection"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fetch NFL seasons historical spreads data')
    parser.add_argument('--start-year', type=int, help='Start year (e.g., 2021)')
    parser.add_argument('--end-year', type=int, help='End year (e.g., 2024)')
    parser.add_argument('--interval', type=int, default=24, help='Hours between snapshots (default: 24)')
    parser.add_argument('--bookmakers', default='draftkings,fanduel', help='Comma-separated bookmakers')
    parser.add_argument('--dry-run', action='store_true', help='Show strategy without fetching data')
    parser.add_argument('--single-season', type=int, help='Fetch only one season (year)')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = os.getenv('ODDS_API_KEY')
    if not api_key:
        print("❌ ODDS_API_KEY environment variable not set")
        sys.exit(1)
    
    # Database configuration
    db_config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'betting_analytics'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', 'password')
    }
    
    try:
        collector = NFLSeasonsDataCollector(api_key, db_config)
        
        # Test database connection
        conn = collector.api.get_connection()
        print("✅ Database connection successful")
        conn.close()
        
        if args.single_season:
            # Fetch single season
            seasons = [s for s in collector.seasons if s['year'] == args.single_season]
            if not seasons:
                print(f"❌ Season {args.single_season} not found")
                sys.exit(1)
            
            result = collector.fetch_season_data(
                seasons[0], 
                args.interval, 
                args.bookmakers, 
                args.dry_run
            )
        else:
            # Fetch multiple seasons
            results = collector.fetch_all_seasons(
                interval_hours=args.interval,
                bookmakers=args.bookmakers,
                start_year=args.start_year,
                end_year=args.end_year,
                dry_run=args.dry_run
            )
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()