#!/usr/bin/env python3
"""
UAV Antenna Coverage Analysis Example

Demonstrates multi-antenna coverage analysis matching MATLAB uav_antenna_coverage.m.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt

from antenna_coverage_analysis import (
    load_uav_config,
    analyze_coverage,
    print_statistics
)


def main():
    """Run UAV antenna coverage analysis example."""

    print("=" * 70)
    print("UAV ANTENNA COVERAGE ANALYSIS")
    print("=" * 70)

    # Load configuration
    config = load_uav_config()

    print(f"\nUAV Configuration:")
    print(f"  Frequency: {config.frequency_ghz:.2f} GHz")
    print(f"  Number of antennas: {config.num_antennas}")
    print(f"  Spiral beamwidth: {config.spiral_antenna.beamwidth_deg}°")
    print(f"  Spiral gain: {config.spiral_antenna.gain_dbi} dBi")

    print("\nAntenna Positions:")
    for ant in config.antennas:
        print(f"  {ant.name}: pos={ant.position}, orient={ant.orientation}°")

    # Analyze coverage
    print("\nCalculating combined coverage...")
    result = analyze_coverage(config)

    # Print statistics
    print("\n" + print_statistics(result))

    # Generate plots
    generate_plots(result)

    print("\nAnalysis complete!")


def generate_plots(result):
    """Generate coverage plots matching MATLAB."""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    AZ, EL = np.meshgrid(result.azimuth, result.elevation)

    # Plot 1: 2D Coverage map
    ax1 = axes[0, 0]
    c = ax1.contourf(AZ, EL, result.coverage_db, levels=20, cmap='jet')
    plt.colorbar(c, ax=ax1, label='Gain (dBi)')
    ax1.set_xlabel('Azimuth (degrees)')
    ax1.set_ylabel('Elevation (degrees)')
    ax1.set_title('Combined Coverage Map - Max Gain (dBi)')
    ax1.grid(True, alpha=0.3)
    # Mark forward direction
    ax1.plot(0, 0, 'w*', markersize=15, linewidth=2)
    ax1.text(0, 5, 'Forward', color='white', ha='center', fontsize=10)

    # Plot 2: Azimuth cut at elevation = 0
    ax2 = axes[0, 1]
    el_idx = np.argmin(np.abs(result.elevation))
    ax2.plot(result.azimuth, result.coverage_db[el_idx, :], 'b-', linewidth=2)
    ax2.set_xlabel('Azimuth (degrees)')
    ax2.set_ylabel('Gain (dB)')
    ax2.set_title('Coverage - Azimuth Cut (Elevation = 0°)')
    ax2.set_xlim([-180, 180])
    ax2.grid(True, alpha=0.3)
    ax2.axhline(result.max_gain_db - 3, color='r', linestyle='--', label='-3 dB')
    ax2.legend()

    # Plot 3: Elevation cut at azimuth = 0 (forward)
    ax3 = axes[1, 0]
    az_idx = np.argmin(np.abs(result.azimuth))
    ax3.plot(result.elevation, result.coverage_db[:, az_idx], 'r-', linewidth=2)
    ax3.set_xlabel('Elevation (degrees)')
    ax3.set_ylabel('Gain (dB)')
    ax3.set_title('Coverage - Elevation Cut (Azimuth = 0° - Forward)')
    ax3.set_xlim([-90, 90])
    ax3.grid(True, alpha=0.3)
    ax3.axhline(result.max_gain_db - 3, color='b', linestyle='--', label='-3 dB')
    ax3.legend()

    # Plot 4: Antenna placement visualization
    ax4 = axes[1, 1]
    positions = np.array([ant.position for ant in result.config.antennas])
    ax4.scatter(positions[:, 1], positions[:, 0], s=100, c='red',
                marker='o', label='RX Antennas')

    # Draw orientation arrows
    for i, ant in enumerate(result.config.antennas):
        az_rad = np.radians(ant.orientation[0])
        dx = 0.2 * np.sin(az_rad)
        dy = 0.2 * np.cos(az_rad)
        ax4.arrow(ant.position[1], ant.position[0], dx, dy,
                  head_width=0.05, head_length=0.03, fc='blue', ec='blue')

    ax4.set_xlabel('Y (Right) [m]')
    ax4.set_ylabel('X (Forward) [m]')
    ax4.set_title('Antenna Placement on UAV')
    ax4.grid(True, alpha=0.3)
    ax4.axis('equal')
    ax4.legend()

    # Add UAV outline (simple rectangle)
    uav_w = result.config.uav_width / 2
    uav_l = result.config.uav_length / 2
    rect = plt.Rectangle((-uav_w, -uav_l), 2*uav_w, 2*uav_l,
                         fill=False, edgecolor='gray', linestyle='--')
    ax4.add_patch(rect)

    fig.suptitle(f'UAV Antenna Coverage Analysis ({result.config.frequency_ghz:.0f} GHz)',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / "uav_coverage_analysis.png"
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {filepath}")

    try:
        plt.show()
    except Exception:
        print("(Non-GUI environment - plot saved but not displayed)")


if __name__ == "__main__":
    main()
