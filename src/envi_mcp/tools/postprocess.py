"""Post-processing and validation tools for DEM products."""

from __future__ import annotations

from typing import Any, Optional

from ._helpers import compact_params, run_logical_task


def register(mcp: Any) -> None:
    @mcp.tool()
    def terrain_correct_dem(
        input_dem: str,
        reference_dem: str,
        output_file: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Terrain-correct an InSAR DEM using a reference DEM."""

        return run_logical_task(
            ("SARscape Terrain Correction", "Terrain Correction"),
            ("terrain", "correction"),
            compact_params(input_dem=input_dem, reference_dem=reference_dem, output_file=output_file),
            timeout,
        )

    @mcp.tool()
    def fill_dem_voids(
        input_dem: str,
        output_file: str,
        max_void_size: int = 25,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Fill small no-data gaps in a DEM."""

        return run_logical_task(
            ("DEM Void Fill", "Fill DEM Voids", "Void Fill"),
            ("void", "fill"),
            compact_params(input_dem=input_dem, output_file=output_file, max_void_size=max_void_size),
            timeout,
        )

    @mcp.tool()
    def smooth_dem(
        input_dem: str,
        output_file: str,
        kernel_size: int = 3,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Smooth a DEM with a local filter."""

        return run_logical_task(
            ("DEM Smoothing", "Smooth DEM", "Raster Smoothing"),
            ("smooth",),
            compact_params(input_dem=input_dem, output_file=output_file, kernel_size=kernel_size),
            timeout,
        )

    @mcp.tool()
    def export_dem_to_geotiff(
        input_dem: str,
        output_file: str,
        compression: str = "LZW",
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Export an ENVI DEM raster to GeoTIFF."""

        return run_logical_task(
            ("Export GeoTIFF", "Raster Export", "Export Raster"),
            ("export",),
            compact_params(input_dem=input_dem, output_file=output_file, compression=compression),
            timeout,
        )

    @mcp.tool()
    def generate_quality_mask(
        coherence: str,
        output_file: str,
        threshold: float = 0.2,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Generate a quality mask from coherence."""

        return run_logical_task(
            ("Quality Mask", "Coherence Mask", "Mask Generation"),
            ("mask",),
            compact_params(coherence=coherence, output_file=output_file, threshold=threshold),
            timeout,
        )

    @mcp.tool()
    def calculate_dem_statistics(
        input_dem: str,
        mask: Optional[str] = None,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Calculate DEM statistics through an ENVI task when available."""

        return run_logical_task(
            ("DEM Statistics", "Raster Statistics", "Statistics"),
            ("statistics",),
            compact_params(input_dem=input_dem, mask=mask),
            timeout,
        )

    @mcp.tool()
    def compare_dem_to_reference(
        input_dem: str,
        reference_dem: str,
        output_dir: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Compare an InSAR DEM to a reference DEM through ENVI/SARScape if available."""

        return run_logical_task(
            ("DEM Comparison", "Raster Difference", "Compare DEM"),
            ("difference",),
            compact_params(input_dem=input_dem, reference_dem=reference_dem, output_dir=output_dir),
            timeout,
        )

    @mcp.tool()
    def clip_raster_to_aoi(
        input_raster: str,
        aoi: str,
        output_file: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Clip a raster to an area of interest."""

        return run_logical_task(
            ("Raster Subset", "Clip Raster", "Subset Raster"),
            ("subset",),
            compact_params(input_raster=input_raster, aoi=aoi, output_file=output_file),
            timeout,
        )