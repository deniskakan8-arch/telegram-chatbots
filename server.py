import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"OK: Telegram Bot is running 24/7!")

    def log_message(self, format, *args):
        return

def start_health_server():
    """Запускает фоновый HTTP сервер активности для облачных хостингов."""
    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        print(f"🌐 Фоновый веб-сервер запущен на порту {port} (для Render 24/7)", flush=True)
    except Exception as e:
        print(f"⚠️ Не удалось запустить health-сервер на порту {port}: {e}", flush=True)
