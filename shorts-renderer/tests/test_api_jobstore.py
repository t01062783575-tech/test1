from renderer.api.jobstore import STATUS_COMPLETED, STATUS_FAILED, STATUS_PROCESSING, STATUS_QUEUED, JobStore


def test_create_and_get(tmp_path):
    store = JobStore(str(tmp_path / "jobs.sqlite3"))
    record = store.create_queued("job-1", '{"job_id": "job-1"}')
    assert record.status == STATUS_QUEUED

    fetched = store.get("job-1")
    assert fetched is not None
    assert fetched.job_id == "job-1"
    assert fetched.status == STATUS_QUEUED


def test_get_missing_returns_none(tmp_path):
    store = JobStore(str(tmp_path / "jobs.sqlite3"))
    assert store.get("does-not-exist") is None


def test_status_transitions(tmp_path):
    store = JobStore(str(tmp_path / "jobs.sqlite3"))
    store.create_queued("job-1", "{}")

    store.mark_processing("job-1")
    assert store.get("job-1").status == STATUS_PROCESSING

    store.mark_completed("job-1", output_path="/tmp/out.mp4", width=1080, height=1920, duration=12.0)
    record = store.get("job-1")
    assert record.status == STATUS_COMPLETED
    assert record.output_path == "/tmp/out.mp4"
    assert record.width == 1080
    assert record.duration == 12.0


def test_failed_transition_records_error(tmp_path):
    store = JobStore(str(tmp_path / "jobs.sqlite3"))
    store.create_queued("job-1", "{}")
    store.mark_failed("job-1", error="ffmpeg exited with code 1")

    record = store.get("job-1")
    assert record.status == STATUS_FAILED
    assert "exited with code 1" in record.error


def test_persists_across_reconnection(tmp_path):
    db_path = str(tmp_path / "jobs.sqlite3")
    store1 = JobStore(db_path)
    store1.create_queued("job-1", "{}")
    store1.mark_completed("job-1", output_path="/tmp/out.mp4", width=1080, height=1920, duration=5.0)
    store1.close()

    store2 = JobStore(db_path)  # simulates a server restart
    record = store2.get("job-1")
    assert record is not None
    assert record.status == STATUS_COMPLETED
    assert record.width == 1080


def test_to_public_dict_shape(tmp_path):
    store = JobStore(str(tmp_path / "jobs.sqlite3"))
    record = store.create_queued("job-1", "{}")
    d = record.to_public_dict()
    assert set(d.keys()) == {"job_id", "status", "width", "height", "duration", "error", "created_at", "updated_at"}
    assert "spec_json" not in d  # internal field, not part of the public API surface
