#!/usr/bin/env bash
# AITMERAL Universal Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aitmeral/main/install-universal.sh | bash
# Installs via npm (preferred) or falls back to pip

set -e

BLD='\033[1;33m'; GRN='\033[1;32m'; CYN='\033[1;36m'; DIM='\033[2m'; RST='\033[0m'
echo -e "${BLD}"
echo "     _    _ _____ __  __ _____ ____      _    _    "
echo "    / \  | |_   _|  \/  | ____|  _ \    / \  | |   "
echo "   / _ \ | | | | | |\/| |  _| | |_) |  / _ \ | |   "
echo "  / ___ \| | | | | |  | | |___|  _ <  / ___ \| |___"
echo " /_/   \_\_| | |_|_|  |_|_____|_| \_/_/   \_\_____/"
echo -e "${RST}${DIM}        Universal installer — Video Enhancer · Upscaler · RAW Lossless${RST}"
echo

install_via_npm() {
  if command -v npm >/dev/null 2>&1; then
    echo -e "${CYN}▸ Installing via npm...${RST}"
    if npm install -g aitmeral-enhancer 2>/dev/null || sudo npm install -g aitmeral-enhancer; then
      echo -e "${GRN}✓ Installed via npm${RST}"
      return 0
    fi
  fi
  return 1
}

install_via_pip() {
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python >/dev/null 2>&1; then PY=python
  else return 1; fi
  
  echo -e "${CYN}▸ Installing via pip...${RST}"
  if $PY -m pip install aitmeral 2>/dev/null || $PY -m pip install --user aitmeral; then
    echo -e "${GRN}✓ Installed via pip${RST}"
    return 0
  fi
  return 1
}

install_via_source() {
  echo -e "${CYN}▸ Installing from source...${RST}"
  TMPDIR=$(mktemp -d)
  cd "$TMPDIR"
  if git clone --depth 1 https://github.com/ZetaGo-Aurum/Aitmeral.git 2>/dev/null; then
    cd Aitmeral
    if command -v python3 >/dev/null 2>&1; then PY=python3
    elif command -v python >/dev/null 2>&1; then PY=python
    else return 1; fi
    $PY -m pip install . && echo -e "${GRN}✓ Installed from source${RST}" && return 0
  fi
  return 1
}

# Try installation methods in order
if install_via_npm; then
  :
elif install_via_pip; then
  :
elif install_via_source; then
  :
else
  echo "❌ All installation methods failed."
  echo "   Please install manually:"
  echo "   npm install -g aitmeral-enhancer"
  echo "   # or"
  echo "   pip install aitmeral"
  exit 1
fi

# Check system dependencies
check_bin() {
  if command -v "$1" >/dev/null 2>&1; then echo -e "${GRN}✓${RST} $1"
  else echo -e "${CYN}!${RST} $1 not found — $2"; fi
}
echo
check_bin ffmpeg "install: apt/brew/winget/pkg install ffmpeg"
check_bin yt-dlp "optional: pip install yt-dlp"

echo
echo -e "${BLD}Selesai! Mulai dengan:${RST}"
echo "  aitmeral             # TUI interaktif"
echo "  aitmeral server      # Web UI  → http://127.0.0.1:8765"
echo "  aitmeral --help      # bantuan lengkap"
echo "  aitmeral doctor      # cek sistem"