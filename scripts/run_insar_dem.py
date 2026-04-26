"""Run or dry-run the ENVI/SARScape InSAR DEM pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from envi_mcp.pipeline import load_config, run_pipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="Pipeline YAML config path.")
    parser.add_argument("--output-dir", help="Override common.output_dir from the config.")
    parser.add_argument("--skip-to", help="Start at this pipeline step.")
    parser.add_argument("--only", help="Run only this pipeline step.")
    parser.add_argument("--dry-run", action="store_true", help="Plan steps without running ENVI tasks.")
    parser.add_argument("--resume", action="store_true", help="Resume from output_dir/state.json.")
    parser.add_argument("--timeout", type=int, default=3600, help="Per-task timeout in seconds.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config_path = Path(args.config)
    config = load_config(config_path)
    output_dir = _resolve_output_dir(config, args.output_dir, config_path)
    _configure_logging(output_dir, verbose=args.verbose)

    result = run_pipeline(
        config=config,
        output_dir=output_dir,
        skip_to=args.skip_to,
        only=args.only,
        dry_run=args.dry_run,
        resume=args.resume,
        state_path=output_dir / "state.json",
        timeout=args.timeout,
    )
    result_path = output_dir / "pipeline_result.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"success": result["success"], "result_path": str(result_path)}, ensure_ascii=False, indent=2))
    return 0 if result["success"] else 1


def _resolve_output_dir(config: dict[str, object], override: Optional[str], config_path: Path) -> Path:
    if override:
        return Path(override)
    common = config.get("common", {})
    if isinstance(common, dict) and common.get("output_dir"):
        return Path(str(common["output_dir"]))
    return config_path.parent / "outputs"


def _configure_logging(output_dir: Path, verbose: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        logging.FileHandler(output_dir / "pipeline.log", encoding="utf-8"),
        logging.StreamHandler(),
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


if __name__ == "__main__":
    raise SystemExit(main())