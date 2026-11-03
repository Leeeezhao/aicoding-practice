import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output"


def test_batch_does_not_crash_and_keeps_failures():
    if OUT.exists():
        for p in OUT.glob("*"):
            p.unlink()
    cmd = [
        sys.executable,
        str(ROOT / "starter" / "main.py"),
        "--input",
        str(ROOT / "data" / "html_samples"),
        "--output-dir",
        str(OUT),
    ]
    subprocess.check_call(cmd)
    rows = [json.loads(l) for l in (OUT / "results.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 5
    assert rows[0]["source_file"] == "001.html"
    assert rows[0]["status"] == "success"
    assert rows[0]["currency"] == "CNY"
    assert rows[0]["price"] == 2999.0
    # at least one failure retained
    assert any(r["status"] == "failed" for r in rows)
    summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
    assert summary["total"] == 5
    assert summary["success"] + summary["failed"] == 5
