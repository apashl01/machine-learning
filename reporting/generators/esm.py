"""
ESM Analysis slide generator.
"""

from typing import Dict, Optional, List
from pathlib import Path
import numpy as np
from ..core import DesignReviewGenerator


def add_measurement_accuracy_slides(gen: DesignReviewGenerator,
                                      snr_values: List[float] = None):
    """
    Add pulse parameter measurement accuracy slides.

    Args:
        gen: DesignReviewGenerator instance
        snr_values: List of SNR values to analyze (default: [5, 10, 15, 20, 25])
    """
    try:
        from esm_analysis.measurement_accuracy import (
            MeasurementAccuracyAnalyzer,
            load_from_system_config
        )
    except ImportError:
        return  # Skip if module not available

    if snr_values is None:
        snr_values = [5, 10, 15, 20, 25]  # Threshold-guaranteed SNR values

    config = load_from_system_config()
    analyzer = MeasurementAccuracyAnalyzer(config)

    # Overview slide
    overview_bullets = [
        f"Detection Bandwidth: {config.channel_bandwidth_mhz} MHz",
        f"DLFD Delay Line: {config.dlfd_delay_ns} ns",
        f"Timing Resolution: {config.timing_resolution_ns*1000:.0f} ps",
        "",
        "Threshold-based detection guarantees minimum SNR for all measurements",
    ]
    gen.add_content_slide(
        "Pulse Measurement Configuration",
        bullets=overview_bullets
    )

    # Build table data for measurement accuracy vs SNR
    headers = ["SNR (dB)", "Freq (MHz)", "TOA (ns)", "PW (ns)", "PRI (ns)"]
    rows = []
    for snr in snr_values:
        result = analyzer.analyze(snr, pulse_width_us=1.0)
        rows.append([
            f"{snr:.0f}",
            f"{result.frequency_accuracy_mhz:.3f}",
            f"{result.toa_accuracy_ns:.2f}",
            f"{result.pulse_width_accuracy_ns:.2f}",
            f"{result.pri_accuracy_ns:.2f}"
        ])

    gen.add_table_slide(
        "Measurement Accuracy vs Detection SNR (RMS)",
        headers=headers,
        rows=rows
    )

    # Key findings slide
    result_10db = analyzer.analyze(10.0, pulse_width_us=1.0)
    findings = [
        f"At 10 dB detection threshold:",
        f"  • Frequency accuracy (DLFD): {result_10db.frequency_accuracy_mhz:.3f} MHz (req: 1.0 MHz)",
        f"  • TOA accuracy: {result_10db.toa_accuracy_ns:.2f} ns (req: 10.0 ns)",
        f"  • PW accuracy: {result_10db.pulse_width_accuracy_percent:.1f}% (req: 10%)",
        "",
        "DLFD: Digital Delay Line Frequency Discriminator",
        f"  σ_f = 1 / (2π × τ × √(2×SNR)), τ = {config.dlfd_delay_ns} ns",
    ]
    gen.add_content_slide(
        "Measurement Accuracy Summary",
        bullets=findings
    )


def add_esm_slides(gen: DesignReviewGenerator,
                   config: Optional[Dict] = None,
                   results: Optional[Dict] = None,
                   output_dir: Optional[str] = None):
    """
    Add ESM (Electronic Support Measures) Analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        config: ESM configuration dict
        results: Analysis results dict
        output_dir: Directory containing output plots
    """
    gen.add_section_slide("ESM Analysis",
                          "Electronic Support Measures Performance")

    # Configuration overview
    if config:
        overview_bullets = []
        if 'frequency_range_ghz' in config:
            fr = config['frequency_range_ghz']
            overview_bullets.append(f"Frequency Range: {fr[0]} - {fr[1]} GHz")
        if 'sensitivity_dbm' in config:
            overview_bullets.append(f"Sensitivity: {config['sensitivity_dbm']:.1f} dBm")
        if 'instantaneous_bandwidth_ghz' in config:
            overview_bullets.append(f"Instantaneous Bandwidth: {config['instantaneous_bandwidth_ghz']} GHz")
        if 'scan_type' in config:
            overview_bullets.append(f"Scan Type: {config['scan_type']}")

        if overview_bullets:
            gen.add_content_slide(
                "ESM Configuration",
                bullets=overview_bullets
            )

    # Performance metrics
    if results:
        metrics = {}
        if 'detection_range_km' in results:
            metrics['Detection Range'] = f"{results['detection_range_km']:.1f} km"
        if 'sensitivity_dbm' in results:
            metrics['Sensitivity'] = f"{results['sensitivity_dbm']:.1f} dBm"
        if 'sidelobe_detectable' in results:
            metrics['Sidelobe Detectable'] = f"{results['sidelobe_detectable']} threats"
        if 'main_beam_required' in results:
            metrics['Main Beam Required'] = f"{results['main_beam_required']} threats"
        if 'max_frequency_ghz' in results:
            metrics['Max Frequency'] = f"{results['max_frequency_ghz']:.1f} GHz"

        if metrics:
            gen.add_metrics_slide("ESM Performance Metrics", metrics)

    # Plots - look for ESMPlotter output files
    if output_dir:
        output_path = Path(output_dir)

        # SNR vs Range (main beam / sidelobe / backlobe)
        # ESMPlotter saves as snr_vs_range_{threat_id}.png
        snr_plots = list(output_path.glob("snr_vs_range_*.png"))
        for snr_plot in snr_plots[:1]:  # Just include first one
            gen.add_content_slide(
                "SNR vs Range (Main Beam / Sidelobe / Back Lobe)",
                image_path=str(snr_plot),
                image_width=10.0
            )

        # Categorization summary
        cat_plot = output_path / "categorization_summary.png"
        if cat_plot.exists():
            gen.add_content_slide(
                "Threat Categorization Summary",
                image_path=str(cat_plot),
                image_width=10.0
            )

        # Detection ranges
        ranges_plot = output_path / "detection_ranges.png"
        if ranges_plot.exists():
            gen.add_content_slide(
                "Detection Ranges by Beam Position",
                image_path=str(ranges_plot),
                image_width=10.0
            )

        # Duty cycle comparison
        duty_plot = output_path / "duty_cycle_comparison.png"
        if duty_plot.exists():
            gen.add_content_slide(
                "Duty Cycle Comparison",
                image_path=str(duty_plot),
                image_width=10.0
            )

    # Add measurement accuracy analysis
    add_measurement_accuracy_slides(gen)

    # Add spurious/false alarm analysis
    add_spurious_analysis_slides(gen)


def add_spurious_analysis_slides(gen: DesignReviewGenerator,
                                   pfa_values: List[float] = None):
    """
    Add ADC spurious and false alarm analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        pfa_values: List of target Pfa values to analyze
    """
    try:
        from esm_analysis.spurious_analysis import (
            SpuriousAnalyzer,
            load_from_system_config as load_spurious_config
        )
    except ImportError:
        return  # Skip if module not available

    if pfa_values is None:
        pfa_values = [1e-4, 1e-6, 1e-8, 1e-10]

    config = load_spurious_config()
    analyzer = SpuriousAnalyzer(config)

    # False alarm analysis table
    headers = ["Target Pfa", "Threshold (σ)", "FA/Dwell", "FA Rate (/s)", "MTBFA (s)"]
    rows = []
    for pfa in pfa_values:
        result = analyzer.analyze_statistical_false_alarm(pfa)
        rows.append([
            f"{pfa:.0e}",
            f"{result.threshold_sigma:.2f}",
            f"{result.expected_false_alarms_per_dwell:.2f}",
            f"{result.false_alarm_rate_per_second:.1f}",
            f"{result.mean_time_between_false_alarms_s:.2f}" if result.mean_time_between_false_alarms_s < 1e6 else ">1e6"
        ])

    gen.add_table_slide(
        "Statistical False Alarm Analysis",
        headers=headers,
        rows=rows
    )

    # Deterministic spurious analysis
    spur_result = analyzer.analyze_deterministic_spurious(
        signal_freq_ghz=10.0,
        signal_level_dbm=-30.0
    )

    # ADC spurious overview
    spurious_bullets = [
        f"ADC SFDR: {spur_result.sfdr_db:.1f} dBc",
        f"Total spurious signals identified: {len(spur_result.spurious_signals)}",
        f"In-band spurious: {spur_result.num_in_band_spurs}",
        f"Worst spur: {spur_result.worst_spur_name} at {spur_result.worst_spur_dbfs:.1f} dBFS",
        "",
        "Key spurious sources:",
        "  • ADC harmonics (2nd, 3rd order)",
        "  • Clock feedthrough",
        "  • Intermodulation products",
    ]
    gen.add_content_slide(
        "Deterministic Spurious Analysis",
        bullets=spurious_bullets
    )
