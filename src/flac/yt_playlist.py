import asyncio
import re
import yt_dlp

def download_track(idx, url, playlist_name):
    opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'flac'}],
        'outtmpl': f'downloads/yt/{playlist_name}/{idx:04d}_%(title)s.%(ext)s',
        'restrictfilenames': True,
        'quiet': True,
        'noprogress': True,
        'ignoreerrors': True
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

async def process_playlist(url, max_concurrent=8):
    extract_opts = {'extract_flat': True, 'quiet': True, 'ignoreerrors': True}
    with yt_dlp.YoutubeDL(extract_opts) as ydl:
        info = ydl.extract_info(url, download=False)
    
    raw_title = info.get('title', 'Unknown_Playlist')
    playlist_name = re.sub(r'[\\/*?:"<>|]', "", raw_title).strip()
    
    entries = info.get('entries', [])
    sem = asyncio.Semaphore(max_concurrent)
    
    async def sem_download(idx, link):
        async with sem:
            await asyncio.to_thread(download_track, idx, link, playlist_name)
            
    tasks = [
        sem_download(i + 1, entry['url'])
        for i, entry in enumerate(entries) if entry.get('url')
    ]
    await asyncio.gather(*tasks, return_exceptions=True)