# 🚀 Getting Started - XAUUSD Scalping Bot

## Langkah 1: Persiapkan Environment (2 Menit)

### Install Python 3.8+
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip git -y

# CentOS/RHEL
sudo yum install python3 python3-pip git -y

# Windows: Download dari python.org
```

### Clone Repository
```bash
git clone <repository-url>
cd xauusd_bot
```

## Langkah 2: Install Dependencies (3 Menit)

### Jalankan Install Script
```bash
chmod +x install.sh
./install.sh
```

Atau manual:
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate     # Windows

pip install -r requirements.txt
```

## Langkah 3: Dapatkan Bot Token (5 Menit)

### Cara Mendapatkan Token

1. Buka Telegram di HP atau Desktop
2. Cari @BotFather (bot resmi Telegram)
3. Kirim perintah: `/newbot`
4. Beri nama bot Anda (misal: "XAUUSD Signal Bot")
5. Beri username bot (harus unik, misal: "xauusd_signal_bot123")
6. BotFather akan memberikan token seperti ini:
   ```
   123456789:ABCdefGHIjklMNOpqrSTUvwxyz
   ```
7. Simpan token ini dengan amat!

### Dapatkan Admin User ID

1. Buka Telegram
2. Cari @userinfobot
3. Kirim `/start`
4. Bot akan memberikan User ID Anda

## Langkah 4: Konfigurasi Bot (2 Menit)

### Edit File .env

```bash
# Copy template
# cp .env.example .env  # (jika belum ada)

# Edit file
nano .env
```

### Isi Konfigurasi

```env
# WAJIB DIISI:
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
ADMIN_USER_ID=123456789

# Optional (default values are good)
DEFAULT_TP=3.0
DEFAULT_SL=3.0
EMA_PERIOD=50
RSI_PERIOD=3
ADX_PERIOD=55
ADX_THRESHOLD=30
```

## Langkah 5: Test Bot (3 Menit)

### Jalankan Test Suite
```bash
python test_bot.py
```

### Hasil yang Diharapkan
```
✅ Configuration
✅ WebSocket Connection
✅ Technical Indicators
✅ User Management
✅ Statistics
✅ Position Tracking
✅ Signal Generator

🎉 All tests passed! Bot is ready to run.
```

Jika ada yang FAIL, cek pesan error dan perbaiki.

## Langkah 6: Jalankan Bot (1 Menit)

### Opsi A: Development Mode
```bash
source venv/bin/activate
python main.py
```

### Opsi B: Production Mode
```bash
# Menggunakan helper script
./run.sh start

# Atau dengan screen
screen -S xauusd_bot
source venv/bin/activate
python main.py
# Detach: Ctrl+A, kemudian D
```

## Langkah 7: Test di Telegram (2 Menit)

### 1. Cari Bot Anda
- Buka Telegram
- Cari username bot yang Anda buat (misal: @xauusd_signal_bot123)
- Klik Start

### 2. Kirim Command
```
/start
```

Bot akan membalas dengan welcome message dan dashboard.

### 3. Test Commands
```
/dashboard    # Lihat dashboard live
/stats        # Lihat statistik
/getsignal    # Minta sinyal manual
/info         # Info strategi
/help         # Bantuan
```

## Langkah 8: Deploy untuk 24/7 (Opsional)

### Setup Systemd Service (Linux)

```bash
# Copy service file
sudo cp xauusd_bot.service /etc/systemd/system/

# Edit service (ganti path dan user)
sudo nano /etc/systemd/system/xauusd_bot.service

# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable xauusd_bot

# Start service
sudo systemctl start xauusd_bot

# Cek status
sudo systemctl status xauusd_bot

# Lihat logs
sudo journalctl -u xauusd_bot -f
```

### Setup PM2 (Cross-platform)

```bash
# Install PM2
npm install -g pm2

# Start bot dengan PM2
pm2 start main.py --name xauusd_bot --interpreter python3

# Save process list
pm2 save

# Setup auto-start
pm2 startup

# Monitor
pm2 monit

# Logs
pm2 logs xauusd_bot
```

### Setup Screen (Linux/Mac)

```bash
# Buat screen session
screen -S xauusd_bot

# Jalankan bot
source venv/bin/activate
python main.py

# Detach dari screen
# Tekan Ctrl+A, kemudian D

# Reattach nanti
screen -r xauusd_bot
```

## Langkah 9: Monitor Bot

### Cek Status
```bash
# Cek process
./run.sh status

# Cek logs
./run.sh logs

# Cek systemd (jika pakai systemd)
sudo systemctl status xauusd_bot
```

### Monitor Resource
```bash
# Cek memory
free -h

# Cek CPU
htop

# Cek disk
df -h
```

## 🎯 Cara Menggunakan Bot

### Sinyal Otomatis
- Bot akan otomatis kirim sinyal ketika kondisi terpenuhi
- Sinyal dikirim ke semua user yang aktif
- Posisi akan dipantau hingga TP atau SL

### Sinyal Manual
- Kirim `/getsignal` untuk minta sinyal
- Sinyal khusus untuk Anda sendiri
- Tidak mempengaruhi sinyal otomatis

### Dashboard
- Ketik `/dashboard` untuk buka dashboard
- Harga update setiap 5 detik
- Lihat posisi aktif dengan PnL
- Dashboard akan auto-update

### Statistik
- Ketik `/stats` untuk lihat performa
- Winrate, total PnL, dll.
- Breakdown per timeframe

## 🆘 Troubleshooting

### Bot tidak merespon
1. Cek apakah bot sedang berjalan
2. Cek log untuk error
3. Restart bot

### Tidak ada sinyal
1. Cek `/dashboard` - pastikan WebSocket terhubung
2. Cek ADX > 30 (filter aktif)
3. Tunggu kondisi market sesuai strategi

### WebSocket putus
- Bot akan otomatis reconnect
- Cek koneksi internet
- Cek firewall/proxy

### Dashboard tidak update
```
/stop
/dashboard
```

## 📚 Dokumentasi

Baca file berikut untuk informasi lebih lanjut:
- `README.md` - Dokumentasi lengkap
- `DEPLOYMENT.md` - Guide deployment
- `QUICK_START.md` - Guide ini
- `PROJECT_SUMMARY.md` - Summary project

## 🔧 Tips

### Backup Data
Backup folder `data/` secara berkala:
```bash
tar -czf backup_$(date +%Y%m%d).tar.gz data/
```

### Update Bot
```bash
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
```

### Custom Strategy
Edit file di `src/` untuk strategi custom:
- `indicators.py` - Technical indicators
- `signal_generator.py` - Signal logic

## 🎉 Selamat!

Bot Anda sekarang siap untuk trading XAUUSD 24/7!

### Apa yang Terjadi Selanjutnya?

1. **Bot akan**: Scan market setiap detik
2. **Bot akan**: Kirim sinyal saat kondisi terpenuhi
3. **Bot akan**: Tracking posisi real-time
4. **Bot akan**: Update dashboard setiap 5 detik
5. **Bot akan**: Hitung statistik trading

### Monitoring Otomatis

Bot memiliki fitur monitoring otomatis:
- ✅ Health check WebSocket
- ✅ Memory usage monitoring
- ✅ Error recovery
- ✅ Auto-restart capability

---

**Happy Trading! 🚀📈**

---

## 📞 Butuh Bantuan?

1. Cek log file: `logs/bot.log`
2. Jalankan test: `python test_bot.py`
3. Baca dokumentasi: `README.md`
4. Cek status: `./run.sh status`

## 📊 Progress Checklist

Setelah selesai setup, cek apakah semua berjalan:

- [ ] Bot terhubung ke WebSocket
- [ ] Commands berfungsi di Telegram
- [ ] Dashboard update real-time
- [ ] Sinyal otomatis terkirim
- [ ] Sinyal manual bisa direquest
- [ ] Position tracking berfungsi
- [ ] Statistics dihitung dengan benar
- [ ] Logs tidak menunjukkan error
- [ ] Resource usage normal (<100MB RAM)

Jika semua checklist tercentang, **SELAMAT!** 🎉

Bot Anda siap untuk trading XAUUSD 24/7 dengan strategi scalping yang optimal!