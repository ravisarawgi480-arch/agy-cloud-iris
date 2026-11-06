import os
import sys
import json
import imaplib
import email
from email.header import decode_header
import time
import urllib.parse
import urllib.request
import ssl

sys.stdout.reconfigure(encoding='utf-8')

# Platform-agnostic relative paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "email_config.json")
TELEGRAM_CONFIG_PATH = os.path.join(BASE_DIR, "telegram_config.json")
PROCESSED_PATH = os.path.join(BASE_DIR, "processed_school_emails.json")

def load_processed_ids():
    if os.path.exists(PROCESSED_PATH):
        try:
            with open(PROCESSED_PATH, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_processed_ids(ids_set):
    with open(PROCESSED_PATH, "w", encoding="utf-8") as f:
        json.dump(list(ids_set), f, indent=2)

def decode_mime_words(s):
    if not s:
        return ""
    decoded_fragments = decode_header(s)
    parts = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            if encoding:
                try:
                    parts.append(fragment.decode(encoding, errors="replace"))
                except LookupError:
                    parts.append(fragment.decode("utf-8", errors="replace"))
            else:
                parts.append(fragment.decode("utf-8", errors="replace"))
        else:
            parts.append(str(fragment))
    return "".join(parts)

def detect_ward_tag(subject, body, from_addr):
    text = f"{subject} {body} {from_addr}".lower()
    if any(k in text for k in ["aarav", "4085", "cirs", "chinmaya"]):
        return "👦 *WARD: AARAV (CIRS • ID: 4085)*"
    elif any(k in text for k in ["avni", "10275", "skv", "scindia"]):
        return "👧 *WARD: AVNI (SKV • ID: 10275)*"
    return "🏫 *SCHOOL NOTIFICATION (GENERAL)*"

def fetch_new_school_emails(email_user, app_password, processed_ids, target_label="School"):
    new_alerts = []
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(email_user, app_password)

    try:
        status, _ = mail.select(f'"{target_label}"')
    except Exception:
        status, _ = mail.select("INBOX")

    status, messages = mail.search(None, 'ALL')
    if status != "OK" or not messages[0]:
        mail.logout()
        return []

    msg_ids = messages[0].split()

    for msg_id in reversed(msg_ids[-10:]):
        id_str = msg_id.decode()
        if id_str in processed_ids:
            continue

        res, msg_data = mail.fetch(msg_id, "(RFC822)")
        if res != "OK":
            continue

        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email)

        subject = decode_mime_words(msg.get("Subject", ""))
        from_addr = decode_mime_words(msg.get("From", ""))
        to_addr = decode_mime_words(msg.get("To", ""))
        date_str = msg.get("Date", "")

        body_text = ""
        attachment_files = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                filename = part.get_filename()

                if filename:
                    dec_filename = decode_mime_words(filename)
                    file_data = part.get_payload(decode=True)
                    if file_data and len(file_data) < 15 * 1024 * 1024: # max 15MB
                        attachment_files.append((dec_filename, file_data))
                elif content_type == "text/plain" and "attachment" not in content_disposition:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text += payload.decode("utf-8", errors="replace") + "\n"
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body_text = payload.decode("utf-8", errors="replace")

        clean_body = " ".join(body_text.split())
        summary = clean_body[:350] + ("..." if len(clean_body) > 350 else "")
        ward_tag = detect_ward_tag(subject, clean_body, from_addr)

        new_alerts.append({
            "id": id_str,
            "ward_tag": ward_tag,
            "from": from_addr,
            "to": to_addr or email_user,
            "subject": subject,
            "date": date_str,
            "summary": summary,
            "attachments": [f[0] for f in attachment_files],
            "attachment_data": attachment_files
        })

    mail.logout()
    return new_alerts

def format_alert(alert):
    att_str = ", ".join(alert["attachments"]) if alert["attachments"] else "None"
    msg = (
        f"{alert['ward_tag']}\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *From:* {alert['from']}\n"
        f"📝 *Sub:* {alert['subject']}\n"
        f"📎 *Attachments:* {att_str}\n\n"
        f"📄 *Summary:*\n{alert['summary']}\n"
        f"━━━━━━━━━━━━━━━━━━━"
    )
    return msg

def dispatch_telegram(alert_text):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if (not token or not chat_id) and os.path.exists(TELEGRAM_CONFIG_PATH):
        try:
            with open(TELEGRAM_CONFIG_PATH, "r", encoding="utf-8") as f:
                tg = json.load(f)
            token = token or tg.get("bot_token")
            chat_id = chat_id or tg.get("chat_id")
        except Exception:
            pass

    if not token or not chat_id:
        return False

    try:
        ctx = ssl._create_unverified_context()
        params = urllib.parse.urlencode({'chat_id': chat_id, 'text': alert_text, 'parse_mode': 'Markdown'}).encode('utf-8')
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=params)
        urllib.request.urlopen(req, context=ctx, timeout=10)
        print("Telegram alert delivered successfully!", flush=True)
        return True
    except Exception as e:
        print(f"Telegram dispatch error: {e}", flush=True)
        return False

def dispatch_telegram_document(filename, file_bytes, caption=""):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if (not token or not chat_id) and os.path.exists(TELEGRAM_CONFIG_PATH):
        try:
            with open(TELEGRAM_CONFIG_PATH, "r", encoding="utf-8") as f:
                tg = json.load(f)
            token = token or tg.get("bot_token")
            chat_id = chat_id or tg.get("chat_id")
        except Exception:
            pass

    if not token or not chat_id:
        return False

    boundary = '----AGYBoundary8947219482104'
    body = bytearray()
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'.encode('utf-8'))
    if caption:
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="caption"\r\n\r\n{caption}\r\n'.encode('utf-8'))
    body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="document"; filename="{filename}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode('utf-8'))
    body.extend(file_bytes)
    body.extend(f'\r\n--{boundary}--\r\n'.encode('utf-8'))

    try:
        ctx = ssl._create_unverified_context()
        url = f"https://api.telegram.org/bot{token}/sendDocument"
        req = urllib.request.Request(url, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        urllib.request.urlopen(req, context=ctx, timeout=25)
        print(f"Delivered attachment: {filename}", flush=True)
        return True
    except Exception as e:
        print(f"Document dispatch error for {filename}: {e}", flush=True)
        return False

def run_sync_cycle():
    user = os.environ.get("GMAIL_USER")
    pwd = os.environ.get("GMAIL_APP_PASSWORD")
    if (not user or not pwd) and os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            user = user or config.get("email")
            pwd = pwd or config.get("app_password")
        except Exception:
            pass

    if not user or not pwd:
        print("Credentials not found in environment or config file.", flush=True)
        return

    processed = load_processed_ids()
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Cloud Scanner checking Gmail 'School' label for {user}...", flush=True)

    try:
        new_emails = fetch_new_school_emails(user, pwd, processed)
    except Exception as e:
        print(f"[WATCHDOG] Gmail check exception: {e}", flush=True)
        # Autonomous Watchdog Alert
        dispatch_telegram(f"⚠️ *[AUTONOMOUS CLOUD WATCHDOG]*\nGmail scan encountered a network issue: `{e}`\nSystem is self-healing and will retry automatically.")
        return

    if not new_emails:
        print("No new emails in 'School' label.", flush=True)
        return

    print(f"Found {len(new_emails)} new emails! Sending to Telegram...", flush=True)
    for alert in new_emails:
        msg = format_alert(alert)
        dispatch_telegram(msg)

        # Dispatch any actual PDF or document attachments
        for fname, fbytes in alert.get("attachment_data", []):
            dispatch_telegram_document(fname, fbytes, caption=f"📎 Attachment for: {alert['subject']}")

        processed.add(alert["id"])
        save_processed_ids(processed)
        print(f"Alert dispatched: {alert['subject']}", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    run_sync_cycle()
