"""
LLM Tools Module

Provides functions that the LLM can natively call using Function Calling.
These functions wrap the existing automation scripts so the LLM can use them seamlessly.
"""

from assistant.automation.integrations.check_weather import _fetch_weather_data, _extract_comprehensive_data, get_location
from assistant.automation.integrations.detailed_web_search import get_web_info
from assistant.core.logger import get_logger

logger = get_logger("LLMTools")

def get_weather(location: str = "current") -> str:
    """
    Get the current weather conditions for a specific location.
    
    Args:
        location: The city and country (e.g., 'London, UK'). Use 'current' for the user's current location.
    """
    logger.info(f"LLM called tool: get_weather(location={location})")
    try:
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
    except Exception as e:
        logger.error(f"Error in get_weather tool: {e}")
        return f"Error fetching weather: {str(e)}"

def search_web(query: str) -> str:
    """
    Search the internet for up-to-date information, news, or facts.
    Use this when the user asks a question about recent events or something outside your training data.
    
    Args:
        query: The search query to look up on the web.
    """
    logger.info(f"LLM called tool: search_web(query={query})")
    try:
        # get_web_info returns a summarized string of the search results
        result = get_web_info(query, max_results=3, prints=False)
        return result
    except Exception as e:
        logger.error(f"Error in search_web tool: {e}")
        return f"Error searching the web: {str(e)}"

def execute_terminal_command(command: str) -> str:
    """
    Execute a shell/terminal command on the user's local machine.
    WARNING: You MUST use this tool to compile code, run tests, or execute scripts.
    The user will be prompted for permission before execution.
    
    Args:
        command: The shell command to execute (e.g. 'python test.py', 'dir', 'pip install requests').
    """
    logger.info(f"LLM requesting terminal access for command: {command}")
    try:
        from assistant.core.event_bus import bus, EventType, permission_queue
        
        # Broadcast permission request to the UI
        bus.emit(EventType.PERMISSION_REQUEST, {
            "action": "Terminal Command Execution",
            "details": command
        })
        
        # Wait indefinitely for user approval from UI
        # (This blocks the background LLM thread, which is fine)
        approved = permission_queue.get()
        
        if not approved:
            logger.info("Terminal access denied by user.")
            return "Command execution denied by the user. Do not attempt to run it again unless instructed."
            
        logger.info("Terminal access approved. Executing...")
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
        
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 60 seconds."
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        return f"Error executing command: {str(e)}"

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
    logger.info(f"LLM requesting to execute {language} code via temporary directory.")
    
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
        
    try:
        from assistant.core.event_bus import bus, EventType, permission_queue
        
        # Broadcast permission request to the UI
        bus.emit(EventType.PERMISSION_REQUEST, {
            "action": f"Temporary {language.capitalize()} Script Execution",
            "details": f"The Coder Agent wants to execute a temporary {language} script:\n\n{code[:300]}{'...' if len(code) > 300 else ''}"
        })
        
        approved = permission_queue.get()
        if not approved:
            logger.info(f"{language} script execution denied by user.")
            return "Command execution denied by the user. Do not attempt to run it again unless instructed."
            
        logger.info(f"{language} script execution approved. Running...")
        
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
                
    except subprocess.TimeoutExpired:
        return "Error: Script timed out after 60 seconds."
    except Exception as e:
        logger.error(f"Error executing script: {e}")
        return f"Error executing script: {str(e)}"

def list_workspace_files(relative_dir: str = ".") -> str:
    """
    Lists the files in the workspace directory tree.
    Use this to understand the structure of the project before viewing or editing files.
    """
    logger.info(f"LLM called tool: list_workspace_files(relative_dir={relative_dir})")
    try:
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        target_dir = os.path.normpath(os.path.join(project_root, relative_dir))
        
        # Security sandbox escape check
        if not target_dir.startswith(project_root):
            return "Error: Cannot escape the workspace directory."
            
        exclude_dirs = {'.venv', '.git', '__pycache__', '.planning', 'node_modules', '.pytest_cache', 'dist'}
        file_tree = []
        
        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            rel_path = os.path.relpath(root, project_root)
            indent = "  " * (0 if rel_path == "." else rel_path.count(os.sep) + 1)
            folder_name = os.path.basename(root)
            if folder_name and folder_name != ".":
                file_tree.append(f"{indent}📁 {folder_name}/")
            
            file_indent = "  " * (1 if rel_path == "." else rel_path.count(os.sep) + 2)
            for f in files:
                file_tree.append(f"{file_indent}📄 {f}")
                
        return "\n".join(file_tree) if file_tree else "[Workspace is empty]"
    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return f"Error listing files: {str(e)}"

def view_workspace_file(file_path: str, start_line: int = 1, end_line: int = 200) -> str:
    """
    Read the contents of a specific file in the workspace.
    Supports reading specific line ranges to conserve context token limits.
    """
    logger.info(f"LLM called tool: view_workspace_file(file_path={file_path})")
    try:
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        full_path = os.path.normpath(os.path.join(project_root, file_path))
        
        if not full_path.startswith(project_root):
            return "Error: Cannot escape the workspace directory."
            
        if not os.path.exists(full_path):
            return f"Error: File not found: {file_path}"
            
        from assistant.core.event_bus import bus, EventType, permission_queue
        
        # UI Security check
        bus.emit(EventType.PERMISSION_REQUEST, {
            "action": "View Project File",
            "details": f"The Agent wants to read file: {file_path} (Lines {start_line}-{end_line})"
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
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return f"Error viewing file: {str(e)}"

def edit_workspace_file(file_path: str, search_content: str, replacement_content: str) -> str:
    """
    Edits a specific project file by replacing a block of search content with replacement content.
    The search content block must match exactly once in the file to guarantee safety.
    """
    logger.info(f"LLM called tool: edit_workspace_file(file_path={file_path})")
    try:
        import os
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        full_path = os.path.normpath(os.path.join(project_root, file_path))
        
        if not full_path.startswith(project_root):
            return "Error: Cannot escape the workspace directory."
            
        if not os.path.exists(full_path):
            return f"Error: File not found: {file_path}"
            
        from assistant.core.event_bus import bus, EventType, permission_queue
        
        # UI Security check
        bus.emit(EventType.PERMISSION_REQUEST, {
            "action": "Modify Project File",
            "details": f"The Agent wants to edit: {file_path}\n\nSearch Content:\n{search_content}\n\nReplacement:\n{replacement_content}"
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
    except Exception as e:
        logger.error(f"Error editing file: {e}")
        return f"Error editing file: {str(e)}"

# List of tools to pass to the LLM
AVAILABLE_TOOLS = [get_weather, search_web, execute_terminal_command, execute_code, list_workspace_files, view_workspace_file, edit_workspace_file]
