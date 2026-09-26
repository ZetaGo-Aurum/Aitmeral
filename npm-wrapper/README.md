# AITMERAL v2 npm Wrapper

npm wrapper for the [AITMERAL v2](https://github.com/ZetaGo-Aurum/Aitmeral) Python package — **AI Video/Image Enhancer, Upscaler & RAW Lossless Converter** with MMagic + Real-ESRGAN.

## Installation

### One-line (recommended)
```bash
npm install -g aitmeral-enhancer
```

### Via curl
```bash
curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aitmeral/main/npm-wrapper/install-npm.sh | bash
```

### Universal installer (tries npm, then pip, then source)
```bash
curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aitmeral/main/install-universal.sh | bash
```

## Usage

After installation, the `aitmeral` command will be available globally:

```bash
aitmeral              # Open TUI interface
aitmeral server       # Start Web UI at http://127.0.0.1:8765
aitmeral convert video.mp4 -S 1080p -p superhd
aitmeral url "https://youtube.com/watch?v=..." -S 2160p -p hdr10 --hdr
aitmeral doctor       # Check system requirements

# AI Features (v2)
aitmeral convert photo.jpg -p ai-mmagic-realesrgan-x4          # AI image upscale 4x
aitmeral convert video.mp4 -p ai-mmagic-basicvsr-x4           # AI video upscale 4x
aitmeral convert video.mp4 --ai-engine realesrgan --ai-model realesrgan-anime-x4  # Alternative engine
```

## How it works

This npm package is a lightweight wrapper that:
1. Installs globally via `npm install -g aitmeral-enhancer`
2. On first run, automatically installs the Python `aitmeral` package via pip
3. Proxies all commands to the Python `aitmeral` module

## Requirements

- Node.js 14+
- Python 3.10+ (auto-installed on first run if missing)
- ffmpeg (required for video processing)
- yt-dlp (optional, for URL features)
- **For AI**: CUDA-capable GPU recommended, `pip install "aitmeral-enhancer[mmagic,realesrgan]"`

## AI Engines (v2)

| Engine | Repo | Models | Install |
|--------|------|--------|---------|
| **MMagic (Primary)** | open-mmlab/mmagic | RealESRGAN, SwinIR, BasicVSR, RealBasicVSR | `pip install "aitmeral-enhancer[mmagic]"` |
| **Real-ESRGAN (Alt)** | xinntao/Real-ESRGAN | x4plus, anime-x4, video-x4, GFPGAN | `pip install "aitmeral-enhancer[realesrgan]"` |

## Development

```bash
# Install locally for development
npm install

# Test the wrapper
npm test

# Publish to npm (requires NPM_TOKEN)
npm publish --access public
```

## License

MIT — Same as the main AITMERAL project.