import os
import re
import glob
import asyncio
import yt_dlp

print('Warning! This is for debug purposes only!')
print('This will patch missing numbers, however it WONT complete the playlist.')
FOLDER = 'downloads/yt/main'

def count_partial_files():
    partials = glob.glob(os.path.join(FOLDER, '*.tmp'))
    all_files = glob.glob(os.path.join(FOLDER, '*.aac'))
    for f in all_files:
        if os.path.getsize(f) < 10240:
            partials.append(f)
    return len(partials)

def get_missing_indices():
    files = glob.glob(os.path.join(FOLDER, '*.aac'))
    indices = []
    for f in files:
        match = re.match(r'^(\d+)_', os.path.basename(f))
        if match:
            indices.append(int(match.group(1)))
    
    if not indices:
        return []
    
    max_idx = max(indices)
    return [i for i in range(1, max_idx + 1) if i not in indices]

async def download_missing(url, missing_indices):
    for f in glob.glob(os.path.join(FOLDER, '*.tmp')):
        os.remove(f)

    extract_opts = {'extract_flat': 'in_playlist', 'quiet': True}
    
    print(f"Missing Indices: {len(missing_indices)}")
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        entries = info.get('entries', [])
        
    for i, entry in enumerate(entries):
        idx = i + 1
        if idx in missing_indices:
            print(f"Downloading missing index {idx:04d}: {entry.get('title')}")
            opts = {
                'format': 'bestaudio[ext=m4a]/bestaudio/best',
                'js_runtimes': {'node': {}},
                'outtmpl': f'{FOLDER}/{idx:04d}_%(title)s.%(ext)s',
                'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'aac'}],
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([entry['url']])

    for file in glob.glob(os.path.join(FOLDER, '*.m4a')):
        new_file = file[:-4] + '.aac'
        if os.path.exists(new_file):
            os.remove(new_file)
        os.rename(file, new_file)

if __name__ == "__main__":
    missing = get_missing_indices()
    partial_count = count_partial_files()
    
    print(f"Missing sequence files: {len(missing)}")
    print(f"Partially built/broken files: {partial_count}")
    
    confirm = input("Continue with patch? (Y/N): ").strip().lower()
    
    if confirm == 'y':
        url = input("URL: ")
        if missing:
            asyncio.run(download_missing(url, missing))
        else:
            print("No missing files found in the sequence.")
    else:
        print("Operation cancelled.")