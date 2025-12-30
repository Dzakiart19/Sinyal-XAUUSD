# XAUUSD Scalping Signal Bot

Bot Telegram otomatis untuk sinyal trading XAUUSD (Gold) dengan strategi scalping menggunakan EMA 50, RSI 3, dan ADX 55.

## 🎯 Fitur Utama

- **Real-time 24/7**: Bot berjalan nonstop dengan data real-time dari Deriv
- **Dual Timeframe**: Analisis M1 & M5 untuk presisi scalping
- **Strategi Lengkap**: EMA 50 + RSI 3 + ADX 55 dengan filter trend
- **Signal Otomatis**: Sinyal dikirim ke semua user aktif
- **Sinyal Manual**: Command `/getsignal` untuk sinyal khusus per user
- **Tracking Real-time**: Posisi dipantau setiap 5 detik
- **Dashboard Live**: Harga live dan update posisi otomatis
- **Statistik Lengkap**: Winrate, PnL, dan history trading

## 📊 Strategi Trading

### Indikator
- **EMA 50**: Identifikasi arah trend
- **RSI 3**: Deteksi momentum entry/exit
- **ADX 55**: Filter kekuatan trend (hanya signal jika ADX > 30)

### Logika Sinyal

🟢 **BUY Signal:**
1. Harga di atas EMA 50
2. RSI keluar dari zona oversold (±20-25)
3. ADX > 30 (trend cukup kuat)
4. RSI dalam range ±25-50

🔴 **SELL Signal:**
1. Harga di bawah EMA 50
2. RSI keluar dari zona overbought (±75-80)
3. ADX > 30 (trend cukup kuat)
4. RSI dalam range 50-75

### Risk Management
- Risk:Reward = 1:1
- TP: $3
- SL: $3

## 🚀 Instalasi

### Persyaratan
- Python 3.8+
- Telegram Bot Token
- Koneksi internet stabil

### Langkah Instalasi

1. **Clone Repository**
```bash
git clone <repository-url>
cd xauusd_bot
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Konfigurasi Bot**
```bash
# Edit file .env
TELEGRAM_BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_USER_ID=YOUR_ADMIN_ID
```

4. **Dapatkan Bot Token**
   - Buka Telegram
   - Cari @BotFather
   - Buat bot baru: `/newbot`
   - Salin token yang diberikan
   - Isi di file `.env`

5. **Jalankan Bot**
```bash
python main.py
```

## 📱 Command Telegram

### Perintah Utama

| Command | Fungsi |
|---------|--------|
| `/start` | Aktifkan bot & mulai sinyal otomatis |
| `/dashboard` | Dashboard live dengan harga & posisi |
| `/stats` | Statistik trading lengkap |
| `/getsignal` | Sinyal manual khusus user |
| `/info` | Info sistem & strategi |
| `/riset` | Reset data historis trading |
| `/help` | Bantuan & daftar perintah |
| `/stop` | Hentikan dashboard |

### Fitur Dashboard
- Harga XAUUSD real-time (update 5 detik)
- Posisi aktif dengan PnL
- Status koneksi WebSocket
- Jumlah posisi terbuka

### Fitur Statistik
- Total signal diterima
- Win/Loss count
- Winrate (%)
- Total PnL ($)
- Rata-rata PnL per trade
- Breakdown per timeframe (M1/M5)
- Breakdown manual vs auto signals

## 🏗️ Arsitektur Sistem

### Komponen Utama

1. **WebSocket Client** (`websocket_client.py`)
   - Koneksi ke Deriv WebSocket
   - Stream tick data real-time
   - Historical candle data (M1 & M5)

2. **Technical Indicators** (`indicators.py`)
   - EMA 50 calculation
   - RSI 3 calculation
   - ADX 55 calculation
   - Signal logic validation

3. **Signal Generator** (`signal_generator.py`)
   - Scanning otomatis M1 & M5
   - Generate sinyal BUY/SELL
   - Anti-duplikasi candle
   - Sinyal manual per user

4. **Position Tracker** (`position_tracker.py`)
   - Tracking posisi real-time
   - Hitung PnL setiap 5 detik
   - Deteksi TP/SL
   - Notifikasi hasil trading

5. **Telegram Bot** (`telegram_bot.py`)
   - Command handler
   - Dashboard real-time
   - User management
   - Signal broadcasting

6. **User Manager** (`user_manager.py`)
   - User state isolation (anti-leak)
   - Activity tracking
   - Preferences management

7. **Statistics Manager** (`statistics.py`)
   - Rekam semua trade
   - Hitung winrate
   - Analisis performance
   - Export data

### Alur Data

```
Deriv WebSocket → Candle Data → Indicators → Signal Logic → 
Telegram Bot → User Positions → Tracking → Results → Statistics
```

## ⚙️ Konfigurasi

### Environment Variables (.env)

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_USER_ID=your_admin_user_id

# Deriv WebSocket
DERIV_WS_URL=wss://ws.derivws.com/websockets/v3?app_id=1089

# Risk Management
DEFAULT_TP=3.0
DEFAULT_SL=3.0

# Technical Indicators
EMA_PERIOD=50
RSI_PERIOD=3
ADX_PERIOD=55
ADX_THRESHOLD=30

# Timeframes
M1_CANDLE_COUNT=100
M5_CANDLE_COUNT=100

# Update Intervals (seconds)
SIGNAL_CHECK_INTERVAL=1
DASHBOARD_UPDATE_INTERVAL=5
PRICE_TRACKING_INTERVAL=5
```

### Customization

**Mengubah Indikator:**
Edit nilai di file `.env`:
- `EMA_PERIOD`: Periode EMA (default: 50)
- `RSI_PERIOD`: Periode RSI (default: 3)
- `ADX_PERIOD`: Periode ADX (default: 55)
- `ADX_THRESHOLD`: Filter ADX minimum (default: 30)

**Mengubah Risk Management:**
- `DEFAULT_TP`: Take Profit dalam USD (default: 3.0)
- `DEFAULT_SL`: Stop Loss dalam USD (default: 3.0)

**Mengubah Timeframe:**
- `M1_CANDLE_COUNT`: Jumlah candle M1 yang disimpan (default: 100)
- `M5_CANDLE_COUNT`: Jumlah candle M5 yang disimpan (default: 100)

## 📊 Monitoring & Logging

### Log Files
- `logs/bot.log`: Log utama bot
- `data/positions.json`: Data posisi trading
- `data/statistics.json`: Data statistik trading
- `data/users.json`: Data user dan preferences

### Monitoring Dashboard
Gunakan command `/dashboard` untuk melihat:
- Status koneksi WebSocket
- Harga XAUUSD real-time
- Posisi aktif dengan PnL
- Update setiap 5 detik

### Health Check
Bot otomatis memantau:
- Koneksi WebSocket (auto-reconnect)
- Jumlah candle yang tersedia
- Status signal generator
- User activity

## 🔒 Keamanan

- Bot tidak melakukan auto-trading
- Tidak menyimpan credential broker
- Tidak login ke platform trading
- Semua tracking bersifat informasional
- User state terisolasi (no-leak)
- Data lokal dienkripsi (optional)

## ⚠️ Disclaimer

Bot ini hanya untuk analisis dan sinyal trading. Tidak melakukan eksekusi order otomatis. Trading forex dan emas melibatkan risiko kehilangan modal. Selalu gunakan risk management yang tepat dan pertimbangkan untuk berkonsultasi dengan penasihat keuangan profesional.

## 🆘 Troubleshooting

### Masalah Umum

**Bot tidak merespon:**
1. Cek log: `tail -f logs/bot.log`
2. Pastikan token bot valid
3. Cek koneksi internet

**Tidak ada sinyal:**
1. Cek status WebSocket: `/dashboard`
2. Pastikan ADX > 30
3. Tunggu kondisi market sesuai strategi

**Dashboard tidak update:**
1. Cek command `/stop` untuk stop dashboard
2. Jalankan `/dashboard` lagi
3. Cek koneksi internet

### Error Messages

- "WebSocket not connected": Tunggu beberapa detik untuk reconnect
- "Not enough candle data": Bot sedang mengumpulkan data historis
- "No trending condition": ADX terlalu rendah, tunggu market trending

## 📞 Support

Untuk bantuan lebih lanjut:
- Hubungi admin bot
- Cek log file di `logs/`
- Pastikan semua dependencies terinstall

## 📝 Lisensi

Bot ini untuk penggunaan pribadi dan edukasi. Gunakan dengan bijak dan penuh tanggung jawab.