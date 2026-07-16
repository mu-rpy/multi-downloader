import asyncio
import os
import glob
import yt_dlp

COOKIE_PATH = os.path.join('src', 'cache', 'cookies.txt')

def download_single(url):
    folder = 'downloads/yt/singles'
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [
            {
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'aac',
            },
            {
                'key': 'FFmpegMetadata',
                'add_metadata': True,
            }
        ],
        'parse_metadata': [
            '%(title)s:%(meta_artist)s - %(meta_title)s',
            '%(uploader)s:%(meta_artist)s',
            '%(title)s:%(meta_title)s',
        ],
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'restrictfilenames': False,
        'quiet': True,
        'noprogress': True,
        'ignoreerrors': True,
        'retries': float('inf'),            
        'fragment_retries': float('inf'),   
        'file_access_retries': float('inf'),
        'socket_timeout': 30,
    }
    if os.path.exists(COOKIE_PATH):
        opts['cookiefile'] = COOKIE_PATH

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