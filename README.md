<div align="center">

```
     _    _ _____ __  __ _____ ____      _    _
    / \  | |_   _|  \/  | ____|  _ \    / \  | |
   / _ \ | | | | | |\/| |  _| | |_) |  / _ \ | |
  / ___ \| | | | | |  | | |___|  _ <  / ___ \| |___
 /_/   \_\_| | |_|_|  |_|_____|_| \_/_/   \_\_____|
```

# AUREUS

**Video Enhancer · Upscaler · RAW Lossless Converter**

TUI interaktif ✦ CLI lengkap ✦ Web UI lokal (`aureus server`) ✦ Linux · Windows · macOS · Termux

[![platform](https://img.shields.io/badge/platform-linux%20%7C%20windows%20%7C%20macos%20%7C%20termux-8f6a1f)]() [![python](https://img.shields.io/badge/python-3.9%2B-3776ab)]() [![ffmpeg](https://img.shields.io/badge/powered%20by-ffmpeg%20%2B%20yt--dlp-e39a2d)]()

</div>

---

## ✨ Fitur

| Kategori | Detail |
|---|---|
| **Upscaler resolusi** | 480p → 1080p, 720p, 1440p, 4K, faktor 2×/4×, atau `WxH` kustom — scaler Lanczos/Spline/Bicubic/Gaussian/XBR (pixel-art), aspect ratio selalu terjaga |
| **RAW & Lossless** | FFV1 (lossless arsip), Y4M **uncompressed** (paling raw), Lossless H.264/HEVC, ProRes 4444, DNxHR 444 — setiap piksel hasil proses dijaga bit-exact |
| **HDR / SDR** | SDR → HDR (ekspansi 10-bit BT.2020 PQ + signaling HDR10), HDR → SDR (tone-mapping hable otomatis), sumber HDR tetap HDR |
| **Menjernihkan video** | Denoise hqdn3d/NLMeans (3 level), Deband, Deblock, Deinterlace |
| **Shader & efek** | Sharpen shader CAS (ala FidelityFX) / Unsharp Mask, Film Grain, Color Boost (saturation/kontras/gamma), Frame-rate + motion interpolation 60fps |
| **Link & Embed** | YouTube (watch/embed/shorts/youtu.be) + 1000+ situs lain via yt-dlp, langsung di-convert ke RAW/lossless |
| **File lokal** | Konversi file lokal apa pun (mp4, mkv, mov, avi, webm, ts, dll.) |
| **3 antarmuka** | TUI modern (file manager + queue live), CLI penuh flag, Web UI lokal dengan upload, file browser & progress real-time |
| **Gate spesifikasi** | Cek otomatis **RAM ≥ 8 GB** sebelum konversi (`aureus doctor`), override `--force` / "Proceed anyway" |
| **Encoding stabil & kompatibel** | Preset `superhd` (H.264 CRF 16 + faststart) diputar hampir di semua perangkat; deteksi encoder otomatis + fallback |

---

## 📋 Persyaratan

| Kebutuhan | Keterangan |
|---|---|
| **RAM** | **Minimum 8 GB** untuk proses konversi (di bawah itu harus konfirmasi `--force` / *Proceed anyway*) |
| Python | 3.9+ |
| ffmpeg + ffprobe | wajib untuk konversi |
| yt-dlp | opsional — untuk fitur download URL |
| Ruang disk | Preset RAW sangat besar (lihat tabel preset) |

---

## 🚀 Instalasi

### Metode 1: npm (Paling Mudah — Auto-install Python + Dependencies)
```bash
npm install -g aureus
# Atau one-line via curl:
curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aureus/main/npm-wrapper/install-npm.sh | bash
```

### Metode 2: Universal Installer (Coba npm → pip → source)
```bash
curl -fsSL https://raw.githubusercontent.com/ZetaGo-Aurum/Aureus/main/install-universal.sh | bash
```

### Metode 3: Pip (Python Native)
```bash
pip install aureus
# Dengan fitur YouTube:
pip install "aureus[youtube]"
```

### Metode 4: Dari Source (Development)
```bash
git clone https://github.com/ZetaGo-Aurum/Aureus.git
cd Aureus
pip install -e .
# Atau jalankan helper:
bash install.sh
```

### 1. Siapkan dependensi sistem (hanya untuk metode pip/source)

```bash
# Linux (Debian/Ubuntu)
sudo apt install ffmpeg python3-pip
pip install yt-dlp            # atau: sudo apt install yt-dlp

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

### 2. Pasang AUREUS

Dari folder source ini:

```bash
pip install .            # dasar (TUI + CLI + Web)
pip install ".[youtube]" # sekalian memasang yt-dlp
# atau mode development:
pip install -e .
```

Atau cukup jalankan helper: `bash install.sh`

Verifikasi:

```bash
aureus -V
aureus doctor     # cek RAM, ffmpeg, yt-dlp, encoder & filter
```

> Sebagai alternatif tanpa instalasi: `python -m aureus --help` dari root folder project.

---

## 🖥️ Cara Pakai

### TUI interaktif (default)

```bash
aureus            # langsung membuka TUI
aureus tui        # sama dengan di atas
```

Panel TUI: **Dashboard** · **File Manager** (browser folder + detail probe) · **Enhance & Convert** (preset, efek, shader) · **URL Grabber** (YouTube/embed) · **Jobs/Queue** (progress live) · **System Info**.
Shortcut: `1`–`6` pindah panel, `q` keluar, mouse sepenuhnya didukung.

Screenshot ada di folder [`docs/`](docs/).

### Web UI lokal

```bash
aureus server                       # buka http://127.0.0.1:8765
aureus server --port 9000 --host 0.0.0.0
aureus server --output-dir /mnt/hdd/renders --no-open
```

Fitur web: paste link YouTube/embed → check info → pilih preset & efek → **START ENHANCE**, upload file (drag & drop), file browser server, progress bar live, preview video hasil, download langsung.

### CLI

```bash
aureus --help
aureus -h

# File lokal: 480p → 1080p, output paling raw (FFV1 lossless)
aureus convert video480.mp4 -S 1080p -p raw --effects denoise:2,sharpen:0.5

# File lokal: hasil paling kompatibel untuk semua device
aureus convert video.mp4 -S 1080p -p superhd --effects all

# Dari YouTube (termasuk link embed) → lossless
aureus url "https://www.youtube.com/watch?v=XXXX" -S 1080p -p lossless-x264
aureus url "https://www.youtube.com/embed/XXXX"   -S 2160p -p hdr10 --hdr

# SDR → HDR 4K
aureus convert video.mp4 -S 2160p -p hdr10 --hdr --effects sharpen:0.5,denoise:1

# Inspeksi media / URL
aureus info video.mp4
aureus info "https://youtu.be/XXXX"

# Lihat rencana perintah ffmpeg tanpa menjalankan
aureus convert video.mp4 -S 1080p -p raw --dry-run

aureus presets      # daftar 10 preset output
aureus effects      # daftar efek & shader
aureus doctor       # cek sistem
```

#### Flag penting `aureus convert / url`

| Flag | Nilai | Keterangan |
|---|---|---|
| `-p, --preset` | lihat tabel di bawah | preset output (default `superhd`) |
| `-S, --scale` | `source 720p 1080p 1440p 2160p 2x 4x 1920x1080` | resolusi target (default `source`) |
| `--effects` | daftar dipisah koma | `denoise:1-3, sharpen:0-1, grain:1-12, deband, deblock, deinterlace, hdr, tone-map, color-boost, all` |
| `--shader` | `cas unsharp none` | shader sharpen (default `cas`) |
| `--scaler` | `lanczos spline bicubic gauss neighbor xbr2 xbr4` | algoritma upscale (default `lanczos`) |
| `--hdr` | — | SDR→HDR expansion |
| `--tone-map` | `auto hdr2sdr off` | penanganan sumber HDR |
| `--fps` / `--motion-interp` | `source 24 30 48 60` | frame rate + interpolasi gerak |
| `--audio` | `auto copy flac pcm aac` | mode audio (default `auto`) |
| `--chroma` | `auto 420 422 444 rgb` | subsampling kroma |
| `--depth` | `auto 8 10 12` | bit depth |
| `--crf` | 14–28 | override kualitas untuk preset lossy |
| `--quality` | `best 2160 1440 1080 720 480` | kualitas download (khusus `aureus url`) |
| `-o, --output` | direktori | lokasi output (default: dir file input / cwd) |
| `--force` | — | jalankan meski RAM < 8 GB |
| `--dry-run` | — | tampilkan perintah ffmpeg saja |

---

## 🎚 Preset Output (`aureus presets`)

| Key | Preset | Jenis | Kompatibilitas | Ukuran / menit @1080p |
|---|---|---|---|---|
| `raw` | **RAW FFV1** — MKV | 🔴 lossless total | ☆☆ (arsip/editing) | 2–8 GB |
| `y4m` | **RAW Y4M** — stream uncompressed | 🔴 paling raw | ☆ (pipeline pro) | ~4,5 GB |
| `lossless-x264` | Lossless H.264 (qp=0) | 🟡 lossless | ★★★★ | 0,4–2 GB |
| `lossless-x265` | Lossless HEVC | 🟡 lossless | ★★★ | 0,3–1,5 GB |
| `prores4444` | Apple ProRes 4444 (10-bit 4:4:4) | 🟣 visually lossless | ★★★ (NLE) | 1–2 GB |
| `dnxhr` | Avid DNxHR 444 | 🟣 visually lossless | ★★★ (NLE) | 1–2 GB |
| `hdr10` | **HDR10** — HEVC 10-bit PQ | 🔵 HDR | ★★★★ | 200–600 MB |
| `hq-hevc` | HEVC CRF 17 | 🟣 HQ | ★★★★ | 60–200 MB |
| `superhd` | **Super HD H.264** CRF 16 | 🟢 paling kompatibel | ★★★★★ | 100–350 MB |
| `av1` | AV1 (AOM) | 🟣 HQ efisien | ★★★ | 40–150 MB |

---

## 🎛 Efek & Shader (`aureus effects`)

| Efek | Flag/Setting | Keterangan |
|---|---|---|
| **Denoise** | `--effects denoise:1-3` / `--denoiser nlmeans` | hqdn3d (cepat) atau NLMeans (paling halus) — membersihkan noise & jejak kompresi |
| **Sharpen Shader** | `--shader cas --sharpen 0.5` | CAS (contrast adaptive, ala AMD FidelityFX) atau Unsharp Mask — mempertajam setelah upscale |
| **Deband** | `--deband` / `--effects deband` | menghapus banding pada gradasi (langit, scene gelap) |
| **Deblock** | `--deblock` | melembutkan artefak blok dari video terkompresi berat |
| **Deinterlace** | `--deinterlace` | yadif bob untuk materi DVD/TV interlaced |
| **Film Grain** | `--grain 6` | grain film sintetis (menyamarkan banding, kesan sinematik) |
| **Color Boost** | `--saturation --contrast --gamma --brightness` | koreksi warna (filter eq) |
| **SDR→HDR** | `--hdr` (ideal dengan preset `hdr10`) | ekspansi ke 10-bit BT.2020 + PQ (zimg tone-mapping + signaling x265) |
| **HDR→SDR** | `--tone-map hdr2sdr` / otomatis | tone-mapping hable untuk perangkat SDR |
| **Upscale** | `-S 1080p` dll. | Lanczos/Spline/XBR; AR terjaga otomatis |
| **Frame rate** | `--fps 60 --motion-interp` | minterpolate MCI/AOBMC (sangat lambat) |

---

## 📡 Catatan HDR

- **SDR→HDR** bekerja dengan mengonversi ke cahaya linear → BT.2020 → PQ (SMPTE 2084) lewat zimg, lalu memberi sinyal metadata HDR10 pada stream HEVC. Hasil terbaik diputar di display HDR; di display SDR warna bisa terlihat pudar (wajar, karena butuh decoding HDR).
- **Sumber HDR** dideteksi otomatis: preset RAW/lossless menyimpannya tetap sebagai HDR 10-bit; preset 8-bit (mis. `superhd`) otomatis tone-map ke SDR BT.709.
- Build ffmpeg tanpa `zscale` tetap didukung — AUREUS otomatis fallback ke 10-bit + signaling metadata (cek dengan `aureus doctor`).

## ⚠️ Catatan jujur soal "RAW"

- Preset `raw`/`y4m`/`lossless-*` menjamin **tidak ada degradasi sama sekali** dari hasil proses enhancement — cocok untuk arsip, re-encode berkali-kali, atau editing.
- Upscale **tidak bisa menciptakan detail yang memang tidak ada** di video sumber; yang AUREUS lakukan adalah menaikkan resolusi dengan algoritma terbaik + menjernihkan + menjaga setiap piksel hasilnya secara lossless.
- File RAW itu BESAR. 10 menit video 1080p bisa 20–80 GB (Y4M). Untuk distribusi ke HP/TV gunakan `superhd` atau `hq-hevc`.

---

## 🧰 Troubleshooting

| Masalah | Solusi |
|---|---|
| `ffmpeg NOT FOUND` | `apt/brew/winget/pkg install ffmpeg` — lalu `aureus doctor` |
| `yt-dlp NOT FOUND` | `pip install yt-dlp` (fitur URL butuh ini) |
| Ditolak: "requires at least 8 GB" | Sesuai spesifikasi. Override: `--force` (CLI) / centang *Proceed anyway* (Web/TUI) |
| Download YouTube gagal / 403 | Update yt-dlp: `pip install -U yt-dlp` |
| `no path between colorspaces` (HDR) | Jarang terjadi — pastikan ffmpeg terbaru; AUREUS sudah men-tag otomatis sumber tanpa metadata warna |
| Playback FFV1/Y4M gagal | Normal — codec arsip. Putar dengan VLC/mpv/ffplay, atau konversi ulang ke `superhd` untuk distribusi |
| Port 8765 terpakai | `aureus server --port 9000` |

---

## 🏗 Struktur Proyek

```
aureus/
├── aureus/
│   ├── cli.py               # CLI (argparse) — aureus --help
│   ├── core/
│   │   ├── options.py       # Settings — kontrak tunggal CLI/TUI/Web
│   │   ├── presets.py       # 10 preset output + efek
│   │   ├── filters.py       # pembangun filter-graph (upscale/shader/HDR)
│   │   ├── encoder.py       # konstruksi & eksekusi ffmpeg + progress
│   │   ├── downloader.py    # yt-dlp (link embed/shorts di-normalisasi)
│   │   ├── media.py         # ffprobe wrapper
│   │   ├── pipeline.py      # orkestrasi (gate RAM → download → enhance)
│   │   ├── jobs.py          # job engine (dipakai TUI & Web)
│   │   └── sysinfo.py       # deteksi platform/RAM/kapabilitas
│   ├── tui/app.py           # TUI Textual (file manager, queue live)
│   └── web/
│       ├── server.py        # web server stdlib (upload, range, API)
│       └── static/index.html# UI web (tanpa dependensi eksternal)
├── docs/                    # screenshot TUI (SVG)
├── install.sh
└── pyproject.toml
```

---

## ⚖️ Lisensi & Etika

MIT License. Gunakan hanya untuk konten yang Anda miliki haknya — mengunduh materi berhak cipta dari YouTube/situs lain tanpa izin dapat melanggar ketentuan layanan mereka dan hukum yang berlaku.

<div align="center">
<sub>AUREUS v1.0.0 — dibangun di atas <b>ffmpeg</b>, <b>yt-dlp</b>, <b>Textual</b> & <b>rich</b></sub>
</div>
