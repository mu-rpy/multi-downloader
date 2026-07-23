import asyncio
import os
import re
from datetime import datetime
import yt_dlp

COOKIE_PATH = os.path.join('src', 'cache', 'cookies.txt') if os.path.exists(os.path.join('src', 'cache', 'cookies.txt')) else os.path.join('cache', 'cookies.txt')

def download_track(idx, url, folder, format_type):
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

def get_playlist_entries(url):
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
        info = ydl.extract_info(url, download=False)
    if not info:
        return None, []
    raw_title = info.get('title', 'Unknown_Playlist')
    playlist_name = re.sub(r'[\\/*?:"<>|]', "", raw_title).strip()
    raw_entries = info.get('entries', [])
    entries = [entry for entry in raw_entries if entry is not None and entry.get('url')]
    return playlist_name, entries

async def select_local_folder_async():
    base_dir = os.path.dirname(os.path.dirname(__file__)) if '__file__' in locals() else os.getcwd()
    yt_dir = os.path.join(base_dir, 'downloads', 'yt') if os.path.exists(os.path.join(base_dir, 'downloads')) else 'downloads/yt'
    if not os.path.exists(yt_dir):
        return None
    folders = [d for d in os.listdir(yt_dir) if os.path.isdir(os.path.join(yt_dir, d))]
    if not folders:
        return None
    print("\nAvailable Local Folders:")
    for idx, folder in enumerate(folders, 1):
        print(f"{idx}. {folder}")
    choice = await asyncio.to_thread(input, "Select a folder number: ")
    choice = choice.strip()
    if choice.isdigit() and 1 <= int(choice) <= len(folders):
        return os.path.join(yt_dir, folders[int(choice) - 1])
    return None

async def process_append(url, max_concurrent=8, format_type='audio'):
    playlist_info = await asyncio.to_thread(get_playlist_entries, url)
    if not playlist_info:
        print("Could not retrieve append playlist info.")
        return
    append_playlist_name, append_entries = playlist_info
    if not append_entries:
        print("Could not retrieve append playlist items.")
        return
    target_folder = await select_local_folder_async()
    if not target_folder:
        print("Append requires selecting an existing local playlist folder.")
        return
    playlist_name = os.path.basename(target_folder)
    local_files = [f for f in os.listdir(target_folder) if not f.endswith('.part') and not f.endswith('.ytdl')]
    parsed_files = []
    for f in local_files:
        match = re.match(r'^(\d+)_(.+)$', f)
        if match:
            parsed_files.append((int(match.group(1)), match.group(2), f))
    parsed_files.sort(key=lambda x: x[0])
    
    shift_count = len(append_entries)
    
    rename_mapping = []
    for i, (_, suffix, old_name) in enumerate(parsed_files):
        current_idx = i + 1
        old_path = os.path.join(target_folder, old_name)
        temp_path = os.path.join(target_folder, f"temp_{old_name}")
        final_idx = current_idx + shift_count
        final_path = os.path.join(target_folder, f"{final_idx:04d}_{suffix}")
        rename_mapping.append((old_path, temp_path, final_path))

    for old_path, temp_path, _ in reversed(rename_mapping):
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
        if os.path.exists(old_path):
            os.rename(old_path, temp_path)

    for _, temp_path, final_path in rename_mapping:
        if os.path.exists(final_path):
            try:
                os.remove(final_path)
            except OSError:
                pass
        if os.path.exists(temp_path):
            os.rename(temp_path, final_path)

    sem = asyncio.Semaphore(max_concurrent)
    async def sem_download(idx, entry_url):
        async with sem:
            await asyncio.to_thread(download_track, idx, entry_url, target_folder, format_type)
    tasks = [
        sem_download(i + 1, entry['url'])
        for i, entry in enumerate(append_entries)
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    total_appends = len(append_entries)
    downloaded_count = 0
    missing_items = []
    available_files = os.listdir(target_folder)
    for i, entry in enumerate(append_entries):
        idx = i + 1
        url = entry.get('url', '')
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
    completion_percentage = (downloaded_count / total_appends * 100) if total_appends > 0 else 0.0
    print(f"Append Completion: {completion_percentage:.2f}% ({downloaded_count}/{total_appends} tracks appended)")
    print(f"Append files skipped/missed: {skipped_count}")
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