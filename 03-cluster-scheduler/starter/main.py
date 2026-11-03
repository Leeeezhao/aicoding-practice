#!/usr/bin/env python3
"""集群调度模拟器骨架：实现 FIFO 与可抢占优先级策略。"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal


Priority = Literal["normal", "high"]


@dataclass
class Job:
    job_id: str
    priority: Priority
    resource_num: int
    submit_time: int
    estimated_time: int
    actual_time: int
    remaining: int = 0
    wait_time: int = 0
    start_time: int | None = None
    finish_time: int | None = None
    preempt_count: int = 0

    def __post_init__(self) -> None:
        self.remaining = self.actual_time


@dataclass
class Machine:
    machine_id: int
    free_at: int = 0  # repair until
    job_id: str | None = None


@dataclass
class SimResult:
    metrics: dict[str, Any]
    log: list[dict[str, Any]] = field(default_factory=list)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    ys = sorted(xs)
    k = (len(ys) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(ys[int(k)])
    return ys[f] * (c - k) + ys[c] * (k - f)


class Simulator:
    def __init__(self, machines: int, repair_minutes: int, starve_threshold: int, strategy: str):
        self.machines = [Machine(i) for i in range(machines)]
        self.repair_minutes = repair_minutes
        self.starve_threshold = starve_threshold
        self.strategy = strategy
        self.log: list[dict[str, Any]] = []
        self.busy_machine_time = 0
        self.total_machine_time = 0

    def _free_machines(self, now: int) -> list[Machine]:
        return [m for m in self.machines if m.free_at <= now and m.job_id is None]

    def _running(self) -> list[tuple[Machine, str]]:
        return [(m, m.job_id) for m in self.machines if m.job_id is not None]

    def _log(self, now: int, event: str, **kwargs: Any) -> None:
        self.log.append({"time": now, "event": event, **kwargs})

    def _pick_queue(self, queue: list[Job], now: int) -> Job | None:
        ready = [j for j in queue if j.submit_time <= now and j.finish_time is None and j.remaining > 0]
        # exclude already running
        running_ids = {m.job_id for m in self.machines if m.job_id}
        ready = [j for j in ready if j.job_id not in running_ids]
        if not ready:
            return None
        if self.strategy == "fifo":
            ready.sort(key=lambda j: (j.submit_time, j.job_id))
            return ready[0]
        # priority_preempt: high first, then earlier submit
        ready.sort(key=lambda j: (0 if j.priority == "high" else 1, j.submit_time, j.job_id))
        return ready[0]

    def _try_preempt_for(self, job: Job, now: int, jobs_by_id: dict[str, Job]) -> bool:
        if self.strategy != "priority_preempt" or job.priority != "high":
            return False
        # find normal jobs currently running
        victims = []
        for m in self.machines:
            if m.job_id and jobs_by_id[m.job_id].priority == "normal":
                victims.append(m)
        if not victims:
            return False
        # preempt enough machines
        need = job.resource_num
        free = self._free_machines(now)
        if len(free) >= need:
            return False  # no need
        still_need = need - len(free)
        if len(victims) < still_need:
            return False
        for m in victims[:still_need]:
            v = jobs_by_id[m.job_id]  # type: ignore[index]
            v.remaining += 10  # preempt cost
            v.preempt_count += 1
            v.start_time = None
            self._log(now, "preempt", job_id=v.job_id, by=job.job_id, machine=m.machine_id)
            m.job_id = None
        return True

    def _allocate(self, job: Job, now: int) -> bool:
        free = self._free_machines(now)
        if len(free) < job.resource_num:
            return False
        chosen = free[: job.resource_num]
        for m in chosen:
            m.job_id = job.job_id
        if job.start_time is None:
            job.wait_time = now - job.submit_time
        job.start_time = now
        self._log(now, "start", job_id=job.job_id, machines=[m.machine_id for m in chosen])
        return True

    def run(self, jobs: list[Job], failures: list[dict[str, Any]], horizon: int | None = None) -> SimResult:
        jobs_by_id = {j.job_id: j for j in jobs}
        fail_map = {int(e["time"]): e for e in failures}
        now = 0
        max_t = horizon or (max(j.submit_time + j.actual_time for j in jobs) + 500)

        while now <= max_t:
            # failures
            if now in fail_map:
                mid = int(fail_map[now]["machine_id"])
                m = self.machines[mid]
                if m.job_id:
                    j = jobs_by_id[m.job_id]
                    # interrupted, requeue remaining
                    j.start_time = None
                    self._log(now, "job_interrupted_by_failure", job_id=j.job_id, machine=mid)
                    m.job_id = None
                m.free_at = now + self.repair_minutes
                self._log(now, "machine_repair", machine=mid, until=m.free_at)

            # progress running jobs
            running_jobs: dict[str, list[Machine]] = {}
            for m in self.machines:
                if m.job_id:
                    running_jobs.setdefault(m.job_id, []).append(m)
                    self.busy_machine_time += 1
                self.total_machine_time += 1

            finished = []
            for jid, ms in running_jobs.items():
                j = jobs_by_id[jid]
                j.remaining -= 1
                if j.remaining <= 0:
                    j.finish_time = now
                    finished.append(jid)
                    for m in ms:
                        m.job_id = None
                    self._log(now, "finish", job_id=jid)

            # schedule
            # attempt multiple allocations per tick
            for _ in range(len(jobs)):
                job = self._pick_queue(jobs, now)
                if not job:
                    break
                if len(self._free_machines(now)) < job.resource_num:
                    self._try_preempt_for(job, now, jobs_by_id)
                if not self._allocate(job, now):
                    break

            if all(j.finish_time is not None for j in jobs) and now > max(j.submit_time for j in jobs):
                break
            now += 1

        return SimResult(metrics=self._metrics(jobs), log=self.log)

    def _metrics(self, jobs: list[Job]) -> dict[str, Any]:
        high = [j for j in jobs if j.priority == "high" and j.finish_time is not None]
        normal = [j for j in jobs if j.priority == "normal" and j.finish_time is not None]
        high_waits = [float(j.wait_time) for j in high]
        normal_waits = [float(j.wait_time) for j in normal]
        util = self.busy_machine_time / self.total_machine_time if self.total_machine_time else 0.0
        starve = sum(1 for j in normal if j.wait_time > self.starve_threshold)
        return {
            "high_avg_wait": round(sum(high_waits) / len(high_waits), 4) if high_waits else 0.0,
            "high_p95_wait": round(percentile(high_waits, 0.95), 4),
            "cluster_utilization": round(util, 4),
            "normal_max_wait": max(normal_waits) if normal_waits else 0.0,
            "normal_wait_variance": round(statistics.pvariance(normal_waits), 4) if len(normal_waits) > 1 else 0.0,
            "normal_starve_count": starve,
            "finished": sum(1 for j in jobs if j.finish_time is not None),
            "total_jobs": len(jobs),
        }


def run_once(cluster: dict[str, Any], job_rows: list[dict[str, Any]], events: list[dict[str, Any]], strategy: str) -> SimResult:
    jobs = [
        Job(
            job_id=r["job_id"],
            priority=r["priority"],
            resource_num=int(r["resource_num"]),
            submit_time=int(r["submit_time"]),
            estimated_time=int(r["estimated_time"]),
            actual_time=int(r["actual_time"]),
        )
        for r in job_rows
    ]
    sim = Simulator(
        machines=int(cluster["machines"]),
        repair_minutes=int(cluster.get("repair_minutes", 30)),
        starve_threshold=int(cluster.get("starve_threshold", 40)),
        strategy=strategy,
    )
    failures = [e for e in events if e.get("type") == "machine_failure"]
    return sim.run(jobs, failures)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cluster", required=True)
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--events", required=True)
    ap.add_argument("--strategy", default="priority_preempt")
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    cluster = json.loads(Path(args.cluster).read_text(encoding="utf-8"))
    jobs = load_jsonl(Path(args.jobs))
    events = load_jsonl(Path(args.events))

    primary = run_once(cluster, jobs, events, args.strategy)
    baseline = run_once(cluster, jobs, events, "fifo")

    report = {
        "strategy": args.strategy,
        "metrics": primary.metrics,
        "baseline_metrics": baseline.metrics,
        "events_sample": primary.log[:50],
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report["metrics"], ensure_ascii=False))


if __name__ == "__main__":
    main()
