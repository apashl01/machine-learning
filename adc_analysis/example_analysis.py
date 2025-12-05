#!/usr/bin/env python3
"""
ADC Analysis Example

Demonstrates complete ADC performance analysis including:
- Measurement accuracy (amplitude, timing, frequency, phase)
- Receiver sensitivity with LNA optimization
- Saturation and damage threshold analysis
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib.pyplot as plt

from adc_analysis import (
    load_adc_config,
    MeasurementAnalyzer,
    SensitivityAnalyzer,
    SaturationAnalyzer
)
from adc_analysis.visualization import (
    plot_measurement_summary,
    plot_snr_vs_input,
    plot_sensitivity_comparison,
    plot_lna_heatmap,
    plot_saturation_analysis,
    plot_safe_operating_zones
)


def main():
    """Run ADC analysis example."""

    print("=" * 70)
    print("ADC PERFORMANCE ANALYSIS")
    print("=" * 70)

    # Load configuration
    print("\n[1] Loading ADC Configuration...")
    config = load_adc_config()

    print(f"\n    ADC Specifications:")
    print(f"      Bits: {config.adc.bits}")
    print(f"      ENOB: {config.adc.enob}")
    print(f"      Sample Rate: {config.adc.sample_rate_gsps} GSPS")
    print(f"      Full Scale: {config.adc.fullscale_dbm} dBm")
    print(f"      NSD: {config.adc.nsd_dbm_hz:.1f} dBm/Hz")
    print(f"      SFDR: {config.adc.sfdr_dbc} dBc")

    print(f"\n    Passive Losses:")
    print(f"      Cable: {config.passive.cable_loss_db} dB")
    print(f"      Coupler: {config.passive.coupler_loss_db} dB")
    print(f"      Switch: {config.passive.switch_loss_db} dB")
    print(f"      Filter: {config.passive.filter_loss_db} dB")
    print(f"      Total: {config.passive.total_loss_db} dB")

    # =========================================================================
    # MEASUREMENT ACCURACY ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("MEASUREMENT ACCURACY ANALYSIS")
    print("=" * 70)

    measurement_analyzer = MeasurementAnalyzer(config)
    measurement_result = measurement_analyzer.analyze()

    print(measurement_analyzer.print_summary(measurement_result))

    # =========================================================================
    # SENSITIVITY ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("RECEIVER SENSITIVITY ANALYSIS")
    print("=" * 70)

    sensitivity_analyzer = SensitivityAnalyzer(config)
    sensitivity_result = sensitivity_analyzer.analyze()

    print(sensitivity_analyzer.print_summary(sensitivity_result))

    # =========================================================================
    # SATURATION ANALYSIS
    # =========================================================================
    print("\n" + "=" * 70)
    print("SATURATION AND DAMAGE ANALYSIS")
    print("=" * 70)

    saturation_analyzer = SaturationAnalyzer(config, lna_gain_db=30.0)
    saturation_result = saturation_analyzer.analyze(attenuator_distance_miles=1.0)

    print(saturation_analyzer.print_summary(saturation_result))

    # =========================================================================
    # GENERATE PLOTS
    # =========================================================================
    print("\n" + "=" * 70)
    print("GENERATING PLOTS")
    print("=" * 70)

    try:
        figures = []

        # Measurement summary
        fig1 = plot_measurement_summary(measurement_result)
        figures.append(("measurement_summary", fig1))
        print("    [+] Measurement summary plot")

        # SNR vs input
        fig2 = plot_snr_vs_input(
            config.adc.fullscale_dbm,
            config.adc.enob,
            config.analysis.input_signal_dbm
        )
        figures.append(("snr_vs_input", fig2))
        print("    [+] SNR vs input plot")

        # Sensitivity comparison
        fig3 = plot_sensitivity_comparison(sensitivity_result)
        figures.append(("sensitivity_comparison", fig3))
        print("    [+] Sensitivity comparison plot")

        # LNA heatmap
        fig4 = plot_lna_heatmap(sensitivity_result)
        figures.append(("lna_heatmap", fig4))
        print("    [+] LNA optimization heatmap")

        # Saturation analysis
        fig5 = plot_saturation_analysis(saturation_result)
        figures.append(("saturation_analysis", fig5))
        print("    [+] Saturation analysis plot")

        # Safe operating zones
        fig6 = plot_safe_operating_zones(saturation_result)
        figures.append(("safe_zones", fig6))
        print("    [+] Safe operating zones plot")

        # Save plots
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)

        for name, fig in figures:
            filepath = output_dir / f"adc_{name}.png"
            fig.savefig(filepath, dpi=150, bbox_inches='tight')
            print(f"    Saved: {filepath}")

        plt.show()

    except Exception as e:
        print(f"    Plot generation error: {e}")
        print("    (Plots may not display in non-GUI environment)")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("ANALYSIS COMPLETE")
    print("=" * 70)

    print("\nKey Findings:")
    print(f"\n  MEASUREMENT ACCURACY:")
    print(f"    - TOA: {measurement_result.timing.toa_accuracy_ns:.2f} ns")
    print(f"    - Frequency (IFM): {measurement_result.frequency.ifm_accuracy_hz:.0f} Hz")
    print(f"    - Phase: {measurement_result.phase.phase_accuracy_deg:.2f} deg")
    print(f"    - AOA: {measurement_result.phase.aoa_accuracy_deg:.2f} deg")

    print(f"\n  SENSITIVITY:")
    print(f"    - Passive-only MDS: {sensitivity_result.passive.mds_dbm:.2f} dBm")
    print(f"    - Optimal LNA: Gain={sensitivity_result.optimal_lna.gain_db:.0f}dB, "
          f"NF={sensitivity_result.optimal_lna.nf_db:.1f}dB")
    print(f"    - Best MDS: {sensitivity_result.optimal_lna.mds_dbm:.2f} dBm")
    print(f"    - Improvement: {sensitivity_result.optimal_lna.improvement_db:.2f} dB")

    print(f"\n  SATURATION:")
    # Find highest EIRP that's still safe
    safe_eirps = [cd for cd in saturation_result.critical_distances
                  if cd.status == 'SAFE']
    if safe_eirps:
        max_safe = max(cd.eirp_dbm for cd in safe_eirps)
        print(f"    - Safe for EIRP up to: {max_safe:.0f} dBm (at all distances)")

    if saturation_result.attenuator_recommendation.is_needed:
        print(f"    - High-power operation requires: "
              f"{saturation_result.attenuator_recommendation.required_attenuation_db:.0f} dB attenuator")


if __name__ == "__main__":
    main()
