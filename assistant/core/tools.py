"""
LLM Tools Module

Provides functions that the LLM can natively call using Function Calling.
These functions wrap the existing automation scripts so the LLM can use them seamlessly.
"""

import functools
from assistant.automation.integrations.check_weather import _fetch_weather_data, _extract_comprehensive_data, get_location
from assistant.automation.integrations.detailed_web_search import get_web_info
from assistant.core.logger import get_logger

logger = get_logger("LLMTools")

def llm_tool(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"LLM called tool: {func.__name__}(args={args}, kwargs={kwargs})")
        try:
            return func(*args, **kwargs)
        except Exception as e:
            import subprocess
            if isinstance(e, subprocess.TimeoutExpired):
                logger.error(f"Error in {func.__name__} tool: Command timed out.")
                return f"Error executing {func.__name__}: Command timed out after 60 seconds."
            logger.error(f"Error in {func.__name__} tool: {e}")
            return f"Error executing {func.__name__}: {str(e)}"
    return wrapper

@llm_tool
def get_weather(location: str = "current") -> str:
    """
    Get the current weather conditions for a specific location.
    
    Args:
        location: The city and country (e.g., 'London, UK'). Use 'current' for the user's current location.
    """
    if location.lower() == "current":
        loc_info = get_location()
        if not loc_info:
            return "Error: Could not determine current location."
        weather_data = _fetch_weather_data(lat=loc_info["latitude"], lon=loc_info["longitude"])
        city = loc_info["city"]
        country = loc_info["country"]
    else:
        weather_data = _fetch_weather_data(address=location)
        city = weather_data.get("name", location) if weather_data else location
        country = weather_data.get("sys", {}).get("country", "") if weather_data else ""
        
    if not weather_data:
        return f"Error: Could not fetch weather for {location}."
        
    data = _extract_comprehensive_data(weather_data, "metric", city, country)
    return str(data)

@llm_tool
def search_web(query: str) -> str:
    """
    Search the internet for up-to-date information, news, or facts.
    Use this when the user asks a question about recent events or something outside your training data.
    
    Args:
        query: The search query to look up on the web.
    """
    # get_web_info returns a summarized string of the search results
    result = get_web_info(query, max_results=3, prints=False)
    return result

@llm_tool
def execute_terminal_command(command: str) -> str:
    """
    Execute a shell/terminal command on the user's local machine.
    WARNING: You MUST use this tool to compile code, run tests, or execute scripts.
    The user will be prompted for permission before execution.
    
    Args:
        command: The shell command to execute (e.g. 'python test.py', 'dir', 'pip install requests').
    """
    from assistant.core.event_bus import bus, EventType, permission_queue
    import queue
    
    # Drain any stale responses
    while not permission_queue.empty():
        try:
            permission_queue.get_nowait()
        except queue.Empty:
            break
            
    # Broadcast permission request to the UI
    bus.emit(EventType.PERMISSION_REQUEST, {
        "text": f"Action: Terminal Command Execution\nDetails: {command}"
    })
    
    # Wait indefinitely for user approval from UI
    # (This blocks the background LLM thread, which is fine)
    approved = permission_queue.get()
    
    if not approved:
        return "Command execution denied by the user. Do not attempt to run it again unless instructed."
        
    import subprocess
    # Use shell=True to support windows built-in commands like 'dir'
    result = subprocess.run(
        command, 
        shell=True, 
        capture_output=True, 
        text=True,
        timeout=60
    )
    
    output = result.stdout
    if result.stderr:
        output += f"\n[STDERR]: {result.stderr}"
        
    if not output.strip():
        output = "[Command executed successfully with no output]"
        
    return output

@llm_tool
def execute_code(language: str, code: str) -> str:
    """
    Executes a multi-line script on the user's local machine by saving it to a temporary file,
    running it, capturing the output, and then deleting the file.
    The user will be prompted for permission before execution.
    
    Args:
        language: The programming language of the code. Supported: 'python', 'javascript', 'node', 'batch', 'powershell', 'c', 'c++', 'cpp'.
        code: The complete code to execute.
    """
    language = language.lower()
    
    lang_config = {
        'python': { 'ext': '.py', 'cmd': ['python', '{src}'] },
        'javascript': { 'ext': '.js', 'cmd': ['node', '{src}'] },
        'node': { 'ext': '.js', 'cmd': ['node', '{src}'] },
        'batch': { 'ext': '.bat', 'cmd': ['cmd', '/c', '{src}'] },
        'powershell': { 'ext': '.ps1', 'cmd': ['powershell', '-ExecutionPolicy', 'Bypass', '-File', '{src}'] },
        'c': { 'ext': '.c', 'compile': ['gcc', '{src}', '-o', '{out}'], 'cmd': ['{out}'] },
        'c++': { 'ext': '.cpp', 'compile': ['g++', '{src}', '-o', '{out}'], 'cmd': ['{out}'] },
        'cpp': { 'ext': '.cpp', 'compile': ['g++', '{src}', '-o', '{out}'], 'cmd': ['{out}'] }
    }
    
    if language not in lang_config:
        return f"Error: Unsupported language '{language}'. Supported languages: {', '.join(lang_config.keys())}. Use execute_terminal_command if you need to run compilation commands directly."
        
    from assistant.core.event_bus import bus, EventType, permission_queue
    import queue
    
    # Drain any stale responses
    while not permission_queue.empty():
        try:
            permission_queue.get_nowait()
        except queue.Empty:
            break
            
    # Broadcast permission request to the UI
    bus.emit(EventType.PERMISSION_REQUEST, {
        "text": f"Action: Temporary {language.capitalize()} Script Execution\nDetails: The Coder Agent wants to execute a temporary {language} script:\n\n{code}"
    })
    
    approved = permission_queue.get()
    if not approved:
        return "Command execution denied by the user. Do not attempt to run it again unless instructed."
        
    import tempfile
    import os
    import subprocess
    
    config = lang_config[language]
    
    with tempfile.TemporaryDirectory() as temp_dir:
        src_file = os.path.join(temp_dir, f"script{config['ext']}")
        out_file = os.path.join(temp_dir, "script.exe" if os.name == 'nt' else "script.out")
        
        with open(src_file, 'w', encoding='utf-8') as f:
            f.write(code)
            
        # Compilation step (if required)
        if 'compile' in config:
            compile_cmd = [arg.format(src=src_file, out=out_file) for arg in config['compile']]
            compile_res = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=60, cwd=temp_dir)
            if compile_res.returncode != 0:
                return f"[COMPILATION ERROR]\n{compile_res.stderr}\n{compile_res.stdout}"
        
        # Execution step
        exec_cmd = [arg.format(src=src_file, out=out_file) for arg in config['cmd']]
        exec_res = subprocess.run(exec_cmd, capture_output=True, text=True, timeout=60, cwd=temp_dir)
        
        output = exec_res.stdout
        if exec_res.stderr:
            output += f"\n[STDERR]: {exec_res.stderr}"
            
        if not output.strip():
            output = "[Script executed successfully with no output]"
            
        return output

@llm_tool
def list_workspace_files(relative_dir: str = ".") -> str:
    """
    Lists the files in the workspace directory tree.
    Use this to understand the structure of the project before viewing or editing files.
    """
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    target_dir = os.path.normpath(os.path.join(project_root, relative_dir))
    
    # Security sandbox escape check
    if os.path.commonpath([project_root, target_dir]) != project_root:
        return "Error: Cannot escape the workspace directory."
        
    exclude_dirs = {'.venv', '.git', '__pycache__', '.planning', 'node_modules', '.pytest_cache', 'dist'}
    file_tree = []
    
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        rel_path = os.path.relpath(root, project_root)
        indent = "  " * (0 if rel_path == "." else rel_path.count(os.sep) + 1)
        folder_name = os.path.basename(root)
        if folder_name and folder_name != ".":
            file_tree.append(f"{indent}[DIR] {folder_name}/")
        
        file_indent = "  " * (1 if rel_path == "." else rel_path.count(os.sep) + 2)
        for f in files:
            file_tree.append(f"{file_indent}[FILE] {f}")
            
    return "\n".join(file_tree) if file_tree else "[Workspace is empty]"

@llm_tool
def view_workspace_file(file_path: str, start_line: int = 1, end_line: int = 200) -> str:
    """
    Read the contents of a specific file in the workspace.
    Supports reading specific line ranges to conserve context token limits.
    """
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.normpath(os.path.join(project_root, file_path))
    
    if os.path.commonpath([project_root, full_path]) != project_root:
        return "Error: Cannot escape the workspace directory."
        
    if not os.path.exists(full_path):
        return f"Error: File not found: {file_path}"
        
    from assistant.core.event_bus import bus, EventType, permission_queue
    import queue
    
    # Drain any stale responses
    while not permission_queue.empty():
        try:
            permission_queue.get_nowait()
        except queue.Empty:
            break
            
    # UI Security check
    bus.emit(EventType.PERMISSION_REQUEST, {
        "text": f"Action: View Project File\nDetails: The Agent wants to read file: {file_path} (Lines {start_line}-{end_line})"
    })
    
    approved = permission_queue.get()
    if not approved:
        return "Permission to read file denied by the user."
        
    with open(full_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    total_lines = len(lines)
    start_line = max(1, start_line)
    end_line = min(total_lines, end_line)
    
    subset = lines[start_line-1:end_line]
    numbered_lines = [f"{start_line + i}: {line}" for i, line in enumerate(subset)]
    
    return "".join(numbered_lines)

@llm_tool
def edit_workspace_file(file_path: str, search_content: str, replacement_content: str) -> str:
    """
    Edits a specific project file by replacing a block of search content with replacement content.
    The search content block must match exactly once in the file to guarantee safety.
    """
    import os
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    full_path = os.path.normpath(os.path.join(project_root, file_path))
    
    if os.path.commonpath([project_root, full_path]) != project_root:
        return "Error: Cannot escape the workspace directory."
        
    if not os.path.exists(full_path):
        return f"Error: File not found: {file_path}"
        
    from assistant.core.event_bus import bus, EventType, permission_queue
    import queue
    
    # Drain any stale responses
    while not permission_queue.empty():
        try:
            permission_queue.get_nowait()
        except queue.Empty:
            break
            
    # UI Security check
    bus.emit(EventType.PERMISSION_REQUEST, {
        "text": f"Action: Modify Project File\nDetails: The Agent wants to edit: {file_path}\n\nSearch Content:\n{search_content}\n\nReplacement:\n{replacement_content}"
    })
    
    approved = permission_queue.get()
    if not approved:
        return "Permission to write to file denied by the user."
        
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    occurrences = content.count(search_content)
    if occurrences == 0:
        return "Error: The search content was not found in the file. Make sure lines match exactly including leading whitespace."
    if occurrences > 1:
        return f"Error: Ambiguous edit. The search content matches {occurrences} times. Provide unique surrounding context."
        
    updated_content = content.replace(search_content, replacement_content, 1)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
        
    return "File updated successfully."

@llm_tool
def manage_reminders(action: str, target_time: str = None, message: str = None) -> str:
    """
    Manage alarms and reminders. 
    Args:
        action: 'set_alarm', 'set_reminder', 'list_alarms', 'list_reminders', 'cancel_alarms', 'cancel_reminders'.
        target_time: A string describing the time (e.g., 'in 15 minutes', 'at 5 pm', 'tomorrow at 9 am'). Required for setting.
        message: The message/label for the alarm/reminder.
    """
    if action == 'set_alarm':
        from assistant.automation.integrations.alarm_reminder import set_alarm, active_alarms
        initial_count = len(active_alarms)
        cmd = target_time
        if message:
            cmd += f" to {message}"
        set_alarm(cmd)
        if len(active_alarms) > initial_count:
            return f"Alarm successfully set for {target_time}."
        else:
            return f"Error: Could not understand the time format '{target_time}'. Please use natural language like 'in 15 minutes' or 'at 5 pm'."
    elif action == 'set_reminder':
        from assistant.automation.integrations.alarm_reminder import set_reminder, active_reminders
        initial_count = len(active_reminders)
        cmd = target_time
        if message:
            cmd += f" to {message}"
        set_reminder(cmd)
        if len(active_reminders) > initial_count:
            return f"Reminder successfully set for {target_time}."
        else:
            return f"Error: Could not understand the time format '{target_time}'. Please use natural language like 'in 15 minutes' or 'at 5 pm'."
    elif action == 'list_alarms':
        from assistant.automation.integrations.alarm_reminder import active_alarms
        return f"Active alarms: {active_alarms}"
    elif action == 'list_reminders':
        from assistant.automation.integrations.alarm_reminder import active_reminders
        return f"Active reminders: {active_reminders}"
    elif action == 'cancel_alarms':
        from assistant.automation.integrations.alarm_reminder import cancel_all_alarms
        cancel_all_alarms()
        return "All alarms cancelled."
    elif action == 'cancel_reminders':
        from assistant.automation.integrations.alarm_reminder import cancel_all_reminders
        cancel_all_reminders()
        return "All reminders cancelled."
    else:
        return "Error: Invalid action."

@llm_tool
def manage_memory(action: str, key: str = None, value: str = None) -> str:
    """
    Manage long-term memory to store and recall facts about the user.
    Args:
        action: 'save' to store a fact, 'recall' to retrieve all facts.
        key: A short identifier or timestamp. Required for 'save'.
        value: The information to remember. Required for 'save'.
    """
    from assistant.automation.integrations.task_schedule_automation import _load_remembered_info, _save_remembered_info
    import datetime
    data = _load_remembered_info()
    if action == 'save':
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data[f"{timestamp}_{key}"] = value
        _save_remembered_info(data)
        return "Information successfully saved to memory."
    elif action == 'recall':
        import json
        return json.dumps(data, indent=2) if data else "Memory is empty."
    else:
        return "Error: Invalid action."

@llm_tool
def youtube_controller(action: str, query: str = None) -> str:
    """
    Control YouTube playback and searches.
    Args:
        action: 'play', 'search', 'pause', 'resume', 'mute', 'unmute', 'next', 'previous', 'volume_up', 'volume_down'.
                Use 'play' to both search and immediately play a video. NEVER call 'search' and 'play' together.
        query: The search term or video name. Required for 'play' and 'search'.
    """
    import assistant.automation.integrations.youtube_automation as yt
    if action == 'play':
        yt.play_on_youtube(query)
        return f"Playing {query} on YouTube."
    elif action == 'search':
        yt.search_on_youtube(query)
        return f"Searching {query} on YouTube."
    else:
        action_map = {
            'pause': 'pause', 'resume': 'resume', 'mute': 'mute', 'unmute': 'unmute',
            'next': 'next video', 'previous': 'previous video', 
            'volume_up': 'volume increase', 'volume_down': 'volume decrease'
        }
        if action in action_map:
            yt.control_youtube_video(action_map[action])
            return f"Executed {action} on YouTube."
        else:
            return "Error: Invalid action."

@llm_tool
def email_assistant(action: str, recipient: str = None, subject: str = None, body: str = None) -> str:
    """
    Read unread emails or send a new email.
    Args:
        action: 'read_unread' or 'send'.
        recipient: Email address to send to. Required for 'send'.
        subject: Email subject. Required for 'send'.
        body: Email body content. Required for 'send'.
    """
    from assistant.automation.integrations.email_automation import get_gmail_service
    import base64
    from email.message import EmailMessage
    service = get_gmail_service()
    if not service:
        return "Error: Gmail is not configured or credentials not found."
        
    if action == 'read_unread':
        results = service.users().messages().list(userId='me', labelIds=['UNREAD', 'INBOX']).execute()
        messages = results.get('messages', [])
        if not messages:
            return "No unread emails."
        
        output = []
        count = min(5, len(messages))
        for i in range(count):
            msg = service.users().messages().get(userId='me', id=messages[i]['id'], format='metadata', metadataHeaders=['Subject', 'From']).execute()
            headers = msg['payload']['headers']
            subj = "No Subject"
            sender = "Unknown"
            for h in headers:
                if h['name'] == 'Subject':
                    subj = h['value']
                elif h['name'] == 'From':
                    sender = h['value']
            output.append(f"From: {sender}\nSubject: {subj}\n")
        return f"Total unread: {len(messages)}\n" + "\n".join(output)
        
    elif action == 'send':
        if not all([recipient, subject, body]):
            return "Error: recipient, subject, and body are required to send an email."
        message = EmailMessage()
        message.set_content(body)
        message['To'] = recipient
        message['From'] = 'me'
        message['Subject'] = subject
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={'raw': encoded_message}).execute()
        return "Email sent successfully."
    else:
        return "Error: Invalid action."

@llm_tool
def system_control(action: str) -> str:
    """
    Check system status or control the PC.
    Args:
        action: 'battery', 'cpu', 'memory', 'screenshot', 'volume_up', 'volume_down', 'mute'.
    """
    import psutil
    if action == 'battery':
        battery = psutil.sensors_battery()
        if battery:
            return f"Battery is at {battery.percent}%. Plugged in: {battery.power_plugged}."
        return "Battery information not available."
    elif action == 'cpu':
        return f"CPU Usage: {psutil.cpu_percent(interval=1)}%"
    elif action == 'memory':
        mem = psutil.virtual_memory()
        return f"Memory Usage: {mem.percent}% (Used: {mem.used // (1024**3)}GB, Total: {mem.total // (1024**3)}GB)"
    elif action == 'screenshot':
        import pyautogui
        import os
        import datetime
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filename = f"screenshot_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path = os.path.join(desktop, filename)
        pyautogui.screenshot(path)
        return f"Screenshot saved to {path}"
    elif action in ['volume_up', 'volume_down', 'mute']:
        import pyautogui
        if action == 'volume_up':
            pyautogui.press('volumeup', presses=5)
        elif action == 'volume_down':
            pyautogui.press('volumedown', presses=5)
        elif action == 'mute':
            pyautogui.press('volumemute')
        return f"Executed {action}."
    else:
        return "Error: Invalid action."

@llm_tool
def generate_image(prompt: str) -> str:
    """
    Generate an AI image based on a prompt and save it to the Desktop.
    Args:
        prompt: Description of the image to generate.
    """
    import os
    import shutil
    from assistant.automation.text_to_image.image_manager import generate_image as backend_generate_image
    
    path = backend_generate_image(prompt)
    if path and os.path.exists(path):
        desktop = os.path.join(os.path.expanduser("~"), "Desktop")
        filename = os.path.basename(path)
        dest_path = os.path.join(desktop, filename)
        shutil.copy2(path, dest_path)
        
        # This triggers the UI to show the image while speaking a brief confirmation
        from assistant.core.speak_selector import speak
        import assistant.core.mouth as mouth
        old_mute = mouth.mute_speak
        mouth.mute_speak = False
        try:
            speak("Image generated successfully.", image=f"/images/{filename}")
        finally:
            mouth.mute_speak = old_mute
        
        return f"Image successfully generated and saved to {dest_path}"
    else:
        return "Failed to generate image using available engines."

@llm_tool
def get_news_headlines(category: str = "general", country: str = "us") -> str:
    """
    Fetch the top news headlines using NewsAPI.
    Args:
        category: e.g., 'business', 'entertainment', 'general', 'health', 'science', 'sports', 'technology'.
        country: e.g., 'us', 'gb', 'in'.
    """
    import requests
    from assistant.core.config import config
    api_key = config.news_api_key
    if not api_key:
        return "Error: News API Key is missing in the configuration."
        
    url = f"https://newsapi.org/v2/top-headlines?country={country}&category={category}&apiKey={api_key}"
    response = requests.get(url, timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        articles = data.get("articles", [])
        if not articles:
            return f"No news headlines found for {category} in {country}."
            
        output = []
        for i, article in enumerate(articles[:5]):
            title = article.get("title", "No Title")
            source = article.get("source", {}).get("name", "Unknown Source")
            output.append(f"{i+1}. {title} ({source})")
        return "\\n".join(output)
    else:
        return f"Failed to fetch news. Status code: {response.status_code}"

@llm_tool
def get_current_location() -> str:
    """
    Get the user's current city and country based on GPS coordinates or IP.
    Use this tool when you need to know where the user is (e.g., for local weather forecasts or local news).
    """
    from assistant.automation.integrations.check_weather import get_location, _fetch_weather_data
    loc_info = get_location()
    if not loc_info:
        return "Error: Could not determine current location."
        
    city = loc_info.get("city")
    country = loc_info.get("country")
    
    # If city or country is missing (e.g. native Windows location coordinates only), 
    # reverse geocode using the OpenWeatherMap API
    if not city or not country:
        try:
            weather_data = _fetch_weather_data(lat=loc_info["latitude"], lon=loc_info["longitude"])
            if weather_data:
                if not city:
                    city = weather_data.get("name", "")
                if not country:
                    country = weather_data.get("sys", {}).get("country", "")
        except Exception:
            pass
            
    if not city:
        city = "Unknown City"
    if not country:
        country = "Unknown Country"
        
    return f"User's current location is {city}, {country}."

# List of tools to pass to the LLM
AVAILABLE_TOOLS = [
    get_weather, search_web, execute_terminal_command, execute_code, 
    list_workspace_files, view_workspace_file, edit_workspace_file,
    manage_reminders, manage_memory, youtube_controller, email_assistant,
    system_control, generate_image, get_news_headlines, get_current_location
]
