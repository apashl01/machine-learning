"""
Interferometer Configuration Loader

Loads YAML configuration for RF interferometer analysis.
Supports loading from local config or shared system_config.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union
from pathlib import Path
import yaml


def _to_float(value, default: float = 0.0) -> float:
    """Convert value to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _to_float_list(value, default: List[float] = None) -> List[float]:
    """Convert value to list of floats."""
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return [_to_float(v) for v in value]
    return default


@dataclass
class InterferometerConfig:
    """Interferometer system configuration."""
    n_elements: int
    freq_range_ghz: List[float]  # [min, max]
    phase_error_deg: float
    signal_strength_dbm: float
    noise_floor_dbm: float
    c_light_in_per_ns: float
    element_positions: List[float]  # inches

    # Analysis parameters
    incident_angles_range: List[float]  # [min, max] degrees
    angle_step: float
    test_frequencies_ghz: List[float]

    # Antenna pattern
    antenna_pattern_file: Optional[str] = None
    antenna_pattern_freq_ghz: float = 9.0

    @property
    def baselines(self) -> List[float]:
        """Calculate all unique baselines between elements."""
        baselines = []
        n = len(self.element_positions)
        for i in range(n):
            for j in range(i + 1, n):
                baselines.append(self.element_positions[j] - self.element_positions[i])
        return sorted(set(baselines))

    @property
    def max_baseline(self) -> float:
        """Longest baseline (total aperture)."""
        return max(self.baselines)

    @property
    def min_baseline(self) -> float:
        """Shortest baseline (for ambiguity resolution)."""
        return min(self.baselines)


def load_interferometer_config(filepath: Union[str, Path] = None) -> InterferometerConfig:
    """
    Load interferometer configuration from YAML file.

    Args:
        filepath: Path to config YAML. If None, uses default.

    Returns:
        InterferometerConfig object.
    """
    if filepath is None:
        config_dir = Path(__file__).parent
        filepath = config_dir / "interferometer_config.yaml"

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    system = data.get('system', {})
    analysis = data.get('analysis', {})
    pattern = data.get('antenna_pattern', {})

    return InterferometerConfig(
        n_elements=system.get('n_elements', 4),
        freq_range_ghz=_to_float_list(system.get('freq_range_ghz'), [2, 18]),
        phase_error_deg=_to_float(system.get('phase_error_deg'), 12),
        signal_strength_dbm=_to_float(system.get('signal_strength_dbm'), -60),
        noise_floor_dbm=_to_float(system.get('noise_floor_dbm'), -100),
        c_light_in_per_ns=_to_float(data.get('c_light_in_per_ns'), 11.8028),
        element_positions=_to_float_list(data.get('element_positions'), [0, 0.328, 3.5, 10.0]),
        incident_angles_range=_to_float_list(analysis.get('incident_angles_range'), [-80, 80]),
        angle_step=_to_float(analysis.get('angle_step'), 0.5),
        test_frequencies_ghz=_to_float_list(analysis.get('test_frequencies_ghz'), [2, 5, 10, 15, 18]),
        antenna_pattern_file=pattern.get('file'),
        antenna_pattern_freq_ghz=_to_float(pattern.get('frequency_ghz'), 9.0)
    )


def load_from_system_config(
    signal_strength_dbm: float = -60,
    bandwidth_hz: float = 1e6
) -> InterferometerConfig:
    """
    Load interferometer configuration from shared system_config.

    This integrates with the centralized system configuration to ensure
    consistency across all analysis packages.

    Args:
        signal_strength_dbm: Input signal strength for SNR calculations
        bandwidth_hz: Bandwidth for noise floor calculation

    Returns:
        InterferometerConfig object with parameters from system_config
    """
    # Import system_config
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from system_config import load_system_config, calculate_system_noise_floor

    # Load shared config
    sys_config = load_system_config()

    # Calculate noise floor from system parameters
    noise_result = calculate_system_noise_floor(
        sys_config,
        frequency_ghz=sys_config.freq_reference_ghz,
        bandwidth_hz=bandwidth_hz
    )

    # Build test frequencies across the interferometer's specific frequency range (Task 3)
    freq_min = sys_config.interferometer.freq_min_ghz
    freq_max = sys_config.interferometer.freq_max_ghz
    test_freqs = [freq_min]
    test_freqs.extend([f for f in [5, 10, 15] if freq_min < f < freq_max])
    test_freqs.append(freq_max)

    return InterferometerConfig(
        n_elements=sys_config.interferometer.n_elements,
        freq_range_ghz=[freq_min, freq_max],
        phase_error_deg=sys_config.interferometer.phase_error_high_snr_deg,
        signal_strength_dbm=signal_strength_dbm,
        noise_floor_dbm=noise_result.system_noise_floor_dbm,
        c_light_in_per_ns=sys_config.interferometer.c_light_in_per_ns,
        element_positions=list(sys_config.interferometer.element_positions),
        incident_angles_range=[-sys_config.interferometer.max_incident_angle_deg,
                               sys_config.interferometer.max_incident_angle_deg],
        angle_step=0.5,
        test_frequencies_ghz=test_freqs,
        antenna_pattern_file=None,
        antenna_pattern_freq_ghz=sys_config.freq_reference_ghz
    )


if __name__ == "__main__":
    print("=== Local Config ===")
    config = load_interferometer_config()
    print(f"Elements: {config.n_elements}")
    print(f"Positions: {config.element_positions}")
    print(f"Baselines: {config.baselines}")
    print(f"Noise floor: {config.noise_floor_dbm} dBm")

    print("\n=== From System Config ===")
    try:
        config_sys = load_from_system_config()
        print(f"Elements: {config_sys.n_elements}")
        print(f"Positions: {config_sys.element_positions}")
        print(f"Noise floor: {config_sys.noise_floor_dbm:.1f} dBm (from ADC + RF chain)")
    except ImportError as e:
        print(f"System config not available: {e}")
