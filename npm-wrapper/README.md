# AUREUS npm Wrapper

npm wrapper for the [AUREUS](https://github.com/ZetaGo-Aurum/Aureus) Python package — Video Enhancer, Upscaler & RAW Lossless Converter.

## Installation

### One-line (recommended)
```bash
npm install -g aureus
```

### Via curl
```bash
curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aureus/main/npm-wrapper/install-npm.sh | bash
```

### Universal installer (tries npm, then pip, then source)
```bash
curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aureus/main/install-universal.sh | bash
```

## Usage

After installation, the `aureus` command will be available globally:

```bash
aureus              # Open TUI interface
aureus server       # Start Web UI at http://127.0.0.1:8765
aureus convert video.mp4 -S 1080p -p superhd
aureus url "https://youtube.com/watch?v=..." -S 2160p -p hdr10 --hdr
aureus doctor       # Check system requirements
```

## How it works

This npm package is a lightweight wrapper that:
1. Installs globally via `npm install -g aureus`
2. On first run, automatically installs the Python `aureus` package via pip
3. Proxies all commands to the Python `aureus` module

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

MIT — Same as the main AUREUS project.