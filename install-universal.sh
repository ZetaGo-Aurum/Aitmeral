#!/usr/bin/env bash
# AITMERAL Universal Installer v2
# Usage: curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aitmeral/main/install-universal.sh | bash
# Smart installer: auto-detects platform & GPU, installs optimal AI dependencies

set -e

BLD='\033[1;33m'; GRN='\033[1;32m'; CYN='\033[1;36m'; DIM='\033[2m'; RED='\033[1;31m'; RST='\033[0m'
echo -e "${BLD}"
echo "     _    _ _____ __  __ _____ ____      _    _    "
echo "    / \  | |_   _|  \/  | ____|  _ \    / \  | |   "
echo "   / _ \ | | | | | |\/| |  _| | |_) |  / _ \ | |   "
echo "  / ___ \| | | | | |  | | |___|  _ <  / ___ \| |___"
echo " /_/   \_\_| | |_|_|  |_|_____|_| \_/_/   \_\_____/"
echo -e "${RST}${DIM}        Universal installer — AI Video/Image Enhancer${RST}"
echo

# Detect platform
IS_TERMUX=false
IS_MACOS=false
IS_LINUX=false
IS_WINDOWS=false
HAS_CUDA=false
HAS_MPS=false
EXTERNALLY_MANAGED=false

if [ -n "$TERMUX_VERSION" ] || [ -n "$PREFIX" ] && [[ "$PREFIX" == *com.termux* ]]; then
    IS_TERMUX=true
elif [[ "$OSTYPE" == "darwin"* ]]; then
    IS_MACOS=true
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    IS_LINUX=true
elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]] || [[ -n "$WINDIR" ]]; then
    IS_WINDOWS=true
fi

# Check for CUDA
if command -v nvidia-smi >/dev/null 2>&1; then
    HAS_CUDA=true
fi

# Check for MPS (Apple Silicon)
if [ "$IS_MACOS" = true ] && [[ "$(uname -m)" == "arm64" ]]; then
    HAS_MPS=true
fi

# Check for externally-managed-environment (Arch, Fedora, etc.)
if $PY -m pip install --help 2>&1 | grep -q "externally-managed-environment" 2>/dev/null || \
   python3 -c "import sysconfig; print(sysconfig.get_config_var('EXTERNALLY_MANAGED'))" 2>/dev/null | grep -q "1" 2>/dev/null; then
    EXTERNALLY_MANAGED=true
fi

echo -e "${CYN}🔍 Platform detection:${RST}"
[ "$IS_TERMUX" = true ] && echo -e "   Platform: Termux (ARM)"
[ "$IS_MACOS" = true ] && echo -e "   Platform: macOS $(uname -m)" && [ "$HAS_MPS" = true ] && echo -e "   ${GRN}✓ Apple Silicon (MPS support)${RST}"
[ "$IS_LINUX" = true ] && echo -e "   Platform: Linux" && [ "$HAS_CUDA" = true ] && echo -e "   ${GRN}✓ NVIDIA CUDA detected${RST}" || echo -e "   ${DIM}No CUDA GPU (CPU mode)${RST}"
[ "$IS_WINDOWS" = true ] && echo -e "   Platform: Windows"
[ "$EXTERNALLY_MANAGED" = true ] && echo -e "   ${CYN}🔒 Externally managed Python detected (Arch/Fedora) — will use --break-system-packages${RST}"
echo

# Determine AI install strategy
AI_INSTALL="none"
if [ "$IS_TERMUX" = true ]; then
    AI_INSTALL="none"
    echo -e "${CYN}📱 Termux: AI engines not available (no torch for ARM)${RST}"
elif [ "$HAS_CUDA" = true ]; then
    AI_INSTALL="full"
    echo -e "${GRN}🚀 CUDA GPU detected — installing FULL AI stack (MMagic + Real-ESRGAN)${RST}"
elif [ "$HAS_MPS" = true ]; then
    AI_INSTALL="mps"
    echo -e "${GRN}🍎 Apple Silicon — installing AI with MPS support${RST}"
elif [ "$IS_LINUX" = true ]; then
    AI_INSTALL="cpu"
    echo -e "${CYN}💻 Linux CPU mode — installing Real-ESRGAN (CPU optimized)${RST}"
elif [ "$IS_MACOS" = true ]; then
    AI_INSTALL="cpu"
    echo -e "${CYN}🍎 macOS Intel — installing Real-ESRGAN (CPU mode)${RST}"
elif [ "$IS_WINDOWS" = true ]; then
    AI_INSTALL="cpu"
    echo -e "${CYN}🪟 Windows — installing Real-ESRGAN (CPU mode)${RST}"
fi

# Pip wrapper that handles externally-managed-environment
pip_install() {
    local args=("$@")
    if [ "$EXTERNALLY_MANAGED" = true ]; then
        $PY -m pip install --break-system-packages "${args[@]}"
    else
        $PY -m pip install "${args[@]}"
    fi
}

pip_install_user() {
    local args=("$@")
    if [ "$EXTERNALLY_MANAGED" = true ]; then
        $PY -m pip install --user --break-system-packages "${args[@]}"
    else
        $PY -m pip install --user "${args[@]}"
    fi
}

echo

install_via_npm() {
  if command -v npm >/dev/null 2>&1; then
    echo -e "${CYN}▸ Installing via npm...${RST}"
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

install_ai_dependencies() {
    echo -e "${CYN}🤖 Installing AI dependencies...${RST}"
    
    case "$AI_INSTALL" in
        "full")
            echo -e "${CYN}📦 Installing MMagic (Primary AI Engine)...${RST}"
            pip_install "mmcv>=2.0.1" "mmengine>=0.10"
            pip_install "mmagic @ git+https://github.com/open-mmlab/mmagic.git@main"
            
            echo -e "${CYN}📦 Installing Real-ESRGAN (Alternative AI Engine)...${RST}"
            pip_install "basicsr" "facexlib" "gfpgan"
            pip_install "realesrgan @ git+https://github.com/xinntao/Real-ESRGAN.git@master"
            ;;
        "mps")
            echo -e "${CYN}📦 Installing Real-ESRGAN with MPS support...${RST}"
            pip_install "basicsr" "facexlib" "gfpgan"
            pip_install "realesrgan @ git+https://github.com/xinntao/Real-ESRGAN.git@master"
            
            # Try MMagic with MPS (experimental)
            echo -e "${CYN}📦 Attempting MMagic with MPS...${RST}"
            pip_install "mmcv>=2.0.1" "mmengine>=0.10"
            pip_install "mmagic @ git+https://github.com/open-mmlab/mmagic.git@main" || echo -e "${DIM}! MMagic MPS support experimental, skipping...${RST}"
            ;;
        "cpu")
            echo -e "${CYN}📦 Installing Real-ESRGAN (CPU optimized)...${RST}"
            pip_install "basicsr" "facexlib" "gfpgan"
            pip_install "realesrgan @ git+https://github.com/xinntao/Real-ESRGAN.git@master"
            ;;
        "none")
            echo -e "${CYN}⏭ Skipping AI engines (not supported on this platform)${RST}"
            ;;
    esac
}

install_via_pip() {
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python >/dev/null 2>&1; then PY=python
  else return 1; fi
  
  echo -e "${CYN}▸ Installing AITMERAL base package...${RST}"
  if pip_install aitmeral-enhancer || pip_install_user aitmeral-enhancer; then
    echo -e "${GRN}✓ Base package installed${RST}"
  else
    echo -e "${RED}✗ Failed to install base package${RST}"
    return 1
  fi
  
  # Install AI dependencies based on platform
  if [ "$AI_INSTALL" != "none" ]; then
    install_ai_dependencies
  fi
  
  return 0
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
    
    echo -e "${CYN}▸ Installing base package...${RST}"
    pip_install .
    
    if [ "$AI_INSTALL" != "none" ]; then
      install_ai_dependencies
    fi
    
    echo -e "${GRN}✓ Installed from source${RST}" && return 0
  fi
  return 1
}

# Try installation methods in order
if install_via_npm; then
  # npm wrapper will auto-install Python deps on first run
  echo -e "${CYN}💡 npm wrapper will auto-install Python dependencies on first run${RST}"
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

# Install system dependencies hint
check_bin() {
  if command -v "$1" >/dev/null 2>&1; then echo -e "${GRN}✓${RST} $1"
  else echo -e "${CYN}!${RST} $1 not found — $2"; fi
}
echo
check_bin ffmpeg "install: apt/brew/winget/pkg install ffmpeg"
check_bin yt-dlp "optional: pip install yt-dlp"

# Platform-specific notes
if [ "$IS_TERMUX" = true ]; then
    echo
    echo -e "${CYN}📱 Termux Notes:${RST}"
    echo "  • AI engines require torch (not available on ARM/Termux)"
    echo "  • Traditional ffmpeg-based conversion works fully"
    echo "  • For AI features, use Linux/macOS/Windows with CUDA GPU"
    echo "  • Install ffmpeg: pkg install ffmpeg"
    echo "  • Install yt-dlp: pip install yt-dlp"
fi

if [ "$HAS_CUDA" = true ]; then
    echo
    echo -e "${GRN}🎮 CUDA GPU Ready!${RST}"
    echo "  • MMagic (Primary): RealESRGAN, SwinIR, BasicVSR, RealBasicVSR"
    echo "  • Real-ESRGAN (Alt): x4plus, anime-x4, video-x4, GFPGAN"
    echo "  • Usage: aitmeral convert video.mp4 -p ai-mmagic-realesrgan-x4"
fi

if [ "$HAS_MPS" = true ]; then
    echo
    echo -e "${GRN}🍎 Apple Silicon Ready!${RST}"
    echo "  • Real-ESRGAN with MPS acceleration"
    echo "  • MMagic experimental (may need CPU fallback)"
fi

echo
echo -e "${BLD}Selesai! Mulai dengan:${RST}"
echo "  aitmeral             # TUI interaktif"
echo "  aitmeral server      # Web UI  → http://127.0.0.1:8765"
echo "  aitmeral --help      # bantuan lengkap"
echo "  aitmeral doctor      # cek sistem + AI engines"