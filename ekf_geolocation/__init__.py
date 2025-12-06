"""
EKF Geolocation Package

Extended Kalman Filter for geolocation of stationary emitters using
UAV-mounted interferometer measurements.

Features:
- Multiple UAV trajectory types (figure8, circle, racetrack, sturn, etc.)
- High-fidelity interferometer model with SNR-dependent errors
- Signal propagation with free space path loss
- EKF with optional parameter sweep optimization
- Coordinate transformations (ECEF, NED, Body frame)

Matches MATLAB demo files functionality.
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import (
    load_simulation_config,
    SimulationConfig,
    EmitterConfig,
    InterferometerConfig,
    TrajectoryConfig,
    EKFConfig,
    ParameterSweepConfig
)
from .core import (
    generate_trajectory,
    TrajectoryData,
    calculate_signal_propagation,
    SignalData,
    interferometer_model,
    InterferometerData,
    run_ekf,
    EKFResult,
    run_simulation,
    run_parameter_sweep,
    SimulationResult
)
from .utils import (
    lla_to_ecef,
    ecef_to_lla,
    ecef_to_ned_rotation,
    ned_to_body_rotation,
    interferometer_orientation_rotation
)

__all__ = [
    # Config
    'load_simulation_config',
    'SimulationConfig',
    'EmitterConfig',
    'InterferometerConfig',
    'TrajectoryConfig',
    'EKFConfig',
    'ParameterSweepConfig',
    # Core
    'generate_trajectory',
    'TrajectoryData',
    'calculate_signal_propagation',
    'SignalData',
    'interferometer_model',
    'InterferometerData',
    'run_ekf',
    'EKFResult',
    'run_simulation',
    'run_parameter_sweep',
    'SimulationResult',
    # Utils
    'lla_to_ecef',
    'ecef_to_lla',
    'ecef_to_ned_rotation',
    'ned_to_body_rotation',
    'interferometer_orientation_rotation'
]
