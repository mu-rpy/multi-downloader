import os
import glob
import asyncio
from concurrent.futures import ThreadPoolExecutor

BASE_DIR = 'downloads/yt'

def get_target_folder():
    if not os.path.exists(BASE_DIR):
        print(f"Error: {BASE_DIR} not found.")
        return None
    folders = [d for d in os.listdir(BASE_DIR) if os.path.isdir(os.path.join(BASE_DIR, d))]
    if not folders:
        print("No playlists found.")
        return None
    print("\nPlaylists:")
    for idx, folder in enumerate(folders, 1):
        print(f"  {idx}. {folder}")
    while True:
        choice = input("\nSelect playlist #: ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(folders):
                return os.path.join(BASE_DIR, folders[idx])
        print("Invalid selection.")

def clean_file_sync(file_path):
    import subprocess
    dir_name, file_name = os.path.split(file_path)
    base_name, _ = os.path.splitext(file_name)
    temp_output = os.path.join(dir_name, f"temp_{base_name}.aac")
    final_output = os.path.join(dir_name, f"{base_name}.aac")
    cmd = [
        'ffmpeg', '-y', '-hide_banner', '-loglevel', 'error',
        '-i', file_path,
        '-map_metadata', '-1',
        '-fflags', '+bitexact',
        '-flags:v', '+bitexact',
        '-flags:a', '+bitexact',
        '-c:a', 'copy',
        temp_output
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

async def main():
    target_folder = get_target_folder()
    if not target_folder:
        return
    m4a_files = glob.glob(os.path.join(target_folder, '*.m4a'))
    aac_files = glob.glob(os.path.join(target_folder, '*.aac'))
    all_files = m4a_files + aac_files
    total = len(all_files)
    if total == 0:
        print("No files found to clean.")
        return
    print(f"\nFound {total} files.")
    if input("Strip metadata and convert all to .aac? (y/n): ").strip().lower() != 'y':
        return
    loop = asyncio.get_running_loop()
    num_workers = min(32, (os.cpu_count() or 4) * 4)
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        tasks = [
            loop.run_in_executor(executor, clean_file_sync, f)
            for f in all_files
        ]
        results = await asyncio.gather(*tasks)
    success = sum(1 for r in results if r)
    print(f"\nFinished. Cleaned {success}/{total} files.")

if __name__ == "__main__":
    asyncio.run(main())