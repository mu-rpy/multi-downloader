## Multi Media Downloader

> [!WARNING]
> This is intended for educational purposes only.
> By continuing to use this, you accept the risks and acknowledge that you have been warned.

## Dependencies
The script requires ffmpeg for audio conversion and node to solve YouTube's signature challenges.

- Linux:
```bash
sudo pacman -S ffmpeg nodejs # for cachyos / arch
sudo apt ffmpeg nodejs # for others or rest
```

- Windows (PowerShell):
```PowerShell
winget install ffmpeg
winget install OpenJS.NodeJS
```

## Setup
- Linux
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U "yt-dlp[default]"
```

- Windows
```PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -U "yt-dlp[default]"
```

## Usage
1. Run `python app.py`
2. Enter your default browser (e.g: brave, firefox, chrome, edge, etc...)
3. Choose your download method.

> [!IMPORTANT]
> Make sure you're logged in to your youtube account if you want to download 18+ content.
> If your playlist download gets interrupted/corrupted, you can try to rebuid using rebuild.py (untested).

--
Mu-rpy