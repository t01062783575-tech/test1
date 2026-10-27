"""Reliable job status/metadata storage.

sqlite3 (standard library — no new dependency) so job state survives a
server restart, unlike a plain in-memory dict. One connection guarded by a
lock: at this request volume (a handful of renders a day per
PHASE3_DESIGN.md) a single connection is simpler and exactly as fast as
anything else, and avoids sqlite's per-thread-connection footguns.
"""

from __future__ import annotations

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field

STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


@dataclass
class JobRecord:
    job_id: str
    status: str
    spec_json: str
    output_path: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_public_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "width": self.width,
            "height": self.height,
            "duration": self.duration,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class JobStore:
    def __init__(self, db_path: str):
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    spec_json TEXT NOT NULL,
                    output_path TEXT,
                    width INTEGER,
                    height INTEGER,
                    duration REAL,
                    error TEXT,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
                """
            )
            self._conn.commit()

    def get(self, job_id: str) -> JobRecord | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return self._row_to_record(row) if row else None

    def create_queued(self, job_id: str, spec_json: str) -> JobRecord:
        """Insert a new queued job. Caller must have already checked
        `get(job_id) is None` inside the same lock-protected section
        (see worker.py's submit) to make the enqueue+idempotency-check
        atomic rather than racing two concurrent POSTs with the same id."""
        now = time.time()
        record = JobRecord(job_id=job_id, status=STATUS_QUEUED, spec_json=spec_json, created_at=now, updated_at=now)
        with self._lock:
            self._conn.execute(
                "INSERT INTO jobs (job_id, status, spec_json, created_at, updated_at) VALUES (?,?,?,?,?)",
                (record.job_id, record.status, record.spec_json, record.created_at, record.updated_at),
            )
            self._conn.commit()
        return record

    def mark_processing(self, job_id: str) -> None:
        self._update(job_id, status=STATUS_PROCESSING)

    def mark_completed(self, job_id: str, *, output_path: str, width: int, height: int, duration: float) -> None:
        self._update(job_id, status=STATUS_COMPLETED, output_path=output_path, width=width, height=height, duration=duration)

    def mark_failed(self, job_id: str, *, error: str) -> None:
        self._update(job_id, status=STATUS_FAILED, error=error)

    def _update(self, job_id: str, **fields) -> None:
        fields["updated_at"] = time.time()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [job_id]
        with self._lock:
            self._conn.execute(f"UPDATE jobs SET {set_clause} WHERE job_id = ?", values)
            self._conn.commit()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> JobRecord:
        return JobRecord(
            job_id=row["job_id"], status=row["status"], spec_json=row["spec_json"],
            output_path=row["output_path"], width=row["width"], height=row["height"],
            duration=row["duration"], error=row["error"],
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    def close(self) -> None:
        with self._lock:
            self._conn.close()
