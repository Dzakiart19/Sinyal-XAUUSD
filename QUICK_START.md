# Quick Start Guide

## 🚀 Mulai Cepat (5 Menit)

### 1. Persiapkan Environment

```bash
# Install Python 3.8+ (jika belum)
# Ubuntu/Debian:
sudo apt update && sudo apt install python3 python3-pip git -y

# Windows: Download dari python.org
```

### 2. Setup Bot

```bash
# Clone repository
git clone <repository-url>
cd xauusd_bot

# Jalankan install otomatis
chmod +x install.sh
./install.sh
```

### 3. Dapatkan Bot Token

1. Buka Telegram
2. Cari @BotFather
3. Kirim: `/newbot`
4. Ikuti instruksi
5. Salin token yang diberikan

### 4. Konfigurasi Bot

```bash
# Edit file .env
nano .env

# Ganti token placeholder dengan token Anda:
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrSTUvwxyz
ADMIN_USER_ID=YOUR_TELEGRAM_USER_ID
```

### 5. Jalankan Bot

```bash
# Opsi A: Langsung
python main.py

# Opsi B: Menggunakan helper script
./run.sh start

# Opsi C: Background dengan screen
screen -S xauusd_bot
source venv/bin/activate
python main.py
# Detach: Ctrl+A, kemudian D
```

### 6. Test Bot

```bash
# Jalankan test suite
python test_bot.py
```

## 📱 Pertama Kali Menggunakan Bot

### 1. Start Bot di Telegram

Kirim ke bot Anda:
```
/start
```

Bot akan membalas dengan welcome message dan dashboard otomatis terbuka.

### 2. Command Utama

| Command | Fungsi |
|---------|--------|
| `/dashboard` | Lihat harga live & posisi |
| `/stats` | Statistik trading |
| `/getsignal` | Minta sinyal manual |
| `/info` | Info strategi |
| `/help` | Bantuan |

### 3. Dashboard Live

Dashboard akan otomatis:
- Update harga setiap 5 detik
- Tampilkan posisi aktif
- Hitung PnL real-time

## 🔧 Mode Deployment

### Development Mode

```bash
# Jalankan dengan logging debug
python main.py

# Cek logs
./run.sh logs
```

### Production Mode

```bash
# Setup systemd service
sudo cp xauusd_bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable xauusd_bot
sudo systemctl start xauusd_bot

# Monitor
sudo systemctl status xauusd_bot
sudo journalctl -u xauusd_bot -f
```

## ⚙️ Konfigurasi Cepat

### Ubah Risk Management

Edit `.env`:
```env
DEFAULT_TP=5.0    # Take Profit $5
DEFAULT_SL=5.0    # Stop Loss $5
```

### Ubah Indikator

Edit `.env`:
```env
EMA_PERIOD=50     # EMA 50
RSI_PERIOD=3      # RSI 3
ADX_PERIOD=55     # ADX 55
ADX_THRESHOLD=30  # Filter ADX minimum
```

### Ubah Update Interval

Edit `.env`:
```env
DASHBOARD_UPDATE_INTERVAL=5    # Update setiap 5 detik
PRICE_TRACKING_INTERVAL=5      # Tracking setiap 5 detik
```

## 🎯 Cara Kerja Bot

### Sinyal Otomatis
1. Bot terhubung ke Deriv WebSocket
2. Ambil data candle M1 & M5
3. Hitung indikator EMA, RSI, ADX
4. Cek kondisi sinyal setiap detik
5. Kirim sinyal ke semua user aktif
6. Tracking posisi hingga TP/SL

### Sinyal Manual
1. User kirim `/getsignal`
2. Bot hitung indikator saat ini
3. Cek kondisi sinyal
4. Kirim sinyal khusus user tersebut
5. Tracking terpisah dari sinyal otomatis

### Dashboard
1. Harga update real-time dari WebSocket
2. Posisi aktif dihitung setiap 5 detik
3. PnL diupdate berdasarkan harga terkini
4. Status posisi (TP/SL) dipantau otomatis

## 📊 Monitoring

### Cek Status Bot

```bash
# Cek process
./run.sh status

# Cek logs
./run.sh logs

# Cek systemd service
sudo systemctl status xauusd_bot
```

### Health Check

Bot otomatis memantau:
- ✅ Koneksi WebSocket (auto-reconnect)
- ✅ Data candle tersedia
- ✅ Signal generator berjalan
- ✅ User activity
- ✅ Memory usage

## 🔒 Keamanan

- Bot tidak auto-trading
- Tidak menyimpan credential broker
- Data user terisolasi
- No-leak antar user
- Local data storage

## 🆘 Troubleshooting Cepat

### Bot tidak merespon
```bash
# Cek process
ps aux | grep python

# Restart bot
./run.sh restart
```

### Tidak ada sinyal
1. Cek `/dashboard` - pastikan WebSocket terhubung
2. Cek ADX > 30 (filter aktif)
3. Tunggu kondisi market sesuai strategi

### Dashboard tidak update
```bash
# Stop dan start ulang dashboard
/stop (di Telegram)
/dashboard (di Telegram)
```

### WebSocket putus
- Bot otomatis reconnect
- Cek koneksi internet
- Cek firewall/proxy

## 📈 Performance Tips

### Untuk VPS
- Minimal RAM: 512MB
- Recommended RAM: 1GB
- Storage: 10GB SSD
- Network: Stable 1Mbps+

### Untuk Raspberry Pi
- Model 3B+ atau lebih baru
- OS: Raspberry Pi OS Lite
- Storage: 16GB SD Card
- Network: Ethernet recommended

### Monitoring Resource
```bash
# Cek memory
free -h

# Cek CPU
htop

# Cek disk
df -h
```

## 🎯 Best Practices

1. **Testing dulu**: Jalankan `python test_bot.py` sebelum deployment
2. **Backup data**: Backup file di `data/` secara berkala
3. **Monitor logs**: Cek logs untuk deteksi error
4. **Update dependencies**: Update packages secara berkala
5. **Security**: Jangan share bot token dengan siapa pun

## 🚀 Scale Up

### Multiple Instances
Untuk load balancing atau redundancy:

1. Copy bot ke directory berbeda
2. Gunakan bot token berbeda
3. Setup load balancer (optional)

### Custom Strategy
Ubah logika di `src/indicators.py` dan `src/signal_generator.py` untuk strategi custom.

## 📞 Support

Jika mengalami masalah:
1. Cek `README.md` untuk detail lengkap
2. Cek `DEPLOYMENT.md` untuk troubleshooting
3. Cek log file di `logs/bot.log`
4. Jalankan `python test_bot.py` untuk diagnosis

## 📚 File Penting

| File | Fungsi |
|------|--------|
| `README.md` | Dokumentasi lengkap |
| `DEPLOYMENT.md` | Guide deployment |
| `QUICK_START.md` | Guide cepat (ini) |
| `main.py` | Entry point bot |
| `run.sh` | Helper script |
| `test_bot.py` | Testing suite |
| `.env` | Konfigurasi bot |

## 🎉 Selamat!

Bot Anda sekarang siap beroperasi 24/7 dan akan otomatis:
- ✅ Scan market setiap detik
- ✅ Kirim sinyal saat kondisi terpenuhi
- ✅ Tracking posisi real-time
- ✅ Update dashboard setiap 5 detik
- ✅ Hitung statistik trading

Happy Trading! 🚀📈