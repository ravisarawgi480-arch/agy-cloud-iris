#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "   AGY Cloud Brain - 1-Click Autonomous Server Installer  "
echo "=========================================================="

# Update system packages
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv git curl cron

# Create working directory
APP_DIR="/opt/agy_cloud"
sudo mkdir -p $APP_DIR
sudo cp -r ./* $APP_DIR/
cd $APP_DIR

# Set up Python virtual environment
python3 -m venv venv
./venv/bin/pip install --upgrade pip

# Create systemd service for 24/7 Telegram Commander
cat << 'EOF' | sudo tee /etc/systemd/system/agy_telegram.service
[Unit]
Description=AGY Cloud Telegram Commander
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/agy_cloud
ExecStart=/opt/agy_cloud/venv/bin/python /opt/agy_cloud/cloud_telegram_commander.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Reload and enable systemd service
sudo systemctl daemon-reload
sudo systemctl enable agy_telegram.service
sudo systemctl restart agy_telegram.service

# Setup cron job to run cloud_school_daemon every 4 hours
CRON_JOB="0 */4 * * * /opt/agy_cloud/venv/bin/python /opt/agy_cloud/cloud_school_daemon.py >> /var/log/agy_school.log 2>&1"
(crontab -l 2>/dev/null | grep -Fv "cloud_school_daemon.py" ; echo "$CRON_JOB") | crontab -

echo ""
echo "=========================================================="
echo "   SUCCESS: AGY Cloud Brain is 24/7 Live & Operational!   "
echo "=========================================================="
sudo systemctl status agy_telegram.service --no-pager
