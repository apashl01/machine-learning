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
class AntennaGroup:
    """Group of antennas by role and band."""
    role: str  # 'rx' or 'tx'
    band: str  # 'low', 'mid', or 'all'
    antennas: List[AntennaSpec]
    center_freq_ghz: float

    @property
    def name(self) -> str:
        """Human-readable group name."""
        return f"{self.role.upper()} {self.band.title()} Band"


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

    def get_antenna_groups(self) -> dict:
        """
        Group antennas by role (RX/TX) and band (Low/Mid).

        Returns:
            Dict with keys: 'rx_low', 'rx_mid', 'tx_low', 'tx_mid'
            Each value is an AntennaGroup with antennas in that category.
        """
        groups = {
            'rx_low': AntennaGroup('rx', 'low', [], center_freq_ghz=1.0),
            'rx_mid': AntennaGroup('rx', 'mid', [], center_freq_ghz=10.0),
            'tx_low': AntennaGroup('tx', 'low', [], center_freq_ghz=1.0),
            'tx_mid': AntennaGroup('tx', 'mid', [], center_freq_ghz=10.0),
        }

        # Classify RX antennas
        for ant in self.rx_antennas:
            if _is_low_band(ant.freq_band):
                groups['rx_low'].antennas.append(ant)
            else:
                groups['rx_mid'].antennas.append(ant)

        # Classify TX antennas
        for ant in self.tx_antennas:
            if _is_low_band(ant.freq_band):
                groups['tx_low'].antennas.append(ant)
            else:
                groups['tx_mid'].antennas.append(ant)

        return groups

    def get_nonempty_groups(self) -> List[AntennaGroup]:
        """Get list of antenna groups that have at least one antenna."""
        groups = self.get_antenna_groups()
        return [g for g in groups.values() if len(g.antennas) > 0]


def _is_low_band(freq_band: str) -> bool:
    """Check if frequency band string indicates low band (<2 GHz)."""
    band_lower = freq_band.lower()
    return '<2' in band_lower or 'low' in band_lower or '0-2' in band_lower


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


def load_from_system_config(
    local_config_path: Union[str, Path] = None
) -> UAVCoverageConfig:
    """
    Load antenna coverage config with system_config integration.

    Loads local uav_config.yaml for antenna positions and UAV geometry,
    but uses system_config.yaml for ESM antenna parameters (gain, beamwidth).

    Args:
        local_config_path: Path to local uav_config.yaml. If None, uses default.

    Returns:
        UAVCoverageConfig with system_config ESM parameters applied
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from system_config import load_system_config

    # Load local config first (for antenna positions, UAV geometry)
    local_config = load_uav_config(local_config_path)

    # Load system config for ESM antenna parameters
    sys_config = load_system_config()
    esm_ant = sys_config.antennas

    # Update spiral antenna with system_config values
    spiral_spec = SpiralAntennaSpec(
        beamwidth_deg=esm_ant.esm_beamwidth_deg,
        gain_dbi=esm_ant.esm_peak_gain_dbi,
        front_to_back_db=local_config.spiral_antenna.front_to_back_db
    )

    # Update RX antennas with system_config ESM parameters
    rx_antennas = []
    for ant in local_config.rx_antennas:
        # Only apply ESM params to spiral-type antennas in Mid Band
        if ant.antenna_type == 'spiral' and '2-18' in ant.freq_band:
            rx_antennas.append(AntennaSpec(
                name=ant.name,
                position=ant.position,
                orientation=ant.orientation,
                freq_band=ant.freq_band,
                antenna_type=ant.antenna_type,
                beamwidth_deg=esm_ant.esm_beamwidth_deg,
                gain_dbi=esm_ant.esm_peak_gain_dbi
            ))
        else:
            rx_antennas.append(ant)

    # Use system frequency reference
    frequency_ghz = sys_config.freq_reference_ghz

    # Use analysis parameters from central config (Task 8)
    analysis_params = sys_config.antennas.analysis

    return UAVCoverageConfig(
        frequency_ghz=frequency_ghz,
        spiral_antenna=spiral_spec,
        horn_antenna=local_config.horn_antenna,
        antennas=rx_antennas,  # Legacy field
        rx_antennas=rx_antennas,
        tx_antennas=local_config.tx_antennas,
        uav_length=local_config.uav_length,
        uav_width=local_config.uav_width,
        azimuth_range=analysis_params.azimuth_range,
        elevation_range=analysis_params.elevation_range,
        angular_resolution=analysis_params.angular_resolution
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
