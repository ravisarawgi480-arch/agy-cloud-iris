import os
import sys
import time
import threading
import http.server
import socketserver
import subprocess
import json
import ssl
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8080))
TELEGRAM_CONFIG_PATH = os.path.join(BASE_DIR, "telegram_config.json")

print("=" * 60)
print("🚀 AGY 24/7 CLOUD COMMAND CENTER INITIALIZING...")
print("=" * 60)

def send_telegram_alert(text):
    if not os.path.exists(TELEGRAM_CONFIG_PATH):
        return
    try:
        with open(TELEGRAM_CONFIG_PATH, "r", encoding="utf-8") as f:
            tg = json.load(f)
        token = tg.get("bot_token")
        chat_id = tg.get("chat_id")
        if not token or not chat_id:
            return
        ctx = ssl._create_unverified_context()
        params = urllib.parse.urlencode({'chat_id': chat_id, 'text': text, 'parse_mode': 'Markdown'}).encode('utf-8')
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=params)
        urllib.request.urlopen(req, context=ctx, timeout=10)
    except Exception as e:
        print(f"[ERROR] Alert dispatch: {e}", flush=True)

def run_telegram_bot():
    print("[INIT] Starting 2-Way Telegram Commander...", flush=True)
    while True:
        try:
            p = subprocess.run([sys.executable, os.path.join(BASE_DIR, "cloud_telegram_commander.py")])
            print(f"[RESTART] Telegram Commander exited with {p.returncode}. Auto-restarting in 5s...", flush=True)
        except Exception as e:
            print(f"[ERROR] Telegram Commander crashed: {e}. Retrying in 5s...", flush=True)
        time.sleep(5)

def run_school_monitor():
    print("[INIT] Starting School Email Monitor (Once a day / Every 24 hours)...", flush=True)
    while True:
        try:
            p = subprocess.run([sys.executable, os.path.join(BASE_DIR, "cloud_school_daemon.py")])
            print("[SYNC] School monitor daily cycle finished.", flush=True)
        except Exception as e:
            print(f"[ERROR] School monitor crashed: {e}", flush=True)
        # Sleep for 24 hours (86,400 seconds) between daily polling cycles
        time.sleep(86400)

def run_morning_briefing():
    print("[INIT] Starting Autonomous Morning Briefing Scheduler (8:00 AM IST)...", flush=True)
    # IST is UTC+5:30
    ist_offset = timedelta(hours=5, minutes=30)
    last_sent_day = -1

    while True:
        try:
            now_ist = datetime.now(timezone.utc) + ist_offset
            # Check if it's 8:00 AM IST and hasn't been sent today
            if now_ist.hour == 8 and now_ist.day != last_sent_day:
                briefing_msg = (
                    f"🌅 *GOOD MORNING RAVI BHAI! (Executive Daily Briefing)*\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"📅 *Date:* {now_ist.strftime('%d %B %Y')}\n\n"
                    f"• 🏫 *School Radar:* CIRS & SKV monitoring active\n"
                    f"• ☁️ *Cloud Status:* 24/7 Render Worker 100% Healthy\n"
                    f"• 📲 *On-Demand Commands:* Reply `fees`, `check`, ya kisi bhi circular ka topic poochhein\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"Have a powerful & productive day ahead! 🚀"
                )
                send_telegram_alert(briefing_msg)
                print(f"[BRIEFING] Morning briefing dispatched for {now_ist.strftime('%Y-%m-%d')}", flush=True)
                last_sent_day = now_ist.day
        except Exception as e:
            print(f"[ERROR] Briefing scheduler: {e}", flush=True)
        # Check every 10 minutes
        time.sleep(600)

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "service": "AGY Cloud Iris", "uptime": "24/7 active", "ai_brain": "enabled"}')
    def log_message(self, format, *args):
        # Silence HTTP access logs to keep console clean
        pass

def run_health_server():
    print(f"[INIT] Starting Cloud Healthcheck listener on port {PORT}...", flush=True)
    try:
        with socketserver.TCPServer(("", PORT), HealthHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print(f"[WARN] Health server error: {e}", flush=True)

if __name__ == "__main__":
    # Thread 1: Telegram 2-way Bot with Intelligent Search
    t_tg = threading.Thread(target=run_telegram_bot, daemon=True)
    t_tg.start()

    # Thread 2: School Email Monitor (Daily cycle)
    t_school = threading.Thread(target=run_school_monitor, daemon=True)
    t_school.start()

    # Thread 3: Autonomous Morning Briefing (8:00 AM IST)
    t_briefing = threading.Thread(target=run_morning_briefing, daemon=True)
    t_briefing.start()

    # Main thread: HTTP Healthcheck listener (keeps Render alive)
    run_health_server()
