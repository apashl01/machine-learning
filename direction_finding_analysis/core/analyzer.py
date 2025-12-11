"""
RF Interferometer Analyzer

1D RF interferometer analysis including angle accuracy and ambiguity regions.
Matches MATLAB rf_interferometer_analysis.m functionality.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Callable
import math
import numpy as np
from pathlib import Path

from ..config.loader import InterferometerConfig


@dataclass
class AngleAccuracyResult:
    """Results for angle accuracy analysis."""
    frequencies_ghz: np.ndarray
    incident_angles: np.ndarray
    angle_error_ideal: np.ndarray       # [n_freq, n_angles] - constant phase error
    angle_error_realistic: np.ndarray   # [n_freq, n_angles] - SNR-dependent phase error
    snr_db: np.ndarray                  # [n_freq, n_angles]
    phase_error_realistic: np.ndarray   # [n_freq, n_angles]


@dataclass
class AmbiguityResult:
    """Results for ambiguity analysis."""
    frequencies_ghz: np.ndarray
    baselines: List[float]
    ambiguity_angles: np.ndarray  # [n_baselines, n_freq] - half-angle of ambiguity-free region


@dataclass
class InterferometerResults:
    """Complete interferometer analysis results."""
    config: InterferometerConfig
    accuracy: AngleAccuracyResult
    ambiguity: AmbiguityResult

    # Summary at boresight (0 degrees)
    boresight_idx: int
    boresight_angle_error_ideal: np.ndarray   # per frequency
    boresight_angle_error_realistic: np.ndarray
    boresight_snr_db: np.ndarray


class InterferometerAnalyzer:
    """
    Analyzer for 1D RF interferometer.

    Matches MATLAB rf_interferometer_analysis.m.
    """

    def __init__(self, config: InterferometerConfig):
        """
        Initialize analyzer.

        Task 11: Now generates analytical antenna pattern when no file specified,
        using peak_gain_dbi and beamwidth_deg from system_config.

        Args:
            config: Interferometer configuration.
        """
        self.config = config
        self.antenna_gain_func = None
        self.peak_gain_dbi = 0.0  # Default isotropic
        self.beamwidth_deg = 90.0  # Default wide beam

        # Load antenna pattern if specified
        if config.antenna_pattern_file:
            self._load_antenna_pattern(config.antenna_pattern_file)
        else:
            # Task 11: Generate analytical pattern from system_config if available
            self._generate_analytical_pattern()

    def _load_antenna_pattern(self, filepath: str):
        """Load antenna pattern from CSV file."""
        path = Path(filepath)
        if not path.exists():
            print(f"Warning: Antenna pattern file not found: {filepath}. Using analytical.")
            self._generate_analytical_pattern()
            return

        try:
            data = np.loadtxt(path, delimiter=',', skiprows=1)
            angles = data[:, 0]
            gains = data[:, 1]

            # Create interpolation function
            self.antenna_gain_func = lambda angle: np.interp(
                np.abs(angle), angles, gains, left=gains[0], right=gains[-1]
            )
        except Exception as e:
            print(f"Warning: Could not load antenna pattern: {e}. Using analytical.")
            self._generate_analytical_pattern()

    def _generate_analytical_pattern(self):
        """
        Generate analytical antenna pattern (Task 11).

        Uses Gaussian model based on peak_gain_dbi and beamwidth_deg from system_config.
        If system_config unavailable, falls back to realistic spiral antenna defaults.

        Gaussian model: G(theta) = G_peak - 12 * (theta/beamwidth_3db)^2
        This approximates a typical antenna pattern rolloff.
        """
        try:
            from system_config import load_system_config
            sys_config = load_system_config()
            # Access ESM antenna parameters from system_config
            self.peak_gain_dbi = sys_config.antennas.esm_peak_gain_dbi
            self.beamwidth_deg = sys_config.antennas.esm_beamwidth_deg
            print(f"Using antenna pattern from system_config: {self.peak_gain_dbi} dBi, {self.beamwidth_deg}° beamwidth")
        except Exception as e:
            # Default to typical spiral antenna parameters
            print(f"Warning: Could not load antenna parameters from system_config ({e}). Using defaults.")
            self.peak_gain_dbi = 3.0   # Typical spiral antenna gain
            self.beamwidth_deg = 70.0  # Realistic beamwidth

        # Create Gaussian pattern function
        # G(theta) = G_peak - 12 * (theta / (beamwidth/2))^2
        # This gives -3 dB at half-beamwidth and realistic rolloff
        half_beamwidth = self.beamwidth_deg / 2

        def gaussian_pattern(angle_deg):
            """Gaussian antenna pattern with realistic rolloff."""
            angle = abs(angle_deg)
            # Gaussian rolloff: -12 dB at full beamwidth edge
            rolloff_db = 12.0 * (angle / half_beamwidth) ** 2
            gain = self.peak_gain_dbi - rolloff_db
            # Floor at -20 dB relative to peak (realistic sidelobe level)
            return max(gain, self.peak_gain_dbi - 20.0)

        self.antenna_gain_func = gaussian_pattern

    def get_antenna_gain(self, angle_deg: float) -> float:
        """
        Get antenna gain at angle off boresight.

        Args:
            angle_deg: Angle off boresight in degrees.

        Returns:
            Antenna gain in dB. If no pattern loaded, returns 0 dB (isotropic).
        """
        if self.antenna_gain_func is not None:
            return float(self.antenna_gain_func(abs(angle_deg)))
        return 0.0

    def calculate_snr_dependent_phase_error(self, snr_linear: float) -> float:
        """
        Calculate SNR-dependent phase error.

        Phase error increases with decreasing SNR:
        - At high SNR (>20 dB): phase_error = baseline value
        - At low SNR: phase_error scales as 1/sqrt(SNR)

        Args:
            snr_linear: SNR in linear scale.

        Returns:
            Phase error in degrees.
        """
        if snr_linear > 100:  # High SNR threshold (20 dB)
            return self.config.phase_error_deg
        else:
            # Phase error degrades as SNR drops
            return self.config.phase_error_deg * math.sqrt(100 / max(snr_linear, 1))

    def calculate_angle_error(self, freq_ghz: float, incident_angle_deg: float,
                               baseline_in: float, phase_error_deg: float) -> float:
        """
        Calculate angle estimation error.

        Formula: 11.8028 * phase_error_rad / (2*pi*D*f*cos(theta))

        Args:
            freq_ghz: Frequency in GHz.
            incident_angle_deg: Incident angle off boresight in degrees.
            baseline_in: Baseline length in inches.
            phase_error_deg: Phase measurement error in degrees.

        Returns:
            Angle error in degrees.
        """
        phase_error_rad = math.radians(phase_error_deg)
        cos_theta = math.cos(math.radians(incident_angle_deg))

        if abs(cos_theta) < 0.01:  # Near 90 degrees - avoid division by zero
            return float('inf')

        angle_error_rad = abs(
            self.config.c_light_in_per_ns * phase_error_rad /
            (2 * math.pi * baseline_in * freq_ghz * cos_theta)
        )
        return math.degrees(angle_error_rad)

    def calculate_ambiguity_angle(self, freq_ghz: float, baseline_in: float) -> float:
        """
        Calculate unambiguous half-angle for a baseline at given frequency.

        Unambiguous when: sin(theta) = lambda/D

        Args:
            freq_ghz: Frequency in GHz.
            baseline_in: Baseline length in inches.

        Returns:
            Unambiguous half-angle in degrees (90 if no ambiguity).
        """
        wavelength_in = self.config.c_light_in_per_ns / freq_ghz
        ratio = wavelength_in / baseline_in

        if ratio >= 1.0:
            return 90.0  # No ambiguity - full hemisphere
        else:
            return math.degrees(math.asin(ratio))

    def analyze(self) -> InterferometerResults:
        """
        Perform complete interferometer analysis.

        Returns:
            InterferometerResults with all analysis data.
        """
        # Create angle and frequency arrays
        angle_min, angle_max = self.config.incident_angles_range
        incident_angles = np.arange(angle_min, angle_max + self.config.angle_step,
                                     self.config.angle_step)
        frequencies_ghz = np.array(self.config.test_frequencies_ghz)

        n_freq = len(frequencies_ghz)
        n_angles = len(incident_angles)

        # Get longest baseline for accuracy calculations
        max_baseline = self.config.max_baseline

        # Pre-allocate arrays
        angle_error_ideal = np.zeros((n_freq, n_angles))
        angle_error_realistic = np.zeros((n_freq, n_angles))
        snr_db = np.zeros((n_freq, n_angles))
        phase_error_realistic = np.zeros((n_freq, n_angles))

        # Calculate angle accuracy for each frequency and angle
        for f_idx, freq in enumerate(frequencies_ghz):
            for a_idx, theta in enumerate(incident_angles):
                # Get antenna gain at this angle
                gain_db = self.get_antenna_gain(theta)

                # Calculate SNR
                snr_db[f_idx, a_idx] = (self.config.signal_strength_dbm +
                                         gain_db - self.config.noise_floor_dbm)
                snr_linear = 10 ** (snr_db[f_idx, a_idx] / 10)

                # Calculate phase error (SNR-dependent)
                phase_error = self.calculate_snr_dependent_phase_error(snr_linear)
                phase_error_realistic[f_idx, a_idx] = phase_error

                # Calculate angle error - ideal (constant phase error)
                angle_error_ideal[f_idx, a_idx] = self.calculate_angle_error(
                    freq, theta, max_baseline, self.config.phase_error_deg
                )

                # Calculate angle error - realistic (SNR-dependent phase error)
                angle_error_realistic[f_idx, a_idx] = self.calculate_angle_error(
                    freq, theta, max_baseline, phase_error
                )

        accuracy_result = AngleAccuracyResult(
            frequencies_ghz=frequencies_ghz,
            incident_angles=incident_angles,
            angle_error_ideal=angle_error_ideal,
            angle_error_realistic=angle_error_realistic,
            snr_db=snr_db,
            phase_error_realistic=phase_error_realistic
        )

        # Calculate ambiguity regions for all baselines
        baselines = self.config.baselines
        n_baselines = len(baselines)
        ambiguity_angles = np.zeros((n_baselines, n_freq))

        for b_idx, baseline in enumerate(baselines):
            for f_idx, freq in enumerate(frequencies_ghz):
                ambiguity_angles[b_idx, f_idx] = self.calculate_ambiguity_angle(freq, baseline)

        ambiguity_result = AmbiguityResult(
            frequencies_ghz=frequencies_ghz,
            baselines=baselines,
            ambiguity_angles=ambiguity_angles
        )

        # Find boresight index
        boresight_idx = np.argmin(np.abs(incident_angles))

        return InterferometerResults(
            config=self.config,
            accuracy=accuracy_result,
            ambiguity=ambiguity_result,
            boresight_idx=boresight_idx,
            boresight_angle_error_ideal=angle_error_ideal[:, boresight_idx],
            boresight_angle_error_realistic=angle_error_realistic[:, boresight_idx],
            boresight_snr_db=snr_db[:, boresight_idx]
        )


def analyze_interferometer(config: InterferometerConfig) -> InterferometerResults:
    """
    Analyze interferometer performance.

    Convenience function matching MATLAB calling convention.

    Args:
        config: Interferometer configuration.

    Returns:
        InterferometerResults.
    """
    analyzer = InterferometerAnalyzer(config)
    return analyzer.analyze()


def print_summary(results: InterferometerResults) -> str:
    """Generate formatted summary of interferometer analysis."""
    config = results.config
    lines = [
        "=" * 60,
        "INTERFEROMETER ANALYSIS RESULTS",
        "=" * 60,
        "",
        f"Number of elements: {config.n_elements}",
        f"Total aperture: {config.max_baseline:.2f} inches ({config.max_baseline*25.4:.1f} mm)",
        f"Shortest baseline: {config.min_baseline:.3f} inches ({config.min_baseline*25.4:.2f} mm)",
        f"Element positions: {config.element_positions} inches",
        f"Phase error at high SNR: {config.phase_error_deg:.1f} degrees",
        f"Signal strength: {config.signal_strength_dbm:.1f} dBm",
        f"Noise floor: {config.noise_floor_dbm:.1f} dBm",
        "",
        "ANGLE ACCURACY AT BORESIGHT (0°):",
    ]

    for f_idx, freq in enumerate(results.accuracy.frequencies_ghz):
        lines.append(
            f"  {freq:.0f} GHz: {results.boresight_angle_error_ideal[f_idx]:.4f}° (ideal) / "
            f"{results.boresight_angle_error_realistic[f_idx]:.4f}° (realistic)"
        )

    lines.extend([
        "",
        "SNR AT BORESIGHT:",
    ])
    for f_idx, freq in enumerate(results.accuracy.frequencies_ghz):
        lines.append(f"  {freq:.0f} GHz: {results.boresight_snr_db[f_idx]:.1f} dB")

    lines.extend([
        "",
        f"AMBIGUITY-FREE RANGE (Shortest baseline: {config.min_baseline:.2f} in):",
    ])
    for f_idx, freq in enumerate(results.accuracy.frequencies_ghz):
        lines.append(f"  {freq:.0f} GHz: ±{results.ambiguity.ambiguity_angles[0, f_idx]:.1f}°")

    lines.append("=" * 60)
    return "\n".join(lines)
