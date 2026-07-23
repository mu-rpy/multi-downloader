import asyncio
import os
import re
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

async def rebuild_playlist_from_tracker(info_file_path, max_concurrent=8, max_retries=3, base_retry_delay=5):
    if not os.path.exists(info_file_path):
        return
    playlist_name = None
    missing_tasks_data = []
    with open(info_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if line.startswith('[') and line.endswith(']') and not re.match(r'^\[\d{4}-\d{2}-\d{2}', line):
            playlist_name = line[1:-1].strip()
            continue
        match = re.match(r'^(\d{4})\s+"([^"]+)"', line)
        if match and playlist_name:
            idx = int(match.group(1))
            url = match.group(2)
            missing_tasks_data.append((idx, url, playlist_name))
    if not missing_tasks_data:
        try:
            os.remove(info_file_path)
        except OSError:
            pass
        return
    print(f"\n[REBUILD] Select target format for missing items in: {playlist_name}")
    print("1. Audio (m4a)")
    print("2. Video (mp4)")
    format_choice = await asyncio.to_thread(input, "Select format option: ")
    format_choice = format_choice.strip()
    format_type = 'video' if format_choice == '2' or format_choice.lower() == 'video' else 'audio'
    sem = asyncio.Semaphore(max_concurrent)
    async def retry_download_worker(idx, url, p_name):
        async with sem:
            retries = 0
            current_delay = base_retry_delay
            while retries < max_retries:
                try:
                    await asyncio.to_thread(download_track, idx, url, p_name, format_type)
                    return (idx, url, True)
                except Exception:
                    retries += 1
                    if retries < max_retries:
                        await asyncio.sleep(current_delay)
                        current_delay *= 2
            return (idx, url, False)
    tasks = [
        retry_download_worker(idx, url, p_name)
        for idx, url, p_name in missing_tasks_data
    ]
    results = await asyncio.gather(*tasks)
    still_missing = [item for item in results if item[2] is False]
    if not still_missing:
        try:
            os.remove(info_file_path)
        except OSError:
            pass
        print(f"Rebuild successful for {playlist_name}. All missing tracks fetched.")
    else:
        print(f"Rebuild incomplete for {playlist_name}. {len(still_missing)} tracks still failed consecutively.")
        with open(info_file_path, 'w', encoding='utf-8') as f:
            from datetime import datetime
            current_date = datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
            f.write(f"{current_date}\n")
            f.write(f"[{playlist_name}]\n")
            for idx, url, _ in still_missing:
                f.write(f"{idx:04d} \"{url}\"\n")
        opts_clear = {'quiet': True}
        with yt_dlp.YoutubeDL(opts_clear) as ydl:
            try:
                ydl.cache.remove()
            except Exception:
                pass

async def main(*args, **kwargs):
    base_dir = os.path.dirname(os.path.dirname(__file__)) if '__file__' in locals() else os.getcwd()
    cache_dir = os.path.join(base_dir, 'src', 'cache') if os.path.exists(os.path.join(base_dir, 'src')) else os.path.join(base_dir, 'cache')
    if not os.path.exists(cache_dir):
        return
    info_files = [
        os.path.join(cache_dir, f) 
        for f in os.listdir(cache_dir) 
        if f.endswith('.info')
    ]
    for info_file in info_files:
        await rebuild_playlist_from_tracker(info_file)

if __name__ == "__main__":
    asyncio.run(main())