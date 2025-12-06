"""
Interferometer Model Module

Implements high-fidelity interferometer model including:
- Incident angle calculation at each time step
- Antenna pattern gain (angle-dependent)
- SNR-dependent phase error
- Geometry-dependent angle accuracy

Matches MATLAB demo/interferometer_model.m functionality.
"""

import numpy as np
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from scipy.interpolate import interp1d

from ..utils.coordinates import (
    ecef_to_ned_rotation,
    ned_to_body_rotation,
    interferometer_orientation_rotation
)


# Physical constants
K_BOLTZMANN = 1.380649e-23      # Boltzmann constant (J/K)


@dataclass
class InterferometerData:
    """Container for interferometer measurement data."""
    measurements: np.ndarray           # Angle measurements with noise (radians) [N_steps]
    measurements_true: np.ndarray      # True angles without noise (radians) [N_steps]
    incident_angles: np.ndarray        # Incident angle from boresight (degrees) [N_steps]
    antenna_gain_db: np.ndarray        # Antenna gain at each angle (dB) [N_steps]
    snr_db: np.ndarray                 # Signal-to-noise ratio (dB) [N_steps]
    phase_error_deg: np.ndarray        # Phase measurement error (degrees) [N_steps]
    angle_error_deg: np.ndarray        # Angle measurement error (degrees) [N_steps]
    angle_error_1sigma_rad: np.ndarray # 1-sigma angle error (radians) [N_steps]
    measurement_valid: np.ndarray      # Measurement validity flags [N_steps]

    # Antenna pattern (for reference/plotting)
    antenna_pattern_angles: np.ndarray
    antenna_pattern_gain: np.ndarray

    def print_summary(self, time: np.ndarray):
        """Print interferometer performance summary."""
        n_valid = np.sum(self.measurement_valid)
        n_steps = len(time)
        n_invalid = n_steps - n_valid

        print(f"\nInterferometer Performance Summary:")
        print(f"  Incident angle range: {np.min(self.incident_angles):.1f} deg to "
              f"{np.max(self.incident_angles):.1f} deg")
        print(f"  Valid measurements: {n_valid} / {n_steps} ({100*n_valid/n_steps:.1f}%)")
        print(f"  SNR range: {np.min(self.snr_db):.1f} to {np.max(self.snr_db):.1f} dB")
        print(f"  Phase error range: {np.min(self.phase_error_deg):.2f} deg to "
              f"{np.max(self.phase_error_deg):.2f} deg")
        print(f"  Angle error range: {np.min(self.angle_error_deg):.4f} deg to "
              f"{np.max(self.angle_error_deg):.4f} deg")

        # Best and worst accuracy points
        min_idx = np.argmin(self.angle_error_deg)
        max_idx = np.argmax(self.angle_error_deg)

        print(f"\n  Best accuracy: {self.angle_error_deg[min_idx]:.4f} deg at t={time[min_idx]:.0f}s "
              f"(incident={self.incident_angles[min_idx]:.1f} deg, SNR={self.snr_db[min_idx]:.1f} dB)")
        print(f"  Worst accuracy: {self.angle_error_deg[max_idx]:.4f} deg at t={time[max_idx]:.0f}s "
              f"(incident={self.incident_angles[max_idx]:.1f} deg, SNR={self.snr_db[max_idx]:.1f} dB)")


def interferometer_model(config, trajectory, signal_data) -> InterferometerData:
    """
    Calculate angle measurements with realistic errors.

    Args:
        config: SimulationConfig object
        trajectory: TrajectoryData object
        signal_data: SignalData object

    Returns:
        InterferometerData object with measurements and analysis
    """
    print("Computing interferometer measurements with high-fidelity model...")

    n_steps = config.n_steps
    np.random.seed(config.random_seed)

    # Load antenna pattern
    antenna_pattern_file = config.interferometer.antenna_pattern_file
    antenna_angles, antenna_gain_db = _load_antenna_pattern(antenna_pattern_file)

    # Create interpolation function
    antenna_gain_interp = interp1d(
        antenna_angles, antenna_gain_db,
        kind='linear', bounds_error=False, fill_value=-40.0
    )

    # Extract parameters
    c_light_in_per_ns = config.interferometer.c_light_in_per_ns
    phase_error_baseline = config.interferometer.phase_error_high_snr_deg
    D_max = config.interferometer.max_baseline
    frequency_hz = config.emitter.frequency_hz
    max_incident_angle = config.interferometer.max_incident_angle_deg

    # Get emitter ECEF from LLA
    from ..utils.coordinates import lla_to_ecef
    emitter_ecef = lla_to_ecef(config.emitter.lat, config.emitter.lon, config.emitter.alt)

    print(f"  Frequency: {frequency_hz/1e9:.2f} GHz")
    print(f"  Longest baseline: {D_max:.2f} inches ({D_max*25.4:.1f} mm)")
    print(f"  Baseline phase error: {phase_error_baseline:.1f} deg")

    # Initialize output arrays
    measurements = np.zeros(n_steps)
    measurements_true = np.zeros(n_steps)
    incident_angles = np.zeros(n_steps)
    antenna_gain_arr = np.zeros(n_steps)
    snr_db = np.zeros(n_steps)
    phase_error_deg = np.zeros(n_steps)
    angle_error_deg = np.zeros(n_steps)
    angle_error_1sigma_rad = np.zeros(n_steps)
    measurement_valid = np.zeros(n_steps, dtype=bool)

    # Calculate measurements for each time step
    for i in range(n_steps):
        # Vector from interferometer to emitter in ECEF
        r_ecef = emitter_ecef - trajectory.interferometer_ecef[i]

        # Transform to NED frame
        R_ecef_to_ned = ecef_to_ned_rotation(
            trajectory.platform_lat[i],
            trajectory.platform_lon[i]
        )
        r_ned = R_ecef_to_ned @ r_ecef

        # Transform to body frame
        R_ned_to_body = ned_to_body_rotation(
            trajectory.platform_pitch[i],
            trajectory.platform_roll[i],
            trajectory.platform_yaw[i]
        )
        r_body = R_ned_to_body @ r_ned

        # Apply interferometer orientation
        R_interfero = interferometer_orientation_rotation(config.interferometer.orientation)
        r_interfero = R_interfero @ r_body

        # True angle measurement in interferometer frame (X-Z plane)
        angle_true_rad = np.arctan2(r_interfero[2], r_interfero[0])
        measurements_true[i] = angle_true_rad

        # Calculate incident angle from boresight
        # Boresight is [0, 0, 1] (down) in interferometer frame
        boresight = np.array([0.0, 0.0, 1.0])
        cos_incident = np.dot(r_interfero, boresight) / np.linalg.norm(r_interfero)
        cos_incident = np.clip(cos_incident, -1.0, 1.0)  # Numerical safety
        incident_angle_deg = np.degrees(np.arccos(cos_incident))
        incident_angles[i] = incident_angle_deg

        # Check measurement validity
        if incident_angle_deg <= max_incident_angle:
            measurement_valid[i] = True

        # Get antenna gain at this incident angle
        gain_db = float(antenna_gain_interp(min(abs(incident_angle_deg), 90.0)))
        antenna_gain_arr[i] = gain_db

        # Calculate SNR
        received_power_dbm = signal_data.received_power_dbw[i] + 30  # dBW to dBm
        noise_floor_dbm = 10 * np.log10(K_BOLTZMANN * 290 * 1e6) + 30 + 3

        snr = received_power_dbm + gain_db - noise_floor_dbm
        snr_db[i] = snr
        snr_linear = 10 ** (snr / 10)

        # Calculate phase error (SNR-dependent)
        # At high SNR (>20 dB): phase error = baseline value
        # At low SNR: phase error increases as 1/sqrt(SNR)
        if snr_linear > 100:  # 20 dB threshold
            phase_err = phase_error_baseline
        else:
            phase_err = phase_error_baseline * np.sqrt(100 / max(snr_linear, 1))
        phase_error_deg[i] = phase_err

        # Calculate angle measurement error
        # Formula: angle_error = c * phase_error / (2π * D * f * cos(incident_angle))
        phase_error_rad = np.radians(phase_err)

        # Avoid division by zero near 90 degrees
        cos_incident_clipped = np.cos(np.radians(min(incident_angle_deg, 89.0)))

        angle_err_rad = abs(c_light_in_per_ns * phase_error_rad /
                          (2 * np.pi * D_max * (frequency_hz / 1e9) * cos_incident_clipped))

        angle_error_deg[i] = np.degrees(angle_err_rad)
        angle_error_1sigma_rad[i] = angle_err_rad

        # Add noise to measurement
        measurements[i] = angle_true_rad + angle_err_rad * np.random.randn()

    interferometer_data = InterferometerData(
        measurements=measurements,
        measurements_true=measurements_true,
        incident_angles=incident_angles,
        antenna_gain_db=antenna_gain_arr,
        snr_db=snr_db,
        phase_error_deg=phase_error_deg,
        angle_error_deg=angle_error_deg,
        angle_error_1sigma_rad=angle_error_1sigma_rad,
        measurement_valid=measurement_valid,
        antenna_pattern_angles=antenna_angles,
        antenna_pattern_gain=antenna_gain_db
    )

    interferometer_data.print_summary(trajectory.time)
    print("\nInterferometer model complete!\n")

    return interferometer_data


def _load_antenna_pattern(pattern_file: Optional[str]) -> tuple:
    """
    Load antenna pattern from file or generate idealized pattern.

    Args:
        pattern_file: Path to antenna pattern CSV file

    Returns:
        Tuple of (angles, gain_db) arrays
    """
    if pattern_file is None or not Path(pattern_file).exists():
        print("  Using idealized cos-squared antenna pattern")
        # Idealized antenna pattern: cos^2 approximation
        antenna_angles = np.arange(0, 91, 1, dtype=float)
        antenna_gain_db = 10 * np.log10(np.cos(np.radians(antenna_angles))**2 + 1e-10)
        antenna_gain_db = np.clip(antenna_gain_db, -40, None)
    else:
        print(f"  Loading antenna pattern from: {pattern_file}")
        antenna_data = np.loadtxt(pattern_file, delimiter=',')

        all_angles = antenna_data[:, 0]
        all_gains = antenna_data[:, 1]

        # Extract 0:90 degrees
        idx_0_90 = (all_angles >= 0) & (all_angles <= 90)
        angles_0_90 = all_angles[idx_0_90]
        gains_0_90 = all_gains[idx_0_90]

        # Extract 270:360 degrees and convert to 90:0 (mirror)
        idx_270_360 = (all_angles >= 270) & (all_angles <= 360)
        angles_270_360 = 360 - all_angles[idx_270_360]
        gains_270_360 = all_gains[idx_270_360]

        # Combine and sort
        antenna_angles = np.concatenate([angles_0_90, angles_270_360])
        antenna_gain_db = np.concatenate([gains_0_90, gains_270_360])

        sort_idx = np.argsort(antenna_angles)
        antenna_angles = antenna_angles[sort_idx]
        antenna_gain_db = antenna_gain_db[sort_idx]

        print(f"  Antenna pattern loaded: {len(antenna_angles)} points from 0 deg to "
              f"{np.max(antenna_angles):.1f} deg")

    return antenna_angles, antenna_gain_db
