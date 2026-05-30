import os
import os.path
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from assistant.core.registry import on_regex, on_fuzzy
from assistant.core.speak_selector import speak

# If modifying these scopes, delete the file calendar_token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

CREDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "data", "credentials")
os.makedirs(CREDS_DIR, exist_ok=True)
TOKEN_PATH = os.path.join(CREDS_DIR, 'calendar_token.json')
CREDS_PATH = os.path.join(CREDS_DIR, 'credentials.json')

def get_calendar_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDS_PATH):
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        return service
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

@on_fuzzy(["what's on my schedule", "check my calendar", "do i have any meetings", "what is on my calendar", "read my calendar", "any events today", "what's my schedule", "upcoming events", "upcoming meetings"], score_cutoff=85)
def check_calendar(text):
    service = get_calendar_service()
    if not service:
        speak("Google Calendar is not configured. Please check the setup guide.")
        return
        
    speak("Checking your calendar for upcoming events...")
    
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z' 
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=5, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            speak("You have no upcoming events on your schedule.")
            return

        speak(f"You have {len(events)} upcoming events.")
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            
            if 'T' in start:
                dt = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                dt_local = dt.astimezone()
                time_str = dt_local.strftime("%I:%M %p on %b %d")
            else:
                time_str = f"All day on {start}"
                
            summary = event.get('summary', 'Untitled Event')
            speak(f"{summary} at {time_str}")
            
    except Exception as e:
        print(f"Error checking calendar: {e}")
        speak("I ran into an issue while reading your calendar.")

@on_regex(r".*(?:schedule|add|create|book|set up).*(?:a\s+)?(?:meeting|event|appointment).*(?:about|for|regarding)\s+(.*)", priority=5)
def add_calendar_event(topic):
    topic = topic.strip()
    
    service = get_calendar_service()
    if not service:
        speak("Google Calendar is not configured. Please see the setup guide.")
        return
        
    speak("I am opening a text editor. Please type the date and time for the event, for example: 'tomorrow at 3 PM' or 'October 5th at 10 AM', save, and close.")
    
    import tempfile
    import subprocess
    
    with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as tf:
        tf_name = tf.name
        
    subprocess.call(['notepad.exe', tf_name])
    
    with open(tf_name, 'r') as f:
        time_text = f.read().strip()
        
    try:
        os.unlink(tf_name)
    except Exception:
        pass
    
    if not time_text:
        speak("No time was provided. Event cancelled.")
        return
        
    speak(f"I am parsing the time and scheduling {topic}.")
    
    from assistant.core.llm_manager import manager
    if manager and manager.gemini_client:
        try:
            now = datetime.datetime.now().astimezone().isoformat()
            prompt = f"Given the current local time is {now}, convert this natural language time '{time_text}' into a strict ISO 8601 datetime format WITH timezone offset (e.g., YYYY-MM-DDTHH:MM:SS+05:30). Output ONLY the ISO string, nothing else."
            
            response = manager.gemini_client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt
            )
            
            if response.text:
                iso_time = response.text.strip().strip('"').strip("'")
                
                dt_start = datetime.datetime.fromisoformat(iso_time)
                dt_end = dt_start + datetime.timedelta(hours=1)
                
                event = {
                  'summary': topic,
                  'start': {
                    'dateTime': dt_start.isoformat(),
                  },
                  'end': {
                    'dateTime': dt_end.isoformat(),
                  },
                }
                
                service.events().insert(calendarId='primary', body=event).execute()
                speak("The event has been successfully added to your calendar.")
                return
        except Exception as e:
            print(f"Failed to parse time with LLM: {e}")
            
    speak("I couldn't understand the time format or failed to reach the server. The event was not scheduled.")

@on_regex(r".*(?:cancel|delete|remove).*(?:a\s+)?(?:meeting|event|appointment).*(?:about|for|regarding)\s+(.*)", priority=5)
def delete_calendar_event(topic):
    topic = topic.strip().lower()
    
    service = get_calendar_service()
    if not service:
        speak("Google Calendar is not configured.")
        return
        
    speak(f"Looking for an event about {topic} to cancel...")
    
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z' 
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                              maxResults=10, singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        matches = [e for e in events if topic in e.get('summary', '').lower()]
        
        if not matches:
            speak(f"I couldn't find any upcoming events about {topic}.")
            return
            
        event_to_delete = matches[0]
        summary = event_to_delete.get('summary', 'Untitled')
        
        service.events().delete(calendarId='primary', eventId=event_to_delete['id']).execute()
        speak(f"I have successfully cancelled the event: {summary}.")
        
    except Exception as e:
        print(f"Error deleting event: {e}")
        speak("I ran into an issue while trying to cancel the event.")
