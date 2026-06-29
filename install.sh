#!/bin/bash

# ==========================================
# XAUUSD Scalping Bot - Install Script
# ==========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo ""
echo -e "${BLUE}=========================================="
echo -e "  XAUUSD Scalping Bot - Installer"
echo -e "==========================================${NC}"
echo ""

# 1. Cek Python tersedia
echo -e "${YELLOW}[1/5] Mengecek Python...${NC}"
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo -e "${RED}ERROR: Python tidak ditemukan! Pastikan Python 3.10+ sudah terinstall.${NC}"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON --version 2>&1)
echo -e "${GREEN}      ✅ $PYTHON_VERSION ditemukan${NC}"

# 2. Cek pip tersedia
echo ""
echo -e "${YELLOW}[2/5] Mengecek pip...${NC}"
if ! command -v pip &>/dev/null && ! command -v pip3 &>/dev/null; then
    echo -e "${RED}ERROR: pip tidak ditemukan!${NC}"
    exit 1
fi
PIP=$(command -v pip3 || command -v pip)
echo -e "${GREEN}      ✅ pip ditemukan${NC}"

# 3. Install semua dependencies dari requirements.txt
echo ""
echo -e "${YELLOW}[3/5] Menginstall dependencies...${NC}"
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}ERROR: File requirements.txt tidak ditemukan!${NC}"
    exit 1
fi
$PIP install -r requirements.txt -q
if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Gagal menginstall dependencies. Cek koneksi internet dan coba lagi.${NC}"
    exit 1
fi
echo -e "${GREEN}      ✅ Semua dependencies berhasil diinstall${NC}"

# 4. Buat direktori yang dibutuhkan
echo ""
echo -e "${YELLOW}[4/5] Membuat direktori data dan logs...${NC}"
mkdir -p data logs
echo -e "${GREEN}      ✅ Direktori data/ dan logs/ siap${NC}"

# 5. Cek environment variables yang wajib ada
echo ""
echo -e "${YELLOW}[5/5] Mengecek environment variables...${NC}"
MISSING=0

if [ -z "$TELEGRAM_BOT_TOKEN" ]; then
    echo -e "${RED}      ❌ TELEGRAM_BOT_TOKEN belum di-set${NC}"
    MISSING=1
else
    echo -e "${GREEN}      ✅ TELEGRAM_BOT_TOKEN sudah di-set${NC}"
fi

if [ -z "$ADMIN_USER_ID" ]; then
    echo -e "${RED}      ❌ ADMIN_USER_ID belum di-set${NC}"
    MISSING=1
else
    echo -e "${GREEN}      ✅ ADMIN_USER_ID sudah di-set${NC}"
fi

if [ $MISSING -eq 1 ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Set environment variables yang kurang sebelum menjalankan bot.${NC}"
    echo -e "   Di Replit: gunakan tab ${BLUE}Secrets${NC}"
    echo -e "   Di server: export ke shell atau simpan di file .env"
fi

# Selesai
echo ""
echo -e "${GREEN}=========================================="
echo -e "  ✅ Instalasi selesai!"
echo -e "==========================================${NC}"
echo ""
echo -e "Jalankan bot dengan perintah:"
echo -e "  ${BLUE}python main.py${NC}"
echo ""
