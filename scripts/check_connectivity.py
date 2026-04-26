"""Run the local ENVI/SARScape connectivity acceptance check."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from envi_mcp.engine import ENVIEngineManager  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", dest="json_path", help="Write the full report to this JSON file.")
    parser.add_argument("--engine", help="Explicit taskengine.exe path. ENVI_ENGINE still has priority.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    manager = ENVIEngineManager(engine_path=args.engine)
    report = manager.connectivity_check()

    if args.json_path:
        json_path = Path(args.json_path)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    _print_summary(report)
    return 0 if report.get("success") else 1


def _print_summary(report: dict[str, Any]) -> None:
    taskengine = report.get("taskengine", {})
    print("ENVI/SARScape connectivity check")
    print(f"  Python: {report.get('python', {}).get('executable')}")
    print(f"  envipyengine importable: {report.get('envipyengine_importable')}")
    print(f"  taskengine: {taskengine.get('path')} ({taskengine.get('source')})")
    print(f"  ENVI started: {report.get('envi_started')}")
    print(f"  task count: {report.get('task_count')}")
    print(f"  SAR task count: {report.get('sar_task_count')}")
    examples = report.get("sar_task_examples") or []
    if examples:
        print("  SAR task examples:")
        for task_name in examples[:10]:
            print(f"    - {task_name}")
    errors = report.get("errors") or []
    if errors:
        print("  Errors:")
        for error in errors:
            print(f"    - {error}")
    suggestions = report.get("suggestions") or []
    if suggestions:
        print("  Suggestions:")
        for suggestion in suggestions:
            print(f"    - {suggestion}")
    print(f"  SUCCESS: {report.get('success')}")


if __name__ == "__main__":
    raise SystemExit(main())