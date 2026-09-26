<div align="center">

```
     _    _ _____ __  __ _____ ____      _    _
    / \  | |_   _|  \/  | ____|  _ \    / \  | |
   / _ \ | | | | | |\/| |  _| | |_) |  / _ \ | |
  / ___ \| | | | | |  | | |___|  _ <  / ___ \| |___
 /_/   \_\_| | |_|_|_|  |_|_____|_| \_/_/   \_\_____|
```

# AITMERAL v2

**AI Video/Image Enhancer · Upscaler · RAW Lossless Converter**

TUI interaktif ✦ CLI lengkap ✦ Web UI lokal (`aitmeral server`) ✦ Linux · Windows · macOS · Termux

[![platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos%20%7C%20termux-8f6a1f)]() [![python](https://img.shields.io/badge/python-3.10%2B-3776ab)]() [![ffmpeg](https://img.shields.io/badge/powered%20by-ffmpeg%20%2B%20yt--dlp-e39a2d)]() [![ai](https://img.shields.io/badge/AI-mmagic%20%2B%20Real--ESRGAN-6c4fd4)]()

</div>

---

## ✨ Fitur v2

| Kategori | Detail |
|---|---|
| **🤖 AI Upscaling (v2 Baru)** | **MMagic (Primary)** — RealESRGAN, SwinIR, BasicVSR, RealBasicVSR · **Real-ESRGAN (Alternative)** — x4plus, anime-x4, video-x4 · 2x/4x/8x scaling dengan artifact removal |
| **🖼️ Image Support (v2 Baru)** | Upscale/enhance foto: jpg, png, webp, bmp, tiff, avif, jxl — output PNG lossless |
| **📹 Video Enhancement** | 480p → 1080p, 720p, 1440p, 4K, faktor 2×/4×, atau `WxH` kustom — scaler Lanczos/Spline/Bicubic/Gaussian/XBR (pixel-art), aspect ratio selalu terjaga |
| **💾 RAW & Lossless** | FFV1 (lossless arsip), Y4M **uncompressed** (paling raw), Lossless H.264/HEVC, ProRes 4444, DNxHR 444 — setiap piksel hasil proses dijaga bit-exact |
| **🌈 HDR / SDR** | SDR → HDR (ekspansi 10-bit BT.2020 PQ + signaling HDR10), HDR → SDR (tone-mapping hable otomatis), sumber HDR tetap HDR |
| **🧹 Menjernihkan video** | Denoise hqdn3d/NLMeans (3 level), Deband, Deblock, Deinterlace |
| **🎨 Shader & efek** | Sharpen shader CAS (ala FidelityFX) / Unsharp Mask, Film Grain, Color Boost (saturation/kontras/gamma), Frame-rate + motion interpolation 60fps |
| **🔗 Link & Embed** | YouTube (watch/embed/shorts/youtu.be) + 1000+ situs lain via yt-dlp, langsung di-convert ke RAW/lossless/AI |
| **📁 File lokal** | Konversi file lokal apa pun (mp4, mkv, mov, avi, webm, ts, dll.) |
| **🖥️ 3 antarmuka** | TUI modern (file manager + queue live), CLI penuh flag, Web UI lokal dengan upload, file browser & progress real-time |
| **🛡️ Gate spesifikasi** | Cek otomatis **RAM ≥ 8 GB** sebelum konversi (`aitmeral doctor`), override `--force` / "Proceed anyway" |
| **⚡ Encoding stabil & kompatibel** | Preset `superhd` (H.264 CRF 16 + faststart) diputar hampir di semua perangkat; deteksi encoder otomatis + fallback |

---

## 🤖 AI Engine — Cara Kerja

AITMERAL v2 hadir dengan **dua AI engine** yang bisa dipilih:

### 1. MMagic (Primary) — `open-mmlab/mmagic`
- **Repo**: https://github.com/open-mmlab/mmagic
- **Arsitektur**: Berbasis PyTorch + MMEngine + MMCV
- **Model yang didukung**:
  - **RealESRGAN** — General purpose super-resolution (x2, x4)
  - **SwinIR** — Transformer-based, detail recovery superior
  - **BasicVSR** — Video super-resolution dengan temporal consistency
  - **RealBasicVSR** — Real-world video SR, handle compression artifacts
- **Cara kerja**:
  1. Load model checkpoint (otomatis download saat pertama kali)
  2. Preprocess: BGR→RGB, normalize, tensor conversion
  3. Inference: Model forward pass (FP16 default, FP32 optional)
  4. Postprocess: Clamp, denormalize, RGB→BGR, save
  5. Video: Frame-by-frame dengan optional temporal consistency

### 2. Real-ESRGAN (Alternative) — `xinntao/Real-ESRGAN`
- **Repo**: https://github.com/xinntao/Real-ESRGAN
- **Arsitektur**: RRDBNet + BasicSR framework
- **Model yang didukung**:
  - **realesrgan-x4plus** — General purpose 4x
  - **realesrgan-x2plus** — General purpose 2x
  - **realesrgan-anime-x4** — Optimized untuk anime/cartoon
  - **realesrgan-video-x4** — Temporal consistency untuk video
  - **GFPGAN** — Face restoration (opsional)
- **Cara kerja**:
  1. Load RRDBNet weights
  2. Tiling untuk image besar (memory efficient)
  3. Enhance dengan `RealESRGANer` class
  4. Support face enhancement via GFPGAN

### ⚡ Perbandingan

| Aspek | MMagic (Primary) | Real-ESRGAN (Alternative) |
|---|---|---|
| **Kualitas Video** | ⭐⭐⭐⭐⭐ (BasicVSR temporal) | ⭐⭐⭐⭐ |
| **Kualitas Image** | ⭐⭐⭐⭐⭐ (SwinIR) | ⭐⭐⭐⭐ |
| **Kecepatan** | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Memory** | Tinggi (PyTorch) | Sedang |
| **Install** | `pip install "aitmeral-enhancer[mmagic]"` | `pip install "aitmeral-enhancer[realesrgan]"` |

---

## 🚀 Instalasi

### Metode 1: npm (Paling Mudah — Auto-install Python + Dependencies)
```bash
npm install -g aitmeral-enhancer
# Atau one-line via curl:
curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aitmeral/main/npm-wrapper/install-npm.sh | bash
```

### Metode 2: Universal Installer (Coba npm → pip → source)
```bash
curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aitmeral/main/install-universal.sh | bash
```

### Metode 3: Pip (Python Native) — **Direkomendasikan untuk AI**
```bash
# Full AI (both engines)
pip install "aitmeral-enhancer[mmagic,realesrgan]"

# Primary only (MMagic)
pip install "aitmeral-enhancer[mmagic]"

# Alternative only (Real-ESRGAN)
pip install "aitmeral-enhancer[realesrgan]"

# Dengan fitur YouTube:
pip install "aitmeral-enhancer[full]"
```

### Metode 4: Dari Source (Development)
```bash
git clone https://github.com/ZetaGo-Aurum/Aitmeral.git
cd Aitmeral
pip install -e ".[mmagic,realesrgan]"
# Atau jalankan helper:
bash install.sh
```

### 1. Siapkan dependensi sistem (hanya untuk metode pip/source)

```bash
# Linux (Debian/Ubuntu)
sudo apt install ffmpeg python3-pip python3-venv
pip install yt-dlp

# Linux (Fedora)                # Linux (Arch)
sudo dnf install ffmpeg python-pip    sudo pacman -S ffmpeg python-pip
pip install yt-dlp                   pip install yt-dlp

# macOS (Homebrew)
brew install ffmpeg yt-dlp python

# Windows (winget)
winget install Gyan.FFmpeg yt-dlp.yt-dlp Python.Python.3.12

# Termux (Android)
pkg update && pkg install ffmpeg python git
pip install yt-dlp
```

### 2. Pasang AI Engine (Setelah install base)

```bash
# MMagic (Primary) - butuh MMCV compile
pip install "aitmeral-enhancer[mmagic]"
# Atau manual:
pip install mmcv>=2.0.1 mmengine>=0.10
# mmagic akan auto-install saat pertama dipakai

# Real-ESRGAN (Alternative) - lebih ringan
pip install "aitmeral-enhancer[realesrgan]"
# Atau manual:
pip install basicsr facexlib gfpgan
```

> **Catatan**: MMagic butuh `mmcv` yang compile C++ — pastikan punya build tools (gcc, cmake). Real-ESRGAN lebih ringan, pure Python.

---

## 🖥️ Cara Pakai

### TUI interaktif (default)
```bash
aitmeral            # langsung membuka TUI
aitmeral tui        # sama dengan di atas
```
Panel TUI: **Dashboard** · **File Manager** · **Enhance & Convert** · **URL Grabber** · **Jobs/Queue** · **System Info**.

### Web UI lokal
```bash
aitmeral server                       # buka http://127.0.0.1:8765
aitmeral server --port 9000 --host 0.0.0.0
aitmeral server --output-dir /mnt/hdd/renders --no-open
```
Web UI v2: AI Engine selector, Model picker, Process mode (video/image/auto).

### CLI — Traditional (ffmpeg)
```bash
aitmeral --help
aitmeral -h

# File lokal: 480p → 1080p, output RAW (FFV1 lossless)
aitmeral convert video480.mp4 -S 1080p -p raw --effects denoise:2,sharpen:0.5

# File lokal: hasil kompatibel semua device
aitmeral convert video.mp4 -S 1080p -p superhd --effects all

# Dari YouTube → lossless
aitmeral url "https://www.youtube.com/watch?v=XXXX" -S 1080p -p lossless-x264
aitmeral url "https://www.youtube.com/embed/XXXX"   -S 2160p -p hdr10 --hdr

# SDR → HDR 4K
aitmeral convert video.mp4 -S 2160p -p hdr10 --hdr --effects sharpen:0.5,denoise:1

# Inspeksi media / URL
aitmeral info video.mp4
aitmeral info "https://youtu.be/XXXX"

# Dry-run
aitmeral convert video.mp4 -S 1080p -p raw --dry-run

aitmeral presets      # daftar preset output
aitmeral effects      # daftar efek & shader
aitmeral doctor       # cek sistem
```

### CLI — AI Enhanced (v2 Baru)

```bash
# 🖼️ AI Image Upscale 4x (MMagic Primary)
aitmeral convert photo.jpg -p ai-mmagic-realesrgan-x4

# 🖼️ AI Image Upscale 4x → PNG lossless
aitmeral convert photo.jpg -p ai-img-mmagic-x4

# 🎬 AI Video Upscale 4x dengan temporal consistency (MMagic Primary)
aitmeral convert video.mp4 -p ai-mmagic-basicvsr-x4

# 🎬 AI Video Upscale 4x — RealBasicVSR (real-world video)
aitmeral convert video.mp4 -p ai-mmagic-realbasicvsr-x4

# 🎨 AI Video Anime/Cartoon (Real-ESRGAN Alternative)
aitmeral convert anime.mp4 --ai-engine realesrgan --ai-model realesrgan-anime-x4

# 🎭 AI Video General (Real-ESRGAN Alternative)
aitmeral convert video.mp4 --ai-engine realesrgan --ai-model realesrgan-video-x4

# ⚙️ Custom AI settings
aitmeral convert video.mp4 -p ai-mmagic-swinir-x4 \
    --ai-engine mmagic --ai-model swinir-x4 --ai-scale 4 \
    --ai-tile 512 --ai-fp32 --ai-gpu 0

# 🔄 Auto mode (detect image/video)
aitmeral convert input.jpg --mode auto -p ai-mmagic-realesrgan-x4
aitmeral convert input.mp4 --mode auto -p ai-mmagic-basicvsr-x4
```

### Flag AI Baru (`aitmeral convert / url`)

| Flag | Nilai | Keterangan |
|---|---|---|
| `--mode` | `video\|image\|auto` | Processing mode (default: auto) |
| `--ai-engine` | `mmagic\|realesrgan\|off` | AI engine (default: mmagic) |
| `--ai-model` | model name | AI model (lihat `aitmeral presets`) |
| `--ai-scale` | `2\|4\|8` | AI upscale factor (default: 4) |
| `--ai-tile` | `0-2048` | Tile size untuk image besar (0=auto) |
| `--ai-fp32` | flag | Gunakan FP32 instead of FP16 |
| `--ai-gpu` | `0-7` | GPU device ID (default: 0) |

---

## 🎚 Preset Output (`aitmeral presets`)

### Traditional (ffmpeg)

| Key | Preset | Jenis | Kompat | Ukuran/menit @1080p |
|---|---|---|---|---|
| `raw` | **RAW FFV1** — MKV | 🔴 lossless total | ☆☆ | 2–8 GB |
| `y4m` | **RAW Y4M** — uncompressed | 🔴 paling raw | ☆ | ~4,5 GB |
| `lossless-x264` | Lossless H.264 (qp=0) | 🟡 lossless | ★★★★ | 0,4–2 GB |
| `lossless-x265` | Lossless HEVC | 🟡 lossless | ★★★ | 0,3–1,5 GB |
| `prores4444` | Apple ProRes 4444 | 🟣 visually lossless | ★★★ | 1–2 GB |
| `dnxhr` | Avid DNxHR 444 | 🟣 visually lossless | ★★★ | 1–2 GB |
| `hdr10` | **HDR10** — HEVC 10-bit PQ | 🔵 HDR | ★★★★ | 200–600 MB |
| `hq-hevc` | HEVC CRF 17 | 🟣 HQ | ★★★★ | 60–200 MB |
| `superhd` | **Super HD H.264** CRF 16 | 🟢 kompatibel | ★★★★★ | 100–350 MB |
| `av1` | AV1 (AOM) | 🟣 HQ efisien | ★★★ | 40–150 MB |

### AI-Powered (v2)

| Key | Preset | Engine | Model | Scale | Output |
|---|---|---|---|---|---|
| `ai-mmagic-realesrgan-x4` | **AI: MMagic RealESRGAN x4** | MMagic | realesrgan-x4 | 4x | MP4 |
| `ai-mmagic-swinir-x4` | **AI: MMagic SwinIR x4** | MMagic | swinir-x4 | 4x | MP4 |
| `ai-mmagic-basicvsr-x4` | **AI: MMagic BasicVSR x4** | MMagic | basicvsr-x4 | 4x | MP4 |
| `ai-mmagic-realbasicvsr-x4` | **AI: MMagic RealBasicVSR x4** | MMagic | realbasicvsr-x4 | 4x | MP4 |
| `ai-realesrgan-x4plus` | **AI: Real-ESRGAN x4plus** | Real-ESRGAN | realesrgan-x4plus | 4x | MP4 |
| `ai-realesrgan-anime-x4` | **AI: Real-ESRGAN Anime x4** | Real-ESRGAN | realesrgan-anime-x4 | 4x | MP4 |
| `ai-realesrgan-video-x4` | **AI: Real-ESRGAN Video x4** | Real-ESRGAN | realesrgan-video-x4 | 4x | MP4 |
| `ai-img-mmagic-x4` | **AI Image: MMagic → PNG** | MMagic | realesrgan-x4 | 4x | PNG |
| `ai-img-realesrgan-x4` | **AI Image: Real-ESRGAN → PNG** | Real-ESRGAN | realesrgan-x4plus | 4x | PNG |

---

## 🎛 Efek & Shader (`aitmeral effects`)

| Efek | Flag/Setting | Keterangan |
|---|---|---|
| **Denoise** | `--effects denoise:1-3` / `--denoiser nlmeans` | hqdn3d (cepat) atau NLMeans (paling halus) |
| **Sharpen Shader** | `--shader cas --sharpen 0.5` | CAS (FidelityFX-style) atau Unsharp Mask |
| **Deband** | `--deband` / `--effects deband` | menghapus banding pada gradasi |
| **Deblock** | `--deblock` | melembutkan artefak blok |
| **Deinterlace** | `--deinterlace` | yadif bob untuk materi interlaced |
| **Film Grain** | `--grain 6` | grain film sintetis |
| **Color Boost** | `--saturation --contrast --gamma --brightness` | koreksi warna (filter eq) |
| **SDR→HDR** | `--hdr` (ideal dengan preset `hdr10`) | ekspansi 10-bit BT.2020 PQ |
| **HDR→SDR** | `--tone-map hdr2sdr` / otomatis | tone-mapping hable untuk SDR |
| **Upscale** | `-S 1080p` dll. | Lanczos/Spline/XBR; AR terjaga |
| **Frame rate** | `--fps 60 --motion-interp` | minterpolate MCI/AOBMC (lambat) |
| **🤖 AI Upscale** | `--effects ai-upscale` / `-p ai-*` | AI super-resolution 2x/4x/8x |
| **🤖 AI Face Enhance** | `--effects ai-face-enhance` | GFPGAN/CodeFormer face restoration |
| **🤖 AI Colorize** | `--effects ai-colorize` | DDColor/DeOldify colorization B&W |
| **🤖 AI Denoise** | `--effects ai-denoise` | AI-based denoising (superior) |
| **🤖 AI Interpolate** | `--effects ai-interpolate` | RIFE/FLAVR frame interpolation |

---

## 📡 Catatan HDR

- **SDR→HDR** konversi ke cahaya linear → BT.2020 → PQ (SMPTE 2084) lewat zimg, lalu metadata HDR10 pada HEVC. Terbaik di display HDR.
- **Sumber HDR** dideteksi otomatis: preset RAW/lossless menyimpan HDR 10-bit; preset 8-bit otomatis tone-map ke SDR BT.709.
- Build ffmpeg tanpa `zscale` didukung — fallback ke 10-bit + signaling metadata (cek `aitmeral doctor`).

---

## ⚠️ Catatan Jujur soal "RAW" & AI

- Preset `raw`/`y4m`/`lossless-*` menjamin **tidak ada degradasi** dari hasil proses — cocok arsip, re-encode, editing.
- **AI upscale tidak menciptakan detail yang tidak ada** — hanya recover/enhance detail yang ada dengan neural network.
- File RAW besar (10 menit 1080p = 20–80 GB Y4M). Untuk distribusi gunakan `superhd` atau `hq-hevc`.
- AI processing butuh GPU (CUDA) untuk kecepatan optimal. CPU fallback tersedia tapi lambat.

---

## 🧰 Troubleshooting

| Masalah | Solusi |
|---|---|
| `ffmpeg NOT FOUND` | `apt/brew/winget/pkg install ffmpeg` → `aitmeral doctor` |
| `yt-dlp NOT FOUND` | `pip install yt-dlp` |
| Ditolak: "requires at least 8 GB" | Override: `--force` / centang *Proceed anyway* |
| Download YouTube gagal / 403 | `pip install -U yt-dlp` |
| `no path between colorspaces` (HDR) | Pastikan ffmpeg terbaru; AITMERAL auto-tag sumber |
| Playback FFV1/Y4M gagal | Codec arsip — putar VLC/mpv/ffplay, atau konversi ke `superhd` |
| Port 8765 terpakai | `aitmeral server --port 9000` |
| **AI: CUDA out of memory** | Kurangi `--ai-tile 256` atau `--ai-fp32` / `--ai-scale 2` |
| **AI: mmagic not found** | `pip install "aitmeral-enhancer[mmagic]"` |
| **AI: realesrgan not found** | `pip install "aitmeral-enhancer[realesrgan]"` |
| **AI: MMCV compile error** | Install build tools: `sudo apt install build-essential cmake` |

---

## 🏗 Struktur Proyek v2

```
aitmeral/
├── aitmeral/
│   ├── cli.py               # CLI (argparse) — aitmeral --help
│   ├── core/
│   │   ├── ai_engine.py     # 🤖 AI Engine abstraction (MMagic, Real-ESRGAN)
│   │   ├── options.py       # Settings — kontrak CLI/TUI/Web + AI config
│   │   ├── presets.py       # Preset tradisional + AI presets
│   │   ├── filters.py       # Filter-graph tradisional (upscale/shader/HDR)
│   │   ├── encoder.py       # ffmpeg command + hardware accel (NVENC/QSV/AMF)
│   │   ├── downloader.py    # yt-dlp (link embed/shorts dinormalisasi)
│   │   ├── media.py         # ffprobe wrapper
│   │   ├── pipeline.py      # Orkeštrai: tradisional + AI image/video jobs
│   │   ├── jobs.py          # Job engine (TUI & Web)
│   │   └── sysinfo.py       # Deteksi platform/RAM/GPU/encoder/filter
│   ├── tui/app.py           # TUI Textual (file manager, queue live)
│   └── web/
│       ├── server.py        # Web server stdlib + AI API endpoints
│       └── static/index.html# Web UI v2 (AI engine selector, model picker)
├── docs/                    # screenshot TUI (SVG)
├── install.sh               # Installer tradisional
├── install-universal.sh     # Universal installer
├── npm-wrapper/             # npm package wrapper
├── pyproject.toml           # Package config + AI optional deps
└── README.md
```

---

## ⚖️ Lisensi & Etika

MIT License. Gunakan hanya untuk konten yang Anda miliki haknya — mengunduh materi berhak cipta dari YouTube/situs lain tanpa izin dapat melanggar ketentuan layanan mereka dan hukum yang berlaku.

<div align="center">
<sub>AITMERAL v2.0.0 — dibangun di atas <b>ffmpeg</b>, <b>yt-dlp</b>, <b>Textual</b>, <b>rich</b>, <b>PyTorch</b>, <b>MMagic</b>, <b>Real-ESRGAN</b></sub>
</div>