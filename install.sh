#!/usr/bin/env bash
# AITMERAL installer — Linux / macOS / Termux / Windows
# Methods: npm (global), pip, or source
set -e

BLD='\033[1;33m'; GRN='\033[1;32m'; CYN='\033[1;36m'; DIM='\033[2m'; RST='\033[0m'
echo -e "\033[0;97m     \033[0;37m▄   \033[0;97m  \033[0;37m▄\033[0;97m   \033[0;37m▄  \033[0;97m  \033[0;37m▄\033[0;97m  \033[0;37m▄   \033[0;97m  \033[0;37m▄\033[0;97m  \033[0;37m▄   \033[0;97m  \033[0;37m▄\033[0;97m   \033[0;37m▄  \033[0;97m   \033[0;37m▄   \033[0m"
echo -e "\033[0;97m \033[0;37m▄\033[0;97;47m▒\033[0;37m▀▀\033[0;97;47m▒▓\033[0;37m▄ \033[0;97m \033[0;97;47m▒▓\033[0;97m   \033[0;97;47m▓▒\033[0;37m ▄\033[0;97;47m▓▒\033[0;37m▄▀\033[0;97;47m▒▓\033[0;37m  ▄\033[0;97;47m▓▒\033[0;37m▄▀\033[0;97;47m▒░\033[0;37m  \033[0;97m \033[0;97;47m▒▓\033[0;97m   \033[0;97;47m▓▒\033[0;37m \033[0;97m \033[0;37m▄▀\033[0;97;47m░▒\033[0;37m▄ \033[0m"
echo -e "\033[0;97;47m▓▒\033[0;97m   \033[0;97;47m░▒\033[0;37m  \033[0;97m \033[0;97;47m▓▒\033[0;97m   \033[0;97;47m▒▓\033[0;37m \033[0;97m \033[0;97;47m▒▓\033[0;97m   \033[0;97;47m▒░\033[0;37m \033[0;97m \033[0;97;47m▒░\033[0;97m   \033[0;37m▀  \033[0;97m \033[0;97;47m▓▒\033[0;97m   \033[0;97;47m▒▓\033[0;37m \033[0;97;47m▓▒\033[0;97m  \033[0;37m▀\033[0;97;47m▓▒\033[0m"
echo -e "\033[0;97;47m▒░\033[0;97m   \033[0;97;47m▒░\033[0;37m  \033[0;97m \033[0;97;47m▒░\033[0;97m   \033[0;97;47m░▒\033[0;37m \033[0;97m \033[0;97;47m░░\033[0;97m   \033[0;97;47m░\033[0;37m  \033[0;97m \033[0;97;47m░ \033[0;37m      \033[0;97m \033[0;97;47m▒░\033[0;97m   \033[0;97;47m░▒\033[0;37m \033[0;97;47m▒░\033[0;97m   \033[0;37m▀▀\033[0m"
echo -e "\033[0;37m▀▀\033[0;97m   \033[0;37m▀▀  \033[0;97m \033[0;37m▀▀\033[0;97m   \033[0;37m▀▀ \033[0;97m \033[0;37m▀▀▀▀▀   \033[0;97m \033[0;37m▀▀▀▀▀   \033[0;97m \033[0;37m▀▀\033[0;97m   \033[0;37m▀▀ \033[0;97m \033[0;37m▀▀    \033[0m"
echo -e "\033[0;34m█\033[0;94;44m░\033[0;97m   \033[0;94;44m░\033[0;34m█\033[0;37m  \033[0;97m \033[0;94;44m░▒\033[0;97m   \033[0;94;44m▒░\033[0;37m \033[0;97m \033[0;94;44m░▒\033[0;97m  \033[0;94;44m░\033[0;37m   \033[0;97m \033[0;94;44m ░\033[0;37m      \033[0;97m \033[0;94;44m░▒\033[0;97m   \033[0;94;44m▒░\033[0;37m \033[0;97m   \033[0;34m▀\033[0;94;44m░\033[0;34m▄\033[0;37m \033[0m"
echo -e "\033[0;94;44m░▒\033[0;97m   \033[0;94;44m▒░\033[0;37m  \033[0;97m \033[0;94;44m▒░\033[0;97m   \033[0;94;44m░▒\033[0;37m \033[0;97m \033[0;94;44m▒░\033[0;97m  \033[0;94;44m▒░\033[0;37m  \033[0;97m \033[0;94;44m░▒\033[0;37m      \033[0;97m \033[0;94;44m▒░\033[0;97m   \033[0;94;44m░▒\033[0;37m \033[0;97m     \033[0;94;44m░▒\033[0m"
echo -e "\033[0;94;44m▒▓\033[0;97m   \033[0;94;44m▓▒\033[0;37m  \033[0;97m \033[0;94;44m▓▒\033[0;34m▄\033[0;97m  \033[0;94;44m▒▓\033[0;37m \033[0;97m \033[0;94;44m▓▒\033[0;97m  \033[0;94;44m▓▒\033[0;37m  \033[0;97m \033[0;94;44m▒▓\033[0;34m▄\033[0;97m  \033[0;94;44m▒▓\033[0;37m \033[0;97m \033[0;94;44m▓▒\033[0;34m▄\033[0;97m  \033[0;94;44m▒▓\033[0;97m   \033[0;94;44m▒░\033[0;34m▄\033[0;97m  \033[0;94;44m▒▓\033[0m"
echo -e "\033[0;34m▀\033[0;94;44m▓▓\033[0;34m▄▀\033[0;94;44m▓▓\033[0;34m▀\033[0;37m \033[0;97m  \033[0;34m▀\033[0;94;44m▒▓\033[0;34m▄▀\033[0;37m  \033[0;34m \033[0;94;44m▒▓\033[0;97m \033[0;34m \033[0;94;44m▒▓\033[0;37m  \033[0;97m  \033[0;34m▀\033[0;94;44m▓▒\033[0;34m▄▀\033[0;37m  \033[0;97m  \033[0;34m▀\033[0;94;44m▒▓\033[0;34m▄▀\033[0;37m  \033[0;97m \033[0;34m▀\033[0;94;44m▒▓\033[0;34m▄▀\033[0;37m \033[0m"
echo -e "\033[0;97m  \033[0;34m▀\033[0;37m      \033[0;97m    \033[0;34m▀\033[0;37m    \033[0;97m  \033[0;34m▀\033[0;97m   \033[0;34m▀\033[0;37m           \033[0;97m    \033[0;34m▀\033[0;37m    \033[0;97m   \033[0;34m▀\033[0;37m   \033[0m"
echo -e "${DIM}        installer — Video Enhancer · Upscaler · RAW Lossless${RST}"
echo

# ---- Try npm first (easiest, auto-installs Python deps) ----
if command -v npm >/dev/null 2>&1; then
  echo -e "${CYN}▸ npm ditemukan — memasang via npm (global)…${RST}"
  if npm install -g aitmeral-enhancer 2>/dev/null || sudo npm install -g aitmeral-enhancer; then
    echo -e "${GRN}✓ Terpasang via npm.${RST}"
    echo
    echo -e "${BLD}Selesai! Mulai dengan:${RST}"
    echo "  aitmeral             # TUI interaktif"
    echo "  aitmeral server      # Web UI  → http://127.0.0.1:8765"
    echo "  aitmeral --help      # bantuan lengkap"
    echo "  aitmeral doctor      # cek sistem (RAM / ffmpeg / yt-dlp)"
    exit 0
  fi
  echo -e "${CYN}! npm install gagal, mencoba pip…${RST}"
fi

# ---- python fallback ----
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "✗ Python 3 tidak ditemukan."
  case "$(uname -s)" in
    Linux)  echo "  → sudo apt install python3 python3-pip   (atau pkg install python di Termux)";;
    Darwin) echo "  → brew install python";;
  esac
  exit 1
fi
echo -e "${GRN}✓${RST} Python: $($PY --version)"

# ---- system deps ----
check_bin () {
  if command -v "$1" >/dev/null 2>&1; then echo -e "${GRN}✓${RST} $1: $(command -v "$1")"
  else echo -e "${CYN}!${RST} $1 belum ada — $2"; fi
}
check_bin ffmpeg "install dengan: sudo apt install ffmpeg | brew install ffmpeg | pkg install ffmpeg (Termux) | winget install Gyan.FFmpeg (Windows)"
check_bin ffprobe "bagian dari paket ffmpeg"
check_bin yt-dlp "opsional (fitur URL): pip install yt-dlp"

echo
echo -e "${CYN}▸ Memasang AITMERAL via pip…${RST}"
if $PY -m pip install aitmeral 2>/dev/null || $PY -m pip install --user aitmeral; then
  echo -e "${GRN}✓ Terpasang.${RST}"
else
  echo -e "${CYN}! pip install gagal — coba manual: ${RST}pip install --user aitmeral"
  exit 1
fi

echo
echo -e "${BLD}Selesai! Mulai dengan:${RST}"
echo "  aitmeral             # TUI interaktif"
echo "  aitmeral server      # Web UI  → http://127.0.0.1:8765"
echo "  aitmeral --help      # bantuan lengkap"
echo "  aitmeral doctor      # cek sistem (RAM / ffmpeg / yt-dlp)"
