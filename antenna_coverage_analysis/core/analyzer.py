"""
UAV Antenna Coverage Analyzer

Multi-antenna coverage analysis for UAV platforms.
Matches MATLAB uav_antenna_coverage.m functionality.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import math
import numpy as np

from ..config.loader import (
    UAVCoverageConfig, SpiralAntennaSpec, HornAntennaSpec,
    AntennaSpec, AntennaGroup
)


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

    # Blind spot analysis (Phase 2 Enhancement)
    blind_spot_mask: Optional[np.ndarray] = None  # True where coverage < threshold
    blind_spot_threshold_db: Optional[float] = None
    blind_spot_fraction: Optional[float] = None  # Fraction of coverage that is blind

    # Optional group info for multi-band analysis
    group_name: Optional[str] = None
    group_freq_ghz: Optional[float] = None
    num_antennas_in_group: int = 0


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

    def analyze(
        self,
        antennas: Optional[List[AntennaSpec]] = None,
        group_name: Optional[str] = None,
        group_freq_ghz: Optional[float] = None,
        blind_spot_threshold_db: Optional[float] = None
    ) -> CoverageResult:
        """
        Perform coverage analysis.

        Args:
            antennas: Optional list of antennas to analyze. If None, uses config.antennas.
            group_name: Optional name for this analysis group.
            group_freq_ghz: Optional frequency for this group (for multi-band analysis).
            blind_spot_threshold_db: Optional threshold for blind spot detection.
                If provided, creates a boolean mask where coverage < threshold.
                If None, uses -10 dBi as default threshold.

        Returns:
            CoverageResult with combined coverage data and optional blind spot mask.
        """
        # Use provided antennas or default to config.antennas
        if antennas is None:
            antennas = self.config.antennas

        # Create angular grids
        az_min, az_max = self.config.azimuth_range
        el_min, el_max = self.config.elevation_range
        res = self.config.angular_resolution

        azimuth = np.arange(az_min, az_max + res, res)
        elevation = np.arange(el_min, el_max + res, res)
        AZ, EL = np.meshgrid(azimuth, elevation)

        # Calculate coverage for each antenna
        coverage_db = np.full_like(AZ, -np.inf)
        antenna_patterns = []

        for ant in antennas:
            # Create pattern generator based on antenna type
            if ant.antenna_type == 'horn':
                pattern_gen = self._get_pattern_generator_for_antenna(ant)
            else:
                pattern_gen = self.spiral_gen

            # Transform to antenna-local coordinates
            az_local, el_local = self._rotate_coordinates(
                AZ, EL, ant.orientation[0], ant.orientation[1]
            )

            # Generate pattern in local coordinates
            pattern = pattern_gen.generate(az_local, el_local)

            antenna_patterns.append(AntennaPattern(
                azimuth=azimuth,
                elevation=elevation,
                gain_db=pattern
            ))

            # Take maximum (best antenna selection)
            coverage_db = np.maximum(coverage_db, pattern)

        # Statistics (handle empty antenna list)
        if len(antennas) == 0:
            return CoverageResult(
                config=self.config,
                azimuth=azimuth,
                elevation=elevation,
                coverage_db=np.full_like(AZ, -np.inf),
                antenna_patterns=[],
                max_gain_db=-np.inf,
                min_gain_db=-np.inf,
                mean_gain_db=-np.inf,
                median_gain_db=-np.inf,
                group_name=group_name,
                group_freq_ghz=group_freq_ghz,
                num_antennas_in_group=0
            )

        valid_mask = np.isfinite(coverage_db)
        coverage_valid = coverage_db[valid_mask]

        # Calculate blind spot mask (Phase 2 Enhancement)
        # Default threshold: -10 dBi (areas with very poor coverage)
        threshold = blind_spot_threshold_db if blind_spot_threshold_db is not None else -10.0
        blind_mask = coverage_db < threshold
        blind_fraction = np.sum(blind_mask) / blind_mask.size if blind_mask.size > 0 else 0.0

        return CoverageResult(
            config=self.config,
            azimuth=azimuth,
            elevation=elevation,
            coverage_db=coverage_db,
            antenna_patterns=antenna_patterns,
            max_gain_db=float(np.max(coverage_valid)) if len(coverage_valid) > 0 else -np.inf,
            min_gain_db=float(np.min(coverage_valid)) if len(coverage_valid) > 0 else -np.inf,
            mean_gain_db=float(np.mean(coverage_valid)) if len(coverage_valid) > 0 else -np.inf,
            median_gain_db=float(np.median(coverage_valid)) if len(coverage_valid) > 0 else -np.inf,
            blind_spot_mask=blind_mask,
            blind_spot_threshold_db=threshold,
            blind_spot_fraction=blind_fraction,
            group_name=group_name,
            group_freq_ghz=group_freq_ghz,
            num_antennas_in_group=len(antennas)
        )

    def _get_pattern_generator_for_antenna(self, ant: AntennaSpec):
        """Get appropriate pattern generator for an antenna."""
        if ant.antenna_type == 'horn':
            return HornPatternGenerator(HornAntennaSpec(
                beamwidth_deg=ant.beamwidth_deg,
                gain_dbi=ant.gain_dbi,
                position=ant.position,
                orientation=ant.orientation
            ))
        else:
            # Create a spiral generator with this antenna's specific parameters
            return SpiralPatternGenerator(SpiralAntennaSpec(
                beamwidth_deg=ant.beamwidth_deg,
                gain_dbi=ant.gain_dbi,
                front_to_back_db=self.config.spiral_antenna.front_to_back_db
            ))

    def analyze_group(self, group: AntennaGroup,
                      blind_spot_threshold_db: Optional[float] = None) -> CoverageResult:
        """
        Analyze coverage for a specific antenna group.

        Args:
            group: AntennaGroup containing antennas to analyze.
            blind_spot_threshold_db: Optional threshold for blind spot detection.

        Returns:
            CoverageResult for this group.
        """
        return self.analyze(
            antennas=group.antennas,
            group_name=group.name,
            group_freq_ghz=group.center_freq_ghz,
            blind_spot_threshold_db=blind_spot_threshold_db
        )

    def analyze_all_groups(self) -> dict:
        """
        Analyze coverage for all antenna groups (RX/TX, Low/Mid bands).

        Returns:
            Dict mapping group key to CoverageResult.
            Keys: 'rx_low', 'rx_mid', 'tx_low', 'tx_mid'
        """
        groups = self.config.get_antenna_groups()
        results = {}

        for key, group in groups.items():
            if len(group.antennas) > 0:
                results[key] = self.analyze_group(group)
                print(f"  Analyzed {group.name}: {len(group.antennas)} antennas")

        return results


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

    # Blind spot statistics (Phase 2 Enhancement)
    if result.blind_spot_mask is not None:
        lines.append("")
        lines.append("BLIND SPOT ANALYSIS:")
        lines.append(f"  Threshold: {result.blind_spot_threshold_db:.1f} dBi")
        lines.append(f"  Blind spot coverage: {result.blind_spot_fraction*100:.1f}%")
        if result.blind_spot_fraction > 0.1:
            lines.append("  WARNING: >10% of coverage area has poor gain")

    lines.append("=" * 60)
    return "\n".join(lines)
