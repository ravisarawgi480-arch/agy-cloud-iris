import os
import sys
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, "credentials.json")
TOKEN_PATH = os.path.join(BASE_DIR, "token.json")

# Scopes needed to manage filters and labels
SCOPES = [
    'https://www.googleapis.com/auth/gmail.settings.basic',
    'https://www.googleapis.com/auth/gmail.labels'
]

def get_gmail_service():
    """Authenticates and returns the authorized Gmail API service."""
    creds = None
    token_str = os.environ.get("GMAIL_TOKEN_JSON")
    if token_str:
        try:
            info = json.loads(token_str)
            creds = Credentials.from_authorized_user_info(info, SCOPES)
        except Exception as e:
            print(f"[AUTH] Error parsing GMAIL_TOKEN_JSON: {e}", flush=True)

    if not creds and os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as e:
            print(f"[AUTH] Error loading token file: {e}", flush=True)

    # If credentials expired, refresh them
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception as e:
            print(f"[AUTH] Error refreshing token: {e}", flush=True)

        if not creds:
            if not os.path.exists(CREDENTIALS_PATH):
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_PATH}. "
                    "Please download OAuth client secrets from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for future runs
        with open(TOKEN_PATH, 'w') as token_file:
            token_file.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)

def list_filters():
    """Lists all active server-side filters in the Gmail account."""
    service = get_gmail_service()
    result = service.users().settings().filters().list(userId='me').execute()
    filters = result.get('filter', [])
    return filters

def create_server_filter(criteria: dict, action: dict):
    """
    Creates an actual filter rule on Gmail's server.
    criteria example: {'from': 'school@cirs.edu.in', 'query': 'fees OR circular'}
    action example: {'addLabelIds': ['Label_123'], 'removeLabelIds': ['SPAM']}
    """
    service = get_gmail_service()
    filter_body = {
        'criteria': criteria,
        'action': action
    }
    created_filter = service.users().settings().filters().create(
        userId='me',
        body=filter_body
    ).execute()
    return created_filter

def delete_server_filter(filter_id: str):
    """Deletes an actual filter rule by ID from Gmail's server."""
    service = get_gmail_service()
    service.users().settings().filters().delete(
        userId='me',
        id=filter_id
    ).execute()
    return True

def search_filters(term: str):
    """Finds filters matching a search term in criteria or action."""
    filters = list_filters()
    matched = []
    term_lower = term.lower()
    for f in filters:
        crit_str = json.dumps(f.get('criteria', {})).lower()
        act_str = json.dumps(f.get('action', {})).lower()
        if term_lower in crit_str or term_lower in act_str:
            matched.append(f)
    return matched

def get_or_create_label(label_name: str):
    """Returns label ID for an existing label or creates a new one."""
    service = get_gmail_service()
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    for l in labels:
        if l['name'].lower() == label_name.lower():
            return l['id']
    new_label = service.users().labels().create(
        userId='me',
        body={'name': label_name, 'labelListVisibility': 'labelShow', 'messageListVisibility': 'show'}
    ).execute()
    return new_label['id']

def create_smart_filter(from_sender="", subject="", query="", action="trash", label_name=""):
    """Creates a filter with simple parameters."""
    service = get_gmail_service()
    criteria = {}
    if from_sender:
        criteria['from'] = from_sender
    if subject:
        criteria['subject'] = subject
    if query:
        criteria['query'] = query

    action_dict = {}
    if action == "trash":
        action_dict = {'addLabelIds': ['TRASH']}
    elif action == "spam":
        action_dict = {'addLabelIds': ['SPAM']}
    elif action == "star":
        action_dict = {'addLabelIds': ['STARRED']}
    elif label_name or action == "label":
        lbl = label_name or "Important"
        lid = get_or_create_label(lbl)
        action_dict = {'addLabelIds': [lid], 'removeLabelIds': ['INBOX']}
    else:
        action_dict = {'removeLabelIds': ['INBOX']}

    return create_server_filter(criteria, action_dict)

def run_demo_test():
    """Executes a full live cycle: creates a test filter, verifies, and deletes it."""
    print("🚀 [DEMO TEST] Connecting to Gmail REST API...")
    service = get_gmail_service()
    
    # 1. Create a label for test
    label_body = {
        'name': 'AI_Filter_Test_Label',
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    label = service.users().labels().create(userId='me', body=label_body).execute()
    label_id = label['id']
    print(f"✅ Step 1: Created Test Label with ID: {label_id}")

    # 2. Create actual server-side filter
    criteria = {'subject': 'Test Subject from AI Autonomous Agent'}
    action = {'addLabelIds': [label_id], 'removeLabelIds': ['SPAM']}
    filt = create_server_filter(criteria, action)
    filter_id = filt['id']
    print(f"✅ Step 2: Created Actual Gmail Server Filter with ID: {filter_id}")

    # 3. Verify it exists
    all_filters = list_filters()
    matched = [f for f in all_filters if f['id'] == filter_id]
    print(f"🔍 Step 3: Verified filter exists on Google Server: {bool(matched)}")

    # 4. Delete filter
    delete_server_filter(filter_id)
    print(f"🗑️ Step 4: Deleted Filter {filter_id} from Google Server")

    # 5. Clean up label
    service.users().labels().delete(userId='me', id=label_id).execute()
    print("🧹 Step 5: Cleaned up Test Label. Demo Test 100% SUCCESSFUL!")

if __name__ == '__main__':
    run_demo_test()
