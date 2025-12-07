"""
ESM Analysis slide generator.
"""

from typing import Dict, Optional, List
from pathlib import Path
from ..core import DesignReviewGenerator


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
