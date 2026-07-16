import asyncio
import os
import re
import glob
import yt_dlp

COOKIE_PATH = os.path.join('src', 'cache', 'cookies.txt')

def download_track(idx, url, folder):
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

def get_playlist_entries(url):
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
        return None, []
    raw_title = info.get('title', 'Unknown_Playlist')
    playlist_name = re.sub(r'[\\/*?:"<>|]', "", raw_title).strip()
    raw_entries = info.get('entries', [])
    entries = [entry for entry in raw_entries if entry is not None and entry.get('url')]
    return playlist_name, entries

def select_local_folder():
    base_dir = 'downloads/yt'
    if not os.path.exists(base_dir):
        return None
    folders = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d))]
    if not folders:
        return None
    print("\nAvailable Local Folders:")
    for idx, folder in enumerate(folders, 1):
        print(f"{idx}. {folder}")
    choice = input("Select a folder number (or press Enter to skip and do a fresh download): ").strip()
    if choice.isdigit() and 1 <= int(choice) <= len(folders):
        return os.path.join(base_dir, folders[int(choice) - 1])
    return None

async def process_update(url):
    playlist_name, entries = get_playlist_entries(url)
    if not entries:
        print("Could not retrieve playlist info.")
        return
        
    target_folder = select_local_folder()
    if not target_folder:
        target_folder = f'downloads/yt/{playlist_name}'
        os.makedirs(target_folder, exist_ok=True)
        
    local_files = glob.glob(os.path.join(target_folder, '*.aac'))
    local_map = {}
    for f in local_files:
        basename = os.path.basename(f)
        match = re.match(r'^\d+_(.+)\.aac$', basename)
        if match:
            local_map[match.group(1)] = f

    opts = {
        'restrictfilenames': False, 
        'quiet': True,
        'retries': float('inf'),
        'fragment_retries': float('inf'),
        'file_access_retries': float('inf'),
        'socket_timeout': 30,
    }
    if os.path.exists(COOKIE_PATH):
        opts['cookiefile'] = COOKIE_PATH
        
    with yt_dlp.YoutubeDL(opts) as ydl:
        for entry in entries:
            entry['clean_title'] = ydl.prepare_filename(entry)[:-4]

    expected_clean_titles = {entry['clean_title'] for entry in entries}
    for title, filepath in local_map.items():
        if title not in expected_clean_titles:
            try:
                os.remove(filepath)
            except OSError:
                pass

    sem = asyncio.Semaphore(8)
    async def sem_download(idx, entry_url):
        async with sem:
            await asyncio.to_thread(download_track, idx, entry_url, target_folder)

    tasks = []
    for i, entry in enumerate(entries):
        idx = i + 1
        title = entry['clean_title']
        expected_name = f"{idx:04d}_{title}.aac"
        expected_path = os.path.join(target_folder, expected_name)
        
        if title in local_map:
            current_path = local_map[title]
            if current_path != expected_path:
                if os.path.exists(expected_path):
                    os.remove(expected_path)
                os.rename(current_path, expected_path)
        else:
            tasks.append(sem_download(idx, entry['url']))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)

async def process_append(url):
    _, append_entries = get_playlist_entries(url)
    if not append_entries:
        print("Could not retrieve append playlist info.")
        return
        
    target_folder = select_local_folder()
    if not target_folder:
        print("Append requires selecting an existing local playlist folder.")
        return

    local_files = glob.glob(os.path.join(target_folder, '*.aac'))
    parsed_files = []
    for f in local_files:
        basename = os.path.basename(f)
        match = re.match(r'^(\d+)_(.+)$', basename)
        if match:
            parsed_files.append((int(match.group(1)), match.group(2), f))
            
    parsed_files.sort(key=lambda x: x[0])
    
    healed_files = []
    for i, (_, suffix, old_path) in enumerate(parsed_files):
        new_idx = i + 1
        new_name = f"{new_idx:04d}_{suffix}"
        new_path = os.path.join(target_folder, new_name)
        healed_files.append((new_idx, suffix, old_path, new_path))

    shift_count = len(append_entries)
    for _, _, old_path, _ in reversed(healed_files):
        temp_name = "temp_" + os.path.basename(old_path)
        os.rename(old_path, os.path.join(target_folder, temp_name))

    for current_idx, suffix, old_path, _ in reversed(healed_files):
        temp_path = os.path.join(target_folder, "temp_" + os.path.basename(old_path))
        final_idx = current_idx + shift_count
        final_name = f"{final_idx:04d}_{suffix}"
        os.rename(temp_path, os.path.join(target_folder, final_name))

    sem = asyncio.Semaphore(8)
    async def sem_download(idx, entry_url):
        async with sem:
            await asyncio.to_thread(download_track, idx, entry_url, target_folder)

    tasks = [
        sem_download(i + 1, entry['url'])
        for i, entry in enumerate(append_entries)
    ]
    
    await asyncio.gather(*tasks, return_exceptions=True)