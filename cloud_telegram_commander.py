import os
import sys
import json
import time
import urllib.parse
import urllib.request
import ssl
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TELEGRAM_CONFIG_PATH = os.path.join(BASE_DIR, "telegram_config.json")
CONFIG_PATH = os.path.join(BASE_DIR, "email_config.json")
DAEMON_PATH = os.path.join(BASE_DIR, "cloud_school_daemon.py")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AUTHORIZED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

if (not BOT_TOKEN or not AUTHORIZED_CHAT_ID) and os.path.exists(TELEGRAM_CONFIG_PATH):
    try:
        with open(TELEGRAM_CONFIG_PATH, "r", encoding="utf-8") as f:
            tg_config = json.load(f)
            BOT_TOKEN = BOT_TOKEN or tg_config.get("bot_token")
            AUTHORIZED_CHAT_ID = AUTHORIZED_CHAT_ID or tg_config.get("chat_id")
    except Exception as e:
        print(f"Config load error: {e}")

if AUTHORIZED_CHAT_ID:
    AUTHORIZED_CHAT_ID = int(AUTHORIZED_CHAT_ID)

def send_reply(chat_id, text):
    ctx = ssl._create_unverified_context()
    params = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'Markdown'
    }).encode('utf-8')
    req = urllib.request.Request(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", data=params)
    try:
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except Exception as e:
        print(f"Error sending reply: {e}", flush=True)

def handle_school_check():
    result = subprocess.run([
        sys.executable,
        DAEMON_PATH
    ], capture_output=True, text=True, encoding="utf-8")
    return "✅ 24/7 Cloud School check completed.\n" + (result.stdout[-300:] if result.stdout else "No new updates.")

def handle_fee_summary():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    import imaplib, email
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(cfg['email'], cfg['app_password'])
    mail.select('"School"')

    status, msgs = mail.search(None, 'X-GM-RAW', '"fee OR fees OR payment OR receipt"')
    if not status == 'OK' or not msgs[0]:
        mail.logout()
        return "No fee records found in School label."

    ids = msgs[0].split()
    output = "📋 *RECENT SCHOOL FEE RECORDS (CIRS & SKV):*\n━━━━━━━━━━━━━━━━━━━\n"
    for mid in reversed(ids[-5:]):
        res, data = mail.fetch(mid, '(RFC822)')
        msg = email.message_from_bytes(data[0][1])
        sub = msg.get('Subject', '')
        date = msg.get('Date', '')[:16]
        output += f"• *{date}*: {sub}\n"

    mail.logout()
    return output

def process_message(text, chat_id):
    clean = text.strip().lower()

    if clean in ["/start", "hi", "hello", "hey"]:
        return (
            "👋 *Namaste Ravi Bhai! 24/7 Cloud AGY Brain Live Hai.*\n\n"
            "Aapka computer band ho tab bhi yeh cloud server 24/7 active rehta hai:\n"
            "• `/check` — Naye circulars / school mails ka live sync\n"
            "• `/fees` — Aarav & Avni ki recent fee receipts & payments\n"
            "• `/status` — 24/7 Cloud server health\n"
            "• `/help` — Commands list\n\n"
            "Bataiye kya command run karein?"
        )
    elif clean in ["/check", "check", "check mail", "school"]:
        send_reply(chat_id, "⏳ 24/7 Cloud engine scanning School emails...")
        return handle_school_check()
    elif clean in ["/fees", "fees", "fee", "aarav", "avni"]:
        send_reply(chat_id, "🔍 Fetching fee records from Gmail...")
        return handle_fee_summary()
    elif clean in ["/status", "status"]:
        return (
            "☁️ *24/7 CLOUD HOST HEALTH REPORT:*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "• **Status:** 24/7 Cloud Active\n"
            "• **Host:** Linux Cloud VPS\n"
            "• **Gmail Target:** ravikumarsarawgi@gmail.com\n"
            "• **Label:** School (Active Watcher)\n"
            "• **PC Dependency:** Zero (Independent 24/7)\n"
            "━━━━━━━━━━━━━━━━━━━"
        )
    elif clean in ["/help", "help"]:
        return (
            "📖 *COMMANDS:*\n"
            "• `check` — School mails check\n"
            "• `fees` — Fee summary\n"
            "• `status` — Server status"
        )
    else:
        return f"🤖 *Command Received:* \"{text}\"\nType `fees` or `check` to query your cloud database."

def start_listening():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Cloud Telegram Commander listening (Chat ID: {AUTHORIZED_CHAT_ID})...", flush=True)
    last_update_id = 0
    ctx = ssl._create_unverified_context()

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=20"
            req = urllib.request.Request(url)
            res = urllib.request.urlopen(req, context=ctx, timeout=30)
            data = json.loads(res.read().decode())

            if data.get("ok") and data.get("result"):
                for update in data["result"]:
                    last_update_id = update["update_id"]
                    msg = update.get("message")
                    if not msg or not msg.get("text"):
                        continue

                    sender_id = msg.get("chat", {}).get("id")
                    if sender_id != AUTHORIZED_CHAT_ID:
                        continue

                    user_text = msg.get("text", "")
                    print(f"Cloud command from Ravi: {user_text}", flush=True)

                    reply = process_message(user_text, sender_id)
                    send_reply(sender_id, reply)

            time.sleep(1)
        except Exception:
            time.sleep(3)

if __name__ == "__main__":
    start_listening()
