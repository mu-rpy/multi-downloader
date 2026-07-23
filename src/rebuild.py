import os
import re
import glob
import asyncio
import subprocess
import yt_dlp
from concurrent.futures import ThreadPoolExecutor

COOKIE_PATH = os.path.join('src', 'cache', 'cookies.txt')
BASE_DIR = 'downloads'
FOLDER = None

def ensure_cached_cookies(browser_name):
    cache_dir = os.path.join('src', 'cache')
    os.makedirs(cache_dir, exist_ok=True)
    cookie_file = os.path.join(cache_dir, 'cookies.txt')
    
    if not os.path.exists(cookie_file):
        print("Caching browser cookies...")
        try:
            opts = {
                'cookiesfrombrowser': (browser_name,),
                'cookiefile': cookie_file,
                'quiet': True,
                'noprogress': True,
                'ignoreerrors': True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
        except Exception as e:
            print(e)

def interactive_select_folder():
    if not os.path.exists(BASE_DIR):
        print(f"Error: {BASE_DIR}/ directory not found.")
        return None

    platforms = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    if not platforms:
        print("No platform folders found.")
        return None

    print("\nSelect Platform:")
    for idx, platform in enumerate(platforms, 1):
        print(f"  {idx}. {platform}")
        
    while True:
        p_choice = input("\nSelect platform #: ").strip()
        if p_choice.isdigit():
            p_idx = int(p_choice) - 1
            if 0 <= p_idx < len(platforms):
                platform_path = os.path.join(BASE_DIR, platforms[p_idx])
                break
        print("Invalid selection.")

    folders = [d for d in os.listdir(platform_path) if os.path.isdir(os.path.join(platform_path, d))]
    if not folders:
        print(f"No playlists found inside {platforms[p_idx]}.")
        return None

    print("\nSelect Folder:")
    for idx, folder in enumerate(folders, 1):
        print(f"  {idx}. {folder}")

    while True:
        f_choice = input("\nSelect folder #: ").strip()
        if f_choice.isdigit():
            f_idx = int(f_choice) - 1
            if 0 <= f_idx < len(folders):
                return os.path.join(platform_path, folders[f_idx])
        print("Invalid selection.")

def count_partial_files():
    partials = glob.glob(os.path.join(FOLDER, '*.tmp'))
    all_files = glob.glob(os.path.join(FOLDER, '*.aac'))
    for f in all_files:
        if os.path.getsize(f) < 10240:
            partials.append(f)
    return len(partials)

def get_missing_indices():
    files = glob.glob(os.path.join(FOLDER, '*.aac')) + glob.glob(os.path.join(FOLDER, '*.m4a'))
    indices = []
    for f in files:
        match = re.match(r'^(\d+)_', os.path.basename(f))
        if match:
            indices.append(int(match.group(1)))
    if not indices:
        return []
    return [i for i in range(1, max(indices) + 1) if i not in indices]

def clean_file_sync(file_path):
    dir_name, file_name = os.path.split(file_path)
    base_name, _ = os.path.splitext(file_name)
    temp_output = os.path.join(dir_name, f"temp_{base_name}.aac")
    final_output = os.path.join(dir_name, f"{base_name}.aac")
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-i', file_path, '-map_metadata', '-1',
        '-fflags', '+bitexact', '-flags:v', '+bitexact', '-flags:a', '+bitexact',
        '-c:a', 'copy', temp_output
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        os.remove(file_path)
        os.rename(temp_output, final_output)
        return True
    except Exception:
        if os.path.exists(temp_output):
            try: os.remove(temp_output)
            except OSError: pass
        return False

def download_track_sync(idx, url):
    opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'nocachefile': True,
        'js_runtimes': {'node': {}},
        'outtmpl': f'{FOLDER}/{idx:04d}_%(title)s.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'aac'}],
        'restrictfilenames': False,
        'quiet': True,
        'noprogress': True,
        'ignoreerrors': True,
    }
    if os.path.exists(COOKIE_PATH):
        opts['cookiefile'] = COOKIE_PATH
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

async def download_missing(url, missing_indices):
    for f in glob.glob(os.path.join(FOLDER, '*.tmp')):
        os.remove(f)

    extract_opts = {'extract_flat': 'in_playlist', 'quiet': True}
    if os.path.exists(COOKIE_PATH):
        extract_opts['cookiefile'] = COOKIE_PATH

    print(f"Scanning playlist metadata...")
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get('entries', [])

    sem = asyncio.Semaphore(8)
    loop = asyncio.get_running_loop()

    async def sem_download(idx, entry_url, title):
        async with sem:
            print(f"[Download] Index {idx:04d}: {title}")
            await loop.run_in_executor(None, download_track_sync, idx, entry_url)

    tasks = []
    for i, entry in enumerate(entries):
        idx = i + 1
        if idx in missing_indices and entry.get('url'):
            tasks.append(sem_download(idx, entry['url'], entry.get('title', 'Unknown')))

    if tasks:
        print(f"\nDownloading {len(tasks)} missing files concurrently...")
        await asyncio.gather(*tasks, return_exceptions=True)

    m4a_files = glob.glob(os.path.join(FOLDER, '*.m4a'))
    aac_files = glob.glob(os.path.join(FOLDER, '*.aac'))
    all_files = m4a_files + aac_files

    if all_files:
        num_workers = min(32, (os.cpu_count() or 4) * 4)
        print(f"\nProcessing {len(all_files)} files through clean queue...")
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            clean_tasks = [
                loop.run_in_executor(executor, clean_file_sync, f)
                for f in all_files
            ]
            results = await asyncio.gather(*clean_tasks)
        print(f"Finished. Cleaned {sum(1 for r in results if r)}/{len(all_files)} files.")

if __name__ == "__main__":
    browser = input('Enter Browser Name: ').strip().lower()
    if browser:
        ensure_cached_cookies(browser)

    FOLDER = interactive_select_folder()
    if FOLDER:
        missing = get_missing_indices()
        partial_count = count_partial_files()
        
        print(f"Missing sequence files: {len(missing)}")
        print(f"Partially built/broken files: {partial_count}")
        
        if input("Continue with patch? (Y/N): ").strip().lower() == 'y':
            url = input("URL: ").strip()
            if missing and url:
                asyncio.run(download_missing(url, missing))
            else:
                print("No missing entries to download or invalid URL.")