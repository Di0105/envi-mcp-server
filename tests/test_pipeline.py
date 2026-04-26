from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from envi_mcp.pipeline import PipelineState, resolve_pipeline_steps, run_pipeline


class FakeManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def run_first_available_task(
        self,
        candidate_names: Sequence[str],
        keywords: Sequence[str],
        params: Mapping[str, Any],
        timeout: int = 3600,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "candidate_names": tuple(candidate_names),
                "keywords": tuple(keywords),
                "params": dict(params),
                "timeout": timeout,
            }
        )
        return {"success": True, "outputs": {"ok": True}}


def test_pipeline_state_load_save_roundtrip(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    state = PipelineState().mark_completed("baseline", {"baseline": "baseline.json"})

    state.save(state_path)
    loaded = PipelineState.load(state_path)

    assert loaded.completed_steps == ("baseline",)
    assert loaded.outputs["baseline"] == "baseline.json"


def test_resolve_pipeline_steps_supports_skip_only_and_resume() -> None:
    assert resolve_pipeline_steps(skip_to="coherence")[:2] == ("coherence", "filter")
    assert resolve_pipeline_steps(only="unwrap") == ("unwrap",)
    assert "baseline" not in resolve_pipeline_steps(completed_steps=("baseline",))


def test_run_pipeline_dry_run_preserves_coherence_before_unwrap(tmp_path: Path) -> None:
    result = run_pipeline(config={}, output_dir=tmp_path, dry_run=True)
    step_names = [step["step"] for step in result["steps"]]

    assert result["success"] is True
    assert step_names.index("coherence") < step_names.index("unwrap")
    assert result["state"]["outputs"]["coherence"].endswith("coherence.dat")


def test_run_pipeline_only_unwrap_fails_without_coherence(tmp_path: Path) -> None:
    result = run_pipeline(config={}, output_dir=tmp_path, only="unwrap", manager=FakeManager())

    assert result["success"] is False
    assert "coherence" in result["steps"][0]["error"]


def test_run_pipeline_resume_skips_completed_and_uses_state_outputs(tmp_path: Path) -> None:
    state_path = tmp_path / "state.json"
    PipelineState().mark_completed("baseline", {"baseline": "baseline.json"}).save(state_path)
    manager = FakeManager()

    result = run_pipeline(
        config={},
        output_dir=tmp_path,
        only="coregistration",
        resume=True,
        state_path=state_path,
        manager=manager,
    )

    assert result["success"] is True
    assert manager.calls[0]["params"]["baseline"] == "baseline.json"