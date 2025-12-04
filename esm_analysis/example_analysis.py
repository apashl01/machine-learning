#!/usr/bin/env python3
"""
ESM Detection Analysis - Example Script

This script demonstrates the ESM detection analysis capabilities,
matching the functionality of the MATLAB radar_range_analysis.m
with additional scan position dwell scheduling features.

Run this script to generate analysis plots and console output.
"""

import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Import from the esm_analysis package
from esm_detection import (
    RadarParameters, ReceiverParameters, ESMDetector,
    compare_to_radar_range, monte_carlo_analysis
)
from dwell_scheduler import (
    DwellScheduler, EmitterModel, generate_threat_set
)
from visualization import (
    plot_detection_range_comparison,
    plot_sensitivity_sweep,
    plot_monte_carlo_results,
    plot_dwell_schedule,
    plot_schedule_evaluation,
    plot_range_vs_frequency,
)


def main():
    """Run complete ESM detection analysis."""

    print("=" * 60)
    print("ESM DETECTION ANALYSIS")
    print("Ported from MATLAB radar_range_analysis.m")
    print("=" * 60)
    print()

    # =========================================================================
    # PART 1: BASIC ESM DETECTION ANALYSIS
    # =========================================================================

    print("=== PART 1: BASIC ESM DETECTION ===\n")

    # Define ESM receiver parameters
    receiver = ReceiverParameters(
        antenna_gain_dB=0.0,        # Omni-directional
        noise_figure_dB=5.0,        # Conservative NF
        bandwidth_MHz=20.0,         # Analysis bandwidth
        snr_required_dB=13.0,       # Required SNR for detection
        system_loss_dB=6.0,         # Total system losses
        freq_min_GHz=2.0,           # Scan range start
        freq_max_GHz=18.0,          # Scan range end
    )

    print("RECEIVER PARAMETERS:")
    print(f"  Antenna Gain: {receiver.antenna_gain_dB:.1f} dB")
    print(f"  Noise Figure: {receiver.noise_figure_dB:.1f} dB")
    print(f"  Bandwidth: {receiver.bandwidth_MHz:.1f} MHz")
    print(f"  Required SNR: {receiver.snr_required_dB:.1f} dB")
    print(f"  System Loss: {receiver.system_loss_dB:.1f} dB")
    print(f"  Noise Floor: {receiver.noise_floor_dBm:.1f} dBm")
    print(f"  Sensitivity: {receiver.sensitivity_dBm:.1f} dBm")
    print()

    # Define multiple radar emitters (threats)
    radars = [
        ("Fighter Radar", RadarParameters(eirp_dBW=50, freq_GHz=10, antenna_gain_dB=35)),
        ("Air Defense Radar", RadarParameters(eirp_dBW=70, freq_GHz=3, antenna_gain_dB=40)),
        ("SAM Radar", RadarParameters(eirp_dBW=60, freq_GHz=6, antenna_gain_dB=30)),
        ("AESA Fighter", RadarParameters(eirp_dBW=55, freq_GHz=10, antenna_gain_dB=35)),
        ("Naval Radar", RadarParameters(eirp_dBW=80, freq_GHz=3, antenna_gain_dB=45)),
    ]

    # Create detector
    detector = ESMDetector(receiver)

    # Analyze each radar
    print("DETECTION RANGES:")
    print("-" * 60)
    print(f"{'Radar Type':<25} {'EIRP (dBW)':<12} {'Det. Range (km)':<15}")
    print("-" * 60)

    comparison_results = []
    for name, radar in radars:
        detection_range = detector.calculate_detection_range(radar)
        comparison = compare_to_radar_range(radar, receiver, target_rcs_m2=5.0)
        comparison_results.append(comparison)

        print(f"{name:<25} {radar.eirp_dBW:<12.1f} {detection_range:<15.1f}")

    print("-" * 60)
    print()

    # =========================================================================
    # PART 2: COMPARISON WITH RADAR DETECTION
    # =========================================================================

    print("=== PART 2: ESM vs RADAR COMPARISON ===\n")

    print("Comparing ESM detection range to radar detection range")
    print("(R² vs R⁴ advantage)\n")

    print(f"{'Radar Type':<25} {'Radar Range':<15} {'ESM Range':<15} {'Multiplier':<12}")
    print("-" * 70)

    for (name, radar), comp in zip(radars, comparison_results):
        print(f"{name:<25} {comp['radar_detection_range_km']:<15.1f} "
              f"{comp['esm_detection_range_km']:<15.1f} {comp['range_multiplier']:<12.1f}x")

    print("-" * 70)
    print("\nKey Insight: ESM uses one-way propagation (R²) giving significant")
    print("advantage over radar's two-way propagation (R⁴)")
    print()

    # =========================================================================
    # PART 3: SCAN POSITION DWELL SCHEDULING
    # =========================================================================

    print("=== PART 3: DWELL SCHEDULING ANALYSIS ===\n")

    # Create dwell scheduler
    scheduler = DwellScheduler(
        receiver=receiver,
        freq_min_GHz=2.0,
        freq_max_GHz=18.0,
        channel_bandwidth_MHz=20.0,
    )

    print(f"Scheduler Configuration:")
    print(f"  Frequency Range: {scheduler.freq_min_GHz} - {scheduler.freq_max_GHz} GHz")
    print(f"  Channel Bandwidth: {scheduler.channel_bandwidth_MHz} MHz")
    print(f"  Number of Scan Positions: {scheduler.n_positions}")
    print()

    # Generate threat emitters for scheduling
    threats = [
        EmitterModel(
            radar=RadarParameters(eirp_dBW=60, freq_GHz=3.5, pri_us=1000, scan_period_s=10),
            antenna_scan_type="rotating",
            antenna_beamwidth_deg=3.0,
        ),
        EmitterModel(
            radar=RadarParameters(eirp_dBW=55, freq_GHz=10.0, pri_us=500, scan_period_s=5),
            antenna_scan_type="phased_array",
            antenna_beamwidth_deg=2.0,
        ),
        EmitterModel(
            radar=RadarParameters(eirp_dBW=70, freq_GHz=6.0, pri_us=2000, scan_period_s=15),
            antenna_scan_type="rotating",
            antenna_beamwidth_deg=4.0,
        ),
    ]

    print("Threats to intercept:")
    for i, threat in enumerate(threats):
        print(f"  {i+1}. Freq: {threat.radar.freq_GHz} GHz, "
              f"EIRP: {threat.radar.eirp_dBW} dBW, "
              f"Type: {threat.antenna_scan_type}")
    print()

    # Create different schedules
    range_km = 200.0  # Analysis range

    # Uniform schedule
    uniform_schedule = scheduler.create_uniform_schedule(dwell_time_ms=10.0)
    print(f"Uniform Schedule: {uniform_schedule.total_scan_time_ms:.1f} ms total, "
          f"{uniform_schedule.scan_revisit_time_s:.2f} s revisit")

    # Threat-weighted schedule
    weighted_schedule = scheduler.create_threat_weighted_schedule(
        threats=threats,
        total_scan_time_ms=5000,
        min_dwell_ms=5.0,
        max_dwell_ms=50.0,
    )
    print(f"Threat-Weighted Schedule: {weighted_schedule.total_scan_time_ms:.1f} ms total, "
          f"{weighted_schedule.scan_revisit_time_s:.2f} s revisit")

    # Optimized schedule
    optimized_schedule = scheduler.optimize_schedule_for_poi(
        threats=threats,
        range_km=range_km,
        total_scan_time_ms=5000,
        poi_target=0.9,
    )
    print(f"Optimized Schedule: {optimized_schedule.total_scan_time_ms:.1f} ms total, "
          f"{optimized_schedule.scan_revisit_time_s:.2f} s revisit")
    print()

    # Evaluate schedules
    print("Schedule Performance Comparison:")
    print("-" * 70)
    print(f"{'Schedule':<20} {'Min POI':<12} {'Mean POI':<12} {'Max TTI (s)':<15}")
    print("-" * 70)

    for name, schedule in [("Uniform", uniform_schedule),
                           ("Threat-Weighted", weighted_schedule),
                           ("Optimized", optimized_schedule)]:
        eval_results = scheduler.evaluate_schedule(schedule, threats, range_km)
        summary = eval_results['summary']
        print(f"{name:<20} {summary['min_poi']:<12.1%} "
              f"{summary['mean_poi']:<12.1%} {summary['max_tti_s']:<15.1f}")

    print("-" * 70)
    print()

    # =========================================================================
    # PART 4: MONTE CARLO ANALYSIS
    # =========================================================================

    print("=== PART 4: MONTE CARLO ANALYSIS ===\n")

    n_iterations = 10000
    print(f"Running {n_iterations:,} Monte Carlo iterations...")

    mc_results = monte_carlo_analysis(
        receiver=receiver,
        radar=RadarParameters(eirp_dBW=60, freq_GHz=10),
        n_iterations=n_iterations,
        random_seed=42,
    )

    stats = mc_results['statistics']
    print("\nDetection Range Statistics:")
    print(f"  Mean: {stats['mean']:.1f} km")
    print(f"  Median: {stats['median']:.1f} km")
    print(f"  Std Dev: {stats['std']:.1f} km")
    print(f"  5th Percentile: {stats['p5']:.1f} km")
    print(f"  95th Percentile: {stats['p95']:.1f} km")
    print()

    print("Parameter Sensitivity (correlation with range):")
    sorted_corrs = sorted(mc_results['correlations'].items(),
                          key=lambda x: abs(x[1]), reverse=True)
    for param, corr in sorted_corrs:
        impact = "HIGH" if abs(corr) > 0.5 else ("MOD" if abs(corr) > 0.2 else "LOW")
        print(f"  {param:<20}: {corr:+.3f} ({impact})")
    print()

    # =========================================================================
    # PART 5: GENERATE PLOTS
    # =========================================================================

    print("=== PART 5: GENERATING PLOTS ===\n")

    # Create output directory
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)

    # Plot 1: Range comparison
    print("Generating range comparison plot...")
    fig1 = plot_detection_range_comparison(
        comparison_results,
        target_labels=[name for name, _ in radars],
    )
    fig1.savefig(output_dir / "01_range_comparison.png", dpi=150, bbox_inches='tight')

    # Plot 2: Sensitivity sweep
    print("Generating sensitivity sweep plot...")
    fig2 = plot_sensitivity_sweep(receiver, radars[0][1])
    fig2.savefig(output_dir / "02_sensitivity_sweep.png", dpi=150, bbox_inches='tight')

    # Plot 3: Monte Carlo results
    print("Generating Monte Carlo plot...")
    fig3 = plot_monte_carlo_results(mc_results)
    fig3.savefig(output_dir / "03_monte_carlo.png", dpi=150, bbox_inches='tight')

    # Plot 4: Dwell schedule
    print("Generating dwell schedule plot...")
    fig4 = plot_dwell_schedule(optimized_schedule, threats)
    fig4.savefig(output_dir / "04_dwell_schedule.png", dpi=150, bbox_inches='tight')

    # Plot 5: Schedule evaluation
    print("Generating schedule evaluation plot...")
    eval_results = scheduler.evaluate_schedule(optimized_schedule, threats, range_km)
    fig5 = plot_schedule_evaluation(eval_results)
    fig5.savefig(output_dir / "05_schedule_evaluation.png", dpi=150, bbox_inches='tight')

    # Plot 6: Range vs frequency
    print("Generating range vs frequency plot...")
    fig6 = plot_range_vs_frequency(receiver)
    fig6.savefig(output_dir / "06_range_vs_frequency.png", dpi=150, bbox_inches='tight')

    print(f"\nPlots saved to: {output_dir}")
    print()

    # =========================================================================
    # SUMMARY
    # =========================================================================

    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print()
    print("Key Findings:")
    print(f"  1. ESM detection ranges: {stats['p5']:.0f} - {stats['p95']:.0f} km (90% CI)")
    print(f"  2. ESM advantage over radar: {np.mean([c['range_multiplier'] for c in comparison_results]):.1f}x average")
    print(f"  3. Optimized dwell schedule achieves {eval_results['summary']['min_poi']:.0%} min POI")
    print(f"  4. Time to intercept: {eval_results['summary']['max_tti_s']:.1f} s worst case")
    print()

    # Show plots if running interactively
    plt.show()


if __name__ == "__main__":
    main()
