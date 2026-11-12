import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from . import lan

WEB = Path(__file__).parent / "web"


def make_handler(engine):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            try:
                return json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return {}

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                data = (WEB / "index.html").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            elif self.path == "/api/state":
                self._json(engine.snapshot())
            elif self.path == "/api/discover":
                try:
                    self._json(lan.discover())
                except OSError as e:
                    self._json({"error": str(e)}, 500)
            elif self.path == "/api/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                try:
                    while engine.running:
                        flat = [c for row in engine.frame for px in row for c in px]
                        self.wfile.write(b"data: " + json.dumps(flat).encode() + b"\n\n")
                        self.wfile.flush()
                        time.sleep(1 / 30)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            else:
                self.send_error(404)

        def do_POST(self):
            b = self._body()
            if self.path == "/api/params":
                engine.set_params(b)
            elif self.path == "/api/effect":
                engine.set_effect(b.get("name", ""))
            elif self.path == "/api/device":
                engine.set_device(str(b.get("ip", "")).strip(), b.get("mode", "razer"))
            else:
                return self.send_error(404)
            self._json(engine.snapshot())

    return H


def serve(engine, port):
    srv = ThreadingHTTPServer(("0.0.0.0", port), make_handler(engine))
    srv.daemon_threads = True
    threading.Thread(target=engine.run, daemon=True).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        engine.stop()
