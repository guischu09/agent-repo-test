"""Tests for the pure Python reverse proxy."""

import http.server
import json
import threading
import urllib.request
import urllib.error

from reverse_proxy import create_proxy_handler, parse_args


def _start_backend(handler_class, port):
    """Start a backend HTTP server in a background thread."""
    server = http.server.HTTPServer(("127.0.0.1", port), handler_class)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _start_proxy(backend_url, port):
    """Start the reverse proxy in a background thread."""
    handler = create_proxy_handler(backend_url)
    server = http.server.HTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class EchoHandler(http.server.BaseHTTPRequestHandler):
    """Backend that echoes request details back as JSON."""

    def _handle(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

        response_data = {
            "method": self.command,
            "path": self.path,
            "body": body,
            "headers": {k: v for k, v in self.headers.items()},
        }
        response_body = json.dumps(response_data).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_body)))
        self.send_header("X-Backend-Header", "present")
        self.end_headers()
        self.wfile.write(response_body)

    do_GET = _handle
    do_POST = _handle
    do_PUT = _handle
    do_DELETE = _handle
    do_PATCH = _handle
    do_HEAD = _handle

    def log_message(self, format, *args):
        pass  # Suppress log output during tests


class ErrorHandler(http.server.BaseHTTPRequestHandler):
    """Backend that returns a specific error status code."""

    def do_GET(self):
        body = b"Not Found"
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


# --- Test fixtures: backend on 18081, proxy on 18080 ---

BACKEND_PORT = 18081
PROXY_PORT = 18080
ERROR_BACKEND_PORT = 18082
ERROR_PROXY_PORT = 18083

_servers_started = False


def _ensure_servers():
    global _servers_started
    if not _servers_started:
        _start_backend(EchoHandler, BACKEND_PORT)
        _start_proxy(f"http://127.0.0.1:{BACKEND_PORT}", PROXY_PORT)
        _start_backend(ErrorHandler, ERROR_BACKEND_PORT)
        _start_proxy(f"http://127.0.0.1:{ERROR_BACKEND_PORT}", ERROR_PROXY_PORT)
        _servers_started = True


def _proxy_request(method, path, body=None, port=PROXY_PORT):
    """Send a request to the proxy and return (status, headers, decoded_body)."""
    url = f"http://127.0.0.1:{port}{path}"
    data = body.encode("utf-8") if isinstance(body, str) else body
    req = urllib.request.Request(url, data=data, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.headers, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.headers, e.read().decode("utf-8")


# --- Tests ---


def test_proxy_get_request():
    """Test that GET requests are properly proxied."""
    _ensure_servers()
    status, headers, body = _proxy_request("GET", "/hello?foo=bar")
    data = json.loads(body)

    assert status == 200
    assert data["method"] == "GET"
    assert data["path"] == "/hello?foo=bar"


def test_proxy_post_request_with_body():
    """Test that POST requests with a body are properly proxied."""
    _ensure_servers()
    payload = '{"key": "value"}'
    status, headers, body = _proxy_request("POST", "/api/data", body=payload)
    data = json.loads(body)

    assert status == 200
    assert data["method"] == "POST"
    assert data["body"] == payload


def test_proxy_put_request():
    """Test that PUT requests are properly proxied."""
    _ensure_servers()
    payload = "updated content"
    status, headers, body = _proxy_request("PUT", "/resource/1", body=payload)
    data = json.loads(body)

    assert status == 200
    assert data["method"] == "PUT"
    assert data["body"] == "updated content"


def test_proxy_delete_request():
    """Test that DELETE requests are properly proxied."""
    _ensure_servers()
    status, headers, body = _proxy_request("DELETE", "/resource/1")
    data = json.loads(body)

    assert status == 200
    assert data["method"] == "DELETE"


def test_proxy_forwards_x_forwarded_headers():
    """Test that the proxy adds X-Forwarded-* headers."""
    _ensure_servers()
    status, headers, body = _proxy_request("GET", "/check-headers")
    data = json.loads(body)

    assert "X-Forwarded-For" in data["headers"]
    assert "X-Forwarded-Host" in data["headers"]
    assert "X-Forwarded-Proto" in data["headers"]
    assert data["headers"]["X-Forwarded-Proto"] == "http"


def test_proxy_forwards_backend_headers():
    """Test that response headers from the backend are forwarded."""
    _ensure_servers()
    status, headers, body = _proxy_request("GET", "/any")

    assert headers.get("X-Backend-Header") == "present"


def test_proxy_handles_backend_error_status():
    """Test that error status codes from the backend are forwarded."""
    _ensure_servers()
    status, headers, body = _proxy_request("GET", "/not-found", port=ERROR_PROXY_PORT)

    assert status == 404
    assert body == "Not Found"


def test_proxy_returns_502_when_backend_unreachable():
    """Test that the proxy returns 502 when the backend is down."""
    # Create a proxy pointing to a port with no server
    dead_port = 19999
    proxy_port = 19998
    handler = create_proxy_handler(f"http://127.0.0.1:{dead_port}")
    server = http.server.HTTPServer(("127.0.0.1", proxy_port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    status, headers, body = _proxy_request("GET", "/anything", port=proxy_port)
    assert status == 502
    assert "Bad Gateway" in body

    server.shutdown()


def test_parse_args_defaults():
    """Test argument parsing with default port."""
    args = parse_args(["--backend", "http://localhost:9000"])
    assert args.backend == "http://localhost:9000"
    assert args.port == 8000


def test_parse_args_custom_port():
    """Test argument parsing with a custom port."""
    args = parse_args(["--backend", "http://example.com", "--port", "3000"])
    assert args.backend == "http://example.com"
    assert args.port == 3000


def test_proxy_preserves_query_string():
    """Test that query strings are preserved through the proxy."""
    _ensure_servers()
    status, headers, body = _proxy_request("GET", "/search?q=hello&page=2")
    data = json.loads(body)

    assert data["path"] == "/search?q=hello&page=2"


def test_proxy_preserves_path():
    """Test that nested paths are preserved through the proxy."""
    _ensure_servers()
    status, headers, body = _proxy_request("GET", "/api/v1/users/42/profile")
    data = json.loads(body)

    assert data["path"] == "/api/v1/users/42/profile"
