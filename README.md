# ENVI/SARScape MCP Server

FastMCP server and standalone scripts for discovering a local ENVI Task Engine installation, checking SARScape task visibility, and running ENVI/SARScape InSAR DEM workflow steps.

## One-Command Install

For Windows users with ENVI/SARScape, Python Launcher, and Git installed:

```powershell
$script = "$env:TEMP\install-envi-mcp.ps1"
Invoke-WebRequest "https://raw.githubusercontent.com/Di0105/envi-mcp-server/main/scripts/install_user.ps1" -OutFile $script
powershell -ExecutionPolicy Bypass -File $script
```

This clones the repo to `%USERPROFILE%\envi-mcp-server`, creates `.venv312`, installs the MCP extra, runs connectivity, registers the VS Code user-level MCP server, and installs the workspace-agnostic `envi-sarscape` agent.

After install, open any VS Code workspace and choose the `envi-sarscape` agent.

The local acceptance target is:

1. Python can import `envipyengine`.
2. The server can auto-detect or use a configured ENVI 5.6 Task Engine path.
3. `Engine("ENVI")` starts successfully.
4. ENVI tasks can be listed.
5. SARScape/SAR-related tasks are visible.

The default Windows shortcut discovery hint is:

```text
%USERPROFILE%\Desktop\ENVI 5.6 (64-bit).lnk
```

## Project Layout

```text
envi-mcp-server/
??? pyproject.toml
??? README.md
??? src/envi_mcp/
?   ??? __init__.py
?   ??? engine.py
?   ??? pipeline.py
?   ??? schemas.py
?   ??? server.py
?   ??? tools/
??? scripts/
?   ??? check_connectivity.py
?   ??? run_insar_dem.py
?   ??? config_template.yaml
?   ??? compare_dems.py
??? tests/
??? .vscode/mcp.json
```

## Setup

For connectivity checks and standalone scripts, Python 3.9+ is enough. Use the Python environment that can import ENVI Task Engine packages. If ENVI provides its own Python, run these commands from that environment.

```powershell
python -m pip install -e .[dev]
```

For the MCP server, use Python 3.10+ because `fastmcp` requires it:

```powershell
py -3.12 -m venv .venv312
.\.venv312\Scripts\python.exe -m pip install -e .[mcp,dev]
```

Optional DEM comparison dependencies:

```powershell
python -m pip install -e .[compare]
```

If auto-discovery misses ENVI, set `ENVI_ENGINE` to the full `taskengine.exe` path:

```powershell
$env:ENVI_ENGINE = "C:\????\taskengine.exe"
$env:PYTHONUTF8 = "1"
```

Discovery checks, in order:

- `ENVI_ENGINE`
- explicit script/manager path
- common Harris, NV5, Exelis, and ITT install paths
- Windows registry uninstall entries
- the ENVI 5.6 desktop shortcut
- `PATH`

## Connectivity Check

Run the real local acceptance script:

```powershell
python scripts/check_connectivity.py --json connectivity_report.json
.\.venv312\Scripts\python.exe scripts/check_connectivity.py --json connectivity_report_py312.json
```

Success requires `envipyengine` import, ENVI startup, a non-empty task list, and at least one SARScape/SAR-related task.

For a quick task-name inspection after the first successful connection, use the MCP tools `list_envi_tasks("SAR")` and `list_envi_tasks("SARscape")`.

## MCP Configuration

This repo includes a project-level config at `.vscode/mcp.json`:

```json
{
  "servers": {
    "envi-sarscape": {
      "type": "stdio",
      "command": "${workspaceFolder}\\.venv312\\Scripts\\python.exe",
      "args": ["-m", "envi_mcp.server"],
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src",
        "PYTHONUTF8": "1"
      }
    }
  }
}
```

Make sure the `python` resolved by this MCP config is a Python 3.10+ environment with `python -m pip install -e .[mcp]` already run.

To register this server globally for all VS Code workspaces and install the user-level agent:

```powershell
.\.venv312\Scripts\python.exe scripts/register_vscode_agent.py --repo-root . --python .\.venv312\Scripts\python.exe
```

The global agent template lives at `agents/envi-sarscape.agent.md` and is rendered into `%APPDATA%\Code\User\prompts\envi-sarscape.agent.md`.

User-level template:

```json
{
  "servers": {
    "envi-sarscape": {
      "command": "python",
      "args": ["-m", "envi_mcp.server"],
      "cwd": "C:\\Users\\<you>\\envi-mcp-server",
      "env": {
        "PYTHONPATH": "C:\\Users\\<you>\\envi-mcp-server\\src",
        "PYTHONUTF8": "1",
        "ENVI_ENGINE": "C:\\????\\taskengine.exe"
      }
    }
  }
}
```

`ENVI_ENGINE` is optional when auto-discovery works.

## MCP Tools

The server registers 37 tools across five modules:

- General: connectivity, task discovery, task listing, task info, exact task execution.
- SAR import: Sentinel-1, RADARSAT-2, ALOS/PALSAR, TerraSAR-X, COSMO-SkyMed, generic SAR import.
- Interferometry: baseline, coregistration, interferogram, coherence, adaptive filtering, unwrapping, GCP, refinement/reflattening, phase-to-height, geocoding, mosaic, flat-earth removal, multilooking.
- Postprocess: terrain correction, void fill, smoothing, GeoTIFF export, quality mask, statistics, DEM comparison, raster clip.
- Utils: pipeline step listing, input path validation, output workspace creation, pipeline state loading, full InSAR DEM pipeline.

SARScape task names differ across installs, so logical tools search installed ENVI task names by exact candidates and fallback keywords. If a wrapper cannot find a matching task, run `list_envi_tasks` to confirm the local name, then call `run_envi_task` directly.

## InSAR DEM Script

Copy and edit the config template:

```powershell
python scripts/run_insar_dem.py --config scripts/config_template.yaml --dry-run
python scripts/run_insar_dem.py --config scripts/config_template.yaml --resume
python scripts/run_insar_dem.py --config scripts/config_template.yaml --skip-to coherence
python scripts/run_insar_dem.py --config scripts/config_template.yaml --only unwrap
```

The script writes:

- `state.json`
- `pipeline.log`
- `pipeline_result.json`

Pipeline order is fixed as:

```text
baseline -> coregistration -> interferogram -> coherence -> filter -> unwrap -> gcp -> refine -> phase_to_height -> geocode -> mosaic
```

`coherence` is always produced before `unwrap`, and resumed runs require the needed upstream output keys to exist in `state.json`.

## DEM Comparison

After installing the comparison extra, run:

```powershell
python scripts/compare_dems.py --dem C:\data\dem.tif --reference C:\data\reference_dem.tif --output-dir C:\data\dem_compare
```

Outputs:

- `accuracy_report.txt`
- `diff_map.png`
- `diff_histogram.png`
- `scatter.png`

## Tests

Mock tests do not require a real ENVI license:

```powershell
python -m pytest
```

They cover engine discovery priority, task filtering, task metadata serialization, task success/failure handling, pipeline state load/save, and skip/resume/only logic.

## Notes

- ENVI/SARScape may require an available license; `Engine("ENVI")` can consume one.
- Actual InSAR DEM correctness needs a real SLC pair and reference DEM.
- SARScape task names are version-dependent; inspect local names after connectivity succeeds.
- Keep project and intermediate output paths ASCII-only when using C/C++ geospatial libraries on Windows.