#!/bin/bash

# XAUUSD Bot Runner Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check if bot is running
check_running() {
    if pgrep -f "python.*main.py" > /dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to start bot
start_bot() {
    if check_running; then
        echo -e "${YELLOW}Bot sudah berjalan!${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Menjalankan XAUUSD Bot...${NC}"
    
    # Activate virtual environment
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}Virtual environment tidak ditemukan!${NC}"
        echo "Jalankan ./install.sh terlebih dahulu"
        return 1
    fi
    
    # Check .env file
    if [ ! -f ".env" ]; then
        echo -e "${RED}File .env tidak ditemukan!${NC}"
        echo "Silakan copy .env.example dan isi dengan token bot Anda"
        return 1
    fi
    
    # Check if token is configured
    if grep -q "YOUR_TELEGRAM_BOT_TOKEN_HERE" .env; then
        echo -e "${RED}Token bot belum dikonfigurasi!${NC}"
        echo "Edit file .env dan isi TELEGRAM_BOT_TOKEN dengan token Anda"
        return 1
    fi
    
    # Run bot
    python main.py
}

# Function to stop bot
stop_bot() {
    if ! check_running; then
        echo -e "${YELLOW}Bot tidak sedang berjalan!${NC}"
        return 1
    fi
    
    echo -e "${GREEN}Menghentikan bot...${NC}"
    pkill -f "python.*main.py"
    
    # Wait for process to stop
    for i in {1..10}; do
        if ! check_running; then
            echo -e "${GREEN}Bot berhasil dihentikan!${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}Gagal menghentikan bot!${NC}"
    return 1
}

# Function to show status
show_status() {
    if check_running; then
        echo -e "${GREEN}Status: Bot sedang berjalan ✅${NC}"
        
        # Show process info
        PID=$(pgrep -f "python.*main.py")
        if [ ! -z "$PID" ]; then
            echo "PID: $PID"
            echo "Memory: $(ps -o pid,vsz,rss,comm -p $PID | tail -1 | awk '{print $3/1024 " MB"}')"
            echo "CPU: $(ps -o pid,pcpu,comm -p $PID | tail -1 | awk '{print $2 "%"}')"
        fi
    else
        echo -e "${RED}Status: Bot tidak berjalan ❌${NC}"
    fi
}

# Function to show logs
show_logs() {
    echo -e "${GREEN}Menampilkan log terakhir...${NC}"
    if [ -f "logs/bot.log" ]; then
        tail -n 50 logs/bot.log
    else
        echo -e "${YELLOW}File log tidak ditemukan!${NC}"
    fi
}

# Function to show help
show_help() {
    echo "=========================================="
    echo "XAUUSD Bot Control Panel"
    echo "=========================================="
    echo ""
    echo "Usage: ./run.sh [option]"
    echo ""
    echo "Options:"
    echo "  start     - Jalankan bot"
    echo "  stop      - Hentikan bot"
    echo "  restart   - Restart bot"
    echo "  status    - Cek status bot"
    echo "  logs      - Lihat log terakhir"
    echo "  help      - Tampilkan bantuan"
    echo ""
    echo "Contoh:"
    echo "  ./run.sh start"
    echo "  ./run.sh status"
    echo "  ./run.sh logs"
}

# Main script logic
case "${1:-help}" in
    "start")
        start_bot
        ;;
    "stop")
        stop_bot
        ;;
    "restart")
        stop_bot
        sleep 2
        start_bot
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    "help"|"--help"|"-h")
        show_help
        ;;
    *)
        echo -e "${RED}Perintah tidak dikenal: $1${NC}"
        show_help
        ;;
esac