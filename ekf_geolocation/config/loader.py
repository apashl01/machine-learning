"""
Configuration loader for EKF Geolocation simulation.

Matches MATLAB demo/config_setup.m functionality.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
import yaml
import numpy as np


@dataclass
class EmitterConfig:
    """Emitter configuration."""
    lat: float                    # Latitude (degrees)
    lon: float                    # Longitude (degrees)
    alt: float                    # Altitude (meters)
    eirp_dbw: float              # EIRP (dBW)
    frequency_hz: float          # Carrier frequency (Hz)

    @property
    def frequency_ghz(self) -> float:
        return self.frequency_hz / 1e9


@dataclass
class InterferometerConfig:
    """Interferometer configuration."""
    offset_body: np.ndarray      # Mounting offset [X, Y, Z] in meters
    orientation: np.ndarray      # Orientation [roll, pitch, yaw] in degrees
    n_elements: int              # Number of elements
    c_light_in_per_ns: float     # Speed of light (inches/ns)
    element_positions: np.ndarray  # Element positions (inches)
    phase_error_high_snr_deg: float  # Phase error at high SNR (degrees)
    max_incident_angle_deg: float    # Max incident angle for valid measurements
    antenna_pattern_file: Optional[str] = None  # Antenna pattern file

    @property
    def baselines(self) -> np.ndarray:
        """Calculate all unique baselines from element positions."""
        baselines = []
        for i in range(self.n_elements):
            for j in range(i + 1, self.n_elements):
                baselines.append(self.element_positions[j] - self.element_positions[i])
        return np.unique(baselines)

    @property
    def max_baseline(self) -> float:
        """Maximum baseline length (inches)."""
        return float(np.max(self.baselines))

    @property
    def min_baseline(self) -> float:
        """Minimum baseline length (inches)."""
        return float(np.min(self.baselines))


@dataclass
class TrajectoryConfig:
    """Trajectory configuration."""
    type: str                     # Trajectory type
    standoff_distance_km: float   # Standoff distance (km)
    size_scale: float             # Size scale factor
    altitude_mean: float          # Mean altitude (m)
    altitude_variation: float     # Altitude variation (m)

    VALID_TYPES = ['circle', 'figure8', 'racetrack', 'sturn',
                   'straight_offset', 'curved_approach']

    def __post_init__(self):
        if self.type.lower() not in self.VALID_TYPES:
            raise ValueError(f"Unknown trajectory type: {self.type}. "
                           f"Valid types: {self.VALID_TYPES}")


@dataclass
class EKFConfig:
    """EKF tuning configuration."""
    initial_offset_km: float      # Initial guess offset
    default_Q: float              # Process noise
    default_P0: float             # Initial covariance
    default_R_scale: float        # Measurement noise scale

    # These are set during parameter sweep or to defaults
    best_Q: float = field(init=False)
    best_P0: float = field(init=False)
    best_R_scale: float = field(init=False)

    def __post_init__(self):
        self.best_Q = self.default_Q
        self.best_P0 = self.default_P0
        self.best_R_scale = self.default_R_scale


@dataclass
class ParameterSweepConfig:
    """Parameter sweep configuration."""
    enabled: bool
    Q_values: List[float]
    P0_values: List[float]
    R_scale_values: List[float]

    @property
    def n_combinations(self) -> int:
        return len(self.Q_values) * len(self.P0_values) * len(self.R_scale_values)


@dataclass
class SimulationConfig:
    """Complete simulation configuration."""
    emitter: EmitterConfig
    interferometer: InterferometerConfig
    trajectory: TrajectoryConfig
    ekf: EKFConfig
    parameter_sweep: ParameterSweepConfig
    dt: float                     # Time step (seconds)
    t_total: float                # Total simulation time (seconds)
    random_seed: int              # Random seed

    @property
    def time(self) -> np.ndarray:
        """Time vector for simulation."""
        return np.arange(0, self.t_total + self.dt, self.dt)

    @property
    def n_steps(self) -> int:
        """Number of simulation steps."""
        return len(self.time)

    def print_summary(self):
        """Print configuration summary."""
        print("=" * 70)
        print("EKF GEOLOCATION SIMULATION CONFIGURATION")
        print("=" * 70)

        print(f"\nEmitter Configuration:")
        print(f"  Position: Lat={self.emitter.lat:.6f} deg, "
              f"Lon={self.emitter.lon:.6f} deg, Alt={self.emitter.alt:.2f} m")
        print(f"  EIRP: {self.emitter.eirp_dbw:.1f} dBW")
        print(f"  Frequency: {self.emitter.frequency_ghz:.2f} GHz")

        print(f"\nInterferometer Configuration:")
        print(f"  Mounting Position (body frame):")
        print(f"    X (forward): {self.interferometer.offset_body[0]:.2f} m")
        print(f"    Y (right):   {self.interferometer.offset_body[1]:.2f} m")
        print(f"    Z (down):    {self.interferometer.offset_body[2]:.2f} m")
        print(f"  Array Configuration:")
        print(f"    Elements: {self.interferometer.n_elements}")
        print(f"    Element positions: {self.interferometer.element_positions} inches")
        print(f"    Max baseline: {self.interferometer.max_baseline:.2f} inches "
              f"({self.interferometer.max_baseline * 25.4:.1f} mm)")
        print(f"    Phase error (high SNR): {self.interferometer.phase_error_high_snr_deg:.1f} deg")
        print(f"    Max incident angle: {self.interferometer.max_incident_angle_deg:.1f} deg")

        print(f"\nTrajectory Configuration:")
        print(f"  Type: {self.trajectory.type}")
        print(f"  Standoff Distance: {self.trajectory.standoff_distance_km:.1f} km")
        print(f"  Size Scale: {self.trajectory.size_scale:.2f}")
        print(f"  Altitude: {self.trajectory.altitude_mean:.0f} +/- "
              f"{self.trajectory.altitude_variation:.0f} m")

        print(f"\nSimulation Parameters:")
        print(f"  Time step: {self.dt:.1f} s")
        print(f"  Total time: {self.t_total:.1f} s")
        print(f"  Number of steps: {self.n_steps}")

        if self.parameter_sweep.enabled:
            print(f"\nParameter Sweep:")
            print(f"  Q values: {len(self.parameter_sweep.Q_values)} options")
            print(f"  P0 values: {len(self.parameter_sweep.P0_values)} options")
            print(f"  R_scale values: {len(self.parameter_sweep.R_scale_values)} options")
            print(f"  Total combinations: {self.parameter_sweep.n_combinations}")
        else:
            print(f"\nEKF Parameters (fixed):")
            print(f"  Q: {self.ekf.default_Q}")
            print(f"  P0: {self.ekf.default_P0}")
            print(f"  R_scale: {self.ekf.default_R_scale}")

        print()


def load_interferometer_from_system_config() -> InterferometerConfig:
    """
    Load interferometer configuration from shared system_config.

    This ensures the EKF uses the same interferometer parameters as the
    direction finding analysis, providing consistency across packages.

    Returns:
        InterferometerConfig with parameters from shared system_config.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from system_config import load_system_config as load_shared_config

    # Load shared config
    shared = load_shared_config()
    interf = shared.interferometer

    return InterferometerConfig(
        offset_body=interf.mounting.offset_body_m,
        orientation=interf.mounting.orientation_deg,
        n_elements=interf.n_elements,
        c_light_in_per_ns=interf.c_light_in_per_ns,
        element_positions=interf.element_positions,
        phase_error_high_snr_deg=interf.phase_error_high_snr_deg,
        max_incident_angle_deg=interf.max_incident_angle_deg,
        antenna_pattern_file=None
    )


def load_simulation_config(config_path: Optional[str] = None) -> SimulationConfig:
    """
    Load simulation configuration from YAML file.

    Args:
        config_path: Path to YAML config file. If None, uses default.

    Returns:
        SimulationConfig object
    """
    if config_path is None:
        config_path = Path(__file__).parent / "simulation_config.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    # Parse emitter config
    emitter = EmitterConfig(
        lat=float(data['emitter']['lat']),
        lon=float(data['emitter']['lon']),
        alt=float(data['emitter']['alt']),
        eirp_dbw=float(data['emitter']['eirp_dbw']),
        frequency_hz=float(data['emitter']['frequency_hz'])
    )

    # Parse interferometer config
    interferometer = InterferometerConfig(
        offset_body=np.array(data['interferometer']['offset_body']),
        orientation=np.array(data['interferometer']['orientation']),
        n_elements=data['interferometer']['n_elements'],
        c_light_in_per_ns=data['interferometer']['c_light_in_per_ns'],
        element_positions=np.array(data['interferometer']['element_positions']),
        phase_error_high_snr_deg=data['interferometer']['phase_error_high_snr_deg'],
        max_incident_angle_deg=data['interferometer']['max_incident_angle_deg'],
        antenna_pattern_file=data['interferometer'].get('antenna_pattern_file')
    )

    # Parse trajectory config
    trajectory = TrajectoryConfig(
        type=data['trajectory']['type'],
        standoff_distance_km=data['trajectory']['standoff_distance_km'],
        size_scale=data['trajectory']['size_scale'],
        altitude_mean=data['trajectory']['altitude_mean'],
        altitude_variation=data['trajectory']['altitude_variation']
    )

    # Parse EKF config
    ekf = EKFConfig(
        initial_offset_km=data['ekf']['initial_offset_km'],
        default_Q=data['ekf']['default_Q'],
        default_P0=data['ekf']['default_P0'],
        default_R_scale=data['ekf']['default_R_scale']
    )

    # Parse parameter sweep config
    sweep = data['parameter_sweep']
    parameter_sweep = ParameterSweepConfig(
        enabled=sweep['enabled'],
        Q_values=sweep['Q_values'],
        P0_values=sweep['P0_values'],
        R_scale_values=sweep['R_scale_values']
    )

    # Create simulation config
    sim = data['simulation']
    return SimulationConfig(
        emitter=emitter,
        interferometer=interferometer,
        trajectory=trajectory,
        ekf=ekf,
        parameter_sweep=parameter_sweep,
        dt=sim['dt'],
        t_total=sim['t_total'],
        random_seed=sim['random_seed']
    )
