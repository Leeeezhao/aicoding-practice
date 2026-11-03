#!/usr/bin/env python3
"""脏 HTML 批处理 Pipeline 骨架。"""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


CURRENCY_MAP = {
    "人民币": "CNY",
    "cny": "CNY",
    "¥": "CNY",
    "元": "CNY",
    "usd": "USD",
    "$": "USD",
}


class TextCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.chunks: list[str] = []

    def handle_data(self, data: str) -> None:
        t = data.strip()
        if t:
            self.chunks.append(t)


def collect_text(html: str) -> str:
    p = TextCollector()
    try:
        p.feed(html)
    except Exception:
        return html
    return "\n".join(p.chunks)


def normalize_currency(text: str) -> str | None:
    low = text.lower()
    for k, v in CURRENCY_MAP.items():
        if k.lower() in low or k in text:
            return v
    return None


def parse_price(text: str) -> float | None:
    # Prefer explicit price contexts / currency symbols; avoid matching tag names like h1.
    patterns = [
        r"(?:price|价格)\s*[:：]?\s*[¥$￥]?\s*([\d][\d\s,]*\.?\d*)",
        r"[¥￥]\s*([\d][\d\s,]*\.?\d*)",
        r"\$\s*([\d][\d\s,]*\.?\d*)",
        r"([\d][\d\s,]*\.?\d*)\s*(?:元|USD|CNY)",
    ]
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if not m:
            continue
        raw = m.group(1).replace(",", "").replace(" ", "")
        try:
            val = float(raw)
        except ValueError:
            continue
        if val == val:
            return val
    return None


def parse_stock(text: str) -> int | None:
    if re.search(r"缺货|售罄", text):
        return 0
    if "有货" in text:
        return 1
    m = re.search(r"(?:库存|stock)\s*[:：]?\s*(\d+)", text, re.I)
    if m:
        return int(m.group(1))
    m = re.search(r"\b(\d+)\b", text)
    if m and ("库存" in text or "stock" in text.lower()):
        return int(m.group(1))
    return None


def parse_name(html: str, text: str) -> str | None:
    for pat in [
        r"<h1[^>]*>(.*?)</h1>",
        r'id="name"[^>]*>(.*?)<',
        r"商品名[:：]\s*([^\n<]+)",
        r"<h2[^>]*>(.*?)</h2>",
    ]:
        m = re.search(pat, html, re.I | re.S)
        if m:
            name = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if name and name not in {"Broken Item"}:
                return name
            if name:
                return name
    # plaintext fallback
    m = re.search(r"商品名[:：]\s*([^\n]+)", text)
    if m:
        return m.group(1).strip()
    return None


def process_file(path: Path) -> dict[str, Any]:
    rec: dict[str, Any] = {
        "source_file": path.name,
        "status": "failed",
        "product_name": None,
        "price": None,
        "currency": None,
        "stock": None,
        "errors": [],
    }
    try:
        html = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:  # noqa: BLE001
        rec["errors"].append("parse_error")
        rec["errors"].append(str(e))
        return rec

    text = collect_text(html)
    name = parse_name(html, text)
    price = parse_price(html + "\n" + text)
    currency = normalize_currency(html + "\n" + text)
    stock = parse_stock(html + "\n" + text)

    if not name:
        rec["errors"].append("missing_name")
    if price is None:
        rec["errors"].append("missing_price")
    if currency is None:
        # try infer from price symbol
        if "¥" in html or "￥" in html or "元" in html:
            currency = "CNY"
        elif "$" in html:
            currency = "USD"
        else:
            rec["errors"].append("missing_currency")
    if stock is None:
        rec["errors"].append("invalid_stock")

    rec["product_name"] = name
    rec["price"] = price
    rec["currency"] = currency
    rec["stock"] = stock

    # success only if required fields present
    if name and price is not None and currency and stock is not None:
        rec["status"] = "success"
        rec["errors"] = []
    return rec


def run(input_dir: Path, output_dir: Path) -> dict[str, Any]:
    files = sorted(input_dir.glob("*.html"), key=lambda p: p.name)
    rows = [process_file(p) for p in files]
    output_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = output_dir / "results.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    err_counts: dict[str, int] = {}
    success = sum(1 for r in rows if r["status"] == "success")
    failed = len(rows) - success
    for r in rows:
        for e in r.get("errors") or []:
            err_counts[e] = err_counts.get(e, 0) + 1
    summary = {
        "total": len(rows),
        "success": success,
        "failed": failed,
        "error_counts": err_counts,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return summary


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    summary = run(Path(args.input), Path(args.output_dir))
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
