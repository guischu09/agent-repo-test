"""
A pure Python reverse proxy server with no external dependencies.

Uses only the standard library (http.server, urllib.request) to forward
incoming HTTP requests to a configurable backend server.

Usage:
    python3 reverse_proxy.py --backend http://localhost:8080 --port 8000
"""

import argparse
import http.server
import urllib.request
import urllib.error
import urllib.parse


HOP_BY_HOP_HEADERS = frozenset(
    h.lower()
    for h in [
        "Connection",
        "Keep-Alive",
        "Proxy-Authenticate",
        "Proxy-Authorization",
        "TE",
        "Trailers",
        "Transfer-Encoding",
        "Upgrade",
    ]
)


def create_proxy_handler(backend_url: str):
    """Create a request handler class that proxies to the given backend URL."""

    backend = backend_url.rstrip("/")

    class ProxyHandler(http.server.BaseHTTPRequestHandler):
        """HTTP request handler that forwards requests to a backend server."""

        def _proxy_request(self):
            target_url = backend + self.path

            # Read request body if present
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else None

            # Build forwarded headers, filtering out hop-by-hop headers
            headers = {}
            for key, value in self.headers.items():
                if key.lower() not in HOP_BY_HOP_HEADERS:
                    headers[key] = value

            # Add X-Forwarded headers
            client_host = self.client_address[0]
            headers["X-Forwarded-For"] = client_host
            headers["X-Forwarded-Host"] = self.headers.get("Host", "")
            headers["X-Forwarded-Proto"] = "http"

            request = urllib.request.Request(
                target_url,
                data=body,
                headers=headers,
                method=self.command,
            )

            try:
                with urllib.request.urlopen(request) as response:
                    self._send_response(response.status, response.headers, response.read())
            except urllib.error.HTTPError as e:
                self._send_response(e.code, e.headers, e.read())
            except urllib.error.URLError as e:
                error_message = f"Bad Gateway: {e.reason}".encode("utf-8")
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.send_header("Content-Length", str(len(error_message)))
                self.end_headers()
                self.wfile.write(error_message)

        def _send_response(self, status_code, headers, body):
            self.send_response(status_code)
            for key, value in headers.items():
                if key.lower() not in HOP_BY_HOP_HEADERS and key.lower() != "content-length":
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            """Log proxy requests with the backend target."""
            message = format % args
            print(f"[proxy] {self.address_string()} -> {backend}: {message}")

        # Support common HTTP methods
        def do_GET(self):
            self._proxy_request()

        def do_POST(self):
            self._proxy_request()

        def do_PUT(self):
            self._proxy_request()

        def do_DELETE(self):
            self._proxy_request()

        def do_PATCH(self):
            self._proxy_request()

        def do_HEAD(self):
            self._proxy_request()

        def do_OPTIONS(self):
            self._proxy_request()

    return ProxyHandler


def run_proxy(port: int, backend_url: str):
    """Start the reverse proxy server."""
    handler = create_proxy_handler(backend_url)
    server = http.server.HTTPServer(("", port), handler)
    print(f"Reverse proxy listening on port {port}, forwarding to {backend_url}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down proxy server.")
    finally:
        server.server_close()


def parse_args(args=None):
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Pure Python reverse proxy server")
    parser.add_argument(
        "--backend",
        required=True,
        help="Backend server URL to proxy requests to (e.g., http://localhost:8080)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to listen on (default: 8000)",
    )
    return parser.parse_args(args)


if __name__ == "__main__":
    parsed = parse_args()
    run_proxy(parsed.port, parsed.backend)
