# AITMERAL npm Wrapper

npm wrapper for the [AITMERAL](https://github.com/ZetaGo-Aurum/Aitmeral) Python package — Video Enhancer, Upscaler & RAW Lossless Converter.

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
```

## How it works

This npm package is a lightweight wrapper that:
1. Installs globally via `npm install -g aitmeral-enhancer`
2. On first run, automatically installs the Python `aitmeral` package via pip
3. Proxies all commands to the Python `aitmeral` module

## Requirements

- Node.js 14+
- Python 3.9+ (auto-installed on first run if missing)
- ffmpeg (required for video processing)
- yt-dlp (optional, for URL features)

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