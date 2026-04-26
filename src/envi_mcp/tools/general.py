"""General ENVI discovery and task tools."""

from __future__ import annotations

from typing import Any

from ..engine import get_default_manager


def register(mcp: Any) -> None:
    manager = get_default_manager()

    @mcp.tool()
    def check_envi_connectivity() -> dict[str, Any]:
        """Check envipyengine import, ENVI startup, task listing, and SAR task visibility."""

        return manager.connectivity_check()

    @mcp.tool()
    def find_envi_taskengine(refresh: bool = False) -> dict[str, Any]:
        """Auto-detect the local ENVI taskengine.exe path."""

        return manager.discover_taskengine(refresh=refresh).to_dict()

    @mcp.tool()
    def list_envi_tasks(filter_str: str = "") -> dict[str, Any]:
        """List ENVI tasks, optionally filtering by a case-insensitive substring."""

        tasks = manager.list_tasks(filter_str=filter_str)
        return {"count": len(tasks), "tasks": tasks}

    @mcp.tool()
    def get_envi_task_info(task_name: str) -> dict[str, Any]:
        """Return best-effort metadata for a single ENVI task."""

        return manager.task_info(task_name)

    @mcp.tool()
    def run_envi_task(
        task_name: str,
        params: dict[str, Any],
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Run an exact ENVI task name with caller-provided parameters."""

        return manager.run_task(task_name, params, timeout=timeout)