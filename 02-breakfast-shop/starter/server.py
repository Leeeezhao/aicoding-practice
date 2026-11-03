#!/usr/bin/env python3
"""早餐店订单 HTTP 服务 —— 标准库实现，避免额外依赖。"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from typing import Any
from urllib.parse import urlparse

OWNER_TOKEN = "shop-owner"

MENU = [
    {"id": "baozi", "name": "包子", "price": 2.0},
    {"id": "youtiao", "name": "油条", "price": 3.0},
    {"id": "doujiang", "name": "豆浆", "price": 2.5},
]

VALID_TRANSITIONS = {
    "PENDING": {"CONFIRMED", "CANCELLED"},
    "CONFIRMED": {"COOKING", "CANCELLED"},
    "COOKING": {"READY"},
    "READY": {"PAID"},
    "PAID": set(),
    "CANCELLED": set(),
}


class Store:
    def __init__(self) -> None:
        self.lock = Lock()
        self.next_id = 1
        self.orders: dict[int, dict[str, Any]] = {}

    def reset(self) -> None:
        with self.lock:
            self.next_id = 1
            self.orders.clear()

    def create_order(self, customer: str, items: list[dict[str, Any]]) -> dict[str, Any]:
        with self.lock:
            oid = self.next_id
            self.next_id += 1
            order = {
                "id": oid,
                "customer": customer,
                "items": items,
                "status": "PENDING",
            }
            self.orders[oid] = order
            return dict(order)

    def list_orders(self) -> list[dict[str, Any]]:
        with self.lock:
            return [dict(self.orders[k]) for k in sorted(self.orders)]

    def get_order(self, oid: int) -> dict[str, Any] | None:
        with self.lock:
            o = self.orders.get(oid)
            return dict(o) if o else None

    def update_status(self, oid: int, new_status: str, token: str | None) -> tuple[int, dict[str, Any]]:
        if token != OWNER_TOKEN:
            return 403, {"error": "forbidden"}
        with self.lock:
            order = self.orders.get(oid)
            if not order:
                return 404, {"error": "not_found"}
            cur = order["status"]
            if new_status not in VALID_TRANSITIONS.get(cur, set()):
                return 400, {"error": "invalid_transition", "from": cur, "to": new_status}
            order["status"] = new_status
            return 200, dict(order)


STORE = Store()


class Handler(BaseHTTPRequestHandler):
    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def _send(self, code: int, payload: Any) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args: Any) -> None:  # quieter tests
        return

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/menu":
            self._send(200, {"menu": MENU})
            return
        if path == "/orders":
            self._send(200, {"orders": STORE.list_orders()})
            return
        if path.startswith("/orders/"):
            try:
                oid = int(path.split("/")[2])
            except Exception:
                self._send(400, {"error": "bad_id"})
                return
            order = STORE.get_order(oid)
            if not order:
                self._send(404, {"error": "not_found"})
                return
            self._send(200, order)
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path == "/reset":
            STORE.reset()
            self._send(200, {"ok": True})
            return
        if path == "/orders":
            data = self._read_json()
            items = data.get("items") or []
            customer = data.get("customer") or "guest"
            if not isinstance(items, list) or not items:
                self._send(400, {"error": "items_required"})
                return
            order = STORE.create_order(customer, items)
            self._send(201, order)
            return
        self._send(404, {"error": "not_found"})

    def do_PUT(self) -> None:
        path = urlparse(self.path).path
        parts = path.strip("/").split("/")
        # orders/{id}/status
        if len(parts) == 3 and parts[0] == "orders" and parts[2] == "status":
            try:
                oid = int(parts[1])
            except Exception:
                self._send(400, {"error": "bad_id"})
                return
            data = self._read_json()
            code, payload = STORE.update_status(oid, data.get("status", ""), data.get("token"))
            self._send(code, payload)
            return
        self._send(404, {"error": "not_found"})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8025)
    args = ap.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"breakfast shop listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
