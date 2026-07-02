import asyncio
import datetime
import threading
from typing import Set
from assistant.core.logger import get_logger
from assistant.core.speak_selector import speak
from google.auth.exceptions import RefreshError
import os

logger = get_logger("Proactive")

class ProactiveManager:
    def __init__(self, interval_seconds: int = 120):
        self.interval = interval_seconds
        self._running = False
        self._task = None
        self._notified_events: Set[str] = set()
        self._notified_emails: Set[str] = set()
        self._loop = None
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_thread, daemon=True)
        self._thread.start()
        logger.info("Proactive Background Manager started.")

    def _run_thread(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._task = self._loop.create_task(self._main_loop())
        try:
            self._loop.run_until_complete(self._task)
        except asyncio.CancelledError:
            pass
        finally:
            self._loop.close()

    def stop(self):
        self._running = False
        if self._loop and self._task:
            self._loop.call_soon_threadsafe(self._task.cancel)
            
    async def _main_loop(self):
        # Give the system time to boot fully before starting proactive polling
        await asyncio.sleep(10)
        
        while self._running:
            try:
                await self._check_calendar()
                await self._check_email()
            except Exception as e:
                logger.error(f"Error in proactive loop: {e}")
                
            await asyncio.sleep(self.interval)
            
    async def _check_calendar(self):
        # We need to run synchronous google api calls in a thread
        await asyncio.to_thread(self._sync_check_calendar)
        
    def _sync_check_calendar(self):
        from assistant.automation.integrations.calendar_automation import get_calendar_service, TOKEN_PATH
        try:
            service = get_calendar_service()
        except RefreshError:
            if os.path.exists(TOKEN_PATH):
                os.remove(TOKEN_PATH)
            speak("Sir, your calendar token has expired. I have opened the browser to re-authenticate.")
            service = get_calendar_service()
            
        if not service:
            return
        
        try:
            now = datetime.datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            # Look ahead exactly 15 minutes
            time_max = (now + datetime.timedelta(minutes=15)).isoformat() + 'Z'
            
            events_result = service.events().list(calendarId='primary', timeMin=time_min, timeMax=time_max,
                                                  maxResults=5, singleEvents=True,
                                                  orderBy='startTime').execute()
            events = events_result.get('items', [])
            
            for event in events:
                event_id = event.get('id')
                if event_id in self._notified_events:
                    continue
                    
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                if 'T' in start_str:
                    # Parse the start time
                    dt_start = datetime.datetime.fromisoformat(start_str.replace('Z', '+00:00'))
                    
                    # Convert 'now' to an aware datetime in UTC for comparison
                    now_utc = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc)
                    
                    dt_local = dt_start.astimezone()
                    time_str = dt_local.strftime("%I:%M %p").lstrip("0")
                    summary = event.get('summary', 'Untitled Event')
                    
                    # Change tense depending on if the event already started
                    if dt_start < now_utc:
                        msg = f"Sir, I'd like to remind you that you had an event: {summary} that started at {time_str}."
                    else:
                        msg = f"Sir, I'd like to remind you that you have an upcoming event: {summary} starting at {time_str}."
                        
                    speak(msg)
                    self._notified_events.add(event_id)
        except Exception as e:
            logger.error(f"Proactive calendar check failed: {e}")

    async def _check_email(self):
        await asyncio.to_thread(self._sync_check_email)
        
    def _sync_check_email(self):
        from assistant.automation.integrations.email_automation import get_gmail_service, TOKEN_PATH
        try:
            service = get_gmail_service()
        except RefreshError:
            if os.path.exists(TOKEN_PATH):
                os.remove(TOKEN_PATH)
            speak("Sir, your email token has expired. I have opened the browser to re-authenticate.")
            service = get_gmail_service()
            
        if not service:
            return
        
        try:
            results = service.users().messages().list(userId='me', labelIds=['UNREAD', 'INBOX', 'IMPORTANT']).execute()
            messages = results.get('messages', [])
            
            for msg_item in messages:
                msg_id = msg_item['id']
                if msg_id in self._notified_emails:
                    continue
                    
                msg = service.users().messages().get(userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From']).execute()
                headers = msg['payload']['headers']
                subject = "No Subject"
                sender = "Unknown"
                for h in headers:
                    if h['name'] == 'Subject':
                        subject = h['value']
                    elif h['name'] == 'From':
                        sender = h['value'].split('<')[0].strip()
                        
                # Only announce if we haven't seen it yet
                speak_msg = f"Sir, you have just received an important email from {sender} regarding {subject}."
                speak(speak_msg)
                self._notified_emails.add(msg_id)
                # Just notify for one to avoid spamming multiple emails at once
                break
                
        except Exception as e:
            logger.error(f"Proactive email check failed: {e}")

proactive_manager = ProactiveManager(interval_seconds=120)
