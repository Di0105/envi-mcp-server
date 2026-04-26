"""FastMCP entry point for ENVI/SARScape automation."""

from __future__ import annotations

from typing import Any

try:
    from fastmcp import FastMCP
except ImportError:
    FastMCP = None

from .tools import general, interferometry, postprocess, sar_import, utils

INSTRUCTIONS = """
Use this server to inspect and run ENVI/SARScape tasks from a local ENVI Task
Engine installation. Recommended InSAR DEM flow: import -> baseline ->
coregister -> interferogram -> coherence -> filter -> unwrap -> GCP -> refine
-> phase2height -> geocode -> validate. Start with check_envi_connectivity and
list_envi_tasks before running data-processing tools, because SARScape task
names can differ by version.
""".strip()


def create_mcp() -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "FastMCP is required to run the MCP server. Use Python 3.10+ and run: "
            "python -m pip install -e .[mcp]"
        )
    mcp = FastMCP("ENVI-SARScape", instructions=INSTRUCTIONS)
    for module in (general, sar_import, interferometry, postprocess, utils):
        module.register(mcp)
    return mcp


mcp = create_mcp() if FastMCP is not None else None


def main() -> None:
    active_mcp = mcp or create_mcp()
    try:
        active_mcp.run(transport="stdio")
    except TypeError:
        active_mcp.run()


if __name__ == "__main__":
    main()