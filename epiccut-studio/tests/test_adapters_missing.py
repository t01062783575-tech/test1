"""RIFE and Real-ESRGAN being absent must never crash the base editor —
detection reports unavailable cleanly, and calling the real (Phase D) body
anyway raises a normal Python exception rather than crashing the process."""

import pytest

from epiccut.adapters.real_esrgan import RealEsrganAdapter
from epiccut.adapters.rife import RifeAdapter
from epiccut.engine.retiming import compute_retiming


def test_rife_unavailable_by_default_in_this_environment(monkeypatch):
    monkeypatch.delenv("EPICCUT_RIFE_PATH", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    adapter = RifeAdapter()
    assert adapter.is_available() is False
    assert adapter.unavailable_reason() is not None
    assert "RIFE" in adapter.unavailable_reason()


def test_rife_interpolate_raises_cleanly_when_unavailable(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    adapter = RifeAdapter()
    with pytest.raises(RuntimeError):
        adapter.interpolate("in/", "out/", target_fps=60)


def test_real_esrgan_unavailable_by_default(monkeypatch):
    monkeypatch.delenv("EPICCUT_REALESRGAN_PATH", raising=False)
    monkeypatch.setattr("shutil.which", lambda name: None)
    adapter = RealEsrganAdapter()
    assert adapter.is_available() is False
    assert "Real-ESRGAN" in adapter.unavailable_reason()


def test_real_esrgan_upscale_raises_cleanly_when_unavailable(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    adapter = RealEsrganAdapter()
    with pytest.raises(RuntimeError):
        adapter.upscale("in.mp4", "out.mp4", factor=2.0)


def test_rife_available_when_executable_configured(tmp_path):
    fake_binary = tmp_path / "rife-ncnn-vulkan"
    fake_binary.write_text("#!/bin/sh\n")
    fake_binary.chmod(0o755)
    adapter = RifeAdapter(executable=str(fake_binary))
    assert adapter.is_available() is True
    assert adapter.unavailable_reason() is None


def test_retiming_still_computes_without_any_adapter():
    """The core retiming/render path never imports or requires an adapter —
    engine.retiming works identically whether or not RIFE exists."""
    plan = compute_retiming(5.04, 12.0)
    assert plan.recommend_rife is True  # a *recommendation*, not a requirement
    assert plan.speed_factor > 0  # the plan itself never depends on RIFE being present
