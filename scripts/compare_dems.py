"""Compare an InSAR DEM against a reference DEM and create validation plots."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dem", required=True, help="InSAR DEM raster path.")
    parser.add_argument("--reference", required=True, help="Reference DEM raster path.")
    parser.add_argument("--output-dir", required=True, help="Directory for report and plots.")
    parser.add_argument("--sample-size", type=int, default=100000, help="Maximum scatter plot sample size.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        import rasterio
    except ImportError as exc:
        print(
            "Missing optional comparison dependencies. Install with: "
            "python -m pip install -e .[compare]",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with rasterio.open(args.dem) as dem_dataset, rasterio.open(args.reference) as reference_dataset:
        dem_data = dem_dataset.read(1, masked=True)
        reference_data = reference_dataset.read(1, masked=True)

    if dem_data.shape != reference_data.shape:
        print("DEM and reference DEM must have the same raster shape for direct comparison.", file=sys.stderr)
        return 1

    difference = dem_data - reference_data
    valid_difference = np.ma.masked_invalid(difference).compressed()
    valid_dem = np.ma.masked_invalid(dem_data).compressed()
    valid_reference = np.ma.masked_invalid(reference_data).compressed()

    if valid_difference.size == 0:
        print("No valid overlapping pixels found.", file=sys.stderr)
        return 1

    stats = _calculate_stats(np, valid_difference)
    _write_report(output_dir / "accuracy_report.txt", stats)
    _save_difference_map(plt, difference, output_dir / "diff_map.png")
    _save_histogram(plt, valid_difference, output_dir / "diff_histogram.png")
    _save_scatter(plt, np, valid_reference, valid_dem, args.sample_size, output_dir / "scatter.png")
    print(f"Wrote report and plots to {output_dir}")
    return 0


def _calculate_stats(np: Any, valid_difference: Any) -> dict[str, Any]:
    rmse = math.sqrt(float(np.mean(valid_difference**2)))
    return {
        "count": int(valid_difference.size),
        "mean_error": float(np.mean(valid_difference)),
        "median_error": float(np.median(valid_difference)),
        "mae": float(np.mean(np.abs(valid_difference))),
        "rmse": rmse,
        "std": float(np.std(valid_difference)),
        "min": float(np.min(valid_difference)),
        "max": float(np.max(valid_difference)),
    }


def _write_report(path: Path, stats: dict[str, Any]) -> None:
    lines = ["DEM accuracy report", ""]
    lines.extend(f"{key}: {value}" for key, value in stats.items())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _save_difference_map(plt: Any, difference: Any, path: Path) -> None:
    plt.figure(figsize=(9, 7))
    image = plt.imshow(difference, cmap="RdBu", vmin=-50, vmax=50)
    plt.colorbar(image, label="DEM difference")
    plt.title("DEM Difference Map")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _save_histogram(plt: Any, valid_difference: Any, path: Path) -> None:
    plt.figure(figsize=(8, 5))
    plt.hist(valid_difference, bins=80, color="#2f6f9f", alpha=0.85)
    plt.xlabel("DEM difference")
    plt.ylabel("Pixel count")
    plt.title("DEM Difference Histogram")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _save_scatter(
    plt: Any,
    np: Any,
    valid_reference: Any,
    valid_dem: Any,
    sample_size: int,
    path: Path,
) -> None:
    sample_count = min(sample_size, valid_reference.size, valid_dem.size)
    sample_indices = np.linspace(0, valid_reference.size - 1, num=sample_count, dtype=int)
    reference_sample = valid_reference[sample_indices]
    dem_sample = valid_dem[sample_indices]
    plt.figure(figsize=(6, 6))
    plt.scatter(reference_sample, dem_sample, s=2, alpha=0.25)
    plt.xlabel("Reference DEM")
    plt.ylabel("InSAR DEM")
    plt.title("DEM Scatter")
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


if __name__ == "__main__":
    raise SystemExit(main())