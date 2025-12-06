"""
Trajectory Generation Module

Generates UAV platform trajectories with multiple flight patterns:
- figure8: Figure-8 pattern around emitter
- circle: Circular orbit around emitter
- racetrack: Racetrack/oval pattern
- sturn: S-turn approach pattern
- straight_offset: Straight approach with lateral offset
- curved_approach: Curved approach toward emitter

Matches MATLAB demo/generate_trajectory.m functionality.
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
class TrajectoryData:
    """Container for trajectory data."""
    # Platform position (LLA)
    platform_lat: np.ndarray      # Latitude (degrees) [N_steps]
    platform_lon: np.ndarray      # Longitude (degrees) [N_steps]
    platform_alt: np.ndarray      # Altitude (meters) [N_steps]

    # Platform attitude
    platform_pitch: np.ndarray    # Pitch (degrees) [N_steps]
    platform_roll: np.ndarray     # Roll (degrees) [N_steps]
    platform_yaw: np.ndarray      # Yaw (degrees) [N_steps]

    # ECEF positions
    platform_ecef_cg: np.ndarray  # Platform CG in ECEF [N_steps x 3]
    interferometer_ecef: np.ndarray  # Interferometer in ECEF [N_steps x 3]

    # Boresight vectors
    boresight_body: np.ndarray    # Boresight in body frame [N_steps x 3]
    boresight_ned: np.ndarray     # Boresight in NED frame [N_steps x 3]
    boresight_ecef: np.ndarray    # Boresight in ECEF frame [N_steps x 3]

    # Derived data
    distances_from_emitter: np.ndarray  # Distance to emitter (km) [N_steps]
    time: np.ndarray              # Time vector (seconds) [N_steps]

    def print_summary(self):
        """Print trajectory summary statistics."""
        min_dist = np.min(self.distances_from_emitter)
        max_dist = np.max(self.distances_from_emitter)
        mean_dist = np.mean(self.distances_from_emitter)

        print(f"Trajectory Summary:")
        print(f"  Duration: {self.time[-1]:.1f} s")
        print(f"  Points: {len(self.time)}")
        print(f"  Altitude range: {np.min(self.platform_alt):.0f} - "
              f"{np.max(self.platform_alt):.0f} m")
        print(f"  Distance from emitter:")
        print(f"    Minimum: {min_dist:.2f} km")
        print(f"    Maximum: {max_dist:.2f} km")
        print(f"    Mean: {mean_dist:.2f} km")


def generate_trajectory(config) -> TrajectoryData:
    """
    Generate platform trajectory based on configuration.

    Args:
        config: SimulationConfig object

    Returns:
        TrajectoryData object with complete trajectory information
    """
    n_steps = config.n_steps
    time = config.time
    dt = config.dt
    t_total = config.t_total

    # Extract configuration
    traj_type = config.trajectory.type.lower()
    standoff_km = config.trajectory.standoff_distance_km
    size_scale = config.trajectory.size_scale
    alt_mean = config.trajectory.altitude_mean
    alt_var = config.trajectory.altitude_variation

    emitter_lat = config.emitter.lat
    emitter_lon = config.emitter.lon
    emitter_ecef = lla_to_ecef(emitter_lat, emitter_lon, config.emitter.alt)

    # Initialize arrays
    platform_lat = np.zeros(n_steps)
    platform_lon = np.zeros(n_steps)
    platform_alt = np.zeros(n_steps)
    platform_pitch = np.zeros(n_steps)
    platform_roll = np.zeros(n_steps)
    platform_yaw = np.zeros(n_steps)

    # Generate trajectory based on type
    if traj_type == 'figure8':
        print("Generating Figure-8 trajectory...")
        platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll = \
            _generate_figure8(time, t_total, emitter_lat, emitter_lon,
                            standoff_km, size_scale, alt_mean, alt_var)

    elif traj_type == 'circle':
        print("Generating Circular trajectory...")
        platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll = \
            _generate_circle(time, t_total, emitter_lat, emitter_lon,
                           standoff_km, size_scale, alt_mean, alt_var)

    elif traj_type == 'racetrack':
        print("Generating Racetrack trajectory...")
        platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll = \
            _generate_racetrack(time, t_total, emitter_lat, emitter_lon,
                              standoff_km, size_scale, alt_mean, alt_var)

    elif traj_type == 'sturn':
        print("Generating S-Turn trajectory...")
        platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll = \
            _generate_sturn(time, t_total, emitter_lat, emitter_lon,
                          standoff_km, size_scale, alt_mean, alt_var)

    elif traj_type == 'straight_offset':
        print("Generating Straight Approach with Lateral Offset...")
        platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll = \
            _generate_straight_offset(time, t_total, emitter_lat, emitter_lon,
                                    standoff_km, size_scale, alt_mean, alt_var)

    elif traj_type == 'curved_approach':
        print("Generating Curved Approach trajectory...")
        platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll = \
            _generate_curved_approach(time, t_total, dt, emitter_lat, emitter_lon,
                                    standoff_km, size_scale, alt_mean, alt_var)

    else:
        raise ValueError(f"Unknown trajectory type: {traj_type}")

    # Convert platform CG to ECEF
    platform_ecef_cg = np.zeros((n_steps, 3))
    for i in range(n_steps):
        platform_ecef_cg[i] = lla_to_ecef(platform_lat[i], platform_lon[i], platform_alt[i])

    # Calculate boresight vectors
    boresight_body = np.zeros((n_steps, 3))
    boresight_ned = np.zeros((n_steps, 3))
    boresight_ecef = np.zeros((n_steps, 3))

    # Boresight reference is downward in body frame (nadir)
    boresight_body_ref = np.array([0.0, 0.0, 1.0])

    print("Calculating boresight vectors...")

    for i in range(n_steps):
        # Apply interferometer orientation offset
        R_interfero = interferometer_orientation_rotation(config.interferometer.orientation)
        boresight_body[i] = R_interfero @ boresight_body_ref

        # Transform to NED
        R_ned_to_body = ned_to_body_rotation(platform_pitch[i], platform_roll[i], platform_yaw[i])
        boresight_ned[i] = R_ned_to_body.T @ boresight_body[i]

        # Transform to ECEF
        R_ecef_to_ned = ecef_to_ned_rotation(platform_lat[i], platform_lon[i])
        boresight_ecef[i] = R_ecef_to_ned.T @ boresight_ned[i]

    # Calculate interferometer position in ECEF
    interferometer_ecef = np.zeros((n_steps, 3))

    for i in range(n_steps):
        R_ecef_to_ned = ecef_to_ned_rotation(platform_lat[i], platform_lon[i])
        R_ned_to_body = ned_to_body_rotation(platform_pitch[i], platform_roll[i], platform_yaw[i])
        R_ecef_to_body = R_ned_to_body @ R_ecef_to_ned

        # Transform offset from body to ECEF
        offset_ecef = R_ecef_to_body.T @ config.interferometer.offset_body
        interferometer_ecef[i] = platform_ecef_cg[i] + offset_ecef

    # Calculate distances from emitter
    distances_from_emitter = np.zeros(n_steps)
    for i in range(n_steps):
        distances_from_emitter[i] = np.linalg.norm(interferometer_ecef[i] - emitter_ecef) / 1000.0

    trajectory = TrajectoryData(
        platform_lat=platform_lat,
        platform_lon=platform_lon,
        platform_alt=platform_alt,
        platform_pitch=platform_pitch,
        platform_roll=platform_roll,
        platform_yaw=platform_yaw,
        platform_ecef_cg=platform_ecef_cg,
        interferometer_ecef=interferometer_ecef,
        boresight_body=boresight_body,
        boresight_ned=boresight_ned,
        boresight_ecef=boresight_ecef,
        distances_from_emitter=distances_from_emitter,
        time=time
    )

    print("Trajectory generated successfully!")
    trajectory.print_summary()
    print()

    return trajectory


def _generate_figure8(time, t_total, emitter_lat, emitter_lon,
                     standoff_km, size_scale, alt_mean, alt_var):
    """Generate Figure-8 trajectory."""
    n_steps = len(time)
    omega = 2 * np.pi / t_total

    # Base amplitude in degrees
    a_base = standoff_km / 111.0
    b_base = standoff_km / (111.0 * np.cos(np.radians(emitter_lat)))
    a = a_base * size_scale
    b = b_base * size_scale

    # Center offset
    center_offset_lat = standoff_km / 111.0
    platform_center_lat = emitter_lat + center_offset_lat
    platform_center_lon = emitter_lon

    platform_lat = np.zeros(n_steps)
    platform_lon = np.zeros(n_steps)
    platform_alt = np.zeros(n_steps)
    platform_yaw = np.zeros(n_steps)
    platform_pitch = np.zeros(n_steps)
    platform_roll = np.zeros(n_steps)

    for i in range(n_steps):
        t = time[i]
        theta = omega * t

        delta_lat = a * np.sin(theta)
        delta_lon = b * np.sin(2 * theta) / 2

        platform_lat[i] = platform_center_lat + delta_lat
        platform_lon[i] = platform_center_lon + delta_lon
        platform_alt[i] = alt_mean + alt_var * np.sin(3 * theta)

        vx = a * np.cos(theta)
        vy = b * np.cos(2 * theta)
        platform_yaw[i] = np.degrees(np.arctan2(vy, vx))

        platform_pitch[i] = 3.0 * np.sin(theta) * np.cos(theta)
        platform_roll[i] = 2.0 * np.sin(2 * theta)

    return platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll


def _generate_circle(time, t_total, emitter_lat, emitter_lon,
                    standoff_km, size_scale, alt_mean, alt_var):
    """Generate circular trajectory."""
    n_steps = len(time)
    omega = 2 * np.pi / t_total

    radius_lat = standoff_km / 111.0
    radius_lon = standoff_km / (111.0 * np.cos(np.radians(emitter_lat)))
    radius = (radius_lat + radius_lon) / 2 * size_scale

    platform_center_lat = emitter_lat + standoff_km / 111.0
    platform_center_lon = emitter_lon + standoff_km / (111.0 * np.cos(np.radians(emitter_lat)))

    platform_lat = np.zeros(n_steps)
    platform_lon = np.zeros(n_steps)
    platform_alt = np.zeros(n_steps)
    platform_yaw = np.zeros(n_steps)
    platform_pitch = np.zeros(n_steps)
    platform_roll = np.zeros(n_steps)

    for i in range(n_steps):
        t = time[i]
        theta = omega * t

        platform_lat[i] = platform_center_lat + radius * np.cos(theta)
        platform_lon[i] = platform_center_lon + radius * np.sin(theta)
        platform_alt[i] = alt_mean + alt_var * np.sin(2 * theta)

        platform_yaw[i] = np.degrees(theta + np.pi / 2)
        platform_pitch[i] = 2.0 * np.sin(theta)
        platform_roll[i] = 1.5 * np.cos(1.5 * theta)

    return platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll


def _generate_racetrack(time, t_total, emitter_lat, emitter_lon,
                       standoff_km, size_scale, alt_mean, alt_var):
    """Generate racetrack trajectory."""
    n_steps = len(time)

    straight_length = standoff_km * size_scale / 111.0
    turn_radius = standoff_km / (2 * 111.0)

    platform_center_lat = emitter_lat + standoff_km / 111.0
    platform_center_lon = emitter_lon

    turn_length = np.pi * turn_radius
    total_length = 2 * straight_length + 2 * turn_length
    velocity = total_length / t_total

    platform_lat = np.zeros(n_steps)
    platform_lon = np.zeros(n_steps)
    platform_alt = np.zeros(n_steps)
    platform_yaw = np.zeros(n_steps)
    platform_pitch = np.zeros(n_steps)
    platform_roll = np.zeros(n_steps)

    for i in range(n_steps):
        t = time[i]
        distance = (velocity * t) % total_length

        if distance < straight_length:
            platform_lat[i] = platform_center_lat + distance
            platform_lon[i] = platform_center_lon - turn_radius
            platform_yaw[i] = 0
        elif distance < straight_length + turn_length:
            theta = (distance - straight_length) / turn_radius
            platform_lat[i] = platform_center_lat + straight_length + turn_radius * np.sin(theta)
            platform_lon[i] = platform_center_lon - turn_radius * np.cos(theta)
            platform_yaw[i] = np.degrees(theta)
        elif distance < 2 * straight_length + turn_length:
            platform_lat[i] = platform_center_lat + straight_length - (distance - straight_length - turn_length)
            platform_lon[i] = platform_center_lon + turn_radius
            platform_yaw[i] = 180
        else:
            theta = (distance - 2 * straight_length - turn_length) / turn_radius
            platform_lat[i] = platform_center_lat - turn_radius * np.sin(theta)
            platform_lon[i] = platform_center_lon + turn_radius * np.cos(theta)
            platform_yaw[i] = 180 + np.degrees(theta)

        platform_alt[i] = alt_mean + alt_var * np.sin(2 * np.pi * t / t_total)
        platform_pitch[i] = 2.0 * np.sin(2 * np.pi * t / t_total)
        platform_roll[i] = 1.5 * np.cos(3 * 2 * np.pi * t / t_total)

    return platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll


def _generate_sturn(time, t_total, emitter_lat, emitter_lon,
                   standoff_km, size_scale, alt_mean, alt_var):
    """Generate S-turn trajectory."""
    n_steps = len(time)

    start_distance_km = standoff_km * size_scale * 1.5
    start_lat_offset = start_distance_km / 111.0

    n_turns = 3
    lateral_amplitude_km = standoff_km * 0.6
    lateral_amplitude_lon = lateral_amplitude_km / (111.0 * np.cos(np.radians(emitter_lat)))

    approach_distance_km = start_distance_km - standoff_km * 0.3
    approach_distance_deg = approach_distance_km / 111.0
    approach_velocity = approach_distance_deg / t_total

    platform_lat = np.zeros(n_steps)
    platform_lon = np.zeros(n_steps)
    platform_alt = np.zeros(n_steps)
    platform_yaw = np.zeros(n_steps)
    platform_pitch = np.zeros(n_steps)
    platform_roll = np.zeros(n_steps)

    for i in range(n_steps):
        t = time[i]
        progress = t / t_total

        lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress)
        lon_offset = lateral_amplitude_lon * np.sin(2 * np.pi * n_turns * progress)

        platform_lat[i] = lat_approach
        platform_lon[i] = emitter_lon + lon_offset

        alt_descent = alt_var * progress
        platform_alt[i] = alt_mean + alt_var * np.sin(4 * np.pi * progress) - alt_descent

        v_lat = -approach_velocity
        v_lon = lateral_amplitude_lon * 2 * np.pi * n_turns * np.cos(2 * np.pi * n_turns * progress) / t_total
        platform_yaw[i] = np.degrees(np.arctan2(v_lon, v_lat))

        turn_phase = 2 * np.pi * n_turns * progress
        platform_pitch[i] = -2.0 * progress
        platform_roll[i] = 15.0 * np.sin(turn_phase)

    return platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll


def _generate_straight_offset(time, t_total, emitter_lat, emitter_lon,
                             standoff_km, size_scale, alt_mean, alt_var):
    """Generate straight approach with lateral offset."""
    n_steps = len(time)

    start_distance_km = standoff_km * size_scale * 1.5
    start_lat_offset = start_distance_km / 111.0
    lateral_offset_km = standoff_km * 0.6
    lateral_offset_lon = lateral_offset_km / (111.0 * np.cos(np.radians(emitter_lat)))
    approach_distance_km = start_distance_km - standoff_km * 0.3
    approach_distance_deg = approach_distance_km / 111.0

    platform_lat = np.zeros(n_steps)
    platform_lon = np.zeros(n_steps)
    platform_alt = np.zeros(n_steps)
    platform_yaw = np.zeros(n_steps)
    platform_pitch = np.zeros(n_steps)
    platform_roll = np.zeros(n_steps)

    for i in range(n_steps):
        t = time[i]
        progress = t / t_total

        lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress)
        platform_lat[i] = lat_approach
        platform_lon[i] = emitter_lon + lateral_offset_lon
        platform_alt[i] = alt_mean + alt_var * np.sin(2 * np.pi * progress) - alt_var * 0.5 * progress
        platform_yaw[i] = 0
        platform_pitch[i] = -1.5 * progress
        platform_roll[i] = 1.0 * np.sin(4 * np.pi * progress)

    return platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll


def _generate_curved_approach(time, t_total, dt, emitter_lat, emitter_lon,
                             standoff_km, size_scale, alt_mean, alt_var):
    """Generate curved approach trajectory."""
    n_steps = len(time)

    start_distance_km = standoff_km * size_scale * 1.5
    start_lat_offset = start_distance_km / 111.0
    initial_lateral_offset_km = standoff_km * 0.8
    initial_lateral_offset_lon = initial_lateral_offset_km / (111.0 * np.cos(np.radians(emitter_lat)))
    approach_distance_km = start_distance_km - standoff_km * 0.3
    approach_distance_deg = approach_distance_km / 111.0

    platform_lat = np.zeros(n_steps)
    platform_lon = np.zeros(n_steps)
    platform_alt = np.zeros(n_steps)
    platform_yaw = np.zeros(n_steps)
    platform_pitch = np.zeros(n_steps)
    platform_roll = np.zeros(n_steps)

    for i in range(n_steps):
        t = time[i]
        progress = t / t_total

        lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress)
        curve_factor = 3 * progress**2 - 2 * progress**3
        lon_offset = initial_lateral_offset_lon * (1 - curve_factor)

        platform_lat[i] = lat_approach
        platform_lon[i] = emitter_lon + lon_offset
        platform_alt[i] = alt_mean + alt_var * np.sin(3 * np.pi * progress) - alt_var * 0.6 * progress

    # Calculate yaw based on velocity direction
    for i in range(n_steps):
        if i < n_steps - 1:
            lon_rate = (platform_lon[min(i + 1, n_steps - 1)] - platform_lon[i]) / dt
            lat_rate = (platform_lat[min(i + 1, n_steps - 1)] - platform_lat[i]) / dt
        else:
            lon_rate = (platform_lon[i] - platform_lon[i - 1]) / dt
            lat_rate = (platform_lat[i] - platform_lat[i - 1]) / dt

        platform_yaw[i] = np.degrees(np.arctan2(lon_rate, lat_rate))
        progress = time[i] / t_total
        platform_pitch[i] = -2.0 * progress

        turn_rate = initial_lateral_offset_lon * 6 * (progress - progress**2) / t_total
        platform_roll[i] = -np.degrees(np.arctan2(turn_rate, 1.0)) * 2.0

    return platform_lat, platform_lon, platform_alt, platform_yaw, platform_pitch, platform_roll
