"""Pydantic models for ENVI/SARScape task parameter groups."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelBase(BaseModel):
    """Base model with strict names and path-friendly serialization."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    def to_task_params(self) -> dict[str, object]:
        return {
            key: str(value) if isinstance(value, Path) else value
            for key, value in self.model_dump(exclude_none=True).items()
        }


class BaselineParams(ModelBase):
    master_slc: Path
    slave_slc: Path
    output_dir: Path
    orbit_file: Optional[Path] = None
    perpendicular_baseline_limit_m: Optional[float] = Field(default=None, gt=0)


class InterferogramParams(ModelBase):
    master_slc: Path
    slave_slc: Path
    output_dir: Path
    range_looks: int = Field(default=1, gt=0)
    azimuth_looks: int = Field(default=1, gt=0)
    remove_flat_earth: bool = True


class FilterParams(ModelBase):
    interferogram: Path
    output_file: Path
    filter_method: str = "goldstein"
    goldstein_alpha: float = Field(default=0.5, ge=0.1, le=1.0)
    window_size: int = Field(default=5, gt=0)


class UnwrappingParams(ModelBase):
    filtered_interferogram: Path
    coherence: Path
    output_file: Path
    coherence_threshold: float = Field(default=0.2, ge=0.0, le=1.0)
    grid_size: int = Field(default=64, gt=0)


class RefinementParams(ModelBase):
    unwrapped_phase: Path
    gcp_file: Path
    output_file: Path
    polynomial_degree: int = Field(default=2, ge=1, le=5)
    coherence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)


class GeocodingParams(ModelBase):
    input_raster: Path
    dem: Path
    output_file: Path
    pixel_size: float = Field(default=10.0, gt=0)
    resampling: str = "bilinear"