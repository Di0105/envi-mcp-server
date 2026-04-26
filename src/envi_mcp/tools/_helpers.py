"""Shared helpers for MCP tool modules."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from ..engine import get_default_manager


def compact_params(**kwargs: Any) -> dict[str, Any]:
    return {key: value for key, value in kwargs.items() if value is not None}


def run_logical_task(
    candidate_names: Sequence[str],
    keywords: Sequence[str],
    params: Mapping[str, Any],
    timeout: int = 3600,
) -> dict[str, Any]:
    return get_default_manager().run_first_available_task(
        tuple(candidate_names),
        tuple(keywords),
        dict(params),
        timeout=timeout,
    )