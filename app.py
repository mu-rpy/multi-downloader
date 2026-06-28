import os
import sys
import importlib
import asyncio

def get_capabilities():
    caps = {}
    all_formats = set()
    all_modes = set()
    src_dir = 'src'
    
    if not os.path.exists(src_dir):
        return caps, [], []
        
    formats = [d for d in os.listdir(src_dir) if os.path.isdir(os.path.join(src_dir, d))]
    for fmt in formats:
        all_formats.add(fmt)
        fmt_dir = os.path.join(src_dir, fmt)
        files = [f for f in os.listdir(fmt_dir) if f.endswith('.py') and f != '__init__.py']
        
        for file in files:
            base = file[:-3]
            parts = base.split('_', 1)
            if len(parts) >= 2:
                platform = parts[0]
                mode = parts[1]
                all_modes.add(mode)
                
                if platform not in caps:
                    caps[platform] = {}
                if fmt not in caps[platform]:
                    caps[platform][fmt] = []
                if mode not in caps[platform][fmt]:
                    caps[platform][fmt].append(mode)
                    
    return caps, sorted(list(all_formats)), sorted(list(all_modes))

def prompt_selection(prompt_text, available_items, all_items, descriptions=None):
    if descriptions is None:
        descriptions = {}
        
    print(prompt_text)
    options = []
    display_idx = 1
    
    for item in all_items:
        if item in available_items:
            desc = f" - {descriptions.get(item, '')}" if item in descriptions else ""
            print(f"{display_idx}. {item}{desc}")
            options.append({'item': item, 'available': True, 'idx': str(display_idx)})
            display_idx += 1
        else:
            print(f"\033[90m-. {item} (Currently unavailable for this selection)\033[0m")
            options.append({'item': item, 'available': False, 'idx': '-'})
            
    while True:
        choice = input("Select an option: ").strip()
        for opt in options:
            if opt['available'] and (choice == opt['item'] or choice == opt['idx']):
                return opt['item']
            elif not opt['available'] and (choice == opt['item']):
                print("That option is currently unavailable. Please select a valid option.")
                break
        else:
            print("Invalid selection. Try again.")

def main():
    caps, all_formats, all_modes = get_capabilities()
    if not caps:
        print("No scripts found. Please ensure the 'src' directory structure is correct.")
        sys.exit(1)
        
    platforms = sorted(list(caps.keys()))
    print("\n--- Platform Selection ---")
    selected_platform = prompt_selection("Available platforms:", platforms, platforms)
    
    format_descriptions = {
        'aac': 'Highly compatible, excellent compression, lighter file size.',
        'flac': 'High quality lossless audio, extremely heavy file size.'
    }
    
    available_formats = sorted(list(caps[selected_platform].keys()))
    print("\n--- Format Selection ---")
    selected_format = prompt_selection("Available formats:", available_formats, all_formats, format_descriptions)
    
    available_modes = caps[selected_platform][selected_format]
    
    display_modes = []
    if 'playlist' in available_modes or 'edit' in available_modes:
        display_modes.append('playlist')
    if 'single' in available_modes:
        display_modes.append('single')
        
    all_possible_top_modes = []
    if 'playlist' in all_modes or 'edit' in all_modes:
        all_possible_top_modes.append('playlist')
    if 'single' in all_modes:
        all_possible_top_modes.append('single')
        
    print("\n--- Mode Selection ---")
    selected_top_mode = prompt_selection("Available modes:", display_modes, all_possible_top_modes)
    
    selected_sub_mode = None
    if selected_top_mode == 'playlist':
        sub_options = []
        if 'playlist' in available_modes:
            sub_options.append('create playlist')
        if 'edit' in available_modes:
            sub_options.append('update playlist')
            sub_options.append('append playlist')
            
        all_possible_subs = ['create playlist', 'update playlist', 'append playlist']
        
        print("\n--- Playlist Options ---")
        selected_sub_mode = prompt_selection("Select playlist action:", sub_options, all_possible_subs)
    
    url = input(f"\nEnter URL: ").strip()
    if not url:
        print("URL cannot be empty.")
        sys.exit(1)
        
    if selected_top_mode == 'single':
        module_name = f"src.{selected_format}.{selected_platform}_single"
        func_name = "process_single"
    else:
        if selected_sub_mode == 'create playlist':
            module_name = f"src.{selected_format}.{selected_platform}_playlist"
            func_name = "process_playlist"
        elif selected_sub_mode == 'update playlist':
            module_name = f"src.{selected_format}.{selected_platform}_edit"
            func_name = "process_update"
        elif selected_sub_mode == 'append playlist':
            module_name = f"src.{selected_format}.{selected_platform}_edit"
            func_name = "process_append"
            
    try:
        mod = importlib.import_module(module_name)
        if hasattr(mod, func_name):
            func = getattr(mod, func_name)
            asyncio.run(func(url))
            print("\nDownload operation completed.")
        else:
            print(f"Critical Error: Function '{func_name}' not found in {module_name}.")
    except Exception as e:
        print(f"An execution error occurred: {e}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)