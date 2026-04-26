"""Utility tools for paths, state, and end-to-end pipeline execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..pipeline import PIPELINE_STEPS, PipelineState, run_pipeline


def register(mcp: Any) -> None:
    @mcp.tool()
    def list_insar_pipeline_steps() -> dict[str, Any]:
        """List the fixed InSAR DEM pipeline order."""

        return {"steps": list(PIPELINE_STEPS)}

    @mcp.tool()
    def validate_input_paths(paths: list[str]) -> dict[str, Any]:
        """Check whether input paths exist before starting an ENVI run."""

        checks = [
            {"path": path, "exists": Path(path).exists()}
            for path in paths
        ]
        return {"success": all(item["exists"] for item in checks), "checks": checks}

    @mcp.tool()
    def create_output_workspace(output_dir: str) -> dict[str, Any]:
        """Create an output directory for intermediate and final products."""

        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        return {"success": True, "output_dir": str(path.resolve())}

    @mcp.tool()
    def load_pipeline_state(state_path: str) -> dict[str, Any]:
        """Load a saved InSAR DEM pipeline state.json."""

        return PipelineState.load(Path(state_path)).to_dict()

    @mcp.tool()
    def full_insar_dem_pipeline(
        config: dict[str, Any],
        output_dir: str,
        skip_to: Optional[str] = None,
        only: Optional[str] = None,
        dry_run: bool = False,
        resume: bool = False,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Run the full InSAR DEM pipeline with coherence generated before unwrapping."""

        return run_pipeline(
            config=config,
            output_dir=Path(output_dir),
            skip_to=skip_to,
            only=only,
            dry_run=dry_run,
            resume=resume,
            timeout=timeout,
        )