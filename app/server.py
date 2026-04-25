from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer

from app.main import Application


APP = Application()


class Handler(BaseHTTPRequestHandler):
    def _serve(self) -> None:
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else None
        response = APP.handle(
            method=self.command,
            path=self.path,
            headers={k: v for k, v in self.headers.items()},
            body=raw,
        )
        payload = json.dumps(response.body).encode("utf-8")
        self.send_response(response.status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:  # noqa: N802
        self._serve()

    def do_POST(self) -> None:  # noqa: N802
        self._serve()

    def do_PATCH(self) -> None:  # noqa: N802
        self._serve()


def main() -> None:
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    print("Serving on http://0.0.0.0:8000")
    server.serve_forever()


if __name__ == "__main__":
    main()
