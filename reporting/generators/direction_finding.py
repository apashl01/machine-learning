"""
Direction Finding Analysis slide generator.
"""

from typing import Dict, Optional
from pathlib import Path
from ..core import DesignReviewGenerator


def add_direction_finding_slides(gen: DesignReviewGenerator,
                                  config: Optional[Dict] = None,
                                  results: Optional[Dict] = None,
                                  output_dir: Optional[str] = None):
    """
    Add Direction Finding Analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        config: Interferometer configuration dict
        results: Analysis results dict
        output_dir: Directory containing output plots
    """
    gen.add_section_slide("Direction Finding Analysis",
                          "Interferometer Performance & Accuracy")

    # Configuration slide
    if config:
        overview_bullets = [
            f"Array Type: {config.get('n_elements', 4)}-element interferometer",
            f"Spacing: Non-uniform (Vernier) for ambiguity resolution",
            f"Frequency Range: {config.get('freq_min_ghz', 2)} - {config.get('freq_max_ghz', 18)} GHz",
            f"Phase Error (high SNR): {config.get('phase_error_deg', 12)} deg",
        ]

        if 'element_positions' in config:
            positions = config['element_positions']
            overview_bullets.append(
                f"Element Positions: [{', '.join(f'{p:.2f}' for p in positions)}] inches"
            )

        if 'max_baseline' in config:
            overview_bullets.append(
                f"Max Baseline: {config['max_baseline']:.2f} inches ({config['max_baseline']*25.4:.1f} mm)"
            )

        gen.add_content_slide(
            "Interferometer Configuration",
            bullets=overview_bullets
        )

    # Baselines table
    if config and 'baselines' in config:
        baselines = config['baselines']
        headers = ["Baseline", "Length (in)", "Length (mm)", "Purpose"]
        rows = []
        for i, bl in enumerate(sorted(baselines)):
            purpose = "Ambiguity resolution" if bl < 1.0 else "Accuracy"
            rows.append([
                f"B{i+1}",
                f"{bl:.3f}",
                f"{bl * 25.4:.2f}",
                purpose
            ])
        gen.add_table_slide("Baseline Configuration", headers, rows)

    # Performance metrics
    if results:
        metrics = {}
        if 'angle_accuracy_deg' in results:
            metrics['Angle Accuracy'] = f"{results['angle_accuracy_deg']:.2f} deg"
        if 'ambiguity_free_fov' in results:
            metrics['Ambiguity-Free FOV'] = f"±{results['ambiguity_free_fov']:.1f} deg"
        if 'min_snr_db' in results:
            metrics['Min SNR Required'] = f"{results['min_snr_db']:.1f} dB"
        if 'max_incident_angle' in results:
            metrics['Max Incident Angle'] = f"{results['max_incident_angle']:.1f} deg"

        if metrics:
            gen.add_metrics_slide("Direction Finding Performance", metrics)

    # Plots
    if output_dir:
        output_path = Path(output_dir)

        # Angle error vs frequency
        angle_error_plot = output_path / "df_angle_error.png"
        if angle_error_plot.exists():
            gen.add_content_slide(
                "Angle Error vs Frequency",
                image_path=str(angle_error_plot),
                image_width=10.0
            )

        # Angle error vs incident angle
        incident_plot = output_path / "df_incident_angle.png"
        if incident_plot.exists():
            gen.add_content_slide(
                "Angle Error vs Incident Angle",
                image_path=str(incident_plot),
                image_width=10.0
            )

        # Ambiguity analysis
        ambiguity_plot = output_path / "df_ambiguity.png"
        if ambiguity_plot.exists():
            gen.add_content_slide(
                "Ambiguity Analysis",
                image_path=str(ambiguity_plot),
                image_width=10.0
            )
