"""Register ENVI/SARScape MCP and user-level VS Code agent."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from envi_mcp.engine import ENVIEngineManager  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(PROJECT_ROOT), help="Installed repository root.")
    parser.add_argument("--python", dest="python_exe", help="Python executable for the MCP server.")
    parser.add_argument("--mcp-json", help="VS Code user mcp.json path.")
    parser.add_argument("--prompts-dir", help="VS Code user prompts directory.")
    parser.add_argument("--taskengine", help="Explicit taskengine.exe path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    python_exe = Path(args.python_exe).resolve() if args.python_exe else repo_root / ".venv312" / "Scripts" / "python.exe"
    user_root = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))) / "Code" / "User"
    mcp_json = Path(args.mcp_json).resolve() if args.mcp_json else user_root / "mcp.json"
    prompts_dir = Path(args.prompts_dir).resolve() if args.prompts_dir else user_root / "prompts"
    taskengine = Path(args.taskengine).resolve() if args.taskengine else ENVIEngineManager().discover_taskengine().path

    update_user_mcp(mcp_json, repo_root, python_exe, taskengine)
    render_agent(repo_root, python_exe, taskengine, prompts_dir)
    print(json.dumps({"mcp_json": str(mcp_json), "agent": str(prompts_dir / "envi-sarscape.agent.md")}, indent=2))
    return 0


def update_user_mcp(mcp_json: Path, repo_root: Path, python_exe: Path, taskengine: Optional[Path]) -> None:
    mcp_json.parent.mkdir(parents=True, exist_ok=True)
    data = read_json_file(mcp_json)
    servers = data.get("servers")
    if not isinstance(servers, dict):
        servers = {}

    env = {
        "PYTHONUTF8": "1",
        "PYTHONPATH": str(repo_root / "src"),
    }
    if taskengine:
        env = {**env, "ENVI_ENGINE": str(taskengine)}

    data = {
        **data,
        "servers": {
            **servers,
            "envi-sarscape": {
                "type": "stdio",
                "command": str(python_exe),
                "args": ["-m", "envi_mcp.server"],
                "cwd": str(repo_root),
                "env": env,
            },
        },
    }
    mcp_json.write_text(json.dumps(data, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def render_agent(repo_root: Path, python_exe: Path, taskengine: Optional[Path], prompts_dir: Path) -> None:
    prompts_dir.mkdir(parents=True, exist_ok=True)
    template_path = repo_root / "agents" / "envi-sarscape.agent.md"
    text = template_path.read_text(encoding="utf-8")
    replacements = {
        "{{REPO_ROOT}}": str(repo_root),
        "{{PYTHON_EXE}}": str(python_exe),
        "{{TASKENGINE_PATH}}": str(taskengine) if taskengine else "auto-discovery",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    (prompts_dir / "envi-sarscape.agent.md").write_text(text, encoding="utf-8")


def read_json_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return data


if __name__ == "__main__":
    raise SystemExit(main())