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
            overview_bullets.append(f"Sensitivity: {config['sensitivity_dbm']} dBm")
        if 'scan_type' in config:
            overview_bullets.append(f"Scan Type: {config['scan_type']}")
        if 'revisit_rate_hz' in config:
            overview_bullets.append(f"Revisit Rate: {config['revisit_rate_hz']} Hz")

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
        if 'poi' in results:
            metrics['POI'] = f"{results['poi']*100:.1f}%"
        if 'sensitivity_dbm' in results:
            metrics['Sensitivity'] = f"{results['sensitivity_dbm']:.1f} dBm"
        if 'max_frequency_ghz' in results:
            metrics['Max Frequency'] = f"{results['max_frequency_ghz']:.1f} GHz"

        if metrics:
            gen.add_metrics_slide("ESM Performance Metrics", metrics)

    # Plots
    if output_dir:
        output_path = Path(output_dir)

        # Range comparison
        range_plot = output_path / "01_range_comparison.png"
        if range_plot.exists():
            gen.add_content_slide(
                "Detection Range Comparison",
                image_path=str(range_plot),
                image_width=10.0
            )

        # Sensitivity sweep
        sensitivity_plot = output_path / "02_sensitivity_sweep.png"
        if sensitivity_plot.exists():
            gen.add_content_slide(
                "Sensitivity Analysis",
                image_path=str(sensitivity_plot),
                image_width=10.0
            )

        # Dwell schedule
        dwell_plot = output_path / "04_dwell_schedule.png"
        if dwell_plot.exists():
            gen.add_content_slide(
                "Dwell Schedule",
                image_path=str(dwell_plot),
                image_width=10.0
            )

        # Schedule evaluation
        schedule_plot = output_path / "05_schedule_evaluation.png"
        if schedule_plot.exists():
            gen.add_content_slide(
                "Schedule Evaluation",
                image_path=str(schedule_plot),
                image_width=10.0
            )

        # Range vs frequency
        range_freq_plot = output_path / "06_range_vs_frequency.png"
        if range_freq_plot.exists():
            gen.add_content_slide(
                "Range vs Frequency",
                image_path=str(range_freq_plot),
                image_width=10.0
            )
