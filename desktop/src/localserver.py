"""Tiny web server that only listens on this computer (127.0.0.1) and only serves the bundled website.

A fixed port keeps the page's address the same on every launch, which is what lets the browser engine
keep your saved progress (localStorage) between runs.
"""
import functools
import http.server
import threading

PORT = 47831

# Windows can have wrong file-type entries in the registry; set the ones we need explicitly.
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".json": "application/json", ".woff2": "font/woff2",
         ".svg": "image/svg+xml", ".png": "image/png", ".ico": "image/x-icon"}


class _Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map, **TYPES}

    def log_message(self, *args):          # stay quiet
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def start(directory, port=PORT):
    """Starts the server in a background thread. Returns (server, url). Raises OSError if the port is taken."""
    handler = functools.partial(_Handler, directory=str(directory))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{port}/index.html"
