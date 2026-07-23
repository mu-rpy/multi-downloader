import asyncio
import os
import yt_dlp

COOKIE_PATH = os.path.join('src', 'cache', 'cookies.txt') if os.path.exists(os.path.join('src', 'cache', 'cookies.txt')) else os.path.join('cache', 'cookies.txt')

def download_single(url, format_type):
    folder = 'downloads/yt/singles'
    if format_type == 'video':
        fmt_str = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    else:
        fmt_str = 'bestaudio[ext=m4a]/bestaudio/best'
    opts = {
        'format': fmt_str,
        'nocachefile': True,
        'cache_dir': False,
        'outtmpl': f'{folder}/%(title)s.%(ext)s',
        'restrictfilenames': False,
        'quiet': True,
        'noprogress': True,
        'ignoreerrors': True,
        'retries': 5,            
        'fragment_retries': 5,   
        'file_access_retries': 5,
        'socket_timeout': 30,
        'add_metadata': False,
    }
    if os.path.exists(COOKIE_PATH):
        opts['cookiefile'] = COOKIE_PATH
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

async def process_single(url, format_type='audio'):
    os.makedirs('downloads/yt/singles', exist_ok=True)
    await asyncio.to_thread(download_single, url, format_type)