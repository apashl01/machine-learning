"""
Coordinate transformation utilities for EKF Geolocation.

Implements:
- LLA (Lat/Lon/Alt) to ECEF conversion
- ECEF to LLA conversion
- ECEF to NED rotation matrix
- NED to Body rotation matrix
- Interferometer orientation rotation

Matches MATLAB coordinate transform functions from demo files.
"""

import numpy as np
from typing import Tuple, Union


# WGS84 ellipsoid parameters
WGS84_A = 6378137.0           # Semi-major axis (meters)
WGS84_F = 1.0 / 298.257223563  # Flattening
WGS84_E2 = 2 * WGS84_F - WGS84_F**2  # First eccentricity squared


def lla_to_ecef(lat: float, lon: float, alt: float) -> np.ndarray:
    """
    Convert geodetic coordinates (LLA) to ECEF.

    Args:
        lat: Latitude (degrees)
        lon: Longitude (degrees)
        alt: Altitude above WGS84 ellipsoid (meters)

    Returns:
        ECEF coordinates [X, Y, Z] in meters
    """
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)

    # Prime vertical radius of curvature
    N = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat_rad)**2)

    # ECEF coordinates
    X = (N + alt) * np.cos(lat_rad) * np.cos(lon_rad)
    Y = (N + alt) * np.cos(lat_rad) * np.sin(lon_rad)
    Z = (N * (1 - WGS84_E2) + alt) * np.sin(lat_rad)

    return np.array([X, Y, Z])


def ecef_to_lla(ecef: np.ndarray) -> Tuple[float, float, float]:
    """
    Convert ECEF coordinates to geodetic (LLA).

    Uses iterative algorithm for altitude calculation.

    Args:
        ecef: ECEF coordinates [X, Y, Z] in meters

    Returns:
        Tuple of (lat, lon, alt) where lat/lon in degrees, alt in meters
    """
    X, Y, Z = ecef[0], ecef[1], ecef[2]

    # Longitude is straightforward
    lon = np.degrees(np.arctan2(Y, X))

    # Iterative solution for latitude and altitude
    p = np.sqrt(X**2 + Y**2)
    lat_rad = np.arctan2(Z, p * (1 - WGS84_E2))  # Initial guess

    for _ in range(10):  # Usually converges in 2-3 iterations
        N = WGS84_A / np.sqrt(1 - WGS84_E2 * np.sin(lat_rad)**2)
        alt = p / np.cos(lat_rad) - N
        lat_rad = np.arctan2(Z, p * (1 - WGS84_E2 * N / (N + alt)))

    lat = np.degrees(lat_rad)

    return lat, lon, alt


def ecef_to_ned_rotation(lat: float, lon: float) -> np.ndarray:
    """
    Create rotation matrix from ECEF to NED frame.

    Args:
        lat: Latitude (degrees)
        lon: Longitude (degrees)

    Returns:
        3x3 rotation matrix R such that v_ned = R @ v_ecef
    """
    lat_rad = np.radians(lat)
    lon_rad = np.radians(lon)

    sin_lat = np.sin(lat_rad)
    cos_lat = np.cos(lat_rad)
    sin_lon = np.sin(lon_rad)
    cos_lon = np.cos(lon_rad)

    # Rotation matrix from ECEF to NED
    R = np.array([
        [-sin_lat * cos_lon, -sin_lat * sin_lon,  cos_lat],
        [-sin_lon,            cos_lon,             0      ],
        [-cos_lat * cos_lon, -cos_lat * sin_lon, -sin_lat]
    ])

    return R


def ned_to_body_rotation(pitch: float, roll: float, yaw: float) -> np.ndarray:
    """
    Create rotation matrix from NED to body frame.

    Uses aerospace convention (yaw-pitch-roll order, 3-2-1 Euler angles).

    Args:
        pitch: Pitch angle (degrees)
        roll: Roll angle (degrees)
        yaw: Yaw angle (degrees)

    Returns:
        3x3 rotation matrix R such that v_body = R @ v_ned
    """
    pitch_rad = np.radians(pitch)
    roll_rad = np.radians(roll)
    yaw_rad = np.radians(yaw)

    # Individual rotation matrices
    R_yaw = np.array([
        [np.cos(yaw_rad),  np.sin(yaw_rad), 0],
        [-np.sin(yaw_rad), np.cos(yaw_rad), 0],
        [0,                0,               1]
    ])

    R_pitch = np.array([
        [np.cos(pitch_rad),  0, -np.sin(pitch_rad)],
        [0,                  1,  0                ],
        [np.sin(pitch_rad),  0,  np.cos(pitch_rad)]
    ])

    R_roll = np.array([
        [1, 0,                0               ],
        [0, np.cos(roll_rad), np.sin(roll_rad)],
        [0, -np.sin(roll_rad), np.cos(roll_rad)]
    ])

    # Combined rotation: R = R_roll * R_pitch * R_yaw
    R = R_roll @ R_pitch @ R_yaw

    return R


def interferometer_orientation_rotation(orientation_deg: np.ndarray) -> np.ndarray:
    """
    Create rotation matrix for interferometer orientation offset.

    Args:
        orientation_deg: [roll, pitch, yaw] in degrees

    Returns:
        3x3 rotation matrix
    """
    roll_rad = np.radians(orientation_deg[0])
    pitch_rad = np.radians(orientation_deg[1])
    yaw_rad = np.radians(orientation_deg[2])

    R_yaw = np.array([
        [np.cos(yaw_rad),  np.sin(yaw_rad), 0],
        [-np.sin(yaw_rad), np.cos(yaw_rad), 0],
        [0,                0,               1]
    ])

    R_pitch = np.array([
        [np.cos(pitch_rad),  0, -np.sin(pitch_rad)],
        [0,                  1,  0                ],
        [np.sin(pitch_rad),  0,  np.cos(pitch_rad)]
    ])

    R_roll = np.array([
        [1, 0,                0               ],
        [0, np.cos(roll_rad), np.sin(roll_rad)],
        [0, -np.sin(roll_rad), np.cos(roll_rad)]
    ])

    # Combined rotation: R = R_roll * R_pitch * R_yaw
    R = R_roll @ R_pitch @ R_yaw

    return R
