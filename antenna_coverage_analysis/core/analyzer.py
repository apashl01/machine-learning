"""
UAV Antenna Coverage Analyzer

Multi-antenna coverage analysis for UAV platforms.
Matches MATLAB uav_antenna_coverage.m functionality.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math
import numpy as np

from ..config.loader import UAVCoverageConfig, SpiralAntennaSpec, HornAntennaSpec


@dataclass
class AntennaPattern:
    """2D antenna pattern data."""
    azimuth: np.ndarray         # degrees
    elevation: np.ndarray       # degrees
    gain_db: np.ndarray         # [n_el, n_az] gain in dBi


@dataclass
class CoverageResult:
    """Combined coverage analysis result."""
    config: UAVCoverageConfig
    azimuth: np.ndarray
    elevation: np.ndarray
    coverage_db: np.ndarray     # [n_el, n_az] max gain from any antenna

    # Per-antenna patterns in platform coordinates
    antenna_patterns: List[AntennaPattern]

    # Statistics
    max_gain_db: float
    min_gain_db: float
    mean_gain_db: float
    median_gain_db: float


class SpiralPatternGenerator:
    """Generate spiral antenna patterns."""

    def __init__(self, spec: SpiralAntennaSpec):
        self.spec = spec

    def generate(self, azimuth: np.ndarray, elevation: np.ndarray) -> np.ndarray:
        """
        Generate spiral antenna pattern.

        Uses a cardioid-like pattern matching MATLAB implementation.

        Args:
            azimuth: 2D meshgrid of azimuth angles (degrees)
            elevation: 2D meshgrid of elevation angles (degrees)

        Returns:
            Pattern gain in dBi.
        """
        beamwidth_rad = math.radians(self.spec.beamwidth_deg)

        # Calculate angle from boresight
        theta = np.arccos(np.cos(np.radians(elevation)) * np.cos(np.radians(azimuth)))

        # Elevation factor - hemispherical characteristic
        elevation_factor = np.cos(np.radians(elevation))
        elevation_factor = np.maximum(elevation_factor, 0)  # Zero in back hemisphere

        # Azimuth factor - beamwidth control
        sigma = beamwidth_rad / (2 * np.sqrt(2 * np.log(2)))
        azimuth_factor = np.exp(-(theta ** 2) / (2 * sigma ** 2))

        # Combine patterns
        pattern_normalized = elevation_factor * azimuth_factor

        # Add front-to-back ratio
        back_lobe_level = 10 ** (-self.spec.front_to_back_db / 10)
        pattern_combined = pattern_normalized ** 0.7 + back_lobe_level * (1 - elevation_factor)

        # Convert to dB
        pattern_db_relative = 10 * np.log10(
            pattern_combined / np.maximum(np.max(pattern_combined), 1e-10)
        )
        pattern_db = pattern_db_relative + self.spec.gain_dbi

        return pattern_db


class HornPatternGenerator:
    """Generate horn antenna patterns."""

    def __init__(self, spec: HornAntennaSpec):
        self.spec = spec

    def generate(self, azimuth: np.ndarray, elevation: np.ndarray) -> np.ndarray:
        """
        Generate horn antenna pattern using cos^n model.

        Args:
            azimuth: 2D meshgrid of azimuth angles (degrees)
            elevation: 2D meshgrid of elevation angles (degrees)

        Returns:
            Pattern gain in dBi.
        """
        beamwidth_rad = math.radians(self.spec.beamwidth_deg)

        # Calculate n from beamwidth (cos^n pattern)
        n = math.log(0.5) / math.log(math.cos(beamwidth_rad / 2))

        # Calculate angle from boresight
        theta = np.arccos(np.cos(np.radians(elevation)) * np.cos(np.radians(azimuth)))

        # Cosine^n pattern
        pattern = np.power(np.cos(theta), n)

        # Set minimum level (-40 dB)
        min_level = 10 ** (-40 / 10)
        pattern = np.maximum(pattern, min_level)
        pattern[theta > np.pi / 2] = min_level  # Back hemisphere

        # Convert to dB
        pattern_db_relative = 10 * np.log10(pattern / np.maximum(np.max(pattern), 1e-10))
        pattern_db = pattern_db_relative + self.spec.gain_dbi

        return pattern_db


class CoverageAnalyzer:
    """
    UAV antenna coverage analyzer.

    Calculates combined coverage from multiple antennas.
    """

    def __init__(self, config: UAVCoverageConfig):
        self.config = config
        self.spiral_gen = SpiralPatternGenerator(config.spiral_antenna)
        self.horn_gen = None
        if config.horn_antenna:
            self.horn_gen = HornPatternGenerator(config.horn_antenna)

    def _rotate_coordinates(self, azimuth: np.ndarray, elevation: np.ndarray,
                            az_rot: float, el_rot: float) -> Tuple[np.ndarray, np.ndarray]:
        """
        Transform platform coordinates to antenna-local coordinates.

        Args:
            azimuth: Platform azimuth angles (degrees)
            elevation: Platform elevation angles (degrees)
            az_rot: Antenna azimuth pointing (degrees)
            el_rot: Antenna elevation pointing (degrees)

        Returns:
            (az_local, el_local) in antenna coordinates.
        """
        az_local = azimuth - az_rot
        el_local = elevation - el_rot

        # Wrap azimuth to [-180, 180]
        az_local = np.mod(az_local + 180, 360) - 180

        # Clip elevation to [-90, 90]
        el_local = np.clip(el_local, -90, 90)

        return az_local, el_local

    def analyze(self) -> CoverageResult:
        """
        Perform coverage analysis.

        Returns:
            CoverageResult with combined coverage data.
        """
        # Create angular grids
        az_min, az_max = self.config.azimuth_range
        el_min, el_max = self.config.elevation_range
        res = self.config.angular_resolution

        azimuth = np.arange(az_min, az_max + res, res)
        elevation = np.arange(el_min, el_max + res, res)
        AZ, EL = np.meshgrid(azimuth, elevation)

        # Generate base spiral pattern (boresight pointing)
        base_spiral = self.spiral_gen.generate(AZ, EL)

        # Calculate coverage for each antenna
        coverage_db = np.full_like(AZ, -np.inf)
        antenna_patterns = []

        for ant in self.config.antennas:
            # Transform to antenna-local coordinates
            az_local, el_local = self._rotate_coordinates(
                AZ, EL, ant.orientation[0], ant.orientation[1]
            )

            # Generate pattern in local coordinates
            pattern = self.spiral_gen.generate(az_local, el_local)

            antenna_patterns.append(AntennaPattern(
                azimuth=azimuth,
                elevation=elevation,
                gain_db=pattern
            ))

            # Take maximum (best antenna selection)
            coverage_db = np.maximum(coverage_db, pattern)

        # Statistics
        valid_mask = np.isfinite(coverage_db)
        coverage_valid = coverage_db[valid_mask]

        return CoverageResult(
            config=self.config,
            azimuth=azimuth,
            elevation=elevation,
            coverage_db=coverage_db,
            antenna_patterns=antenna_patterns,
            max_gain_db=float(np.max(coverage_valid)),
            min_gain_db=float(np.min(coverage_valid)),
            mean_gain_db=float(np.mean(coverage_valid)),
            median_gain_db=float(np.median(coverage_valid))
        )


def analyze_coverage(config: UAVCoverageConfig) -> CoverageResult:
    """Analyze UAV antenna coverage."""
    analyzer = CoverageAnalyzer(config)
    return analyzer.analyze()


def print_statistics(result: CoverageResult) -> str:
    """Generate coverage statistics summary."""
    lines = [
        "=" * 60,
        "UAV ANTENNA COVERAGE STATISTICS",
        "=" * 60,
        "",
        f"Number of antennas: {result.config.num_antennas}",
        f"Frequency: {result.config.frequency_ghz:.2f} GHz",
        f"Spiral beamwidth: {result.config.spiral_antenna.beamwidth_deg:.1f} degrees",
        f"Spiral peak gain: {result.config.spiral_antenna.gain_dbi:.1f} dBi",
        "",
        "COVERAGE STATISTICS:",
        f"  Maximum gain: {result.max_gain_db:.2f} dB",
        f"  Minimum gain: {result.min_gain_db:.2f} dB",
        f"  Mean gain: {result.mean_gain_db:.2f} dB",
        f"  Median gain: {result.median_gain_db:.2f} dB",
    ]

    # Calculate coverage thresholds
    thresholds = [-3, -6, -10]
    for thresh in thresholds:
        coverage_fraction = np.sum(result.coverage_db >= (result.max_gain_db + thresh)) / result.coverage_db.size
        lines.append(f"  Coverage within {abs(thresh):.0f} dB of peak: {coverage_fraction*100:.1f}%")

    lines.append("=" * 60)
    return "\n".join(lines)
