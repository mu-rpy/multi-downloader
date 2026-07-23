import os
import sys
import importlib
import asyncio
import inspect
import yt_dlp
import atexit

platforms_config = {
    'yt': 'YouTube'
}

cache_dir = os.path.join('src', 'cache')
os.makedirs(cache_dir, exist_ok=True)
COOKIE_FILE = os.path.join(cache_dir, 'cookies.txt')

def cleanup_cookies():
    if os.path.exists(COOKIE_FILE):
        try:
            os.remove(COOKIE_FILE)
        except OSError:
            pass

atexit.register(cleanup_cookies)

print("[SETUP]")
print("(* Press Enter to skip if you don't need age-restricted/18+ content)")
browser_input = input('Enter your browser name (e.g. firefox, chrome): ').strip().lower()

if browser_input:
    browser_name = browser_input
else:
    browser_name = None

def ensure_cached_cookies():

    if not os.path.exists(COOKIE_FILE):
        try:
            opts = {
                'cookiesfrombrowser': (browser_name,),
                'cookiefile': COOKIE_FILE,
                'quiet': True,
                'noprogress': True,
                'ignoreerrors': True,
            }
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.extract_info("https://youtube.com", download=False)
        except Exception as e:
            print(f"Cookie caching error: {e}")

def get_capabilities():
    caps = {}
    src_dir = 'src'
    if not os.path.exists(src_dir):
        return caps
    files = [f for f in os.listdir(src_dir) if f.endswith('.py') and f != '__init__.py']
    for file in files:
        base = file[:-3]
        parts = base.split('_', 1)
        if len(parts) >= 2:
            platform = parts[0]
            mode = parts[1]
            if platform not in caps:
                caps[platform] = []
            if mode not in caps[platform]:
                caps[platform].append(mode)
    if os.path.exists(os.path.join(src_dir, 'rebuild.py')):
        if 'yt' not in caps:
            caps['yt'] = []
        caps['yt'].append('rebuild')
    return caps

def select_item(header, available, fallback_mapping):
    print(f"\n{header}")
    options = []
    for idx, item in enumerate(available, 1):
        display_name = fallback_mapping.get(item.lower(), item.upper())
        print(f"{idx}. {display_name}")
        options.append((str(idx), item))
    while True:
        choice = input("Select an option: ").strip()
        for idx_str, item in options:
            if choice == idx_str or choice.lower() == item.lower() or choice.lower() == fallback_mapping.get(item.lower(), item.upper()).lower():
                return item
        print("Invalid selection. Try again.")

def main():
    ensure_cached_cookies()
    caps = get_capabilities()
    if not caps:
        print("Error: No valid modules found inside src/")
        sys.exit(1)
        
    selected_platform = select_item("[PLATFORM]", list(caps.keys()), platforms_config)
    available_modes = caps[selected_platform]
    
    top_modes = []
    if 'playlist' in available_modes or 'append' in available_modes or 'rebuild' in available_modes:
        top_modes.append('playlist')
    if 'single' in available_modes:
        top_modes.append('single')
        
    selected_top_mode = select_item("[MODE]", top_modes, {})
    
    selected_sub_mode = None
    if selected_top_mode == 'playlist':
        sub_options = []
        if 'playlist' in available_modes:
            sub_options.append('create')
        if 'append' in available_modes:
            sub_options.append('append')
        if 'rebuild' in available_modes:
            sub_options.append('rebuild')
        selected_sub_mode = select_item("[PLAYLIST]", sub_options, {})

    if selected_top_mode == 'playlist' and selected_sub_mode == 'rebuild':
        module_name = "src.rebuild"
        func_name = "main"
        url = None
        format_type = None
    else:
        url = input("\nEnter URL: ").strip()
        if not url:
            print("Error: URL string cannot be empty.")
            sys.exit(1)
            
        print("\n[FORMAT]")
        print("1. Audio (m4a)")
        print("2. Video (mp4)")
        format_choice = input("Select format option: ").strip()
        format_type = 'video' if format_choice == '2' or format_choice.lower() == 'video' else 'audio'
        
        if selected_top_mode == 'single':
            module_name = f"src.{selected_platform}_single"
            func_name = "process_single"
        elif selected_sub_mode == 'create':
            module_name = f"src.{selected_platform}_playlist"
            func_name = "process_playlist"
        elif selected_sub_mode == 'append':
            module_name = f"src.{selected_platform}_append"
            func_name = "process_append"
            
    try:
        mod = importlib.import_module(module_name)
        if hasattr(mod, func_name):
            func = getattr(mod, func_name)
            if inspect.iscoroutinefunction(func):
                if url is not None:
                    asyncio.run(func(url, format_type=format_type))
                else:
                    asyncio.run(func())
            else:
                if url is not None:
                    func(url, format_type=format_type)
                else:
                    func()
        else:
            print(f"Error: Function {func_name} target not exposed in {module_name}")
    except Exception as e:
        print(f"Runtime Processing Crash Traceback: {e}")
        raise e

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted cleanly by user.")
    finally:
        cleanup_cookies()
        sys.exit(0)