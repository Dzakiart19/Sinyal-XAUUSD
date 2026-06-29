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
echo -e "${YELLOW}[1/4] Mengecek Python...${NC}"
if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo -e "${RED}ERROR: Python tidak ditemukan! Pastikan Python 3.10+ sudah terinstall.${NC}"
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)
PYTHON_VERSION=$($PYTHON --version 2>&1)
echo -e "${GREEN}      ✅ $PYTHON_VERSION ditemukan${NC}"

# 2. Cek pip tersedia
echo ""
echo -e "${YELLOW}[2/4] Mengecek pip...${NC}"
if ! command -v pip &>/dev/null && ! command -v pip3 &>/dev/null; then
    echo -e "${RED}ERROR: pip tidak ditemukan!${NC}"
    exit 1
fi

PIP=$(command -v pip3 || command -v pip)
PIP_VERSION=$($PIP --version 2>&1)
echo -e "${GREEN}      ✅ $PIP_VERSION${NC}"

# 3. Install semua dependencies dari requirements.txt
echo ""
echo -e "${YELLOW}[3/4] Menginstall dependencies...${NC}"

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
echo -e "${YELLOW}[4/4] Membuat direktori data dan logs...${NC}"
mkdir -p data logs
echo -e "${GREEN}      ✅ Direktori data/ dan logs/ siap${NC}"

# Selesai
echo ""
echo -e "${GREEN}=========================================="
echo -e "  ✅ Instalasi selesai!"
echo -e "==========================================${NC}"
echo ""
echo -e "Jalankan bot dengan perintah:"
echo -e "  ${BLUE}python main.py${NC}"
echo ""
