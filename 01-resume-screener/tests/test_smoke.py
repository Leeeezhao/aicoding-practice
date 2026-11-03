import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STARTER = ROOT / "starter"
OUT = ROOT / "sample_output" / "result.json"


def test_cli_and_schema():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(STARTER / "main.py"),
        "--job",
        str(ROOT / "data" / "job.md"),
        "--resumes",
        str(ROOT / "data" / "resumes"),
        "--output",
        str(OUT),
    ]
    subprocess.check_call(cmd, cwd=str(STARTER))
    data = json.loads(OUT.read_text(encoding="utf-8"))
    assert "job_title" in data
    assert len(data["candidates"]) == 4
    scores = [c["overall_score"] for c in data["candidates"]]
    assert scores == sorted(scores, reverse=True)
    # 张三应明显靠前：北京 + python/k8s/mysql
    names = [c["name"] for c in data["candidates"]]
    assert names[0] == "张三"
    top = data["candidates"][0]
    assert "kubernetes" in [s.lower() for s in top["matched_skills"]] or any(
        "k8s" in s.lower() or "kubernetes" in s.lower() for s in top["matched_skills"]
    )
