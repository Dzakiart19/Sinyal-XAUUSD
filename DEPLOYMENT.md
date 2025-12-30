# Deployment Guide

## Deploy di VPS (Ubuntu/Debian)

### 1. Persiapkan VPS

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.8+
sudo apt install python3 python3-pip python3-venv git -y

# Install screen (optional, untuk background process)
sudo apt install screen -y
```

### 2. Clone dan Setup Bot

```bash
# Clone repository
git clone <repository-url>
cd xauusd_bot

# Jalankan install script
chmod +x install.sh
./install.sh
```

### 3. Konfigurasi Bot

```bash
# Edit file .env
nano .env

# Isi dengan token bot Anda:
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
ADMIN_USER_ID=123456789
```

### 4. Jalankan Bot (3 Metode)

#### Metode A: Screen (Rekomendasi untuk testing)

```bash
# Buat screen session baru
screen -S xauusd_bot

# Aktifkan virtual environment
source venv/bin/activate

# Jalankan bot
python main.py

# Detach dari screen: Ctrl+A, kemudian D

# Reattach ke screen
screen -r xauusd_bot
```

#### Metode B: Systemd Service (Rekomendasi untuk production)

```bash
# Copy service file
sudo cp xauusd_bot.service /etc/systemd/system/

# Edit service file (ganti path dan user)
sudo nano /etc/systemd/system/xauusd_bot.service

# Reload systemd
sudo systemctl daemon-reload

# Enable service (auto-start saat boot)
sudo systemctl enable xauusd_bot

# Start service
sudo systemctl start xauusd_bot

# Cek status
sudo systemctl status xauusd_bot

# Lihat logs
sudo journalctl -u xauusd_bot -f

# Stop service
sudo systemctl stop xauusd_bot

# Restart service
sudo systemctl restart xauusd_bot
```

#### Metode C: PM2 (Alternative)

```bash
# Install PM2
npm install -g pm2

# Jalankan bot dengan PM2
pm2 start main.py --name xauusd_bot --interpreter python3

# Save PM2 process list
pm2 save

# Setup auto-start
pm2 startup

# Monitor
pm2 monit

# Logs
pm2 logs xauusd_bot

# Stop
pm2 stop xauusd_bot

# Restart
pm2 restart xauusd_bot
```

### 5. Monitoring

```bash
# Cek logs
sudo journalctl -u xauusd_bot -f

# atau
pm2 logs xauusd_bot

# atau
tail -f logs/bot.log
```

## Deploy di Windows

### 1. Install Python

Download dan install Python 3.8+ dari [python.org](https://www.python.org/downloads/)

### 2. Setup Bot

```cmd
# Clone atau extract bot files
cd xauusd_bot

# Buat virtual environment
python -m venv venv

# Aktifkan virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Jalankan Bot

```cmd
# Aktifkan virtual environment
venv\Scripts\activate

# Jalankan bot
python main.py
```

### 4. Background Process (Optional)

Gunakan Windows Task Scheduler atau Windows Service untuk auto-start.

## Deploy di Docker

### 1. Buat Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy bot files
COPY . .

# Create directories
RUN mkdir -p data logs

# Set environment variables
ENV PYTHONPATH=/app

# Run bot
CMD ["python", "main.py"]
```

### 2. Build dan Run

```bash
# Build image
docker build -t xauusd_bot .

# Run container
docker run -d \
  --name xauusd_bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/.env:/app/.env:ro \
  xauusd_bot

# Cek logs
docker logs -f xauusd_bot

# Stop container
docker stop xauusd_bot

# Start container
docker start xauusd_bot
```

### 3. Docker Compose (Rekomendasi)

Buat file `docker-compose.yml`:

```yaml
version: '3.8'

services:
  xauusd_bot:
    build: .
    container_name: xauusd_bot
    restart: unless-stopped
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./.env:/app/.env:ro
    environment:
      - TZ=Asia/Jakarta
```

Jalankan:

```bash
# Build dan start
docker-compose up -d

# Cek logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart
```

## Auto-Restart Script

Buat script `auto_restart.sh`:

```bash
#!/bin/bash

# Check if bot is running
if ! pgrep -f "python.*main.py" > /dev/null; then
    echo "$(date): Bot is not running, restarting..."
    cd /path/to/xauusd_bot
    source venv/bin/activate
    nohup python main.py > logs/nohup.log 2>&1 &
    echo "$(date): Bot restarted"
fi
```

Jadikan executable dan tambahkan ke crontab:

```bash
chmod +x auto_restart.sh

# Edit crontab
crontab -e

# Tambahkan baris ini (check setiap 5 menit)
*/5 * * * * /path/to/xauusd_bot/auto_restart.sh
```

## Backup Strategy

### Backup Otomatis

Buat script `backup.sh`:

```bash
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/path/to/backups"
BOT_DIR="/path/to/xauusd_bot"

# Create backup
mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/xauusd_bot_backup_$DATE.tar.gz \
    -C $BOT_DIR \
    data logs .env

# Keep only last 7 backups
find $BACKUP_DIR -name "xauusd_bot_backup_*.tar.gz" -mtime +7 -delete

echo "Backup created: xauusd_bot_backup_$DATE.tar.gz"
```

Tambahkan ke crontab untuk backup harian:

```bash
# Backup setiap hari jam 2 pagi
0 2 * * * /path/to/xauusd_bot/backup.sh
```

### Restore dari Backup

```bash
# Extract backup
tar -xzf xauusd_bot_backup_YYYYMMDD_HHMMSS.tar.gz

# Copy ke directory bot
cp -r data /path/to/xauusd_bot/
cp -r logs /path/to/xauusd_bot/
cp .env /path/to/xauusd_bot/
```

## Monitoring & Alerting

### 1. Health Check Script

Buat `health_check.sh`:

```bash
#!/bin/bash

# Check bot process
if ! pgrep -f "python.*main.py" > /dev/null; then
    echo "Bot is down!" | mail -s "XAUUSD Bot Alert" your-email@example.com
    # atau kirim notifikasi Telegram
    curl -X POST "https://api.telegram.org/botYOUR_BOT_TOKEN/sendMessage" \
        -d "chat_id=YOUR_ADMIN_ID&text=🚨 Bot is down!"
fi

# Check disk space
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "Disk space running low: $DISK_USAGE%" | mail -s "XAUUSD Bot Alert" your-email@example.com
fi
```

### 2. Log Rotation

Setup logrotate:

```bash
# Buat file /etc/logrotate.d/xauusd_bot
sudo nano /etc/logrotate.d/xauusd_bot
```

Isi dengan:

```
/path/to/xauusd_bot/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
```

## Security Best Practices

### 1. Firewall

```bash
# Allow only SSH and necessary ports
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 22/tcp
sudo ufw enable
```

### 2. User Privileges

Jalankan bot dengan user biasa (bukan root):

```bash
# Create user
sudo useradd -m -s /bin/bash xauusd_bot

# Give permissions
sudo chown -R xauusd_bot:xauusd_bot /path/to/xauusd_bot

# Edit service file
sudo nano /etc/systemd/system/xauusd_bot.service
# Ganti User=ubuntu menjadi User=xauusd_bot
```

### 3. File Permissions

```bash
# Protect .env file
chmod 600 .env

# Make scripts executable
chmod +x *.sh

# Restrict data directory
chmod 750 data/
```

## Performance Tuning

### 1. Python Optimization

```bash
# Install optimized packages
pip install --upgrade numpy pandas

# Use PyPy for better performance (optional)
# Install PyPy dan jalankan dengan pypy3 main.py
```

### 2. System Limits

Edit `/etc/security/limits.conf`:

```
xauusd_bot soft nofile 65536
xauusd_bot hard nofile 65536
```

### 3. Network Optimization

```bash
# Increase TCP buffer sizes
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

## Update Bot

### Update dengan Git

```bash
# Stop bot
sudo systemctl stop xauusd_bot

# Pull latest changes
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Start bot
sudo systemctl start xauusd_bot
```

### Manual Update

1. Backup data lama
2. Extract file baru
3. Copy data dan logs
4. Update dependencies
5. Restart bot

## Troubleshooting Production

### Bot tidak start

1. Cek log: `sudo journalctl -u xauusd_bot -n 50`
2. Cek .env file
3. Cek permissions
4. Cek disk space

### Memory leak

Monitor memory usage:

```bash
# Cek memory usage
ps aux | grep xauusd_bot

# Restart jika memory > 500MB
```

### Connection issues

1. Cek firewall
2. Cek DNS settings
3. Test WebSocket connection
4. Cek proxy settings (jika ada)

## Support

Jika mengalami masalah:
1. Cek log file di `logs/bot.log`
2. Cek status service: `sudo systemctl status xauusd_bot`
3. Hubungi admin dengan menyertakan log error