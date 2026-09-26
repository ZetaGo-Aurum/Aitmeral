"""Background job engine — shared by the TUI queue and the web UI."""

from __future__ import annotations

import copy
import os
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from aureus.core import pipeline
from aureus.core.media import human_size
from aureus.core.options import Settings
from aureus.core.sysinfo import total_ram_gb


class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    CANCELED = "canceled"

ACTIVE = {JobStatus.QUEUED, JobStatus.RUNNING}


@dataclass
class Job:
    id: str
    kind: str  # 'url' | 'file'
    source: str
    display: str
    settings: dict
    output_dir: str
    status: str = JobStatus.QUEUED
    stage: str = ""
    stage_key: str = ""
    progress: float = 0.0
    detail: str = ""
    error: str = ""
    output_path: str = ""
    output_name: str = ""
    result: dict = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    started: float = 0.0
    finished: float = 0.0
    log_tail: list = field(default_factory=list)
    cancel_event: threading.Event = field(default_factory=threading.Event)

    def to_public(self) -> dict:
        return {
            "id": self.id,
            "kind": self.kind,
            "source": self.source,
            "display": self.display,
            "settings": copy.deepcopy(self.settings),
            "output_dir": self.output_dir,
            "status": self.status,
            "stage": self.stage,
            "progress": round(self.progress, 4),
            "detail": self.detail,
            "error": self.error,
            "output_path": self.output_path,
            "output_name": self.output_name,
            "result": copy.deepcopy(self.result),
            "created": self.created,
            "started": self.started,
            "finished": self.finished,
            "elapsed": max(0.0, (self.finished or time.time()) - (self.started or self.created)),
            "log_tail": list(self.log_tail[-12:]),
        }


# overall progress weights across stages
STAGE_BASE = {"prepare": 0.0, "download": 0.0, "probe": 0.38, "process": 0.40, "finalize": 0.97, "done": 1.0}
STAGE_SPAN = {"prepare": 0.38, "download": 0.38, "probe": 0.02, "process": 0.57, "finalize": 0.03, "done": 0.0}


class JobManager:
    def __init__(self, output_dir: str = "aureus_output", max_workers: Optional[int] = None):
        self.default_output_dir = output_dir
        self._jobs: Dict[str, Job] = {}
        self._order: List[str] = []
        self._lock = threading.RLock()
        self._queue: "queue.Queue[str]" = queue.Queue()
        if max_workers is None:
            max_workers = 2 if total_ram_gb() >= 16 else 1
        self.max_workers = max(1, int(max_workers))
        self._stop = threading.Event()
        for i in range(self.max_workers):
            threading.Thread(target=self._worker, name=f"aureus-worker-{i}", daemon=True).start()

    # ------------------------------------------------------------- public
    def submit(self, kind: str, source: str, settings: dict, output_dir: Optional[str] = None) -> Job:
        if kind not in ("url", "file"):
            raise ValueError("kind must be 'url' or 'file'")
        s = Settings.from_dict(settings)
        job = Job(
            id=uuid.uuid4().hex[:10],
            kind=kind,
            source=source,
            display=source if kind == "url" else source,
            settings=s.to_dict(),
            output_dir=output_dir or self.default_output_dir,
        )
        with self._lock:
            self._jobs[job.id] = job
            self._order.append(job.id)
        self._queue.put(job.id)
        return job

    def list(self) -> List[Job]:
        with self._lock:
            return [self._jobs[j] for j in self._order]

    def get(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
        if not job or job.status not in ACTIVE:
            return False
        job.cancel_event.set()
        if job.status == JobStatus.QUEUED:
            job.status = JobStatus.CANCELED
            job.finished = time.time()
            job.error = "Canceled before start"
        return True

    def remove(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job or job.status in ACTIVE:
                return False
            del self._jobs[job_id]
            self._order.remove(job_id)
        return True

    def active_count(self) -> int:
        with self._lock:
            return sum(1 for j in self._jobs.values() if j.status in ACTIVE)

    # ------------------------------------------------------------- worker
    def _worker(self):
        while not self._stop.is_set():
            try:
                job_id = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            with self._lock:
                job = self._jobs.get(job_id)
            if job is None or job.status == JobStatus.CANCELED:
                continue
            self._run_job(job)

    def _run_job(self, job: Job):
        job.status = JobStatus.RUNNING
        job.started = time.time()
        job.stage = "Preparing"
        job.stage_key = "prepare"

        def report(stage_key: str, frac: float, detail: str):
            base = STAGE_BASE.get(stage_key, 0.0)
            span = STAGE_SPAN.get(stage_key, 0.0)
            if frac >= 0:
                job.progress = min(100.0, (base + span * max(0.0, min(1.0, frac))) * 100.0)
            job.stage_key = stage_key
            job.stage = {
                "prepare": "Preparing", "download": "Downloading", "probe": "Analyzing",
                "process": "Enhancing & Encoding", "finalize": "Finalizing", "done": "Done",
            }.get(stage_key, stage_key.title())
            if detail:
                job.detail = detail[:160]

        try:
            s = Settings.from_dict(job.settings)
            res = pipeline.run_job(
                kind=job.kind, source=job.source, settings=s,
                output_dir=job.output_dir, report=report,
                cancel_event=job.cancel_event, proc_hook=None,
            )
            job.status = JobStatus.DONE
            job.progress = 100.0
            job.stage = "Done"
            job.detail = f"Finished in {int(res.elapsed)}s"
            job.output_path = res.output_path
            job.output_name = os.path.basename(res.output_path)
            summary = res.summary()
            job.result = {
                "summary": summary,
                "notes": [n for n in res.notes],
            }
        except pipeline.CancelledError:
            job.status = JobStatus.CANCELED
            job.stage = "Canceled"
            job.detail = "Cancelled by user"
        except pipeline.RequirementError as exc:
            job.status = JobStatus.ERROR
            job.stage = "Requirement"
            job.error = str(exc)
        except Exception as exc:  # noqa: BLE001 — surface any failure to the UI
            job.status = JobStatus.ERROR
            job.stage = "Error"
            job.error = str(exc)[:1000]
        finally:
            job.finished = time.time()
