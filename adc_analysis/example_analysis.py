#!/usr/bin/env python3
"""
ADC Analysis Example

Demonstrates RF ADC performance analysis matching MATLAB example_adc_analysis.m.
Compares two ADC models with different noise specification formats.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt
import numpy as np

from adc_analysis import (
    load_adc_specs,
    load_model1_specs,
    load_model2_specs,
    AnalysisConfig,
    analyze_rf_adc,
    print_results_summary,
    compare_adcs,
    print_comparison_table
)


def main():
    """Run ADC analysis example matching MATLAB."""

    print("=" * 70)
    print("RF ADC PERFORMANCE ANALYSIS")
    print("=" * 70)

    # Load ADC specifications for both models
    print("\n[1] Loading ADC Specifications...")

    adc1 = load_model1_specs()
    adc2 = load_model2_specs()

    print(f"\n  {adc1.name}:")
    print(f"    Description: {adc1.description}")
    print(f"    Sample Rate: {adc1.sample_rate_gsps} GSPS")
    print(f"    Noise Units: {adc1.noise_units}")
    print(f"    Number of bands: {adc1.n_bands}")

    print(f"\n  {adc2.name}:")
    print(f"    Description: {adc2.description}")
    print(f"    Sample Rate: {adc2.sample_rate_gsps} GSPS")
    print(f"    Noise Units: {adc2.noise_units}")
    print(f"    Number of bands: {adc2.n_bands}")

    # Configure analysis
    print("\n[2] Configuring Analysis...")

    config = AnalysisConfig(
        rf_input_freq_hz=10e9,   # 10 GHz
        analysis_bw_hz=20e6,     # 20 MHz
        input_impedance_ohm=50   # 50 ohm differential
    )

    print(f"    RF Input Frequency: {config.rf_input_freq_hz/1e9:.1f} GHz")
    print(f"    Analysis Bandwidth: {config.analysis_bw_hz/1e6:.1f} MHz")
    print(f"    Input Impedance: {config.input_impedance_ohm} ohm")

    # Analyze ADC Model 1
    print("\n" + "=" * 70)
    print(f"ANALYSIS: {adc1.name}")
    print("=" * 70)

    results1 = analyze_rf_adc(adc1, config)
    print(print_results_summary(results1))

    # Analyze ADC Model 2
    print("\n" + "=" * 70)
    print(f"ANALYSIS: {adc2.name}")
    print("=" * 70)

    results2 = analyze_rf_adc(adc2, config)
    print(print_results_summary(results2))

    # Compare ADCs
    print("\n" + "=" * 70)
    print("ADC COMPARISON")
    print("=" * 70)

    comparison = compare_adcs([adc1, adc2], config)
    print(print_comparison_table(comparison))

    # Identify winner
    if results1.sensitivity_dbm < results2.sensitivity_dbm:
        print(f"\n  Better Sensitivity: {adc1.name} by {results2.sensitivity_dbm - results1.sensitivity_dbm:.2f} dB")
    else:
        print(f"\n  Better Sensitivity: {adc2.name} by {results1.sensitivity_dbm - results2.sensitivity_dbm:.2f} dB")

    if results1.dynamic_range_db > results2.dynamic_range_db:
        print(f"  Better Dynamic Range: {adc1.name} by {results1.dynamic_range_db - results2.dynamic_range_db:.2f} dB")
    else:
        print(f"  Better Dynamic Range: {adc2.name} by {results2.dynamic_range_db - results1.dynamic_range_db:.2f} dB")

    # Multi-frequency analysis
    print("\n" + "=" * 70)
    print("FREQUENCY SWEEP ANALYSIS")
    print("=" * 70)

    test_freqs_ghz = [5.0, 10.0, 15.0, 25.0, 35.0]

    print(f"\n{'Frequency':<12} {'ADC1 NF(dBm)':<15} {'ADC1 DR(dB)':<12} {'ADC2 NF(dBm)':<15} {'ADC2 DR(dB)':<12}")
    print("-" * 70)

    for freq in test_freqs_ghz:
        config_f = AnalysisConfig(rf_input_freq_hz=freq * 1e9, analysis_bw_hz=20e6)
        try:
            r1 = analyze_rf_adc(adc1, config_f)
            r2 = analyze_rf_adc(adc2, config_f)
            print(f"{freq:<12.1f} {r1.noise_floor_dbm:<15.2f} {r1.dynamic_range_db:<12.2f} "
                  f"{r2.noise_floor_dbm:<15.2f} {r2.dynamic_range_db:<12.2f}")
        except ValueError as e:
            print(f"{freq:<12.1f} {'N/A':<15} {'N/A':<12} {'N/A':<15} {'N/A':<12}")

    # Generate plots
    print("\n" + "=" * 70)
    print("GENERATING PLOTS")
    print("=" * 70)

    generate_plots(adc1, adc2, config)

    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)


def generate_plots(adc1, adc2, config):
    """Generate comparison plots."""

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Plot 1: Band specifications comparison
    ax1 = axes[0, 0]
    x = np.arange(min(adc1.n_bands, adc2.n_bands))
    width = 0.35

    bars1 = ax1.bar(x - width/2, adc1.sfdr_db[:len(x)], width, label=adc1.name, color='steelblue')
    bars2 = ax1.bar(x + width/2, adc2.sfdr_db[:len(x)], width, label=adc2.name, color='coral')

    ax1.set_xlabel('Band')
    ax1.set_ylabel('SFDR (dB)')
    ax1.set_title('SFDR by Frequency Band')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"Band {i+1}" for i in range(len(x))])
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Noise density comparison
    ax2 = axes[0, 1]
    bars1 = ax2.bar(x - width/2, adc1.noise_density[:len(x)], width, label=f"{adc1.name} ({adc1.noise_units})", color='steelblue')
    bars2 = ax2.bar(x + width/2, adc2.noise_density[:len(x)], width, label=f"{adc2.name} ({adc2.noise_units})", color='coral')

    ax2.set_xlabel('Band')
    ax2.set_ylabel('Noise Density (dB/Hz)')
    ax2.set_title('Noise Density by Frequency Band')
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"Band {i+1}" for i in range(len(x))])
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Dynamic range breakdown
    ax3 = axes[1, 0]
    results1 = analyze_rf_adc(adc1, config)
    results2 = analyze_rf_adc(adc2, config)

    categories = ['Noise-Limited\nDR', 'SFDR-Limited\nDR', 'Effective\nDR']
    values1 = [results1.noise_limited_dr_db, results1.sfdr_limited_dr_db, results1.dynamic_range_db]
    values2 = [results2.noise_limited_dr_db, results2.sfdr_limited_dr_db, results2.dynamic_range_db]

    x_cat = np.arange(len(categories))
    bars1 = ax3.bar(x_cat - width/2, values1, width, label=adc1.name, color='steelblue')
    bars2 = ax3.bar(x_cat + width/2, values2, width, label=adc2.name, color='coral')

    ax3.set_xlabel('Metric')
    ax3.set_ylabel('Dynamic Range (dB)')
    ax3.set_title(f'Dynamic Range @ {config.rf_input_freq_hz/1e9:.0f} GHz')
    ax3.set_xticks(x_cat)
    ax3.set_xticklabels(categories)
    ax3.legend()
    ax3.grid(True, alpha=0.3, axis='y')

    # Plot 4: Key metrics comparison
    ax4 = axes[1, 1]
    metrics = ['Sensitivity\n(dBm)', 'Noise Floor\n(dBm)', 'Equiv. NF\n(dB)']
    values1 = [results1.sensitivity_dbm, results1.noise_floor_dbm, results1.equivalent_noise_figure_db]
    values2 = [results2.sensitivity_dbm, results2.noise_floor_dbm, results2.equivalent_noise_figure_db]

    x_met = np.arange(len(metrics))
    bars1 = ax4.bar(x_met - width/2, values1, width, label=adc1.name, color='steelblue')
    bars2 = ax4.bar(x_met + width/2, values2, width, label=adc2.name, color='coral')

    ax4.set_xlabel('Metric')
    ax4.set_ylabel('Value')
    ax4.set_title(f'Key Metrics @ {config.rf_input_freq_hz/1e9:.0f} GHz')
    ax4.set_xticks(x_met)
    ax4.set_xticklabels(metrics)
    ax4.legend()
    ax4.grid(True, alpha=0.3, axis='y')

    fig.suptitle('ADC Comparison Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()

    # Save plot
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / "adc_comparison.png"
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"\nPlot saved to: {filepath}")

    try:
        plt.show()
    except Exception:
        print("(Non-GUI environment - plot saved but not displayed)")


if __name__ == "__main__":
    main()
