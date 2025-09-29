# Docker Deployment - Sports Betting Analytics

## 🐳 Quick Start

### 1. Prerequisites
```bash
# Install Docker and Docker Compose
docker --version
docker-compose --version
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit with your API keys
nano .env
```

### 3. Start Services
```bash
# Start PostgreSQL and Streamlit app
docker-compose up -d

# View logs
docker-compose logs -f streamlit
```

### 4. Access Application
- **Streamlit App:** http://localhost:8501
- **PostgreSQL:** localhost:5432

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Streamlit    │    │   PostgreSQL    │    │ Data Collector  │
│   Container     │◄──►│   Container     │◄──►│   Container     │
│   Port: 8501    │    │   Port: 5432    │    │  (Cron Jobs)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                         ┌─────────────────┐
                         │  Docker Volume  │
                         │ (postgres_data) │
                         └─────────────────┘
```

## 📋 Available Services

### Core Services (Always Running)
- **postgres:** PostgreSQL database
- **streamlit:** Main web application

### Optional Services
- **data-collector:** Scheduled data collection (cron jobs)
- **nginx:** Reverse proxy (production profile)

## 🚀 Usage Examples

### Development Mode
```bash
# Start just database and app
docker-compose up postgres streamlit

# View app logs
docker-compose logs -f streamlit

# Access database directly
docker-compose exec postgres psql -U postgres -d betting_analytics
```

### Production Mode
```bash
# Start all services including nginx
docker-compose --profile production up -d

# Access via nginx (port 80)
curl http://localhost
```

### Data Collection Only
```bash
# Start database and data collector
docker-compose up -d postgres data-collector

# Check cron job logs
docker-compose exec data-collector tail -f /app/logs/current_odds.log
```

## 🔧 Configuration

### Environment Variables
```bash
# Required
CLAUDE_API_KEY=your-key-here
ODDS_API_KEY=your-key-here
DB_PASSWORD=secure-password

# Optional
STREAMLIT_PORT=8501
LOG_LEVEL=INFO
```

### Volume Mounts
- **postgres_data:** Database persistence
- **./logs:** Application logs
- **./scripts:** Data collection scripts

## 📊 Data Management

### Database Initialization
```bash
# Database schema is automatically created on first start
# Check initialization logs:
docker-compose logs postgres

# Manually run database setup:
docker-compose exec streamlit python3 database/db_connection.py
```

### Manual Data Collection
```bash
# Collect current odds
docker-compose exec data-collector python3 fetch_nfl_spreads.py

# Backfill historical data
docker-compose exec data-collector python3 fetch_nfl_seasons.py --single-season 2024

# Check database contents
docker-compose exec postgres psql -U postgres -d betting_analytics -c "SELECT COUNT(*) FROM games;"
```

### Data Backup
```bash
# Create database backup
docker-compose exec postgres pg_dump -U postgres betting_analytics > backup.sql

# Restore from backup
cat backup.sql | docker-compose exec -T postgres psql -U postgres -d betting_analytics
```

## 🔍 Monitoring & Debugging

### View Logs
```bash
# All services
docker-compose logs

# Specific service
docker-compose logs streamlit
docker-compose logs data-collector

# Follow logs in real-time
docker-compose logs -f --tail=100 streamlit
```

### Check Service Health
```bash
# Service status
docker-compose ps

# Database health
docker-compose exec postgres pg_isready -U postgres

# App health  
curl http://localhost:8501/_stcore/health
```

### Debug Container
```bash
# Access running container
docker-compose exec streamlit bash
docker-compose exec data-collector bash

# Check cron jobs
docker-compose exec data-collector crontab -l

# View cron logs
docker-compose exec data-collector tail -f /var/log/cron.log
```

## 🛠️ Maintenance

### Update Application
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Reset Database
```bash
# WARNING: This deletes all data
docker-compose down -v
docker-compose up -d
```

### Clean Up
```bash
# Remove stopped containers
docker-compose down

# Remove everything including volumes
docker-compose down -v --remove-orphans

# Clean up Docker system
docker system prune -a
```

## 📈 Scaling & Performance

### Resource Limits
```yaml
# Add to docker-compose.yml
services:
  streamlit:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Multiple Instances
```bash
# Scale streamlit service
docker-compose up -d --scale streamlit=3

# Load balance with nginx
# (requires nginx configuration)
```

## 🔒 Security

### Production Considerations
- Change default passwords in `.env`
- Use Docker secrets for sensitive data
- Enable nginx SSL/TLS
- Restrict database access
- Regular security updates

### Secrets Management
```bash
# Use Docker secrets instead of environment variables
echo "your-secret-key" | docker secret create claude_api_key -

# Update docker-compose.yml to use secrets
secrets:
  - claude_api_key
```

## 🚧 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check postgres is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres pg_isready -U postgres
```

#### Streamlit Won't Start
```bash
# Check logs for errors
docker-compose logs streamlit

# Rebuild container
docker-compose build streamlit --no-cache
docker-compose up -d streamlit
```

#### Cron Jobs Not Running
```bash
# Check cron service in collector
docker-compose exec data-collector ps aux | grep cron

# Check cron logs
docker-compose exec data-collector tail -f /var/log/cron.log

# Restart collector
docker-compose restart data-collector
```

### Performance Issues
```bash
# Check resource usage
docker stats

# Check database performance
docker-compose exec postgres psql -U postgres -d betting_analytics -c "
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;"
```

## 📞 Support

For issues:
1. Check logs: `docker-compose logs [service]`
2. Verify configuration: `.env` file
3. Test connectivity: `docker-compose exec [service] bash`
4. Reset if needed: `docker-compose down -v && docker-compose up -d`

---

## 🎯 Quick Commands Reference

```bash
# Development
docker-compose up -d postgres streamlit
docker-compose logs -f streamlit

# Production  
docker-compose --profile production up -d
docker-compose logs nginx

# Maintenance
docker-compose exec postgres pg_dump -U postgres betting_analytics > backup.sql
docker-compose down && docker-compose build --no-cache && docker-compose up -d

# Debugging
docker-compose exec streamlit python3 -c "from database.db_connection import DatabaseConnection; print('DB OK' if DatabaseConnection().test_connection() else 'DB Failed')"
```