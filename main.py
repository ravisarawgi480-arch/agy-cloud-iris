import os
import sys
import time
import threading
import http.server
import socketserver
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PORT = int(os.environ.get("PORT", 8080))

print("=" * 60)
print("🚀 AGY 24/7 CLOUD COMMAND CENTER INITIALIZING...")
print("=" * 60)

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
    print("[INIT] Starting 24/7 School Email Monitor (Every 15 mins)...", flush=True)
    while True:
        try:
            p = subprocess.run([sys.executable, os.path.join(BASE_DIR, "cloud_school_daemon.py")])
            print("[SYNC] School monitor cycle finished.", flush=True)
        except Exception as e:
            print(f"[ERROR] School monitor crashed: {e}", flush=True)
        # Sleep for 15 minutes between polling cycles
        time.sleep(900)

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status": "ok", "service": "AGY Cloud Iris", "uptime": "24/7 active"}')
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
    # Thread 1: Telegram 2-way Bot
    t_tg = threading.Thread(target=run_telegram_bot, daemon=True)
    t_tg.start()

    # Thread 2: School Email Monitor (15-min intervals)
    t_school = threading.Thread(target=run_school_monitor, daemon=True)
    t_school.start()

    # Main thread: HTTP Healthcheck listener (keeps Railway / Render alive)
    run_health_server()
