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
        attachments = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                filename = part.get_filename()

                if filename:
                    attachments.append(decode_mime_words(filename))
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

        new_alerts.append({
            "id": id_str,
            "from": from_addr,
            "to": to_addr or email_user,
            "subject": subject,
            "date": date_str,
            "summary": summary,
            "attachments": attachments
        })

    mail.logout()
    return new_alerts

def format_alert(alert):
    att_str = ", ".join(alert["attachments"]) if alert["attachments"] else "None"
    msg = (
        f"🏫 *NEW SCHOOL ALERT (Label: School)*\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *From:* {alert['from']}\n"
        f"📥 *To:* {alert['to']}\n"
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

    new_emails = fetch_new_school_emails(user, pwd, processed)
    if not new_emails:
        print("No new emails in 'School' label.", flush=True)
        return

    print(f"Found {len(new_emails)} new emails! Sending to Telegram...", flush=True)
    for alert in new_emails:
        msg = format_alert(alert)
        dispatch_telegram(msg)
        processed.add(alert["id"])
        save_processed_ids(processed)
        print(f"Alert dispatched: {alert['subject']}", flush=True)
        time.sleep(2)

if __name__ == "__main__":
    run_sync_cycle()
