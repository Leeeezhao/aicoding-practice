#!/usr/bin/env python3
"""简历筛选入口 —— starter 仅提供骨架，需补全解析/评分逻辑。"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from synonyms import normalize_city, normalize_skill


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def parse_job(text: str) -> dict[str, Any]:
    # TODO: 更稳健地解析必备/加分技能、地点、学历、年限
    title = "未知职位"
    m = re.search(r"^#\s*(.+)$", text, re.M)
    if m:
        title = m.group(1).strip()
    skills = re.findall(r"-\s*([^\n（(]+)", text)
    required = [normalize_skill(s.split("或")[0]) for s in skills]
    city = "北京" if "北京" in text else ""
    return {
        "job_title": title,
        "required_skills": required,
        "preferred_skills": [],
        "city": normalize_city(city) if city else "",
        "min_years": 1.0,
        "min_education": "本科",
    }


def parse_resume(path: Path) -> dict[str, Any]:
    text = read_text(path)
    name = path.stem
    m = re.search(r"^#\s*(.+)$", text, re.M)
    if m:
        name = m.group(1).strip()

    # 极简技能抽取：逗号/顿号/斜杠分割的 token
    raw_tokens = re.findall(r"[A-Za-z][A-Za-z0-9+#\.]*|[\u4e00-\u9fff]{2,}", text)
    skills = sorted({normalize_skill(t) for t in raw_tokens if len(t) >= 2})

    city = ""
    for key in ("期望城市", "所在城市", "城市"):
        cm = re.search(rf"{key}[：:]\s*(\S+)", text)
        if cm:
            city = normalize_city(cm.group(1))
            break
    if "北京" in text and not city:
        city = "北京"

    years = 0.0
    ym = re.search(r"(\d+(?:\.\d+)?)\s*年", text)
    if ym:
        years = float(ym.group(1))
    if "半年" in text:
        years = max(years, 0.5)

    edu = "未知"
    for level in ("博士", "硕士", "本科", "大专"):
        if level in text:
            edu = level
            break

    return {
        "file": path.name,
        "name": name,
        "skills": skills,
        "years": years,
        "education": edu,
        "city": city,
        "raw": text,
    }


EDU_RANK = {"未知": 0, "大专": 1, "本科": 2, "硕士": 3, "博士": 4}


def score_candidate(job: dict[str, Any], cand: dict[str, Any]) -> dict[str, Any]:
    req = [normalize_skill(s) for s in job.get("required_skills", [])]
    req = [s for s in req if s]
    cand_skills = set(cand.get("skills", []))
    matched = sorted({s for s in req if s in cand_skills})
    missing = sorted({s for s in req if s not in cand_skills})
    skill_score = (len(matched) / len(req)) if req else 0.0

    min_years = float(job.get("min_years", 0) or 0)
    experience_score = min(1.0, cand.get("years", 0) / min_years) if min_years > 0 else 1.0

    need_edu = job.get("min_education", "本科")
    education_score = 1.0 if EDU_RANK.get(cand.get("education", "未知"), 0) >= EDU_RANK.get(need_edu, 0) else 0.3

    job_city = job.get("city") or ""
    location_score = 1.0 if (not job_city or cand.get("city") == job_city) else 0.2

    overall = (
        0.45 * skill_score
        + 0.25 * experience_score
        + 0.15 * education_score
        + 0.15 * location_score
    )
    return {
        "file": cand["file"],
        "name": cand["name"],
        "overall_score": round(overall, 4),
        "skill_score": round(skill_score, 4),
        "experience_score": round(experience_score, 4),
        "education_score": round(education_score, 4),
        "location_score": round(location_score, 4),
        "matched_skills": matched,
        "missing_skills": missing,
        "reason": f"命中 {len(matched)}/{len(req)} 必备技能，年限 {cand.get('years', 0)}",
    }


def run(job_path: Path, resumes_dir: Path, output: Path) -> dict[str, Any]:
    job = parse_job(read_text(job_path))
    resumes = sorted(resumes_dir.glob("*.md"))
    scored = [score_candidate(job, parse_resume(p)) for p in resumes]
    scored.sort(key=lambda x: (-x["overall_score"], x["file"]))
    result = {"job_title": job["job_title"], "candidates": scored}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--job", required=True)
    ap.add_argument("--resumes", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    run(Path(args.job), Path(args.resumes), Path(args.output))
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
