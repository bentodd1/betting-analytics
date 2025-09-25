#!/usr/bin/env python3
"""
Quick test script to verify database setup
"""
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__)))

try:
    from database.db_connection import get_db_connection, get_database_status
    print("✅ Database module imported successfully")
except ImportError as e:
    print(f"❌ Failed to import database module: {e}")
    print("Make sure you've installed the dependencies:")
    print("pip3 install python-dotenv psycopg2-binary pandas requests python-dateutil")
    sys.exit(1)

def test_database():
    print("🔍 Testing database connection and schema...")

    try:
        # Test basic connection
        db = get_db_connection()

        if db.test_connection():
            print("✅ Database connection successful!")

            # Get database status
            status = get_database_status()

            print("\n📊 Database Status:")
            print(f"Connection: {'✅ Connected' if status['connection'] else '❌ Disconnected'}")

            print("\n📋 Table Status:")
            for table_name, info in status['tables'].items():
                if info['exists']:
                    print(f"  ✅ {table_name}: {info['count']} rows")
                else:
                    print(f"  ❌ {table_name}: Not found or error")
                    if 'error' in info:
                        print(f"     Error: {info['error']}")

            # Test a simple query
            print("\n🔍 Testing sample queries...")

            # Query sports
            sports = db.execute_query("SELECT sport_key, sport_title FROM sports LIMIT 5")
            print(f"✅ Sports query: Found {len(sports)} sports")
            for sport in sports[:3]:
                print(f"   - {sport['sport_key']}: {sport['sport_title']}")

            # Query bookmakers
            bookmakers = db.execute_query("SELECT bookmaker_key, bookmaker_title FROM bookmakers LIMIT 5")
            print(f"✅ Bookmakers query: Found {len(bookmakers)} bookmakers")
            for bm in bookmakers[:3]:
                print(f"   - {bm['bookmaker_key']}: {bm['bookmaker_title']}")

            print("\n🎉 Database setup is complete and working!")
            print("\nNext steps:")
            print("1. Add your Odds API key to .env file")
            print("2. Start fetching historical odds data")
            print("3. Build the Streamlit dashboard")

        else:
            print("❌ Database connection failed!")
            print("Check your PostgreSQL service and connection settings.")

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running: sudo service postgresql start")
        print("2. Check your .env file has correct database settings")
        print("3. Verify the schema was created properly")


if __name__ == "__main__":
    test_database()