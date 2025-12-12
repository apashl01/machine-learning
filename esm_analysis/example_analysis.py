#!/usr/bin/env python3
"""
ESM Detection Analysis - Example Script

Demonstrates the complete ESM analysis workflow:
1. Load configuration files
2. Perform sidelobe detection analysis
3. Categorize threats
4. Generate dwell schedules
5. Produce reports and visualizations

Author: Andrew's Analysis Tools
Date: December 2024
"""

import sys
from pathlib import Path

# Add package to path if running directly
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from esm_analysis.config import load_config, SystemConfig, ThreatLibrary
from esm_analysis.core import SNRCalculator, ThreatCategorizer, DetectionModel
from esm_analysis.scheduling import DwellScheduler
from esm_analysis.visualization import ESMPlotter
from esm_analysis.esm_detection import calculate_dynamic_detection_requirement
from system_config import load_system_config


def print_header(text: str):
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f" {text}")
    print(f"{'='*70}\n")


def run_full_analysis(
    system_config: SystemConfig,
    threat_library: ThreatLibrary,
    threat_set: str = None,
    generate_plots: bool = True
):
    """
    Run complete ESM detection analysis.

    Args:
        system_config: System configuration
        threat_library: Threat library
        threat_set: Name of threat set to analyze (or None for all)
        generate_plots: Whether to generate visualization plots
    """

    # =========================================================================
    # STEP 1: SELECT THREATS TO ANALYZE
    # =========================================================================
    print_header("STEP 1: THREAT SELECTION")

    if threat_set:
        threats = threat_library.get_threat_set(threat_set)
        print(f"Using threat set: {threat_set}")
    else:
        threats = list(threat_library)
        print("Analyzing all threats in library")

    print(f"Number of threats: {len(threats)}")

    # Task 10: Calculate dynamic detection range requirements
    # Load platform RCS from system_config
    try:
        sys_config = load_system_config()
        platform_rcs = sys_config.platform.rcs_m2 if sys_config.platform else 2.0
        print(f"\nCalculating dynamic detection range requirements (platform RCS: {platform_rcs} m²)...")
        print(f"{'Threat':<30} {'Radar Range':>14} {'Required Range':>16} {'Multiplier':>12}")
        print("-" * 80)

        for threat in threats:
            # Convert threat to RadarParameters for the calculation
            from esm_analysis.esm_detection import RadarParameters
            # Estimate radar bandwidth from pulse width: BW ≈ 1 / PW
            bandwidth_mhz = 1.0 / threat.pulse_width_us  # MHz
            # Calculate EIRP: Power (dBW) + Antenna Gain (dBi)
            import numpy as np
            power_dbw = 10 * np.log10(threat.peak_power_w)
            eirp_dbw = power_dbw + threat.antenna_gain_dbi
            radar_params = RadarParameters(
                eirp_dBW=eirp_dbw,
                freq_GHz=threat.frequency_hz / 1e9,
                antenna_gain_dB=threat.antenna_gain_dbi,
                bandwidth_MHz=bandwidth_mhz,
                pulse_width_us=threat.pulse_width_us,
                pri_us=threat.pri_us
            )

            # Calculate dynamic requirement (1.2x threat radar's range)
            dynamic_range_m = calculate_dynamic_detection_requirement(
                radar_params,
                platform_rcs_m2=platform_rcs,
                range_multiplier=1.2
            )

            # Update threat's required range if not already set
            radar_range_m = dynamic_range_m / 1.2  # Back-calculate radar's range
            if threat.required_detection_range_m is None:
                threat.required_detection_range_m = dynamic_range_m

            print(f"  {threat.name:<28} {radar_range_m/1000:>10.1f} km {dynamic_range_m/1000:>12.1f} km {'1.2x':>12}")

    except ImportError:
        print("\nNote: Could not load system config - using default detection ranges")

    print(f"\nThreat summary:")
    for threat in threats:
        print(f"  - {threat.name} ({threat.category}): "
              f"{threat.frequency_hz/1e9:.1f} GHz, "
              f"{threat.peak_power_w/1000:.0f} kW")

    # =========================================================================
    # STEP 2: SIDELOBE DETECTION ANALYSIS
    # =========================================================================
    print_header("STEP 2: SIDELOBE DETECTION ANALYSIS")

    snr_calculator = SNRCalculator(system_config, verbose=False)

    print("Analyzing SNR for each threat at required detection range...\n")
    print(f"{'Threat':<30} {'Range':>10} {'Main Beam':>12} {'Sidelobe':>12} {'Back Lobe':>12}")
    print("-" * 80)

    for threat in threats:
        range_m = threat.required_detection_range_m or \
                  system_config.analysis.required_detection_range_m

        result = snr_calculator.calculate_multi_beam_snr(threat, range_m)

        print(f"{threat.name:<30} {range_m/1000:>8.0f} km "
              f"{result.main_beam_snr.snr_db:>+10.1f} dB "
              f"{result.sidelobe_snr.snr_db:>+10.1f} dB "
              f"{result.back_lobe_snr.snr_db:>+10.1f} dB")

    threshold = system_config.receiver.snr_threshold_db
    print(f"\nDetection threshold: {threshold:.1f} dB")

    # =========================================================================
    # STEP 3: THREAT CATEGORIZATION
    # =========================================================================
    print_header("STEP 3: THREAT CATEGORIZATION")

    categorizer = ThreatCategorizer(system_config, snr_calculator, verbose=False)
    categorization_summary = categorizer.categorize_threats(threats)

    # Collect categorized threats for later use
    categorized_threats = (
        categorization_summary.sidelobe_detectable +
        categorization_summary.main_beam_required +
        categorization_summary.undetectable
    )

    print("SIDELOBE DETECTABLE (low duty cycle monitoring):")
    if categorization_summary.sidelobe_detectable:
        for ct in categorization_summary.sidelobe_detectable:
            print(f"  ✓ {ct.threat.name}: Sidelobe SNR = {ct.sidelobe_snr_db:+.1f} dB "
                  f"(margin: {ct.sidelobe_margin_db:+.1f} dB)")
    else:
        print("  (none)")

    print("\nMAIN BEAM REQUIRED (scan scheduling needed):")
    if categorization_summary.main_beam_required:
        for ct in categorization_summary.main_beam_required:
            print(f"  ⚠ {ct.threat.name}: Main beam SNR = {ct.main_beam_snr_db:+.1f} dB, "
                  f"Sidelobe = {ct.sidelobe_snr_db:+.1f} dB")
    else:
        print("  (none)")

    print("\nUNDETECTABLE at required range:")
    if categorization_summary.undetectable:
        for ct in categorization_summary.undetectable:
            print(f"  ✗ {ct.threat.name}: Best SNR = {ct.main_beam_snr_db:+.1f} dB "
                  f"(need {abs(ct.main_beam_margin_db):.1f} dB more)")
    else:
        print("  (none)")

    # =========================================================================
    # STEP 4: DWELL SCHEDULING
    # =========================================================================
    print_header("STEP 4: DWELL SCHEDULING")

    scheduler = DwellScheduler(system_config, verbose=False)
    scheduling_summary = scheduler.schedule_all_threats(categorized_threats)

    print("SCHEDULING PARAMETERS:\n")

    for schedule in scheduling_summary.sidelobe_threats:
        print(f"  {schedule.threat_name} (SIDELOBE):")
        print(f"    Check interval: {schedule.revisit_interval_s:.0f} s")
        print(f"    Dwell time: {schedule.dwell_time_us:.1f} µs")
        print(f"    Duty cycle: {schedule.duty_cycle_percent:.6f}%")
        print()

    for schedule in scheduling_summary.main_beam_threats:
        print(f"  {schedule.threat_name} (MAIN BEAM):")
        print(f"    Scan positions: {schedule.n_scan_positions}")
        print(f"    Revisit interval: {schedule.revisit_interval_s*1000:.1f} ms")
        print(f"    Dwell time: {schedule.dwell_time_us:.1f} µs (> {schedule.pri_us:.1f} µs PRI)")
        print(f"    Duty cycle: {schedule.duty_cycle_percent:.4f}%")
        print()

    # =========================================================================
    # STEP 5: RESULTS SUMMARY
    # =========================================================================
    print_header("STEP 5: RESULTS SUMMARY")

    print("DUTY CYCLE ANALYSIS:")
    print(f"  Sidelobe threats:   {scheduling_summary.sidelobe_duty_cycle_percent:.6f}%")
    print(f"  Main beam threats:  {scheduling_summary.main_beam_duty_cycle_percent:.4f}%")
    print(f"  TOTAL:              {scheduling_summary.total_duty_cycle_percent:.4f}%")
    print()
    print("COMPARISON:")
    print(f"  Naive approach (all main beam): {scheduling_summary.naive_duty_cycle_percent:.4f}%")
    print(f"  Optimized approach:             {scheduling_summary.total_duty_cycle_percent:.4f}%")
    print(f"  SAVINGS:                        {scheduling_summary.duty_cycle_savings_percent:.1f}%")
    print()

    print("DETECTION GUARANTEE:")
    print(f"  All scheduled threats have Pi = 100% (deterministic detection)")
    print(f"  Binary detection model: SNR ≥ {threshold:.0f} dB → Pd ≈ 99.99%")

    # =========================================================================
    # STEP 6: GENERATE PLOTS (optional)
    # =========================================================================
    if generate_plots:
        print_header("STEP 6: GENERATING PLOTS")

        try:
            plotter = ESMPlotter(system_config, save_plots=True)

            # Generate SNR vs range for first threat
            if threats:
                print("Generating SNR vs range plot...")
                plotter.plot_snr_vs_range(threats[0])

            # Generate categorization summary
            print("Generating categorization summary plot...")
            plotter.plot_categorization_summary(categorization_summary)

            # Generate duty cycle comparison
            print("Generating duty cycle comparison plot...")
            plotter.plot_duty_cycle_comparison(scheduling_summary)

            # Generate detection ranges plot
            print("Generating detection ranges plot...")
            plotter.plot_detection_ranges(categorized_threats)

            print(f"\nPlots saved to: {plotter.output_dir}")

        except ImportError as e:
            print(f"Plotting skipped (matplotlib not available): {e}")
        except Exception as e:
            print(f"Plotting error: {e}")

    print_header("ANALYSIS COMPLETE")

    return {
        'categorized_threats': categorized_threats,
        'categorization_summary': categorization_summary,
        'scheduling_summary': scheduling_summary
    }


def main():
    """Main entry point."""
    print_header("ESM DETECTION ANALYSIS")

    # Load configuration
    print("Loading configuration files...")
    try:
        system_config, threat_library = load_config()
        print(f"  System: {system_config.name}")
        print(f"  Threats loaded: {len(threat_library)}")
    except FileNotFoundError as e:
        print(f"Error loading configuration: {e}")
        print("Make sure you're running from the esm_analysis directory")
        return 1

    # Display system parameters
    print(f"\nSystem Parameters:")
    print(f"  Frequency range: {system_config.receiver.freq_min_hz/1e9:.1f} - "
          f"{system_config.receiver.freq_max_hz/1e9:.1f} GHz")
    print(f"  Receiver NF: {system_config.receiver.noise_figure_db:.1f} dB")
    print(f"  Bandwidth: {system_config.receiver.bandwidth_hz/1e6:.1f} MHz")
    print(f"  SNR threshold: {system_config.receiver.snr_threshold_db:.1f} dB")
    print(f"  Default detection range: "
          f"{system_config.analysis.required_detection_range_m/1000:.0f} km")

    # Run analysis
    results = run_full_analysis(
        system_config,
        threat_library,
        threat_set=None,  # Analyze all threats
        generate_plots=system_config.analysis.generate_plots
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
