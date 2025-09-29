#!/bin/bash

# Quick deployment script for Sports Betting Analytics
# Usage: ./deploy.sh your-server-ip

SERVER_IP=$1

if [ -z "$SERVER_IP" ]; then
    echo "Usage: ./deploy.sh <server-ip>"
    echo "Example: ./deploy.sh 165.227.123.45"
    exit 1
fi

echo "🚀 Deploying Sports Betting Analytics to $SERVER_IP"

# Copy files to server
echo "📦 Copying files..."
rsync -avz --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
    ./ root@$SERVER_IP:/opt/betting/

# Run setup on server
echo "🔧 Setting up server..."
ssh root@$SERVER_IP << 'EOF'
# Update system
apt update && apt upgrade -y

# Install dependencies
apt install -y python3 python3-pip postgresql postgresql-contrib nginx supervisor

# Install Python packages
cd /opt/betting
pip3 install -r requirements.txt

# Setup PostgreSQL
systemctl start postgresql
systemctl enable postgresql
sudo -u postgres psql << 'PSQL'
CREATE DATABASE betting_analytics;
CREATE USER betting_user WITH ENCRYPTED PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE betting_analytics TO betting_user;
\q
PSQL

# Initialize database
python3 database/db_connection.py

# Create systemd service for Streamlit
cat > /etc/systemd/system/betting-analytics.service << 'SERVICE'
[Unit]
Description=Sports Betting Analytics
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/betting
Environment=PATH=/usr/bin:/usr/local/bin
Environment=DB_HOST=localhost
Environment=DB_PORT=5432
Environment=DB_NAME=betting_analytics
Environment=DB_USER=betting_user
Environment=DB_PASSWORD=secure_password
ExecStart=/usr/local/bin/streamlit run dynamic_nfl_reports.py --server.port=8501 --server.address=0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

# Start the service
systemctl daemon-reload
systemctl enable betting-analytics
systemctl start betting-analytics

# Setup nginx proxy
cat > /etc/nginx/sites-available/betting << 'NGINX'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
NGINX

ln -s /etc/nginx/sites-available/betting /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Setup firewall
ufw allow ssh
ufw allow 80
ufw allow 443
ufw --force enable

echo "✅ Deployment complete!"
echo "🌐 Access your app at: http://$HOSTNAME"
echo "📊 Streamlit direct: http://$HOSTNAME:8501"

EOF

echo "🎉 Deployment finished!"
echo "Your app should be running at: http://$SERVER_IP"