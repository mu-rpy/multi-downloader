import asyncio
import os
import yt_dlp

def download_single(url):
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'flac'}],
        'outtmpl': 'downloads/yt/singles/%(title)s.%(ext)s',
        'restrictfilenames': True,
        'quiet': True,
        'noprogress': True,
        'ignoreerrors': True
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

async def process_single(url):
    os.makedirs('downloads/yt/singles', exist_ok=True)
    await asyncio.to_thread(download_single, url)