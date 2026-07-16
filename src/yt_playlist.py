import asyncio
import os
import re
import glob
import yt_dlp

COOKIE_PATH = os.path.join('src', 'cache', 'cookies.txt')

def download_track(idx, url, playlist_name):
    folder = f'downloads/yt/{playlist_name}'
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
        'outtmpl': f'{folder}/{idx:04d}_%(title)s.%(ext)s',
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
        
    for file in glob.glob(f'{folder}/{idx:04d}_*.m4a'):
        new_file = file[:-4] + '.aac'
        if os.path.exists(new_file):
            os.remove(new_file)
        os.rename(file, new_file)

async def process_playlist(url, max_concurrent=8):
    extract_opts = {
        'extract_flat': 'in_playlist',
        'quiet': True,
        'ignoreerrors': True,
        'retries': float('inf'),            
        'fragment_retries': float('inf'),   
        'file_access_retries': float('inf'),
        'socket_timeout': 30,
    }
    if os.path.exists(COOKIE_PATH):
        extract_opts['cookiefile'] = COOKIE_PATH
        
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    if not info:
        return

    raw_title = info.get('title', 'Unknown_Playlist')
    playlist_name = re.sub(r'[\\/*?:"<>|]', "", raw_title).strip()
    os.makedirs(f'downloads/yt/{playlist_name}', exist_ok=True)
    
    raw_entries = info.get('entries', [])
    entries = [entry for entry in raw_entries if entry is not None]
    sem = asyncio.Semaphore(max_concurrent)
    
    async def sem_download(idx, link):
        async with sem:
            await asyncio.to_thread(download_track, idx, link, playlist_name)
            
    tasks = [
        sem_download(i + 1, entry['url'])
        for i, entry in enumerate(entries) if entry.get('url')
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)