"""InSAR and DEM generation tools."""

from __future__ import annotations

from typing import Any, Optional

from ._helpers import compact_params, run_logical_task


def register(mcp: Any) -> None:
    @mcp.tool()
    def calculate_baseline(
        master_slc: str,
        slave_slc: str,
        output_dir: str,
        orbit_file: Optional[str] = None,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Calculate interferometric baseline for an SLC pair."""

        return run_logical_task(
            ("SARscape Baseline", "Baseline Estimation", "Baseline"),
            ("baseline",),
            compact_params(master_slc=master_slc, slave_slc=slave_slc, output_dir=output_dir, orbit_file=orbit_file),
            timeout,
        )

    @mcp.tool()
    def coregister_slc_pair(
        master_slc: str,
        slave_slc: str,
        output_dir: str,
        dem: Optional[str] = None,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Coregister slave SLC to master SLC."""

        return run_logical_task(
            ("SARscape Coregistration", "SLC Coregistration", "Coregistration"),
            ("coreg",),
            compact_params(master_slc=master_slc, slave_slc=slave_slc, output_dir=output_dir, dem=dem),
            timeout,
        )

    @mcp.tool()
    def generate_interferogram(
        master_slc: str,
        slave_slc: str,
        output_dir: str,
        range_looks: int = 1,
        azimuth_looks: int = 1,
        remove_flat_earth: bool = True,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Generate an interferogram from a coregistered SLC pair."""

        return run_logical_task(
            ("SARscape Interferogram", "Interferogram Generation", "Interferogram"),
            ("interferogram",),
            compact_params(
                master_slc=master_slc,
                slave_slc=slave_slc,
                output_dir=output_dir,
                range_looks=range_looks,
                azimuth_looks=azimuth_looks,
                remove_flat_earth=remove_flat_earth,
            ),
            timeout,
        )

    @mcp.tool()
    def generate_coherence(
        interferogram: str,
        output_file: str,
        window_size: int = 5,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Generate coherence for an interferogram."""

        return run_logical_task(
            ("SARscape Coherence", "Coherence Generation", "Coherence"),
            ("coherence",),
            compact_params(interferogram=interferogram, output_file=output_file, window_size=window_size),
            timeout,
        )

    @mcp.tool()
    def apply_adaptive_filter(
        interferogram: str,
        output_file: str,
        goldstein_alpha: float = 0.5,
        window_size: int = 5,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Apply Goldstein/adaptive filtering to an interferogram."""

        return run_logical_task(
            ("SARscape Adaptive Filter", "Goldstein Filter", "Adaptive Filter"),
            ("filter",),
            compact_params(
                interferogram=interferogram,
                output_file=output_file,
                goldstein_alpha=goldstein_alpha,
                window_size=window_size,
            ),
            timeout,
        )

    @mcp.tool()
    def unwrap_phase(
        filtered_interferogram: str,
        coherence: str,
        output_file: str,
        coherence_threshold: float = 0.2,
        grid_size: int = 64,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Unwrap filtered phase using coherence as quality guidance."""

        return run_logical_task(
            ("SARscape Phase Unwrapping", "Phase Unwrapping", "Unwrapping"),
            ("unwrap",),
            compact_params(
                filtered_interferogram=filtered_interferogram,
                coherence=coherence,
                output_file=output_file,
                coherence_threshold=coherence_threshold,
                grid_size=grid_size,
            ),
            timeout,
        )

    @mcp.tool()
    def generate_gcp(
        unwrapped_phase: str,
        dem: str,
        output_file: str,
        coherence: Optional[str] = None,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Generate ground control points for orbital refinement."""

        return run_logical_task(
            ("SARscape GCP Generation", "GCP Generation", "Generate GCP"),
            ("gcp",),
            compact_params(unwrapped_phase=unwrapped_phase, dem=dem, output_file=output_file, coherence=coherence),
            timeout,
        )

    @mcp.tool()
    def refine_orbit_and_reflatten(
        unwrapped_phase: str,
        gcp_file: str,
        output_file: str,
        polynomial_degree: int = 2,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Run orbital refinement and phase reflattening."""

        return run_logical_task(
            ("SARscape Orbital Refinement", "Refinement and Reflattening", "Reflattening"),
            ("refine",),
            compact_params(
                unwrapped_phase=unwrapped_phase,
                gcp_file=gcp_file,
                output_file=output_file,
                polynomial_degree=polynomial_degree,
            ),
            timeout,
        )

    @mcp.tool()
    def convert_phase_to_height(
        refined_phase: str,
        dem: str,
        output_file: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Convert refined phase to height."""

        return run_logical_task(
            ("SARscape Phase to Height", "Phase To Height", "Phase2Height"),
            ("height",),
            compact_params(refined_phase=refined_phase, dem=dem, output_file=output_file),
            timeout,
        )

    @mcp.tool()
    def geocode_dem(
        input_raster: str,
        dem: str,
        output_file: str,
        pixel_size: float = 10.0,
        resampling: str = "bilinear",
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Geocode an InSAR height raster into a DEM product."""

        return run_logical_task(
            ("SARscape Geocoding", "Geocoding"),
            ("geocode",),
            compact_params(
                input_raster=input_raster,
                dem=dem,
                output_file=output_file,
                pixel_size=pixel_size,
                resampling=resampling,
            ),
            timeout,
        )

    @mcp.tool()
    def mosaic_dems(
        input_dems: list[str],
        output_file: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Mosaic multiple DEM tiles."""

        return run_logical_task(
            ("SARscape DEM Mosaic", "DEM Mosaic", "Raster Mosaic"),
            ("mosaic",),
            compact_params(input_dems=input_dems, output_file=output_file),
            timeout,
        )

    @mcp.tool()
    def remove_flat_earth_phase(
        interferogram: str,
        output_file: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Remove flat-earth phase from an interferogram."""

        return run_logical_task(
            ("SARscape Flat Earth Removal", "Flat Earth Removal"),
            ("flat", "earth"),
            compact_params(interferogram=interferogram, output_file=output_file),
            timeout,
        )

    @mcp.tool()
    def multilook_slc(
        input_slc: str,
        output_file: str,
        range_looks: int = 1,
        azimuth_looks: int = 1,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Create a multilooked SAR raster."""

        return run_logical_task(
            ("SARscape Multilook", "Multilook"),
            ("multilook",),
            compact_params(
                input_slc=input_slc,
                output_file=output_file,
                range_looks=range_looks,
                azimuth_looks=azimuth_looks,
            ),
            timeout,
        )