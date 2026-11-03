import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "starter"))
from server import Handler, STORE  # noqa: E402


def _start():
    STORE.reset()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = httpd.server_address[1]
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return httpd, port


def _req(port, method, path, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def test_happy_path_and_guards():
    httpd, port = _start()
    try:
        code, menu = _req(port, "GET", "/menu")
        assert code == 200 and len(menu["menu"]) >= 3

        code, order = _req(
            port,
            "POST",
            "/orders",
            {"customer": "Alice", "items": [{"id": "baozi", "qty": 1}]},
        )
        assert code == 201 and order["status"] == "PENDING"
        oid = order["id"]

        # bad token
        code, _ = _req(port, "PUT", f"/orders/{oid}/status", {"status": "CONFIRMED", "token": "x"})
        assert code == 403

        # illegal jump
        code, err = _req(
            port, "PUT", f"/orders/{oid}/status", {"status": "READY", "token": "shop-owner"}
        )
        assert code == 400
        code, cur = _req(port, "GET", f"/orders/{oid}")
        assert cur["status"] == "PENDING"

        for st in ["CONFIRMED", "COOKING", "READY", "PAID"]:
            code, cur = _req(
                port, "PUT", f"/orders/{oid}/status", {"status": st, "token": "shop-owner"}
            )
            assert code == 200 and cur["status"] == st

        code, _ = _req(port, "POST", "/reset")
        assert code == 200
        code, listing = _req(port, "GET", "/orders")
        assert listing["orders"] == []
    finally:
        httpd.shutdown()
