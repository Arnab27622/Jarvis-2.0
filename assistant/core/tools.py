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

# List of tools to pass to the LLM
AVAILABLE_TOOLS = [get_weather, search_web, execute_terminal_command, execute_code]
