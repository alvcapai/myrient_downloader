# Myrient Downloader

Download files from [myrient.erista.me](https://myrient.erista.me/files/) with a simple interactive interface.

> **⚠️ Important:** Myrient shuts down on **31 March 2026**. Download what matters to you before then!

---

## Features

- **Interactive setup** — asks where to save and what to download
- **Pick categories** — choose specific collections or download everything
- **Keeps folder structure** — files are saved exactly as organised on the site
- **Resumes automatically** — restart the script after an interruption and it skips already-downloaded files
- **Concurrent downloads** — downloads multiple files at the same time for speed
- **Progress bars** — see download speed, size, and time remaining
- **Works everywhere** — Windows, macOS, and Linux

---

## Requirements

- **Python 3.8 or newer** — the script installs everything else automatically on first run
- An internet connection

### Installing Python (if you don't have it)

| Platform | Instructions |
|----------|-------------|
| **Windows** | Download from [python.org/downloads](https://www.python.org/downloads/). During install, **check "Add Python to PATH"**. |
| **macOS** | Download from [python.org/downloads](https://www.python.org/downloads/), or run `brew install python3` if you use Homebrew. |
| **Linux (Ubuntu/Debian)** | `sudo apt install python3 python3-pip` |
| **Linux (Fedora/RHEL)** | `sudo dnf install python3` |

---

## How to Run

### Windows

1. Double-click **`run.bat`**
2. A terminal window opens and guides you through the setup

### macOS / Linux

1. Open a terminal in this folder
2. Run: `./run.sh`

   *(On macOS, if you see a security warning, right-click → Open)*

### Any platform (alternative)

Open a terminal, navigate to this folder, and run:
```
python3 myrient_downloader.py
```
or on Windows:
```
python myrient_downloader.py
```

---

## Step-by-Step Walkthrough

1. **Choose a download folder**
   The script suggests `~/Downloads/Myrient`. Press Enter to accept or type any path.

2. **Pick categories**
   A table shows all available collections. Type:
   - `all` — download everything
   - `1,3,5` — specific categories by number
   - `1-5` — a range of categories
   - `2,4-7,10` — combinations

3. **Set concurrent downloads**
   Enter how many files to download at the same time (default: 3).
   - Slow connection → use 1–2
   - Fast connection → use 5–10

4. **Watch the progress**
   The script shows a progress bar with speed and estimated time remaining.

5. **Interrupt and resume anytime**
   Press `Ctrl+C` to stop. Run the script again — it skips files that are already complete.

---

## File Structure

Downloaded files are saved with the same folder structure as the website:

```
~/Downloads/Myrient/
├── No-Intro/
│   ├── Nintendo - Game Boy/
│   │   ├── Super Mario Land (World).zip
│   │   └── ...
│   └── ...
├── Redump/
│   └── ...
└── ...
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Python is not installed" | Install Python from [python.org](https://www.python.org/downloads/) |
| "Add Python to PATH" error on Windows | Reinstall Python and check the "Add to PATH" box |
| Permission error when saving | Choose a folder you have write access to (e.g. your Desktop or Downloads) |
| Download fails repeatedly | The site may be temporarily unavailable. Wait and try again. |
| Script stops mid-download | Just run it again — it resumes from where it left off |

---

## Advanced usage (optional)

If you prefer to install dependencies manually before running:

```bash
pip install -r requirements.txt
python3 myrient_downloader.py
```
