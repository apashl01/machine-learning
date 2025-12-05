"""
Interferometer Configuration Loader

Loads YAML configuration for RF interferometer analysis.
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


if __name__ == "__main__":
    config = load_interferometer_config()
    print(f"Elements: {config.n_elements}")
    print(f"Positions: {config.element_positions}")
    print(f"Baselines: {config.baselines}")
    print(f"Max baseline: {config.max_baseline} inches")
    print(f"Min baseline: {config.min_baseline} inches")
