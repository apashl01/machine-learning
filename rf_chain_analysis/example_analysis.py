#!/usr/bin/env python3
"""
RF Chain Analysis Example

Demonstrates complete RF chain cascade analysis including:
- Cascaded gain and noise figure calculations
- Sensitivity and dynamic range analysis
- Component-by-component breakdown
- Multi-chain comparison
- Frequency response analysis
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt

from rf_chain_analysis import load_rf_chain_config, RFChainAnalyzer
from rf_chain_analysis.core.analyzer import compare_chains, calculate_noise_temperature
from rf_chain_analysis.visualization import (
    plot_cascade_breakdown,
    plot_frequency_response,
    plot_power_tracking,
    plot_chain_comparison,
    plot_dynamic_range
)


def main():
    """Run RF chain analysis example."""

    print("=" * 70)
    print("RF CHAIN CASCADE ANALYSIS")
    print("=" * 70)

    # Load configuration
    print("\n[1] Loading RF Chain Configuration...")
    config = load_rf_chain_config()

    print(f"    Component Library: {len(config.component_library)} components")
    for comp_id in config.component_library.list_components():
        comp = config.component_library.get(comp_id)
        print(f"      - {comp}")

    print(f"\n    Chains defined: {len(config.chains)}")
    for chain_id in config.list_chains():
        chain = config.get_chain(chain_id)
        print(f"      - {chain.name} ({chain.chain_type.value})")

    # Create analyzer
    print("\n[2] Creating Analyzer...")
    analyzer = RFChainAnalyzer(config.analysis)
    print(f"    Bandwidth: {config.analysis.bandwidth_hz/1e6:.1f} MHz")
    print(f"    SNR Required: {config.analysis.snr_required_db:.1f} dB")
    print(f"    Temperature: {config.analysis.temperature_k:.1f} K")

    # Analyze receive chains
    print("\n" + "=" * 70)
    print("RECEIVE CHAIN ANALYSIS")
    print("=" * 70)

    rx_chains = config.get_receive_chains()
    analysis_freq = 10.0  # GHz - mid-band analysis

    for chain in rx_chains:
        print(f"\n--- {chain.name} ---")
        print(f"    Description: {chain.description}")
        print(f"    Frequency Range: {chain.freq_range_ghz[0]}-{chain.freq_range_ghz[1]} GHz")

        # Cascade analysis
        result = analyzer.analyze_cascade(chain, analysis_freq)

        # Print summary
        print(analyzer.print_cascade_summary(result))

        # Calculate noise temperature
        noise_temp = calculate_noise_temperature(result.total_nf_db)
        print(f"    Equivalent Noise Temperature: {noise_temp:.1f} K")

    # Compare receive chains
    if len(rx_chains) >= 2:
        print("\n" + "=" * 70)
        print("RECEIVE CHAIN COMPARISON")
        print("=" * 70)

        comparison = compare_chains(analyzer, rx_chains, analysis_freq)

        print(f"\n{'Chain':<25} {'Gain(dB)':>10} {'NF(dB)':>10} {'Sens(dBm)':>12} {'DR(dB)':>10}")
        print("-" * 70)

        for chain_id, result in comparison.items():
            print(f"{chain_id:<25} {result.total_gain_db:>10.2f} "
                  f"{result.total_nf_db:>10.2f} {result.sensitivity_dbm:>12.2f} "
                  f"{result.dynamic_range_db:>10.2f}")

        # Identify best chain
        best_sens = min(comparison.items(), key=lambda x: x[1].sensitivity_dbm)
        best_dr = max(comparison.items(), key=lambda x: x[1].dynamic_range_db)
        lowest_nf = min(comparison.items(), key=lambda x: x[1].total_nf_db)

        print(f"\n    Best Sensitivity: {best_sens[0]} ({best_sens[1].sensitivity_dbm:.2f} dBm)")
        print(f"    Best Dynamic Range: {best_dr[0]} ({best_dr[1].dynamic_range_db:.2f} dB)")
        print(f"    Lowest Noise Figure: {lowest_nf[0]} ({lowest_nf[1].total_nf_db:.2f} dB)")

    # Analyze transmit chains
    tx_chains = config.get_transmit_chains()
    if tx_chains:
        print("\n" + "=" * 70)
        print("TRANSMIT CHAIN ANALYSIS")
        print("=" * 70)

        for chain in tx_chains:
            print(f"\n--- {chain.name} ---")
            print(f"    Source Power: {chain.source_power_dbm:.1f} dBm")

            tx_result = analyzer.analyze_tx_chain(chain, analysis_freq)

            print(f"    Total Gain: {tx_result['total_gain_db']:.2f} dB")
            print(f"    Output Power: {tx_result['output_power_dbm']:.2f} dBm")

            if tx_result['any_compression']:
                print("    WARNING: Compression detected in chain!")
                for p in tx_result['power_points']:
                    if p.is_compressed:
                        print(f"      - {p.component_name}: {p.compression_db:.1f} dB compression")

    # Power tracking example
    print("\n" + "=" * 70)
    print("POWER TRACKING EXAMPLE")
    print("=" * 70)

    if rx_chains:
        test_chain = rx_chains[0]
        test_powers = [-60, -40, -20, 0]  # dBm

        print(f"\nTracking power through {test_chain.name}:")

        for pin in test_powers:
            power_points = analyzer.track_power(test_chain, analysis_freq, pin)

            output_power = power_points[-1].output_power_dbm if power_points else pin
            compressed = any(p.is_compressed for p in power_points)

            status = "COMPRESSED" if compressed else "Linear"
            print(f"    Input: {pin:>6.1f} dBm -> Output: {output_power:>7.1f} dBm [{status}]")

    # Frequency response
    print("\n" + "=" * 70)
    print("FREQUENCY RESPONSE ANALYSIS")
    print("=" * 70)

    if rx_chains:
        test_chain = rx_chains[0]
        freq_analysis = analyzer.analyze_frequency_range(test_chain)

        print(f"\n{test_chain.name} across {test_chain.freq_range_ghz[0]}-{test_chain.freq_range_ghz[1]} GHz:")
        print(f"    Gain Range: {freq_analysis.gains_db.min():.2f} to {freq_analysis.gains_db.max():.2f} dB")
        print(f"    NF Range: {freq_analysis.noise_figures_db.min():.2f} to {freq_analysis.noise_figures_db.max():.2f} dB")
        print(f"    Sensitivity Range: {freq_analysis.sensitivities_dbm.max():.2f} to {freq_analysis.sensitivities_dbm.min():.2f} dBm")

    # Generate plots
    print("\n" + "=" * 70)
    print("GENERATING PLOTS")
    print("=" * 70)

    try:
        figures = []

        # Cascade breakdown for first RX chain
        if rx_chains:
            result = analyzer.analyze_cascade(rx_chains[0], analysis_freq)
            fig1 = plot_cascade_breakdown(result, f"{rx_chains[0].name} Cascade")
            figures.append(("cascade_breakdown", fig1))
            print("    [+] Cascade breakdown plot")

            # Frequency response
            freq_analysis = analyzer.analyze_frequency_range(rx_chains[0])
            fig2 = plot_frequency_response(freq_analysis, rx_chains[0].name)
            figures.append(("frequency_response", fig2))
            print("    [+] Frequency response plot")

            # Power tracking
            power_points = analyzer.track_power(rx_chains[0], analysis_freq, -30)
            fig3 = plot_power_tracking(power_points, -30, rx_chains[0].name)
            figures.append(("power_tracking", fig3))
            print("    [+] Power tracking plot")

            # Dynamic range visualization
            fig4 = plot_dynamic_range(result, rx_chains[0].name)
            figures.append(("dynamic_range", fig4))
            print("    [+] Dynamic range plot")

        # Chain comparison
        if len(rx_chains) >= 2:
            comparison = compare_chains(analyzer, rx_chains, analysis_freq)
            fig5 = plot_chain_comparison(comparison, analysis_freq)
            figures.append(("chain_comparison", fig5))
            print("    [+] Chain comparison plot")

        # Save plots
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)

        for name, fig in figures:
            filepath = output_dir / f"rf_chain_{name}.png"
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"    Saved: {filepath}")

        plt.show()

    except Exception as e:
        print(f"    Plot generation error: {e}")
        print("    (Plots may not display in non-GUI environment)")

    # Summary
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)
    print("\nKey findings:")

    if rx_chains:
        best_chain = min(rx_chains,
                         key=lambda c: analyzer.analyze_cascade(c, analysis_freq).total_nf_db)
        best_result = analyzer.analyze_cascade(best_chain, analysis_freq)
        print(f"  - Best RX chain: {best_chain.name}")
        print(f"    - System NF: {best_result.total_nf_db:.2f} dB")
        print(f"    - Sensitivity: {best_result.sensitivity_dbm:.2f} dBm")
        print(f"    - Dynamic Range: {best_result.dynamic_range_db:.2f} dB")


if __name__ == "__main__":
    main()
