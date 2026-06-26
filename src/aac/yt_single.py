import asyncio
import os
import glob
import yt_dlp

def download_single(url):
    folder = 'downloads/yt/singles'
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'aac',
        }],
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'restrictfilenames': True,
        'quiet': True,
        'noprogress': True,
        'ignoreerrors': True
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
        
    for file in glob.glob(f'{folder}/*.m4a'):
        new_file = file[:-4] + '.aac'
        if os.path.exists(new_file):
            os.remove(new_file)
        os.rename(file, new_file)

async def process_single(url):
    os.makedirs('downloads/yt/singles', exist_ok=True)
    await asyncio.to_thread(download_single, url)