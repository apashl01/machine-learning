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
    freq_band: str = "2-18 GHz"
    antenna_type: str = "spiral"
    beamwidth_deg: float = 70.0
    gain_dbi: float = 2.0


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
    antennas: List[AntennaSpec]         # Legacy - RX antennas
    rx_antennas: List[AntennaSpec]      # RX antennas with full spec
    tx_antennas: List[AntennaSpec]      # TX antennas
    uav_length: float
    uav_width: float
    azimuth_range: List[float]
    elevation_range: List[float]
    angular_resolution: float

    @property
    def num_antennas(self) -> int:
        """Number of RX antennas (legacy compatibility)."""
        return len(self.antennas)

    @property
    def num_rx_antennas(self) -> int:
        """Number of receive antennas."""
        return len(self.rx_antennas)

    @property
    def num_tx_antennas(self) -> int:
        """Number of transmit antennas."""
        return len(self.tx_antennas)

    @property
    def total_antennas(self) -> int:
        """Total number of antennas (RX + TX)."""
        return self.num_rx_antennas + self.num_tx_antennas


def _parse_antenna(ant: dict, default_beamwidth: float = 70.0,
                   default_gain: float = 2.0) -> AntennaSpec:
    """Parse a single antenna from config dict."""
    return AntennaSpec(
        name=ant.get('name', 'Unknown'),
        position=_to_float_list(ant.get('position'), [0, 0, 0]),
        orientation=_to_float_list(ant.get('orientation'), [0, 0]),
        freq_band=ant.get('freq_band', '2-18 GHz'),
        antenna_type=ant.get('type', 'spiral'),
        beamwidth_deg=_to_float(ant.get('beamwidth_deg'), default_beamwidth),
        gain_dbi=_to_float(ant.get('gain_dbi'), default_gain)
    )


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

    # Default spiral spec
    spiral_spec = SpiralAntennaSpec(
        beamwidth_deg=_to_float(spiral.get('beamwidth_deg'), 70),
        gain_dbi=_to_float(spiral.get('gain_dbi'), 2),
        front_to_back_db=_to_float(spiral.get('front_to_back_db'), 15)
    )

    # Parse legacy antennas (backwards compatibility)
    antennas = []
    for ant in data.get('antenna_positions', []):
        antennas.append(AntennaSpec(
            name=ant.get('name', 'Unknown'),
            position=_to_float_list(ant.get('position'), [0, 0, 0]),
            orientation=_to_float_list(ant.get('orientation'), [0, 0]),
            freq_band='2-18 GHz',
            antenna_type='spiral',
            beamwidth_deg=spiral_spec.beamwidth_deg,
            gain_dbi=spiral_spec.gain_dbi
        ))

    # Parse RX antennas (new format)
    rx_antennas = []
    for ant in data.get('rx_antennas', []):
        rx_antennas.append(_parse_antenna(
            ant,
            default_beamwidth=spiral_spec.beamwidth_deg,
            default_gain=spiral_spec.gain_dbi
        ))

    # If no rx_antennas defined, use legacy antennas
    if not rx_antennas:
        rx_antennas = antennas.copy()

    # Parse TX antennas
    tx_antennas = []
    for ant in data.get('tx_antennas', []):
        tx_antennas.append(_parse_antenna(ant, default_beamwidth=30, default_gain=12))

    # Parse horn antenna (legacy TX)
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
        spiral_antenna=spiral_spec,
        horn_antenna=horn_antenna,
        antennas=antennas,
        rx_antennas=rx_antennas,
        tx_antennas=tx_antennas,
        uav_length=_to_float(uav.get('length'), 2.0),
        uav_width=_to_float(uav.get('width'), 1.5),
        azimuth_range=_to_float_list(analysis.get('azimuth_range'), [-180, 180]),
        elevation_range=_to_float_list(analysis.get('elevation_range'), [-90, 90]),
        angular_resolution=_to_float(analysis.get('angular_resolution'), 2)
    )


if __name__ == "__main__":
    config = load_uav_config()
    print(f"Frequency: {config.frequency_ghz} GHz")
    print(f"\nRX Antennas ({config.num_rx_antennas}):")
    for ant in config.rx_antennas:
        print(f"  {ant.name}: pos={ant.position}, type={ant.antenna_type}, "
              f"band={ant.freq_band}, gain={ant.gain_dbi} dBi")
    print(f"\nTX Antennas ({config.num_tx_antennas}):")
    for ant in config.tx_antennas:
        print(f"  {ant.name}: pos={ant.position}, type={ant.antenna_type}, "
              f"band={ant.freq_band}, gain={ant.gain_dbi} dBi, bw={ant.beamwidth_deg}°")
