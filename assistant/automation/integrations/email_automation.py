import os
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
from email.message import EmailMessage

from assistant.core.registry import on_regex, on_fuzzy
from assistant.core.speak_selector import speak

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify', 'https://www.googleapis.com/auth/gmail.send']

CREDS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "data", "credentials")
os.makedirs(CREDS_DIR, exist_ok=True)
TOKEN_PATH = os.path.join(CREDS_DIR, 'token.json')
CREDS_PATH = os.path.join(CREDS_DIR, 'credentials.json')

def get_gmail_service():
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
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

@on_fuzzy(["check my email", "do i have new emails", "read my inbox", "any new emails", "read emails", "check emails", "check inbox", "show my emails"], score_cutoff=85)
def check_email(text):
    service = get_gmail_service()
    if not service:
        speak("Gmail is not configured. Please follow the setup guide to link your account.")
        return
        
    try:
        # Request a list of all unread messages
        results = service.users().messages().list(userId='me', labelIds=['UNREAD', 'INBOX']).execute()
        messages = results.get('messages', [])

        if not messages:
            speak("You have no new unread emails.")
            return
            
        speak(f"You have {len(messages)} unread emails.")
        if len(messages) > 0:
            speak("Here are the subjects of the most recent ones:")
            count = min(3, len(messages))
            for i in range(count):
                msg = service.users().messages().get(userId='me', id=messages[i]['id'], format='metadata', metadataHeaders=['Subject', 'From']).execute()
                headers = msg['payload']['headers']
                subject = "No Subject"
                sender = "Unknown"
                for h in headers:
                    if h['name'] == 'Subject':
                        subject = h['value']
                    elif h['name'] == 'From':
                        sender = h['value'].split('<')[0].strip()
                speak(f"From {sender}: {subject}")
                
    except Exception as e:
        print(f"Error checking email: {e}")
        speak("I ran into an issue while checking your inbox.")

@on_regex(r".*(?:send|write|compose|draft).*(?:an\s+)?email\s+(?:to\s+)?(.*?)\s+(?:about|on|regarding)\s+(.*)", priority=5)
def send_email(recipient, subject):
    recipient = recipient.strip()
    subject = subject.strip()
    
    if "@" not in recipient:
        speak(f"I need a full email address to send it to {recipient}. I am unable to do this right now without a contact list.")
        return
        
    service = get_gmail_service()
    if not service:
        speak("Gmail is not configured. Please see the setup guide.")
        return
        
    speak("I have opened a text editor for you. Please type or paste your email body, save the file, and close the window when you are ready to send.")
    
    import tempfile
    import subprocess
    
    with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", delete=False) as tf:
        tf_name = tf.name
        
    # Open notepad and wait for user to close it
    subprocess.call(['notepad.exe', tf_name])
    
    with open(tf_name, 'r') as f:
        body = f.read().strip()
        
    import os
    try:
        os.unlink(tf_name)
    except Exception:
        pass
    
    if not body:
        speak("The email body was empty. Email cancelled.")
        return
        
    speak("Generating a smart subject line and sending your email...")
    
    # Generate a smart subject line using the LLM based on the actual body
    from assistant.core.config import config
    api_key = config.groq_api_key
    if api_key:
        try:
            import requests
            prompt = f"Generate a short, professional email subject line for an email with this body: '{body}'. The user originally described the topic as: '{subject}'. Output ONLY the subject line without any quotes, labels, or extra text."
            
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.3-70b-versatile",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 50
            }
            
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                gen_subject = result['choices'][0]['message']['content']
                if gen_subject:
                    subject = gen_subject.strip().strip('"').strip("'")
        except Exception as e:
            print(f"Failed to generate smart subject via Groq: {e}")
            pass
        
    message = EmailMessage()
    message.set_content(body)
    message['To'] = recipient
    message['From'] = 'me'
    message['Subject'] = subject

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    create_message = {'raw': encoded_message}
    
    try:
        service.users().messages().send(userId="me", body=create_message).execute()
        speak("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        speak("I couldn't send the email due to a network or authentication error.")
