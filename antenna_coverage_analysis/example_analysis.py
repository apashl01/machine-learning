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
    print(f"  RX Antennas: {config.num_rx_antennas}")
    print(f"  TX Antennas: {config.num_tx_antennas}")
    print(f"  Spiral beamwidth: {config.spiral_antenna.beamwidth_deg}°")
    print(f"  Spiral gain: {config.spiral_antenna.gain_dbi} dBi")

    print("\nRX Antenna Positions:")
    for ant in config.rx_antennas:
        print(f"  {ant.name}: pos={ant.position}, orient={ant.orientation}°, "
              f"band={ant.freq_band}")

    print("\nTX Antenna Positions:")
    for ant in config.tx_antennas:
        print(f"  {ant.name}: pos={ant.position}, orient={ant.orientation}°, "
              f"band={ant.freq_band}, gain={ant.gain_dbi} dBi")

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

    # Plot RX antennas (use rx_antennas if available, else legacy antennas)
    rx_ants = result.config.rx_antennas if result.config.rx_antennas else result.config.antennas
    if rx_ants:
        rx_positions = np.array([ant.position for ant in rx_ants])
        # Separate by frequency band
        rx_2_18 = [ant for ant in rx_ants if "2-18" in ant.freq_band]
        rx_low = [ant for ant in rx_ants if "<2" in ant.freq_band or "low" in ant.freq_band.lower()]

        if rx_2_18:
            pos_2_18 = np.array([ant.position for ant in rx_2_18])
            ax4.scatter(pos_2_18[:, 1], pos_2_18[:, 0], s=100, c='blue',
                        marker='o', label=f'RX 2-18 GHz ({len(rx_2_18)})')
        if rx_low:
            pos_low = np.array([ant.position for ant in rx_low])
            ax4.scatter(pos_low[:, 1], pos_low[:, 0], s=100, c='cyan',
                        marker='s', label=f'RX <2 GHz ({len(rx_low)})')

        # Draw RX orientation arrows
        for ant in rx_ants:
            az_rad = np.radians(ant.orientation[0])
            dx = 0.2 * np.sin(az_rad)
            dy = 0.2 * np.cos(az_rad)
            ax4.arrow(ant.position[1], ant.position[0], dx, dy,
                      head_width=0.05, head_length=0.03, fc='blue', ec='blue', alpha=0.6)

    # Plot TX antennas
    tx_ants = result.config.tx_antennas
    if tx_ants:
        tx_2_18 = [ant for ant in tx_ants if "2-18" in ant.freq_band]
        tx_low = [ant for ant in tx_ants if "<2" in ant.freq_band or "low" in ant.freq_band.lower()]

        if tx_2_18:
            pos_2_18 = np.array([ant.position for ant in tx_2_18])
            ax4.scatter(pos_2_18[:, 1], pos_2_18[:, 0], s=150, c='red',
                        marker='^', label=f'TX 2-18 GHz ({len(tx_2_18)})')
        if tx_low:
            pos_low = np.array([ant.position for ant in tx_low])
            ax4.scatter(pos_low[:, 1], pos_low[:, 0], s=150, c='orange',
                        marker='v', label=f'TX <2 GHz ({len(tx_low)})')

        # Draw TX orientation arrows
        for ant in tx_ants:
            az_rad = np.radians(ant.orientation[0])
            dx = 0.25 * np.sin(az_rad)
            dy = 0.25 * np.cos(az_rad)
            ax4.arrow(ant.position[1], ant.position[0], dx, dy,
                      head_width=0.06, head_length=0.04, fc='red', ec='red', alpha=0.7)

    ax4.set_xlabel('Y (Right) [m]')
    ax4.set_ylabel('X (Forward) [m]')
    ax4.set_title('Antenna Placement on UAV (RX & TX)')
    ax4.grid(True, alpha=0.3)
    ax4.axis('equal')
    ax4.legend(loc='upper right', fontsize=8)

    # Add UAV outline (simple rectangle)
    uav_w = result.config.uav_width / 2
    uav_l = result.config.uav_length / 2
    rect = plt.Rectangle((-uav_w, -uav_l), 2*uav_w, 2*uav_l,
                         fill=False, edgecolor='gray', linestyle='--', linewidth=2)
    ax4.add_patch(rect)

    # Add forward direction indicator
    ax4.annotate('FWD', xy=(0, uav_l + 0.1), ha='center', fontsize=10, fontweight='bold')

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
