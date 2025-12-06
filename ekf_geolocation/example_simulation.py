#!/usr/bin/env python3
"""
EKF Geolocation Simulation Example

Demonstrates complete EKF geolocation simulation matching MATLAB main_simulation.m.

This script:
1. Loads configuration
2. Generates trajectory
3. Calculates signal propagation
4. Generates interferometer measurements
5. Runs parameter sweep (optional)
6. Runs EKF with best parameters
7. Visualizes results
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

from ekf_geolocation import (
    load_simulation_config,
    run_simulation,
    SimulationResult
)


def main():
    """Run EKF geolocation simulation example."""

    print("=" * 70)
    print("EKF GEOLOCATION SIMULATION")
    print("=" * 70)

    # Load configuration
    config = load_simulation_config()

    # Optionally modify config for faster testing (disable parameter sweep)
    # config.parameter_sweep.enabled = False

    # Run simulation
    result = run_simulation(config)

    # Generate plots
    generate_plots(result)

    print("\nSimulation complete!")


def generate_plots(result: SimulationResult):
    """Generate visualization plots matching MATLAB."""

    config = result.config
    trajectory = result.trajectory
    interferometer_data = result.interferometer_data
    ekf_result = result.ekf_result

    # Figure 1: Main Trajectory and Error Plot
    fig1, axes1 = plt.subplots(2, 2, figsize=(14, 10))

    # 3D Trajectory
    ax1 = fig1.add_subplot(2, 2, 1, projection='3d')
    # Clear the 2D subplot and replace with 3D
    axes1[0, 0].remove()

    # Plot full trajectory
    ax1.plot(trajectory.platform_lon, trajectory.platform_lat,
             trajectory.platform_alt, 'b-', linewidth=1, label='Path')

    # Mark valid measurement points (green)
    valid_idx = interferometer_data.measurement_valid
    ax1.scatter(trajectory.platform_lon[valid_idx],
                trajectory.platform_lat[valid_idx],
                trajectory.platform_alt[valid_idx],
                c='g', s=10, alpha=0.5, label='Valid Meas')

    # Mark invalid measurement points (red)
    invalid_idx = ~interferometer_data.measurement_valid
    if np.any(invalid_idx):
        ax1.scatter(trajectory.platform_lon[invalid_idx],
                    trajectory.platform_lat[invalid_idx],
                    trajectory.platform_alt[invalid_idx],
                    c='r', s=10, alpha=0.5, label='Rejected')

    # Plot emitter
    ax1.scatter([config.emitter.lon], [config.emitter.lat],
                [config.emitter.alt], c='r', marker='*', s=300, label='Emitter')

    # Plot estimates
    ax1.plot(result.estimated_lla[:, 1], result.estimated_lla[:, 0],
             result.estimated_lla[:, 2], 'm.', markersize=2, label='Estimates')

    # Final estimate
    ax1.scatter([result.estimated_lla[-1, 1]], [result.estimated_lla[-1, 0]],
                [result.estimated_lla[-1, 2]], c='m', marker='o', s=100,
                edgecolors='black', label='Final Est.')

    # Start point
    ax1.scatter([trajectory.platform_lon[0]], [trajectory.platform_lat[0]],
                [trajectory.platform_alt[0]], c='b', marker='s', s=100, label='Start')

    ax1.set_xlabel('Longitude (deg)')
    ax1.set_ylabel('Latitude (deg)')
    ax1.set_zlabel('Altitude (m)')
    ax1.set_title(f'{config.trajectory.type} Trajectory')
    ax1.legend(loc='best', fontsize=8)
    ax1.view_init(elev=25, azim=-45)

    # Top-down view
    ax2 = axes1[0, 1]
    ax2.plot(trajectory.platform_lon, trajectory.platform_lat, 'b-', linewidth=2, label='Platform')
    ax2.plot(config.emitter.lon, config.emitter.lat, 'r*', markersize=20, label='Emitter')
    ax2.plot(result.estimated_lla[:, 1], result.estimated_lla[:, 0], 'g.', markersize=3, label='Estimates')
    ax2.plot(result.estimated_lla[-1, 1], result.estimated_lla[-1, 0], 'go', markersize=12, label='Final')
    ax2.plot(trajectory.platform_lon[0], trajectory.platform_lat[0], 'bs', markersize=12, label='Start')
    ax2.set_xlabel('Longitude (deg)')
    ax2.set_ylabel('Latitude (deg)')
    ax2.set_title('Top-Down View')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.axis('equal')

    # Position Error
    ax3 = axes1[1, 0]
    ax3.plot(config.time, result.position_errors, 'b-', linewidth=2, label='Actual Error')
    uncertainty_bound = np.sqrt(np.sum(ekf_result.P_history, axis=1))
    ax3.plot(config.time, uncertainty_bound, 'r--', linewidth=2, label='1-sigma Uncertainty')
    ax3.set_xlabel('Time (s)')
    ax3.set_ylabel('Error (m)')
    ax3.set_title('Position Estimation Error')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)

    # Distance from Emitter
    ax4 = axes1[1, 1]
    ax4.plot(config.time, trajectory.distances_from_emitter, 'b-', linewidth=2, label='Distance')
    ax4.axhline(config.trajectory.standoff_distance_km, color='r', linestyle='--',
                linewidth=1.5, label='Nominal Standoff')
    ax4.set_xlabel('Time (s)')
    ax4.set_ylabel('Distance (km)')
    ax4.set_title('Interferometer Distance from Emitter')
    ax4.legend(loc='best')
    ax4.grid(True, alpha=0.3)

    fig1.suptitle('EKF Geolocation - Trajectory and Error', fontsize=14, fontweight='bold')
    plt.tight_layout()

    # Figure 2: Component Errors
    fig2, axes2 = plt.subplots(1, 3, figsize=(14, 4))

    # Latitude error
    ax = axes2[0]
    lat_error = result.estimated_lla[:, 0] - config.emitter.lat
    lat_uncertainty = np.sqrt(ekf_result.P_history[:, 0]) / 111000
    ax.plot(config.time, lat_error, 'b-', linewidth=1.5, label='Error')
    ax.plot(config.time, lat_uncertainty, 'r--', linewidth=1.5, label='1-sigma')
    ax.plot(config.time, -lat_uncertainty, 'r--', linewidth=1.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Latitude Error (deg)')
    ax.set_title('Latitude Estimation Error')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    # Longitude error
    ax = axes2[1]
    lon_error = result.estimated_lla[:, 1] - config.emitter.lon
    lon_uncertainty = np.sqrt(ekf_result.P_history[:, 1]) / (111000 * np.cos(np.radians(config.emitter.lat)))
    ax.plot(config.time, lon_error, 'b-', linewidth=1.5, label='Error')
    ax.plot(config.time, lon_uncertainty, 'r--', linewidth=1.5, label='1-sigma')
    ax.plot(config.time, -lon_uncertainty, 'r--', linewidth=1.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Longitude Error (deg)')
    ax.set_title('Longitude Estimation Error')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    # Altitude error
    ax = axes2[2]
    alt_error = result.estimated_lla[:, 2] - config.emitter.alt
    alt_uncertainty = np.sqrt(ekf_result.P_history[:, 2])
    ax.plot(config.time, alt_error, 'b-', linewidth=1.5, label='Error')
    ax.plot(config.time, alt_uncertainty, 'r--', linewidth=1.5, label='1-sigma')
    ax.plot(config.time, -alt_uncertainty, 'r--', linewidth=1.5)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Altitude Error (m)')
    ax.set_title('Altitude Estimation Error')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    fig2.suptitle('EKF Geolocation - Component Errors', fontsize=14, fontweight='bold')
    plt.tight_layout()

    # Figure 3: Interferometer Performance
    fig3, axes3 = plt.subplots(2, 2, figsize=(12, 8))

    # SNR over time
    ax = axes3[0, 0]
    ax.plot(config.time, interferometer_data.snr_db, 'b-', linewidth=2)
    ax.axhline(20, color='r', linestyle='--', linewidth=1.5, label='20 dB threshold')
    ax.axhline(10, color='y', linestyle='--', linewidth=1.5, label='10 dB')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('SNR (dB)')
    ax.set_title('Signal-to-Noise Ratio')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    # Angle measurement error over time
    ax = axes3[0, 1]
    ax.plot(config.time, interferometer_data.angle_error_deg, 'g-', linewidth=2)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Angle Error (degrees)')
    ax.set_title('Angle Measurement Accuracy')
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3)

    # Angle error vs incident angle
    ax = axes3[1, 0]
    sc = ax.scatter(interferometer_data.incident_angles, interferometer_data.angle_error_deg,
                   c=interferometer_data.snr_db, s=30, cmap='viridis')
    plt.colorbar(sc, ax=ax, label='SNR (dB)')
    ax.set_xlabel('Incident Angle (degrees)')
    ax.set_ylabel('Angle Error (degrees)')
    ax.set_title('Angle Error vs Incident Angle (colored by SNR)')
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3)

    # Incident angle over time
    ax = axes3[1, 1]
    ax.plot(config.time, interferometer_data.incident_angles, 'b-', linewidth=2)
    ax.axhline(config.interferometer.max_incident_angle_deg, color='r', linestyle='--',
               linewidth=1.5, label=f'Max valid ({config.interferometer.max_incident_angle_deg} deg)')
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Incident Angle (degrees)')
    ax.set_title('Incident Angle from Boresight')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    fig3.suptitle(f'Interferometer Performance ({config.emitter.frequency_ghz:.1f} GHz, '
                  f'{config.interferometer.max_baseline:.1f}" aperture)',
                  fontsize=14, fontweight='bold')
    plt.tight_layout()

    # Save plots
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    fig1.savefig(output_dir / "ekf_trajectory_error.png", dpi=150, bbox_inches='tight')
    fig2.savefig(output_dir / "ekf_component_errors.png", dpi=150, bbox_inches='tight')
    fig3.savefig(output_dir / "ekf_interferometer_performance.png", dpi=150, bbox_inches='tight')

    print(f"\nPlots saved to: {output_dir}")

    try:
        plt.show()
    except Exception:
        print("(Non-GUI environment - plots saved but not displayed)")


if __name__ == "__main__":
    main()
