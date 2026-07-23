import asyncio
import os
import re
from datetime import datetime
import yt_dlp

COOKIE_PATH = os.path.join('src', 'cache', 'cookies.txt') if os.path.exists(os.path.join('src', 'cache', 'cookies.txt')) else os.path.join('cache', 'cookies.txt')

def download_track(idx, url, playlist_name, format_type):
    folder = f'downloads/yt/{playlist_name}'
    if format_type == 'video':
        fmt_str = 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    else:
        fmt_str = 'bestaudio[ext=m4a]/bestaudio/best'
    opts = {
        'format': fmt_str,
        'nocachefile': True,
        'cache_dir': False,
        'outtmpl': f'{folder}/{idx:04d}_%(title)s.%(ext)s',
        'restrictfilenames': False,
        'quiet': True,
        'noprogress': True,
        'ignoreerrors': False,
        'retries': 5,            
        'fragment_retries': 5,   
        'file_access_retries': 5,
        'socket_timeout': 30,
        'add_metadata': False,
    }
    if os.path.exists(COOKIE_PATH):
        opts['cookiefile'] = COOKIE_PATH
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
    except Exception as e:
        if os.path.exists(folder):
            for file in os.listdir(folder):
                if file.startswith(f"{idx:04d}_") and (file.endswith('.part') or file.endswith('.ytdl')):
                    try:
                        os.remove(os.path.join(folder, file))
                    except OSError:
                        pass
        raise e

async def process_playlist(url, max_concurrent=8, format_type='audio'):
    extract_opts = {
        'extract_flat': 'in_playlist',
        'nocachefile': True,
        'cache_dir': False,
        'quiet': True,
        'ignoreerrors': True,
        'retries': 5,            
        'fragment_retries': 5,   
        'file_access_retries': 5,
        'socket_timeout': 30,
    }
    if os.path.exists(COOKIE_PATH):
        extract_opts['cookiefile'] = COOKIE_PATH
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        info = await asyncio.to_thread(ydl.extract_info, url, download=False)
    if not info:
        print("Error: Could not retrieve playlist info.")
        return
    raw_title = info.get('title', 'Unknown_Playlist')
    playlist_name = re.sub(r'[\\/*?:"<>|]', "", raw_title).strip()
    folder = f'downloads/yt/{playlist_name}'
    os.makedirs(folder, exist_ok=True)
    raw_entries = info.get('entries', [])
    entries = [entry for entry in raw_entries if entry is not None]
    sem = asyncio.Semaphore(max_concurrent)
    async def sem_download(idx, link):
        async with sem:
            await asyncio.to_thread(download_track, idx, link, playlist_name, format_type)
    tasks = [
        sem_download(i + 1, entry['url'])
        for i, entry in enumerate(entries) if entry.get('url')
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    total_tracks = len(entries)
    downloaded_count = 0
    missing_items = []
    if os.path.exists(folder):
        available_files = os.listdir(folder)
    else:
        available_files = []
    for i, entry in enumerate(entries):
        idx = i + 1
        url = entry.get('url', '')
        if not url:
            continue
        found = False
        prefix = f"{idx:04d}_"
        for file in available_files:
            if file.startswith(prefix) and not file.endswith('.part') and not file.endswith('.ytdl'):
                found = True
                break
        if found:
            downloaded_count += 1
        else:
            missing_items.append((idx, url))
    skipped_count = len(missing_items)
    completion_percentage = (downloaded_count / total_tracks * 100) if total_tracks > 0 else 0.0
    print(f"Completion: {completion_percentage:.2f}% ({downloaded_count}/{total_tracks} files downloaded)")
    print(f"Files skipped/missed: {skipped_count}")
    if missing_items:
        base_dir = os.path.dirname(os.path.dirname(__file__)) if '__file__' in locals() else os.getcwd()
        cache_dir = os.path.join(base_dir, 'src', 'cache') if os.path.exists(os.path.join(base_dir, 'src')) else os.path.join(base_dir, 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        info_file_path = os.path.join(cache_dir, f"{playlist_name}.info")
        current_date = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
        with open(info_file_path, 'w', encoding='utf-8') as f:
            f.write(f"{current_date}\n")
            f.write(f"[{playlist_name}]\n")
            for idx, item_url in missing_items:
                f.write(f"{idx:04d} \"{item_url}\"\n")