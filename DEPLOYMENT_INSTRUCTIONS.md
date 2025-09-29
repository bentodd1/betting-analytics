# Deployment Instructions - Sports Betting Analytics

## 🚀 Quick Deployment Options

### Option 1: Local Development (Docker)

```bash
# 1. Clone repository
git clone https://github.com/yourusername/betting-analytics.git
cd betting-analytics

# 2. Set up environment
cp .env.example .env
nano .env  # Add your API keys

# 3. Start local PostgreSQL
brew install postgresql
brew services start postgresql
createdb betting_analytics

# 4. Run with Docker
docker compose up -d

# 5. Access application
open http://localhost:8501
```

### Option 2: Remote Server Deployment (Automated)

```bash
# 1. Get a server (DigitalOcean, Linode, etc.)
# Recommended: 4GB RAM, 2 vCPUs, Ubuntu 22.04

# 2. Deploy with automation script
./deploy.sh your-server-ip

# Example:
./deploy.sh 165.227.123.45

# 3. Access your app
open http://your-server-ip
```

### Option 3: Remote Server Deployment (Manual)

Follow the detailed guide in `SINGLE_SERVER_DEPLOYMENT.md`

## 🔧 Configuration

### Required Environment Variables

```bash
# API Keys (Required)
CLAUDE_API_KEY=your-claude-api-key-here
ODDS_API_KEY=your-odds-api-key-here

# Database (Docker automatically uses F1shF1sh&&)
DB_PASSWORD=F1shF1sh&&
```

### Optional Configuration

```bash
# Custom database settings
DB_HOST=localhost
DB_PORT=5432
DB_NAME=betting_analytics
DB_USER=postgres

# Application settings
STREAMLIT_PORT=8501
LOG_LEVEL=INFO
```

## 📋 Server Requirements

### Minimum Specs
- **OS:** Ubuntu 22.04 LTS
- **RAM:** 4GB
- **CPU:** 2 cores
- **Storage:** 50GB SSD
- **Cost:** $20-40/month

### Recommended Providers
- **DigitalOcean:** $24/month (4GB RAM, 2 vCPUs)
- **Linode:** $24/month (4GB RAM, 2 vCPUs)
- **Vultr:** $24/month (4GB RAM, 2 vCPUs)
- **AWS EC2:** t3.medium (~$30/month)

## 🐳 Docker Architecture

### Local Development
```
┌─────────────────┐    ┌─────────────────┐
│   Local         │    │   Docker        │
│   PostgreSQL    │◄──►│   Streamlit     │
│   Port: 5432    │    │   Port: 8501    │
└─────────────────┘    └─────────────────┘
```

### Production Server
```
┌─────────────────────────────────────────┐
│              VPS Server                  │
│  ┌─────────────┐    ┌─────────────────┐ │
│  │  Streamlit  │    │   PostgreSQL    │ │
│  │   + Nginx   │◄──►│   (Local)       │ │
│  │  Port: 80   │    │   Port: 5432    │ │
│  └─────────────┘    └─────────────────┘ │
│           ▲                             │
│           │                             │
│  ┌─────────────────────────────────────┐ │
│  │            Cron Jobs                │ │
│  │  • Current odds (15min)             │ │
│  │  • Game results (hourly)            │ │
│  │  • Historical data (6hr)            │ │
│  └─────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## 🔍 Verification Steps

### Local Development
```bash
# Check Docker containers
docker compose ps

# View application logs
docker compose logs -f streamlit

# Test database connection
docker compose exec streamlit python3 -c "
from database.db_connection import DatabaseConnection
print('✅ Database OK' if DatabaseConnection().test_connection() else '❌ Database Failed')
"

# Access application
curl http://localhost:8501
```

### Production Server
```bash
# SSH to server
ssh root@your-server-ip

# Check service status
systemctl status betting-analytics
systemctl status nginx
systemctl status postgresql

# View application logs
journalctl -u betting-analytics -f

# Check database
sudo -u postgres psql -d betting_analytics -c "SELECT COUNT(*) FROM games;"

# Test web access
curl http://localhost:8501
curl http://localhost  # nginx proxy
```

## 🛠️ Troubleshooting

### Common Issues

#### Docker: Port 5432 already in use
```bash
# Use local PostgreSQL instead of Docker
# This is already configured in docker-compose.yml
```

#### Cannot connect to database
```bash
# Check PostgreSQL is running
brew services list | grep postgresql

# Create database if missing
createdb betting_analytics

# Check connection from container
docker compose exec streamlit python3 database/db_connection.py
```

#### Missing API keys
```bash
# Check .env file exists and has keys
cat .env

# Should contain:
# CLAUDE_API_KEY=your-actual-key
# ODDS_API_KEY=your-actual-key
```

#### Server deployment fails
```bash
# Check server SSH access
ssh root@your-server-ip

# Check server specs
free -h  # RAM
nproc    # CPU cores
df -h    # Disk space

# Re-run deployment
./deploy.sh your-server-ip
```

## 📊 Data Collection Setup

### Manual Data Collection (Optional)
```bash
# Initialize database schema
python3 database/db_connection.py

# Collect current odds
python3 fetch_nfl_spreads.py

# Backfill historical data
python3 fetch_nfl_seasons.py --single-season 2024

# Check data
python3 -c "
from database.db_connection import DatabaseConnection
db = DatabaseConnection()
result = db.execute_query('SELECT COUNT(*) FROM games')
print(f'Games in database: {result[0][0] if result else 0}')
"
```

### Automated Data Collection (Production)
- Automatically set up with `deploy.sh` script
- Runs every 15 minutes for current odds
- Runs hourly for game results
- See `SINGLE_SERVER_DEPLOYMENT.md` for cron job details

## 🔒 Security Considerations

### Development
- Use strong database passwords
- Keep API keys in .env file (never commit)
- Use localhost-only database access

### Production
- Change default passwords
- Set up firewall (UFW)
- Use nginx reverse proxy
- Enable SSL/HTTPS for public access
- Regular security updates

## 📞 Support

### Getting Help
1. **Check logs first:** `docker compose logs streamlit`
2. **Verify configuration:** Check .env file and database connection
3. **Test components:** Database, API keys, network connectivity
4. **Restart if needed:** `docker compose restart`

### Common Commands
```bash
# Development
docker compose up -d                    # Start services
docker compose logs -f streamlit        # View logs
docker compose restart streamlit        # Restart app
docker compose down                     # Stop all services

# Production  
systemctl restart betting-analytics     # Restart app
systemctl status betting-analytics      # Check status
journalctl -u betting-analytics -f      # View logs
sudo -u postgres psql betting_analytics # Access database
```

---

## 🎯 Quick Start Summary

**Local Development:**
```bash
cp .env.example .env && nano .env
createdb betting_analytics
docker compose up -d
open http://localhost:8501
```

**Production Deployment:**
```bash
./deploy.sh your-server-ip
open http://your-server-ip
```

That's it! Your Sports Betting Analytics platform should be running successfully.