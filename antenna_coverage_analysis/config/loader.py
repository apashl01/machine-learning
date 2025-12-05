"""
UAV Antenna Coverage Configuration Loader
"""

from dataclasses import dataclass, field
from typing import List, Optional, Union
from pathlib import Path
import yaml


def _to_float(value, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _to_float_list(value, default: List[float] = None) -> List[float]:
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return [_to_float(v) for v in value]
    return default


@dataclass
class AntennaSpec:
    """Single antenna specification."""
    name: str
    position: List[float]       # [x, y, z] in meters
    orientation: List[float]    # [azimuth, elevation] in degrees


@dataclass
class SpiralAntennaSpec:
    """Spiral antenna pattern specification."""
    beamwidth_deg: float
    gain_dbi: float
    front_to_back_db: float = 15.0


@dataclass
class HornAntennaSpec:
    """Horn antenna specification."""
    beamwidth_deg: float
    gain_dbi: float
    position: List[float]
    orientation: List[float]


@dataclass
class UAVCoverageConfig:
    """Complete UAV antenna coverage configuration."""
    frequency_ghz: float
    spiral_antenna: SpiralAntennaSpec
    horn_antenna: Optional[HornAntennaSpec]
    antennas: List[AntennaSpec]
    uav_length: float
    uav_width: float
    azimuth_range: List[float]
    elevation_range: List[float]
    angular_resolution: float

    @property
    def num_antennas(self) -> int:
        return len(self.antennas)


def load_uav_config(filepath: Union[str, Path] = None) -> UAVCoverageConfig:
    """Load UAV antenna coverage configuration."""
    if filepath is None:
        config_dir = Path(__file__).parent
        filepath = config_dir / "uav_config.yaml"

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    system = data.get('system', {})
    spiral = data.get('spiral_antenna', {})
    horn = data.get('horn_antenna', {})
    uav = data.get('uav', {})
    analysis = data.get('analysis', {})

    # Parse antennas
    antennas = []
    for ant in data.get('antenna_positions', []):
        antennas.append(AntennaSpec(
            name=ant.get('name', 'Unknown'),
            position=_to_float_list(ant.get('position'), [0, 0, 0]),
            orientation=_to_float_list(ant.get('orientation'), [0, 0])
        ))

    # Parse horn antenna
    horn_antenna = None
    if horn:
        horn_antenna = HornAntennaSpec(
            beamwidth_deg=_to_float(horn.get('beamwidth_deg'), 30),
            gain_dbi=_to_float(horn.get('gain_dbi'), 14),
            position=_to_float_list(horn.get('position'), [0.8, 0, 0]),
            orientation=_to_float_list(horn.get('orientation'), [0, 0])
        )

    return UAVCoverageConfig(
        frequency_ghz=_to_float(system.get('frequency_ghz'), 9.0),
        spiral_antenna=SpiralAntennaSpec(
            beamwidth_deg=_to_float(spiral.get('beamwidth_deg'), 70),
            gain_dbi=_to_float(spiral.get('gain_dbi'), 2),
            front_to_back_db=_to_float(spiral.get('front_to_back_db'), 15)
        ),
        horn_antenna=horn_antenna,
        antennas=antennas,
        uav_length=_to_float(uav.get('length'), 2.0),
        uav_width=_to_float(uav.get('width'), 1.5),
        azimuth_range=_to_float_list(analysis.get('azimuth_range'), [-180, 180]),
        elevation_range=_to_float_list(analysis.get('elevation_range'), [-90, 90]),
        angular_resolution=_to_float(analysis.get('angular_resolution'), 2)
    )


if __name__ == "__main__":
    config = load_uav_config()
    print(f"Frequency: {config.frequency_ghz} GHz")
    print(f"Number of antennas: {config.num_antennas}")
    for ant in config.antennas:
        print(f"  {ant.name}: pos={ant.position}, orient={ant.orientation}")
