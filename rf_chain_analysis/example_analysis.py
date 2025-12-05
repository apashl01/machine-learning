#!/usr/bin/env python3
"""
RF Chain Analysis Example

Demonstrates RF chain analysis with cascaded components.
Shows transmit mode with power tracking and saturation checking.

Matches MATLAB example_rf_chain_analysis.m functionality.
"""

import sys
from pathlib import Path
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt

from rf_chain_analysis import (
    load_chain_config,
    analyze_rf_chain,
    print_results_summary,
    print_gain_breakdown_table
)


def main():
    """Run RF chain analysis example matching MATLAB."""

    # Load chain configuration
    chain = load_chain_config()

    print("=== RF Chain Configuration ===")
    print(f"Chain Type: {chain.chain_type.value}")
    print(f"Chain: {chain.description}")
    print(f"Frequency Range: {chain.freq_range_ghz[0]:.1f} - {chain.freq_range_ghz[1]:.1f} GHz")

    if chain.is_transmit:
        print(f"Source Power: {chain.source_power_dbm:.1f} dBm")
    print()

    # Display components in order
    print("Component Order:")
    for comp in chain.get_components_ordered():
        print(f"  {comp.order}. {comp.name} ({comp.type.value})")
    print()

    # Analyze chain
    results = analyze_rf_chain(chain)

    # Display mid-frequency results
    print(print_results_summary(results))
    print()
    print(print_gain_breakdown_table(results))
    print()

    # Generate plots
    generate_plots(results, chain)

    print("\nAnalysis complete!")


def generate_plots(results, chain):
    """Generate analysis plots matching MATLAB example."""

    fig, axes = plt.subplots(2, 3, figsize=(14, 9))

    n_comp = results.n_components
    mid_idx = np.argmin(np.abs(results.freq_ghz - results.mid_freq_summary.frequency_ghz))
    colors = plt.cm.tab10(np.linspace(0, 1, n_comp))

    # Plot 1: Individual component gains vs frequency
    ax1 = axes[0, 0]
    for i in range(n_comp):
        ax1.plot(results.freq_ghz, results.component_gains[i, :],
                 '-', linewidth=2, color=colors[i], label=results.component_names[i])
    ax1.axhline(0, color='k', linestyle='--', linewidth=1)
    ax1.set_xlabel('Frequency (GHz)')
    ax1.set_ylabel('Gain (dB)')
    ax1.set_title('Individual Component Gain vs Frequency')
    ax1.legend(loc='best', fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Cascaded total gain vs frequency
    ax2 = axes[0, 1]
    ax2.plot(results.freq_ghz, results.total_gain_db, 'b-', linewidth=2.5)
    ax2.plot(results.mid_freq_summary.frequency_ghz, results.mid_freq_summary.total_gain_db,
             'ro', markersize=10, linewidth=2,
             label=f'Mid-Freq: {results.mid_freq_summary.total_gain_db:.2f} dB')
    ax2.axhline(0, color='k', linestyle='--', linewidth=1)
    ax2.set_xlabel('Frequency (GHz)')
    ax2.set_ylabel('Total Gain (dB)')
    ax2.set_title('Cascaded Total Gain vs Frequency')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    # Plot 3: TX output power OR RX damage threshold OR cascaded NF
    ax3 = axes[0, 2]
    if results.has_power_tracking:
        ax3.plot(results.freq_ghz, results.final_output_power_dbm, 'r-', linewidth=2.5,
                 label='Output Power')
        ax3.axhline(chain.source_power_dbm, color='k', linestyle='--', linewidth=1.5,
                    label='Source Power')
        ax3.set_xlabel('Frequency (GHz)')
        ax3.set_ylabel('Power (dBm)')
        ax3.set_title('Output Power vs Frequency')
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3)
    elif results.has_rx_sweep:
        ax3.plot(results.freq_ghz, results.min_damage_threshold_dbm, 'b-', linewidth=2.5,
                 label='Max Safe Input Power')
        ax3.axhline(results.damage_level_dbm, color='r', linestyle='--', linewidth=2,
                    label=f'Damage Level: {results.damage_level_dbm:.1f} dBm')
        ax3.set_xlabel('Frequency (GHz)')
        ax3.set_ylabel('Input Power (dBm)')
        ax3.set_title('Maximum Safe Input Power vs Frequency')
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3)
    elif results.has_nf_data:
        ax3.plot(results.freq_ghz, results.cascaded_nf_db, 'r-', linewidth=2.5)
        if results.mid_freq_summary.cascaded_nf_db is not None:
            ax3.plot(results.mid_freq_summary.frequency_ghz, results.mid_freq_summary.cascaded_nf_db,
                     'bo', markersize=10, linewidth=2,
                     label=f'Mid-Freq: {results.mid_freq_summary.cascaded_nf_db:.2f} dB')
        ax3.set_xlabel('Frequency (GHz)')
        ax3.set_ylabel('Cascaded NF (dB)')
        ax3.set_title('Cascaded Noise Figure vs Frequency')
        ax3.legend(loc='best')
        ax3.grid(True, alpha=0.3)
    else:
        ax3.text(0.5, 0.5, 'No NF data available', ha='center', va='center',
                 fontsize=14, color='r', transform=ax3.transAxes)
        ax3.axis('off')

    # Plot 4: Cumulative gain through chain at mid-frequency
    ax4 = axes[1, 0]
    cumulative_gain = np.cumsum(results.component_gains[:, mid_idx])
    bars = ax4.bar(range(1, n_comp + 1), cumulative_gain, color=[0.3, 0.6, 0.9])
    ax4.set_xticks(range(1, n_comp + 1))
    ax4.set_xticklabels(results.component_names, rotation=45, ha='right')
    ax4.axhline(0, color='k', linestyle='--', linewidth=1.5)
    ax4.set_ylabel('Cumulative Gain (dB)')
    ax4.set_title(f'Cumulative Gain Through Chain @ {results.mid_freq_summary.frequency_ghz:.2f} GHz')
    ax4.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax4.text(bar.get_x() + bar.get_width()/2., height,
                 f'{cumulative_gain[i]:.1f}',
                 ha='center', va='bottom', fontweight='bold', fontsize=8)

    # Plot 5: Power through each stage (TX or RX sweep)
    ax5 = axes[1, 1]
    if results.has_power_tracking:
        power_after_each = results.power_through_chain_dbm[:, mid_idx]
        ax5.stairs(power_after_each[:-1], range(n_comp + 1), baseline=None,
                   color='b', linewidth=2)
        ax5.plot(range(n_comp + 1), power_after_each, 'ro', markersize=8, linewidth=2)

        # Mark saturated amplifiers
        for i in range(n_comp):
            if results.saturation_flags[i, mid_idx]:
                ax5.plot(i + 1, power_after_each[i + 1], 'rx', markersize=15, linewidth=3)

        labels = ['Source'] + results.component_names
        ax5.set_xticks(range(n_comp + 1))
        ax5.set_xticklabels(labels, rotation=45, ha='right')
        ax5.set_ylabel('Power (dBm)')
        ax5.set_title(f'Power Through Chain @ {results.mid_freq_summary.frequency_ghz:.2f} GHz')
        ax5.grid(True, alpha=0.3)

    elif results.has_rx_sweep:
        power_at_thresh = results.mid_freq_summary.power_through_chain_at_threshold
        n_stages = len(power_at_thresh) - 1

        ax5.stairs(power_at_thresh[:-1], range(n_stages + 1), baseline=None,
                   color='b', linewidth=2, label='Power Level')
        ax5.plot(range(n_stages + 1), power_at_thresh, 'ro', markersize=8,
                 linewidth=2, label='Stage Output')

        # Mark damage at ADC input
        ax5.plot(n_stages, power_at_thresh[-1], 'rx', markersize=15, linewidth=3,
                 label='Damage Point')
        ax5.plot(n_stages, results.damage_level_dbm, 'r^', markersize=10,
                 markerfacecolor='r', label=f'Damage Threshold: {results.damage_level_dbm:.1f} dBm')

        labels = ['Input'] + results.component_names + ['ADC']
        ax5.set_xticks(range(n_stages + 1))
        ax5.set_xticklabels(labels, rotation=45, ha='right')
        ax5.set_ylabel('Power (dBm)')
        ax5.set_title(f'Power Through Chain @ Max Safe Input ({results.mid_freq_summary.frequency_ghz:.2f} GHz)')
        ax5.legend(loc='best', fontsize=8)
        ax5.grid(True, alpha=0.3)
    else:
        ax5.axis('off')

    # Plot 6: Output power in watts (TX) OR max safe input vs frequency (RX)
    ax6 = axes[1, 2]
    if results.has_power_tracking:
        ax6.plot(results.freq_ghz, results.final_output_power_watts, 'r-', linewidth=2.5)
        ax6.set_xlabel('Frequency (GHz)')
        ax6.set_ylabel('Output Power (W)')
        ax6.set_title('Output Power (Watts) vs Frequency')
        ax6.grid(True, alpha=0.3)
    elif results.has_rx_sweep:
        ax6.plot(results.freq_ghz, results.min_damage_threshold_dbm, 'b-', linewidth=2.5,
                 label='Max Safe Input Power')
        ax6.axhline(results.damage_level_dbm, color='r', linestyle='--', linewidth=2,
                    label=f'Damage Level: {results.damage_level_dbm:.1f} dBm')
        ax6.plot(results.mid_freq_summary.frequency_ghz,
                 results.mid_freq_summary.min_safe_input_power_dbm,
                 'ro', markersize=10, linewidth=2,
                 label=f'Mid-Freq: {results.mid_freq_summary.min_safe_input_power_dbm:.1f} dBm')
        ax6.set_xlabel('Frequency (GHz)')
        ax6.set_ylabel('Input Power (dBm)')
        ax6.set_title('Maximum Safe Input Power vs Frequency')
        ax6.legend(loc='best')
        ax6.grid(True, alpha=0.3)
    else:
        ax6.axis('off')

    fig.suptitle(f'RF Chain Analysis: {chain.description}', fontsize=14, fontweight='bold')
    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / "rf_chain_analysis.png"
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {filepath}")

    plt.show()


if __name__ == "__main__":
    main()
