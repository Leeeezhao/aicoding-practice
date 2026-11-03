import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "starter" / "main.py"
DATA = ROOT / "sample_data"
OUT = ROOT / "output" / "report.json"


def test_reproducible_and_finished():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(STARTER),
        "--cluster",
        str(DATA / "cluster.json"),
        "--jobs",
        str(DATA / "jobs.jsonl"),
        "--events",
        str(DATA / "events.jsonl"),
        "--strategy",
        "priority_preempt",
        "--output",
        str(OUT),
    ]
    subprocess.check_call(cmd)
    a = json.loads(OUT.read_text(encoding="utf-8"))
    subprocess.check_call(cmd)
    b = json.loads(OUT.read_text(encoding="utf-8"))
    assert a["metrics"] == b["metrics"]
    assert a["metrics"]["finished"] == a["metrics"]["total_jobs"]
    assert "baseline_metrics" in a
    assert a["metrics"]["cluster_utilization"] > 0
