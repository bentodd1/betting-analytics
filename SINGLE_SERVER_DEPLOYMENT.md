# Single Server Deployment Guide - Sports Betting Analytics

## 🖥️ Simple Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    VPS/Cloud Server                      │
│  ┌─────────────────┐    ┌─────────────────────────────┐  │
│  │   Streamlit     │    │        PostgreSQL           │  │
│  │   Port 8501     │◄──►│        Port 5432            │  │
│  │                 │    │                             │  │
│  └─────────────────┘    └─────────────────────────────┘  │
│           ▲                                              │
│           │                                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │                 Cron Jobs                           │  │
│  │  */15 * * * * /opt/betting/fetch_current_odds.py   │  │
│  │  0 * * * *    /opt/betting/fetch_game_results.py   │  │
│  │  0 */6 * * *  /opt/betting/fetch_historical.py     │  │
│  │  0 2 * * *    /opt/betting/cleanup_old_data.py     │  │
│  └─────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## 🚀 Server Requirements

### Minimum Specs
- **OS:** Ubuntu 22.04 LTS
- **RAM:** 4GB (2GB for app, 1GB for PostgreSQL, 1GB system)
- **CPU:** 2 cores
- **Storage:** 50GB SSD
- **Cost:** $20-40/month

### Recommended Providers
- **DigitalOcean:** $24/month (2GB RAM, 2 vCPUs, 50GB SSD)
- **Linode:** $24/month (4GB RAM, 2 vCPUs, 80GB SSD)
- **Vultr:** $24/month (4GB RAM, 2 vCPUs, 80GB SSD)
- **Azure VM:** $31/month (B2s: 2 vCPUs, 4GB RAM)

## 📋 Step-by-Step Deployment

### 1. Server Setup

```bash
# Connect to your server
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install essential packages
apt install -y python3 python3-pip postgresql postgresql-contrib nginx git supervisor htop
```

### 2. PostgreSQL Setup

```bash
# Start PostgreSQL
systemctl start postgresql
systemctl enable postgresql

# Create database and user
sudo -u postgres psql

# In PostgreSQL prompt:
CREATE DATABASE betting_analytics;
CREATE USER betting_user WITH ENCRYPTED PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE betting_analytics TO betting_user;
\q
```

### 3. Application Setup

```bash
# Create application directory
mkdir -p /opt/betting
cd /opt/betting

# Clone your repository (or upload files)
git clone https://github.com/yourusername/betting-analytics.git .

# Install Python dependencies
pip3 install -r requirements.txt

# Create environment file
cat > .env << EOF
DB_HOST=localhost
DB_PORT=5432
DB_NAME=betting_analytics
DB_USER=betting_user
DB_PASSWORD=your-secure-password
CLAUDE_API_KEY=your-claude-api-key
ODDS_API_KEY=your-odds-api-key
EOF

# Set proper permissions
chmod 600 .env
chown -R betting:betting /opt/betting
```

### 4. Database Initialization

```bash
# Run database setup
cd /opt/betting
python3 database/db_connection.py

# Populate initial data (teams, sports, bookmakers)
python3 scripts/populate_reference_data.py

# Optional: Backfill historical data
python3 fetch_nfl_seasons.py --single-season 2024 --interval 72
```

### 5. Cron Jobs Setup

```bash
# Create cron user
useradd -r -s /bin/bash betting

# Setup cron jobs
sudo -u betting crontab -e

# Add these lines:
# Current odds every 15 minutes during active hours (9 AM - 11 PM EST)
*/15 9-23 * * * cd /opt/betting && python3 fetch_nfl_spreads.py >> /var/log/betting/current_odds.log 2>&1

# Game results every hour
0 * * * * cd /opt/betting && python3 fetch_nfl_scores.py --season 2024 >> /var/log/betting/game_results.log 2>&1

# Historical snapshots every 6 hours during season
0 */6 * 9-2 * cd /opt/betting && python3 fetch_historical_spreads.py --interval 6 >> /var/log/betting/historical.log 2>&1

# Database cleanup at 2 AM daily
0 2 * * * cd /opt/betting && python3 scripts/cleanup_old_data.py >> /var/log/betting/cleanup.log 2>&1

# Create log directory
mkdir -p /var/log/betting
chown betting:betting /var/log/betting
```

### 6. Streamlit Service Setup

Create systemd service for Streamlit:

```bash
# Create service file
cat > /etc/systemd/system/betting-analytics.service << EOF
[Unit]
Description=Sports Betting Analytics Streamlit App
After=network.target

[Service]
Type=simple
User=betting
WorkingDirectory=/opt/betting
Environment=PATH=/usr/bin:/usr/local/bin
ExecStart=/usr/local/bin/streamlit run dynamic_nfl_reports.py --server.port=8501 --server.address=0.0.0.0
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
systemctl daemon-reload
systemctl enable betting-analytics
systemctl start betting-analytics
```

### 7. Nginx Reverse Proxy (Optional)

```bash
# Create nginx config
cat > /etc/nginx/sites-available/betting-analytics << EOF
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
EOF

# Enable site
ln -s /etc/nginx/sites-available/betting-analytics /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## 🔧 Data Collection Scripts

### Enhanced Fetch Scripts with Error Handling

```python
# scripts/fetch_current_odds_cron.py
#!/usr/bin/env python3
import sys
import os
import logging
from datetime import datetime

# Add project root to path
sys.path.append('/opt/betting')

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/betting/current_odds.log'),
        logging.StreamHandler()
    ]
)

def main():
    try:
        logging.info("Starting current odds collection...")
        
        # Import your existing fetch function
        from fetch_nfl_spreads import main as fetch_spreads
        
        # Run the fetch
        result = fetch_spreads()
        
        logging.info(f"Successfully collected odds: {result}")
        
    except Exception as e:
        logging.error(f"Failed to collect current odds: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Database Cleanup Script

```python
# scripts/cleanup_old_data.py
#!/usr/bin/env python3
import sys
import os
import logging
from datetime import datetime, timedelta

sys.path.append('/opt/betting')
from database.db_connection import DatabaseConnection

logging.basicConfig(level=logging.INFO)

def cleanup_old_data():
    """Remove old snapshots and logs to keep database size manageable"""
    db = DatabaseConnection()
    
    # Remove snapshots older than 90 days
    cutoff_date = datetime.now() - timedelta(days=90)
    
    query = """
    DELETE FROM api_snapshots 
    WHERE snapshot_timestamp < %s
    """
    
    result = db.execute_query(query, (cutoff_date,))
    logging.info(f"Cleaned up old snapshots before {cutoff_date}")
    
    # Remove old query history (keep 30 days)
    query_cutoff = datetime.now() - timedelta(days=30)
    query = """
    DELETE FROM query_history 
    WHERE created_at < %s
    """
    
    result = db.execute_query(query, (query_cutoff,))
    logging.info(f"Cleaned up old query history before {query_cutoff}")

if __name__ == "__main__":
    cleanup_old_data()
```

## 📊 Monitoring & Maintenance

### 1. Log Management

```bash
# Setup logrotate
cat > /etc/logrotate.d/betting-analytics << EOF
/var/log/betting/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
```

### 2. Health Check Script

```bash
# scripts/health_check.sh
#!/bin/bash

echo "=== Betting Analytics Health Check ==="
echo "Date: $(date)"
echo ""

# Check if Streamlit is running
if pgrep -f "streamlit run" > /dev/null; then
    echo "✅ Streamlit app is running"
else
    echo "❌ Streamlit app is NOT running"
    echo "Attempting to restart..."
    systemctl restart betting-analytics
fi

# Check PostgreSQL
if systemctl is-active --quiet postgresql; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL is NOT running"
fi

# Check recent cron job execution
echo ""
echo "Recent cron job logs:"
tail -n 5 /var/log/betting/current_odds.log

# Check disk space
echo ""
echo "Disk usage:"
df -h /

# Check database size
echo ""
echo "Database size:"
sudo -u postgres psql -d betting_analytics -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

### 3. Backup Script

```bash
# scripts/backup_database.sh
#!/bin/bash

BACKUP_DIR="/opt/betting/backups"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="betting_analytics_$DATE.sql"

mkdir -p $BACKUP_DIR

# Create database backup
sudo -u postgres pg_dump betting_analytics > $BACKUP_DIR/$FILENAME

# Compress backup
gzip $BACKUP_DIR/$FILENAME

# Remove backups older than 7 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/$FILENAME.gz"

# Add to cron for daily backups at 3 AM
# 0 3 * * * /opt/betting/scripts/backup_database.sh >> /var/log/betting/backup.log 2>&1
```

## 🔒 Security Hardening

### 1. Firewall Setup

```bash
# Install and configure UFW
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80    # HTTP
ufw allow 443   # HTTPS (if using SSL)
ufw enable
```

### 2. PostgreSQL Security

```bash
# Edit PostgreSQL config
nano /etc/postgresql/14/main/postgresql.conf

# Set:
listen_addresses = 'localhost'

# Edit access control
nano /etc/postgresql/14/main/pg_hba.conf

# Ensure only local connections:
local   all             all                                     md5
host    all             all             127.0.0.1/32            md5
```

### 3. Application Security

```bash
# Create non-root user for application
useradd -m -s /bin/bash betting
usermod -aG sudo betting

# Set proper file permissions
chown -R betting:betting /opt/betting
chmod 700 /opt/betting
chmod 600 /opt/betting/.env
```

## 💰 Cost Breakdown (Monthly)

### DigitalOcean Example
- **Droplet (4GB RAM, 2 vCPUs):** $24
- **Backups (optional):** $4.80
- **Monitoring:** Free
- **Total:** ~$29/month

### Additional Costs
- **Domain name:** $12/year
- **SSL certificate:** Free (Let's Encrypt)
- **API credits:** $0-50 (depending on usage)

**Total monthly cost:** $30-80 vs $320-400 for Azure microservices

## 🚀 Deployment Checklist

- [ ] Provision server
- [ ] Install dependencies (PostgreSQL, Python, Nginx)
- [ ] Setup database and user
- [ ] Deploy application code
- [ ] Configure environment variables
- [ ] Initialize database schema
- [ ] Setup cron jobs
- [ ] Configure Streamlit service
- [ ] Setup reverse proxy (optional)
- [ ] Configure firewall
- [ ] Setup monitoring and backups
- [ ] Test all functionality

**Estimated setup time:** 2-3 hours vs 1-2 days for Azure

This single-server approach gives you 90% of the functionality with 10% of the complexity!