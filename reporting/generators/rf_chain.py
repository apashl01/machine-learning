"""
RF Chain Analysis slide generator.
"""

from typing import Dict, Optional
from pathlib import Path
from ..core import DesignReviewGenerator


def add_rf_chain_slides(gen: DesignReviewGenerator,
                        config: Optional[Dict] = None,
                        results: Optional[Dict] = None,
                        output_dir: Optional[str] = None):
    """
    Add RF Chain Analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        config: RF chain configuration dict
        results: Analysis results dict
        output_dir: Directory containing output plots
    """
    gen.add_section_slide("RF Chain Analysis",
                          "Link Budget & Component Performance")

    # Overview slide
    if config:
        overview_bullets = [
            f"Chain Type: {config.get('chain_type', 'TX/RX')}",
            f"Frequency: {config.get('frequency_ghz', 'N/A')} GHz",
            f"Components: {config.get('n_components', 'N/A')}",
        ]
        if 'input_power_dbm' in config:
            overview_bullets.append(f"Input Power: {config['input_power_dbm']} dBm")
        if 'damage_threshold_dbm' in config:
            overview_bullets.append(f"Damage Threshold: {config['damage_threshold_dbm']} dBm")

        gen.add_content_slide(
            "RF Chain Configuration",
            bullets=overview_bullets
        )

    # Components table
    if config and 'components' in config:
        components = config['components']
        headers = ["Component", "Type", "Gain/Loss (dB)", "NF (dB)"]
        rows = []
        for comp in components:
            rows.append([
                comp.get('name', 'Unknown'),
                comp.get('type', 'N/A'),
                f"{comp.get('gain_db', 0):.1f}",
                f"{comp.get('noise_figure_db', 0):.1f}"
            ])

        gen.add_table_slide("Component Specifications", headers, rows)

    # Results metrics
    if results:
        metrics = {}
        if 'total_gain_db' in results:
            metrics['Total Gain'] = f"{results['total_gain_db']:.1f} dB"
        if 'cascade_nf_db' in results:
            metrics['Cascade NF'] = f"{results['cascade_nf_db']:.1f} dB"
        if 'output_power_dbm' in results:
            metrics['Output Power'] = f"{results['output_power_dbm']:.1f} dBm"
        if 'saturated' in results:
            metrics['Saturation'] = "Yes" if results['saturated'] else "No"

        if metrics:
            gen.add_metrics_slide("RF Chain Performance", metrics)

    # Plots
    if output_dir:
        output_path = Path(output_dir)

        # Power vs frequency
        power_plot = output_path / "rf_chain_power.png"
        if power_plot.exists():
            gen.add_content_slide(
                "Power Budget Analysis",
                image_path=str(power_plot),
                image_width=10.0
            )

        # Component cascade
        cascade_plot = output_path / "rf_chain_cascade.png"
        if cascade_plot.exists():
            gen.add_content_slide(
                "Component Cascade",
                image_path=str(cascade_plot),
                image_width=10.0
            )
