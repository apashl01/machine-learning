"""
Extended Kalman Filter Module

Implements EKF for geolocation of a stationary emitter using
interferometer angle measurements.

Matches MATLAB demo/runEKF.m functionality.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional

from ..utils.coordinates import (
    lla_to_ecef,
    ecef_to_ned_rotation,
    ned_to_body_rotation,
    interferometer_orientation_rotation
)


@dataclass
class EKFResult:
    """Container for EKF results."""
    x_history: np.ndarray         # Estimated emitter position (ECEF) [N_steps x 3]
    P_history: np.ndarray         # Covariance diagonal [N_steps x 3]
    innovation_history: np.ndarray  # Measurement innovations [N_steps]

    def final_estimate(self):
        """Get final position estimate."""
        return self.x_history[-1]

    def final_covariance(self):
        """Get final covariance diagonal."""
        return self.P_history[-1]


def run_ekf(config, measurements: np.ndarray, trajectory,
            interferometer_data) -> EKFResult:
    """
    Execute Extended Kalman Filter for geolocation.

    Args:
        config: SimulationConfig object
        measurements: Angle measurements in radians [N_steps]
        trajectory: TrajectoryData object
        interferometer_data: InterferometerData object

    Returns:
        EKFResult object with estimation history
    """
    n_steps = config.n_steps

    # Get EKF parameters
    Q_val = config.ekf.best_Q
    P0_val = config.ekf.best_P0
    R_scale = config.ekf.best_R_scale

    # Initial state estimate
    emitter_ecef = lla_to_ecef(config.emitter.lat, config.emitter.lon, config.emitter.alt)
    initial_offset = config.ekf.initial_offset_km * 1000.0
    offset_dir = np.array([1.0, 1.0, 0.5])
    offset_dir = offset_dir / np.linalg.norm(offset_dir)
    x_est = emitter_ecef + initial_offset * offset_dir

    # Initial covariance
    P = np.diag([P0_val**2, P0_val**2, (P0_val / 2)**2])

    # Process noise
    Q = np.diag([Q_val, Q_val, Q_val])

    # History storage
    x_history = np.zeros((n_steps, 3))
    P_history = np.zeros((n_steps, 3))
    innovation_history = np.zeros(n_steps)

    # Initial state
    x_history[0] = x_est
    P_history[0] = np.diag(P)

    # EKF Loop
    for k in range(1, n_steps):
        # Predict (stationary emitter - no motion model)
        x_pred = x_est
        F = np.eye(3)
        P_pred = F @ P @ F.T + Q

        # Check if measurement is valid
        if not interferometer_data.measurement_valid[k]:
            # Skip update step - just use prediction
            x_est = x_pred
            P = P_pred
            innovation_history[k] = 0.0
        else:
            # Measurement update (normal EKF)
            z = measurements[k]

            # Measurement noise (time-varying based on interferometer performance)
            R = (interferometer_data.angle_error_1sigma_rad[k] * R_scale)**2

            # Measurement model with interferometer offset
            h, H = _measurement_model_with_offset(
                x_pred,
                trajectory.interferometer_ecef[k],
                trajectory.platform_lat[k],
                trajectory.platform_lon[k],
                trajectory.platform_pitch[k],
                trajectory.platform_roll[k],
                trajectory.platform_yaw[k],
                config.interferometer.offset_body,
                config.interferometer.orientation
            )

            # Update
            innovation = z - h
            S = H @ P_pred @ H.T + R
            K = P_pred @ H.T / S

            x_est = x_pred + K * innovation
            P = (np.eye(3) - np.outer(K, H)) @ P_pred

            innovation_history[k] = innovation

        # Store
        x_history[k] = x_est
        P_history[k] = np.diag(P)

    return EKFResult(
        x_history=x_history,
        P_history=P_history,
        innovation_history=innovation_history
    )


def _measurement_model_with_offset(x_emitter_ecef: np.ndarray,
                                   interferometer_ecef: np.ndarray,
                                   platform_lat: float,
                                   platform_lon: float,
                                   pitch: float,
                                   roll: float,
                                   yaw: float,
                                   interfero_offset_body: np.ndarray,
                                   interfero_orientation: np.ndarray):
    """
    Compute predicted measurement and Jacobian.

    Args:
        x_emitter_ecef: Estimated emitter position in ECEF (3,)
        interferometer_ecef: Interferometer position in ECEF (3,)
        platform_lat, platform_lon: Platform position (degrees)
        pitch, roll, yaw: Platform attitude (degrees)
        interfero_offset_body: Interferometer offset from CG (3,) meters
        interfero_orientation: Interferometer orientation offset (3,) degrees

    Returns:
        h: Predicted measurement (radians)
        H: Measurement Jacobian (3,)
    """
    # Vector from interferometer to emitter in ECEF
    r_ecef = x_emitter_ecef - interferometer_ecef

    # Convert to platform body frame
    R_ecef_to_ned = ecef_to_ned_rotation(platform_lat, platform_lon)
    r_ned = R_ecef_to_ned @ r_ecef

    R_ned_to_body = ned_to_body_rotation(pitch, roll, yaw)
    r_body = R_ned_to_body @ r_ned

    # Apply interferometer orientation offset
    R_interfero = interferometer_orientation_rotation(interfero_orientation)
    r_interfero = R_interfero @ r_body

    # Predicted measurement (angle in X-Z plane)
    h = np.arctan2(r_interfero[2], r_interfero[0])

    # Numerical Jacobian
    epsilon = 1.0
    H = np.zeros(3)

    for i in range(3):
        x_pert = x_emitter_ecef.copy()
        x_pert[i] += epsilon

        r_ecef_pert = x_pert - interferometer_ecef
        r_ned_pert = R_ecef_to_ned @ r_ecef_pert
        r_body_pert = R_ned_to_body @ r_ned_pert
        r_interfero_pert = R_interfero @ r_body_pert

        h_pert = np.arctan2(r_interfero_pert[2], r_interfero_pert[0])

        H[i] = (h_pert - h) / epsilon

    return h, H
