import os
from assistant.core.registry import on_regex, on_fuzzy
from assistant.core.speak_selector import speak

def get_downloads_folder():
    """Gets the path to the user's Downloads folder."""
    if os.name == 'nt':
        import winreg
        sub_key = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        downloads_guid = "{374DE290-123F-4565-9164-39C4925E467B}"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, sub_key) as key:
                location = winreg.QueryValueEx(key, downloads_guid)[0]
                return location
        except Exception:
            return os.path.join(os.environ['USERPROFILE'], 'Downloads')
    else:
        return os.path.join(os.path.expanduser('~'), 'Downloads')

def format_size(size_bytes):
    if size_bytes == 0:
        return "0 Bytes"
    size_name = ("Bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"

@on_regex(r".*(?:find|search for|look for|locate)\s+(?:the\s+)?(?:file|document)[s]?(?:\s+(?:named|called|name))?\s+(.*)", priority=8)
def find_file(filename):
    filename = filename.strip()
    if not filename:
        speak("What file should I look for?")
        return
        
    speak(f"Searching for {filename}...")
    
    search_dirs = [
        os.path.join(os.environ['USERPROFILE'], 'Documents'),
        get_downloads_folder(),
        os.path.join(os.environ['USERPROFILE'], 'Desktop')
    ]
    
    found = []
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for f in files:
                if filename.lower() in f.lower():
                    found.append(os.path.join(root, f))
                if len(found) >= 5:
                    break
            if len(found) >= 5:
                break
        if len(found) >= 5:
            break
            
    if found:
        speak(f"I found {len(found)} matching files. Opening the first match.")
        
        # Emit to UI (HUD) if possible, or print
        print(f"Found: {found[0]}")
        
        try:
            if os.name == 'nt':
                os.startfile(found[0])
            else:
                import subprocess
                subprocess.Popen(['xdg-open', found[0]])
        except Exception as e:
            print(f"Failed to open file: {e}")
    else:
        speak(f"I couldn't find any files named {filename} in your standard directories.")

@on_regex(r"\b(?:open|show|view|go to)\s+(?:my\s+)?(?:recent\s+)?downloads(?:\s+folder|directory)?\b", priority=15)
def open_downloads(text=None):
    dl_path = get_downloads_folder()
    speak("Opening your downloads folder.")
    if os.name == 'nt':
        os.startfile(dl_path)
    else:
        import subprocess
        subprocess.Popen(['xdg-open', dl_path])

@on_fuzzy(["how big is my downloads folder", "size of downloads folder", "check downloads size", "downloads folder size", "how much space is downloads taking"], score_cutoff=85)
def downloads_size(text):
    dl_path = get_downloads_folder()
    total_size = 0
    try:
        for root, dirs, files in os.walk(dl_path):
            for f in files:
                fp = os.path.join(root, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        
        formatted_size = format_size(total_size)
        speak(f"Your downloads folder is taking up {formatted_size} of space.")
    except Exception as e:
        speak("I ran into an error while calculating the folder size.")
        print(f"Error calculating size: {e}")

@on_fuzzy(["clean up temp files", "empty temp folder", "clear temporary files", "delete temp files", "remove temporary files", "clean temp folder", "empty temp directory", "clear temp"], score_cutoff=85)
def clean_temp_files(text):
    import tempfile
    temp_dir = tempfile.gettempdir()
    speak("Cleaning up temporary files...")
    
    count = 0
    size_freed = 0
    
    for item in os.listdir(temp_dir):
        item_path = os.path.join(temp_dir, item)
        try:
            if os.path.isfile(item_path) or os.path.islink(item_path):
                size = os.path.getsize(item_path)
                os.unlink(item_path)
                size_freed += size
                count += 1
            elif os.path.isdir(item_path):
                # For safety, let's not blindly rmtree directories in Temp unless we're sure
                pass
        except Exception:
            pass
            
    freed_str = format_size(size_freed)
    speak(f"Cleanup complete. I removed {count} items and freed {freed_str} of space.")
