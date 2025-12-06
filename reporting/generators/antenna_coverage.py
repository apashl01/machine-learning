"""
Antenna Coverage Analysis slide generator.
"""

from typing import Dict, Optional, List
from pathlib import Path
from ..core import DesignReviewGenerator


def add_antenna_coverage_slides(gen: DesignReviewGenerator,
                                 config: Optional[Dict] = None,
                                 results: Optional[Dict] = None,
                                 output_dir: Optional[str] = None):
    """
    Add Antenna Coverage Analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        config: Antenna configuration dict
        results: Analysis results dict
        output_dir: Directory containing output plots
    """
    gen.add_section_slide("Antenna Coverage Analysis",
                          "Pattern & Coverage Performance")

    # Antenna inventory
    if config and 'antennas' in config:
        antennas = config['antennas']
        headers = ["Antenna", "Type", "Position", "Orientation", "Gain (dBi)"]
        rows = []
        for ant in antennas:
            rows.append([
                ant.get('name', 'Unknown'),
                ant.get('type', 'N/A'),
                ant.get('position', 'N/A'),
                ant.get('orientation', 'N/A'),
                f"{ant.get('peak_gain_dbi', 0):.1f}"
            ])
        gen.add_table_slide("Antenna Inventory", headers, rows)

    # Configuration bullets
    if config:
        overview_bullets = []
        if 'n_antennas' in config:
            overview_bullets.append(f"Total Antennas: {config['n_antennas']}")
        if 'frequency_ghz' in config:
            overview_bullets.append(f"Operating Frequency: {config['frequency_ghz']} GHz")
        if 'coverage_requirement' in config:
            overview_bullets.append(f"Coverage Requirement: {config['coverage_requirement']}")

        if overview_bullets:
            gen.add_content_slide(
                "Coverage Configuration",
                bullets=overview_bullets
            )

    # Coverage metrics
    if results:
        metrics = {}
        if 'coverage_percentage' in results:
            metrics['Coverage'] = f"{results['coverage_percentage']:.1f}%"
        if 'min_gain_db' in results:
            metrics['Min Gain'] = f"{results['min_gain_db']:.1f} dB"
        if 'max_gain_db' in results:
            metrics['Max Gain'] = f"{results['max_gain_db']:.1f} dB"
        if 'blind_spots' in results:
            metrics['Blind Spots'] = str(results['blind_spots'])

        if metrics:
            gen.add_metrics_slide("Coverage Performance", metrics)

    # Plots
    if output_dir:
        output_path = Path(output_dir)

        # Individual antenna patterns
        pattern_plot = output_path / "antenna_patterns.png"
        if pattern_plot.exists():
            gen.add_content_slide(
                "Individual Antenna Patterns",
                image_path=str(pattern_plot),
                image_width=10.0
            )

        # Combined coverage
        coverage_plot = output_path / "combined_coverage.png"
        if coverage_plot.exists():
            gen.add_content_slide(
                "Combined Coverage Pattern",
                image_path=str(coverage_plot),
                image_width=10.0
            )

        # 3D coverage visualization
        coverage_3d_plot = output_path / "coverage_3d.png"
        if coverage_3d_plot.exists():
            gen.add_content_slide(
                "3D Coverage Visualization",
                image_path=str(coverage_3d_plot),
                image_width=10.0
            )

        # Coverage gaps
        gaps_plot = output_path / "coverage_gaps.png"
        if gaps_plot.exists():
            gen.add_content_slide(
                "Coverage Gap Analysis",
                image_path=str(gaps_plot),
                image_width=10.0
            )
