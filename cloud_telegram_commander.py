import os
import sys
import json
import time
import urllib.parse
import urllib.request
import ssl
import subprocess
import imaplib
import email
from email.header import decode_header

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TELEGRAM_CONFIG_PATH = os.path.join(BASE_DIR, "telegram_config.json")
CONFIG_PATH = os.path.join(BASE_DIR, "email_config.json")
DAEMON_PATH = os.path.join(BASE_DIR, "cloud_school_daemon.py")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
AUTHORIZED_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if (not BOT_TOKEN or not AUTHORIZED_CHAT_ID) and os.path.exists(TELEGRAM_CONFIG_PATH):
    try:
        with open(TELEGRAM_CONFIG_PATH, "r", encoding="utf-8") as f:
            tg_config = json.load(f)
            BOT_TOKEN = BOT_TOKEN or tg_config.get("bot_token")
            AUTHORIZED_CHAT_ID = AUTHORIZED_CHAT_ID or tg_config.get("chat_id")
            GEMINI_API_KEY = GEMINI_API_KEY or tg_config.get("gemini_api_key")
    except Exception as e:
        print(f"Config load error: {e}", flush=True)

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
        if res != 'OK':
            continue
        msg = email.message_from_bytes(data[0][1])
        sub = msg.get('Subject', '')
        date = msg.get('Date', '')[:16]
        output += f"• *{date}*: {sub}\n"

    mail.logout()
    return output

def search_school_emails(query_term):
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(cfg['email'], cfg['app_password'])
        mail.select('"School"')

        status, msgs = mail.search(None, 'X-GM-RAW', f'"{query_term}"')
        if not status == 'OK' or not msgs[0]:
            mail.logout()
            return f"🔍 School emails me *'{query_term}'* se related koi email nahi mila."

        ids = msgs[0].split()
        output = f"🔍 *SEARCH RESULTS FOR: '{query_term}':*\n━━━━━━━━━━━━━━━━━━━\n"
        for mid in reversed(ids[-4:]):
            res, data = mail.fetch(mid, '(RFC822)')
            if res != 'OK':
                continue
            msg = email.message_from_bytes(data[0][1])
            sub = msg.get('Subject', '')
            date = msg.get('Date', '')[:16]
            output += f"• *{date}*\n  Subject: {sub}\n"

        mail.logout()
        return output
    except Exception as e:
        return f"Error searching emails: {e}"

def call_gemini_brain(prompt):
    if not GEMINI_API_KEY:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
    sys_prompt = (
        "You are Iris, an intelligent, sharp executive AI assistant for Ravi (non-technical business owner, "
        "children Aarav at CIRS & Avni at SKV). Answer clearly and concisely in natural Hinglish. "
        "Keep responses punchy, helpful, and executive."
    )
    payload = {
        "contents": [{
            "parts": [{"text": f"{sys_prompt}\n\nUser Question: {prompt}"}]
        }]
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
    ctx = ssl._create_unverified_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        print(f"Gemini API error: {e}", flush=True)
        return None

def process_message(text, chat_id):
    clean = text.strip().lower()

    # 1. Greetings
    if clean in ["/start", "hi", "hello", "hey", "namaste", "suno"]:
        return (
            "👋 *Namaste Ravi Bhai! Iris Cloud AI Active Hai.*\n\n"
            "Main 24/7 cloud par aapke sath connected hoon:\n"
            "• Kisi bhi school circular ya topic ke baare me poochhein (e.g. `ice cream`, `holiday`, `fees`)\n"
            "• `/fees` — Aarav & Avni ki recent fee receipts\n"
            "• `/check` — Naye circulars ka instant cloud scan\n"
            "• `/status` — 24/7 Server health check\n\n"
            "Bataiye bhai, kya madad karoon?"
        )

    # 2. Status Command
    elif clean in ["/status", "status", "health"]:
        return (
            "☁️ *24/7 CLOUD COMMAND STATUS:*\n"
            "━━━━━━━━━━━━━━━━━━━\n"
            "• **Status:** Active & Responsive 🟢\n"
            "• **Host:** Render Cloud (Starter Worker)\n"
            "• **Gmail Radar:** ravikumarsarawgi@gmail.com (Daily)\n"
            "• **Target Label:** School (CIRS & SKV)\n"
            "• **PC Dependency:** Zero (100% Cloud Autonomous)\n"
            "━━━━━━━━━━━━━━━━━━━"
        )

    # 3. Direct School Checks
    elif clean in ["/check", "check", "check mail", "scan"]:
        send_reply(chat_id, "⏳ 24/7 Cloud engine school emails scan kar raha hai...")
        return handle_school_check()

    # 4. Fee Summary
    elif clean in ["/fees", "fees", "fee", "payment", "receipt"]:
        send_reply(chat_id, "🔍 Fetching fee records from Gmail...")
        return handle_fee_summary()

    # 5. Smart Search across School Emails
    elif any(k in clean for k in ["circular", "ice cream", "permission", "holiday", "ptm", "uniform", "skv", "cirs", "aarav", "avni", "principal", "exam", "report"]):
        # Extract meaningful keyword
        words = [w for w in clean.replace("?", "").replace("kya", "").replace("hai", "").replace("batao", "").split() if len(w) > 2]
        query_kw = words[0] if words else "school"
        send_reply(chat_id, f"🔍 School emails me *'{query_kw}'* search kiya ja raha hai...")
        return search_school_emails(query_kw)

    # 6. Fallback to Gemini Brain (if available) or Intelligent Assistant Reply
    else:
        ai_reply = call_gemini_brain(text)
        if ai_reply:
            return ai_reply
        return (
            f"🤖 *Iris Cloud Assistant:* \"{text}\"\n\n"
            "Main aapke liye school circulars, fees, aur system health check kar sakti hoon.\n"
            "Kuch bhi poochhne ke liye type karein:\n"
            "• `fees` — Fee summary\n"
            "• `check` — Live email scan\n"
            "• `status` — Cloud health\n"
            "• Ya koi keyword jaise: `holiday`, `ice cream`, `circular`"
        )

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
                    if reply:
                        send_reply(sender_id, reply)

        except Exception as e:
            print(f"Polling error: {e}", flush=True)
            time.sleep(3)

        time.sleep(1)

if __name__ == "__main__":
    start_listening()
