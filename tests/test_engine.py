from __future__ import annotations

from pathlib import Path

from envi_mcp.engine import ENVIEngineManager


class FakeTask:
    def __init__(self, name: str, should_fail: bool = False) -> None:
        self.name = name
        self.should_fail = should_fail
        self.parameters = {"input_file": Path("C:/data/input.dat")}
        self.outputs = {"output_file": Path("C:/data/output.dat")}

    def execute(self) -> dict[str, str]:
        if self.should_fail:
            raise RuntimeError("task exploded")
        return {"status": "done"}


class FakeEngine:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.created_tasks: list[FakeTask] = []

    def task_names(self) -> tuple[str, ...]:
        return ("OpenRaster", "SARscape Baseline", "SAR Coherence")

    def task(self, task_name: str) -> FakeTask:
        task = FakeTask(task_name, should_fail=self.should_fail)
        self.created_tasks.append(task)
        return task


def test_discovery_prefers_envi_engine(monkeypatch, tmp_path) -> None:
    env_dir = tmp_path / "env"
    constructor_dir = tmp_path / "constructor"
    env_dir.mkdir()
    constructor_dir.mkdir()
    env_taskengine = env_dir / "taskengine.exe"
    constructor_taskengine = constructor_dir / "taskengine.exe"
    env_taskengine.write_text("", encoding="utf-8")
    constructor_taskengine.write_text("", encoding="utf-8")
    monkeypatch.setenv("ENVI_ENGINE", str(env_taskengine))

    manager = ENVIEngineManager(engine_path=constructor_taskengine)
    result = manager.discover_taskengine()

    assert result.path == env_taskengine
    assert result.source == "ENVI_ENGINE"


def test_list_tasks_filters_case_insensitively() -> None:
    manager = ENVIEngineManager()
    manager._engine = FakeEngine()

    assert manager.list_tasks("sar") == ["SAR Coherence", "SARscape Baseline"]


def test_task_info_serializes_path_parameters() -> None:
    manager = ENVIEngineManager()
    manager._engine = FakeEngine()

    info = manager.task_info("SARscape Baseline")

    assert info["name"] == "SARscape Baseline"
    assert info["parameters"]["input_file"] == str(Path("C:/data/input.dat"))


def test_run_task_success_sets_params_and_collects_outputs() -> None:
    fake_engine = FakeEngine()
    manager = ENVIEngineManager()
    manager._engine = fake_engine

    result = manager.run_task("SARscape Baseline", {"master_slc": "master.slc"}, timeout=10)

    assert result["success"] is True
    assert result["result"] == {"status": "done"}
    assert result["outputs"]["outputs"]["output_file"] == str(Path("C:/data/output.dat"))
    assert fake_engine.created_tasks[0].master_slc == "master.slc"


def test_run_task_failure_returns_error_dict() -> None:
    manager = ENVIEngineManager()
    manager._engine = FakeEngine(should_fail=True)

    result = manager.run_task("SARscape Baseline", {}, timeout=10)

    assert result["success"] is False
    assert result["error_type"] == "RuntimeError"