"""SAR import tools."""

from __future__ import annotations

from typing import Any, Optional

from ._helpers import compact_params, run_logical_task


def register(mcp: Any) -> None:
    @mcp.tool()
    def import_sentinel1_slc(
        input_safe: str,
        output_dir: str,
        orbit_file: Optional[str] = None,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Import a Sentinel-1 SLC SAFE package into ENVI/SARScape format."""

        return run_logical_task(
            ("SARscape Sentinel-1 Import", "Sentinel-1 Import"),
            ("sentinel", "import"),
            compact_params(input_safe=input_safe, output_dir=output_dir, orbit_file=orbit_file),
            timeout,
        )

    @mcp.tool()
    def import_radarsat2_slc(
        input_product: str,
        output_dir: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Import a RADARSAT-2 SLC product."""

        return run_logical_task(
            ("SARscape RADARSAT-2 Import", "RADARSAT-2 Import"),
            ("radarsat", "import"),
            compact_params(input_product=input_product, output_dir=output_dir),
            timeout,
        )

    @mcp.tool()
    def import_alos_palsar_slc(
        input_product: str,
        output_dir: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Import an ALOS/PALSAR SLC product."""

        return run_logical_task(
            ("SARscape ALOS PALSAR Import", "PALSAR Import"),
            ("palsar", "import"),
            compact_params(input_product=input_product, output_dir=output_dir),
            timeout,
        )

    @mcp.tool()
    def import_terrasarx_slc(
        input_product: str,
        output_dir: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Import a TerraSAR-X SLC product."""

        return run_logical_task(
            ("SARscape TerraSAR-X Import", "TerraSAR-X Import"),
            ("terrasar", "import"),
            compact_params(input_product=input_product, output_dir=output_dir),
            timeout,
        )

    @mcp.tool()
    def import_cosmo_skymed_slc(
        input_product: str,
        output_dir: str,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Import a COSMO-SkyMed SLC product."""

        return run_logical_task(
            ("SARscape COSMO-SkyMed Import", "COSMO-SkyMed Import"),
            ("cosmo", "import"),
            compact_params(input_product=input_product, output_dir=output_dir),
            timeout,
        )

    @mcp.tool()
    def import_generic_sar_slc(
        input_product: str,
        output_dir: str,
        sensor: Optional[str] = None,
        timeout: int = 3600,
    ) -> dict[str, Any]:
        """Import a generic SAR SLC product when a sensor-specific wrapper is unavailable."""

        return run_logical_task(
            ("SARscape Import", "SAR Import", "Import SAR Data"),
            ("sar", "import"),
            compact_params(input_product=input_product, output_dir=output_dir, sensor=sensor),
            timeout,
        )