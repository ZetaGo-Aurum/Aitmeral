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

# Detect platform
IS_TERMUX=false
if [ -n "$TERMUX_VERSION" ] || [ -n "$PREFIX" ] && [[ "$PREFIX" == *com.termux* ]]; then
    IS_TERMUX=true
fi

install_via_npm() {
  if command -v npm >/dev/null 2>&1; then
    echo -e "${CYN}▸ Installing via npm...${RST}"
    # Try without sudo first, then with sudo (if not Termux)
    if npm install -g aitmeral-enhancer 2>/dev/null; then
      echo -e "${GRN}✓ Installed via npm${RST}"
      return 0
    elif [ "$IS_TERMUX" = false ] && command -v sudo >/dev/null 2>&1; then
      if sudo npm install -g aitmeral-enhancer; then
        echo -e "${GRN}✓ Installed via npm (with sudo)${RST}"
        return 0
      fi
    else
      echo -e "${CYN}! npm install failed (no sudo on Termux)${RST}"
    fi
  fi
  return 1
}

install_via_pip() {
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python >/dev/null 2>&1; then PY=python
  else return 1; fi
  
  echo -e "${CYN}▸ Installing via pip...${RST}"
  # On Termux/ARM, skip AI dependencies (torch not available)
  PIP_ARGS="aitmeral-enhancer"
  if [ "$IS_TERMUX" = true ]; then
      echo -e "${CYN}! Termux detected — installing base package only (AI engines require torch, not available on ARM)${RST}"
      PIP_ARGS="aitmeral-enhancer"
  fi
  
  if $PY -m pip install $PIP_ARGS 2>/dev/null || $PY -m pip install --user $PIP_ARGS; then
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
    
    # On Termux, install without AI dependencies
    PIP_INSTALL="."
    if [ "$IS_TERMUX" = true ]; then
        echo -e "${CYN}! Termux detected — installing base package only${RST}"
    fi
    
    $PY -m pip install $PIP_INSTALL && echo -e "${GRN}✓ Installed from source${RST}" && return 0
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
  echo "   pip install aitmeral-enhancer"
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

# Termux-specific notes
if [ "$IS_TERMUX" = true ]; then
    echo
    echo -e "${CYN}📱 Termux Notes:${RST}"
    echo "  • AI engines (MMagic, Real-ESRGAN) require torch which is not available on ARM/Termux"
    echo "  • Traditional ffmpeg-based conversion works fully"
    echo "  • For AI features, use Linux/macOS/Windows with CUDA GPU"
    echo "  • Install ffmpeg: pkg install ffmpeg"
    echo "  • Install yt-dlp: pip install yt-dlp"
fi

echo
echo -e "${BLD}Selesai! Mulai dengan:${RST}"
echo "  aitmeral             # TUI interaktif"
echo "  aitmeral server      # Web UI  → http://127.0.0.1:8765"
echo "  aitmeral --help      # bantuan lengkap"
echo "  aitmeral doctor      # cek sistem"