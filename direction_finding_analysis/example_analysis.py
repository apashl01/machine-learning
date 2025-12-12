#!/usr/bin/env python3
"""
RF Interferometer Analysis Example

Demonstrates 1D RF interferometer analysis matching MATLAB rf_interferometer_analysis.m.
"""

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt

from direction_finding_analysis import (
    load_interferometer_config,
    analyze_interferometer,
    print_summary
)


def main():
    """Run interferometer analysis example."""

    print("=" * 70)
    print("1D RF INTERFEROMETER ANALYSIS")
    print("=" * 70)

    # Load configuration
    config = load_interferometer_config()

    print(f"\nInterferometer Configuration:")
    print(f"  Number of elements: {config.n_elements}")
    print(f"  Frequency range: {config.freq_range_ghz[0]}-{config.freq_range_ghz[1]} GHz")
    print(f"  Element positions: {config.element_positions} inches")
    print(f"  All baselines: {config.baselines} inches")
    print(f"  Phase error at high SNR: {config.phase_error_deg}°")

    # Analyze
    results = analyze_interferometer(config)

    # Print summary
    print("\n" + print_summary(results))

    # Generate plots
    generate_plots(results)

    print("\nAnalysis complete!")


def generate_plots(results):
    """Generate analysis plots matching MATLAB."""

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    incident_angles = results.accuracy.incident_angles
    frequencies = results.accuracy.frequencies_ghz
    n_freq = len(frequencies)
    colors = plt.cm.tab10(np.linspace(0, 1, n_freq))

    # Plot 1: Angle accuracy vs incident angle
    ax1 = axes[0, 0]
    for f_idx in range(n_freq):
        # Ideal (dashed)
        ax1.semilogy(incident_angles, results.accuracy.angle_error_ideal[f_idx, :],
                     '--', color=colors[f_idx], linewidth=1.5, alpha=0.5)
        # Realistic (solid)
        ax1.semilogy(incident_angles, results.accuracy.angle_error_realistic[f_idx, :],
                     '-', color=colors[f_idx], linewidth=2,
                     label=f'{frequencies[f_idx]:.0f} GHz')

    ax1.set_xlabel('Incident Angle off Boresight (degrees)')
    ax1.set_ylabel('Angle Error (degrees)')
    ax1.set_title(f'Angle Accuracy vs Incident Angle\n(Solid: w/ SNR effects, Dashed: Ideal, D_max = {results.config.max_baseline:.1f} in)')
    ax1.legend(loc='upper left')
    ax1.set_xlim([-80, 80])
    ax1.set_ylim([0.1, 100])
    ax1.grid(True, alpha=0.3)

    # Plot 2: SNR vs angle
    ax2 = axes[0, 1]
    for f_idx in range(n_freq):
        ax2.plot(incident_angles, results.accuracy.snr_db[f_idx, :],
                 '-', color=colors[f_idx], linewidth=2,
                 label=f'{frequencies[f_idx]:.0f} GHz')
    ax2.set_xlabel('Incident Angle off Boresight (degrees)')
    ax2.set_ylabel('SNR (dB)')
    ax2.set_title('SNR vs Angle')
    ax2.legend(loc='lower left')
    ax2.set_xlim([-80, 80])
    ax2.grid(True, alpha=0.3)
    ax2.axhline(20, color='r', linestyle='--', linewidth=1, label='20 dB threshold')

    # Plot 3: Ambiguity-free region (shortest baseline)
    ax3 = axes[1, 0]
    shortest_baseline_idx = 0
    ax3.plot(frequencies, results.ambiguity.ambiguity_angles[shortest_baseline_idx, :],
             'o-', linewidth=2, markersize=10, color='green', markerfacecolor='green')
    ax3.axhline(90, color='r', linestyle='--', linewidth=1.5, label='Full Coverage')
    ax3.set_xlabel('Frequency (GHz)')
    ax3.set_ylabel('Unambiguous Half-Angle (degrees)')
    ax3.set_title(f'Ambiguity-Free Region (Shortest Baseline: {results.config.min_baseline:.2f} in)')
    ax3.set_ylim([0, 95])
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    # Plot 4: Array geometry
    ax4 = axes[1, 1]
    positions = results.config.element_positions
    ax4.plot(positions, [0] * len(positions), 'ro', markersize=15,
             markerfacecolor='red', linewidth=2)

    # Draw baseline lines
    for i in range(len(positions) - 1):
        ax4.plot([positions[i], positions[i + 1]], [0, 0], 'b--', linewidth=1.5)
        mid = (positions[i] + positions[i + 1]) / 2
        spacing = positions[i + 1] - positions[i]
        ax4.text(mid, -0.15, f'{spacing:.2f}"', ha='center', fontsize=9)

    # Total aperture
    ax4.plot([positions[0], positions[-1]], [0.3, 0.3], 'g-', linewidth=2)
    ax4.text(np.mean(positions), 0.35, f'Total: {results.config.max_baseline:.1f}"',
             ha='center', color='green')

    ax4.set_xlabel('Position (inches)')
    ax4.set_title('Interferometer Array Geometry')
    ax4.set_ylim([-0.5, 0.6])
    ax4.set_xlim([-0.5, max(positions) + 0.5])
    ax4.grid(True, alpha=0.3)
    ax4.set_yticks([])

    fig.suptitle('1D RF Interferometer Analysis (2-18 GHz)', fontsize=14, fontweight='bold')
    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Save combined plot
    filepath = output_dir / "interferometer_analysis.png"
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"\nCombined plot saved to: {filepath}")

    # Task 2.4: Save individual subplots for PowerPoint slides
    # Save each subplot as a separate file for the reporting generator
    individual_plots = [
        (ax1, 'df_angle_error.png', 'Angle Accuracy vs Incident Angle'),
        (ax2, 'df_incident_angle.png', 'SNR vs Incident Angle'),
        (ax3, 'df_ambiguity.png', 'Ambiguity-Free Region'),
    ]

    for ax, filename, title in individual_plots:
        # Create a new figure for this subplot
        fig_single = plt.figure(figsize=(8, 6))
        ax_single = fig_single.add_subplot(111)

        # Copy the subplot content
        for line in ax.get_lines():
            ax_single.plot(line.get_xdata(), line.get_ydata(),
                          linestyle=line.get_linestyle(),
                          linewidth=line.get_linewidth(),
                          color=line.get_color(),
                          marker=line.get_marker(),
                          markersize=line.get_markersize(),
                          label=line.get_label() if line.get_label()[0] != '_' else None,
                          alpha=line.get_alpha())

        # Copy axis properties
        ax_single.set_xlabel(ax.get_xlabel())
        ax_single.set_ylabel(ax.get_ylabel())
        ax_single.set_title(ax.get_title())
        ax_single.set_xlim(ax.get_xlim())
        ax_single.set_ylim(ax.get_ylim())
        ax_single.grid(ax.get_xgridlines()[0].get_visible() if ax.get_xgridlines() else True, alpha=0.3)

        # Copy scale (log/linear)
        if ax.get_yscale() == 'log':
            ax_single.set_yscale('log')
        if ax.get_xscale() == 'log':
            ax_single.set_xscale('log')

        # Add legend if original had one
        if ax.get_legend():
            ax_single.legend(loc=ax.get_legend()._loc)

        # Save individual plot
        fig_single.tight_layout()
        individual_path = output_dir / filename
        fig_single.savefig(individual_path, dpi=150, bbox_inches='tight')
        print(f"Individual plot saved to: {individual_path}")
        plt.close(fig_single)

    try:
        plt.show()
    except Exception:
        print("(Non-GUI environment - plot saved but not displayed)")


if __name__ == "__main__":
    main()
