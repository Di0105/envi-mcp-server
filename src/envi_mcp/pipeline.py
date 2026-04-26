"""Shared InSAR DEM pipeline state and execution helpers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional, Sequence

import yaml

from .engine import ENVIEngineManager, get_default_manager, to_jsonable

logger = logging.getLogger(__name__)

PIPELINE_STEPS: tuple[str, ...] = (
    "baseline",
    "coregistration",
    "interferogram",
    "coherence",
    "filter",
    "unwrap",
    "gcp",
    "refine",
    "phase_to_height",
    "geocode",
    "mosaic",
)


@dataclass(frozen=True)
class TaskStepDefinition:
    name: str
    candidate_names: tuple[str, ...]
    keywords: tuple[str, ...]
    output_key: str
    output_suffix: str
    requires: tuple[str, ...] = ()


STEP_DEFINITIONS: Mapping[str, TaskStepDefinition] = MappingProxyType(
    {
        "baseline": TaskStepDefinition(
            name="baseline",
            candidate_names=("SARscape Baseline", "Baseline Estimation"),
            keywords=("baseline",),
            output_key="baseline",
            output_suffix="baseline.json",
        ),
        "coregistration": TaskStepDefinition(
            name="coregistration",
            candidate_names=("SARscape Coregistration", "Coregistration"),
            keywords=("coreg",),
            output_key="coregistered_pair",
            output_suffix="coregistered_pair.dat",
            requires=("baseline",),
        ),
        "interferogram": TaskStepDefinition(
            name="interferogram",
            candidate_names=("SARscape Interferogram", "Interferogram Generation"),
            keywords=("interferogram",),
            output_key="interferogram",
            output_suffix="interferogram.dat",
            requires=("coregistered_pair",),
        ),
        "coherence": TaskStepDefinition(
            name="coherence",
            candidate_names=("SARscape Coherence", "Coherence Generation"),
            keywords=("coherence",),
            output_key="coherence",
            output_suffix="coherence.dat",
            requires=("interferogram",),
        ),
        "filter": TaskStepDefinition(
            name="filter",
            candidate_names=("SARscape Adaptive Filter", "Goldstein Filter"),
            keywords=("filter",),
            output_key="filtered_interferogram",
            output_suffix="filtered_interferogram.dat",
            requires=("interferogram", "coherence"),
        ),
        "unwrap": TaskStepDefinition(
            name="unwrap",
            candidate_names=("SARscape Phase Unwrapping", "Phase Unwrapping"),
            keywords=("unwrap",),
            output_key="unwrapped_phase",
            output_suffix="unwrapped_phase.dat",
            requires=("filtered_interferogram", "coherence"),
        ),
        "gcp": TaskStepDefinition(
            name="gcp",
            candidate_names=("SARscape GCP Generation", "GCP Generation"),
            keywords=("gcp",),
            output_key="gcp_file",
            output_suffix="gcps.txt",
            requires=("unwrapped_phase",),
        ),
        "refine": TaskStepDefinition(
            name="refine",
            candidate_names=("SARscape Orbital Refinement", "Refinement and Reflattening"),
            keywords=("refine",),
            output_key="refined_phase",
            output_suffix="refined_phase.dat",
            requires=("unwrapped_phase", "gcp_file"),
        ),
        "phase_to_height": TaskStepDefinition(
            name="phase_to_height",
            candidate_names=("SARscape Phase to Height", "Phase To Height"),
            keywords=("height",),
            output_key="height_raster",
            output_suffix="height.dat",
            requires=("refined_phase",),
        ),
        "geocode": TaskStepDefinition(
            name="geocode",
            candidate_names=("SARscape Geocoding", "Geocoding"),
            keywords=("geocode",),
            output_key="geocoded_dem",
            output_suffix="dem_geocoded.tif",
            requires=("height_raster",),
        ),
        "mosaic": TaskStepDefinition(
            name="mosaic",
            candidate_names=("SARscape DEM Mosaic", "DEM Mosaic"),
            keywords=("mosaic",),
            output_key="dem_mosaic",
            output_suffix="dem_mosaic.tif",
            requires=("geocoded_dem",),
        ),
    }
)


@dataclass(frozen=True)
class PipelineState:
    completed_steps: tuple[str, ...] = ()
    outputs: Mapping[str, Any] = field(default_factory=dict)
    failed_step: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", MappingProxyType(dict(self.outputs)))

    @classmethod
    def load(cls, path: Path) -> "PipelineState":
        if not path.exists():
            return cls()
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            completed_steps=tuple(data.get("completed_steps", ())),
            outputs=data.get("outputs", {}),
            failed_step=data.get("failed_step"),
            error=data.get("error"),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed_steps": list(self.completed_steps),
            "outputs": to_jsonable(dict(self.outputs)),
            "failed_step": self.failed_step,
            "error": self.error,
        }

    def mark_completed(self, step: str, outputs: Mapping[str, Any]) -> "PipelineState":
        completed_steps = tuple(dict.fromkeys((*self.completed_steps, step)))
        return replace(
            self,
            completed_steps=completed_steps,
            outputs={**dict(self.outputs), **dict(outputs)},
            failed_step=None,
            error=None,
        )

    def mark_failed(self, step: str, error: str) -> "PipelineState":
        return replace(self, failed_step=step, error=error)


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError("Pipeline config must be a YAML mapping.")
    return data


def resolve_pipeline_steps(
    steps: Sequence[str] = PIPELINE_STEPS,
    skip_to: Optional[str] = None,
    only: Optional[str] = None,
    completed_steps: Sequence[str] = (),
) -> tuple[str, ...]:
    if only:
        _ensure_valid_step(only, steps)
        return (only,)

    selected = tuple(steps)
    if skip_to:
        _ensure_valid_step(skip_to, steps)
        start_index = selected.index(skip_to)
        selected = selected[start_index:]

    completed = frozenset(completed_steps)
    return tuple(step for step in selected if step not in completed)


def run_pipeline(
    config: Mapping[str, Any],
    output_dir: Path,
    skip_to: Optional[str] = None,
    only: Optional[str] = None,
    dry_run: bool = False,
    resume: bool = False,
    state_path: Optional[Path] = None,
    manager: Optional[ENVIEngineManager] = None,
    timeout: int = 3600,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    active_state_path = state_path or output_dir / "state.json"
    state = PipelineState.load(active_state_path) if resume else PipelineState()
    selected_steps = resolve_pipeline_steps(
        skip_to=skip_to,
        only=only,
        completed_steps=state.completed_steps if resume else (),
    )
    active_manager = manager or get_default_manager()
    results: list[dict[str, Any]] = []

    for step in selected_steps:
        definition = STEP_DEFINITIONS[step]
        params = build_step_params(config, definition, output_dir, state)
        missing = tuple(key for key in definition.requires if key not in state.outputs)
        if missing:
            error = f"Step {step} requires missing outputs: {', '.join(missing)}"
            state = state.mark_failed(step, error)
            state.save(active_state_path)
            results.append({"step": step, "success": False, "error": error})
            break

        if dry_run:
            results.append({"step": step, "success": True, "dry_run": True, "params": params})
            state = state.mark_completed(step, {definition.output_key: params["output_file"]})
            continue

        logger.info("Running pipeline step: %s", step)
        result = active_manager.run_first_available_task(
            definition.candidate_names,
            definition.keywords,
            params,
            timeout=timeout,
        )
        results.append({"step": step, **result})
        if not result.get("success"):
            state = state.mark_failed(step, str(result.get("error", "Unknown failure")))
            state.save(active_state_path)
            break

        step_outputs = {
            definition.output_key: params["output_file"],
            f"{step}_task_outputs": result.get("outputs", {}),
        }
        state = state.mark_completed(step, step_outputs)
        state.save(active_state_path)

    return {
        "success": all(result.get("success") for result in results),
        "steps": results,
        "state": state.to_dict(),
        "state_path": str(active_state_path),
    }


def build_step_params(
    config: Mapping[str, Any],
    definition: TaskStepDefinition,
    output_dir: Path,
    state: PipelineState,
) -> dict[str, Any]:
    common = _mapping(config.get("common", {}))
    step_config = _mapping(config.get("steps", {}).get(definition.name, {}))
    output_file = output_dir / definition.output_suffix
    return {
        **common,
        **dict(state.outputs),
        **step_config,
        "output_dir": str(output_dir),
        "output_file": str(step_config.get("output_file", output_file)),
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError("Pipeline config sections must be mappings.")
    return value


def _ensure_valid_step(step: str, steps: Sequence[str]) -> None:
    if step not in steps:
        raise ValueError(f"Unknown pipeline step: {step}. Valid steps: {', '.join(steps)}")