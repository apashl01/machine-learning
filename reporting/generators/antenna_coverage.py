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

    # RX Antenna inventory
    if config and 'rx_antennas' in config:
        rx_antennas = config['rx_antennas']
        headers = ["Antenna", "Band", "Type", "Position", "Gain (dBi)"]
        rows = []
        for ant in rx_antennas:
            rows.append([
                ant.get('name', 'Unknown'),
                ant.get('freq_band', '2-18 GHz'),
                ant.get('type', 'N/A'),
                ant.get('position', 'N/A'),
                f"{ant.get('peak_gain_dbi', 0):.1f}"
            ])
        gen.add_table_slide(f"RX Antenna Inventory ({len(rx_antennas)} antennas)", headers, rows)

    # TX Antenna inventory
    if config and 'tx_antennas' in config:
        tx_antennas = config['tx_antennas']
        headers = ["Antenna", "Band", "Type", "Beamwidth", "Gain (dBi)"]
        rows = []
        for ant in tx_antennas:
            rows.append([
                ant.get('name', 'Unknown'),
                ant.get('freq_band', '2-18 GHz'),
                ant.get('type', 'N/A'),
                f"{ant.get('beamwidth_deg', 0):.0f}°",
                f"{ant.get('peak_gain_dbi', 0):.1f}"
            ])
        gen.add_table_slide(f"TX Antenna Inventory ({len(tx_antennas)} antennas)", headers, rows)

    # Legacy antenna inventory (fallback)
    elif config and 'antennas' in config:
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
        if 'n_rx_antennas' in config:
            overview_bullets.append(f"RX Antennas: {config['n_rx_antennas']}")
        if 'n_tx_antennas' in config:
            overview_bullets.append(f"TX Antennas: {config['n_tx_antennas']}")
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

        # Main UAV coverage analysis plot
        main_plot = output_path / "uav_coverage_analysis.png"
        if main_plot.exists():
            gen.add_content_slide(
                "UAV Antenna Coverage Analysis",
                image_path=str(main_plot),
                image_width=10.0
            )

        # Individual antenna patterns (alternate name)
        pattern_plot = output_path / "antenna_patterns.png"
        if pattern_plot.exists():
            gen.add_content_slide(
                "Individual Antenna Patterns",
                image_path=str(pattern_plot),
                image_width=10.0
            )

        # Combined coverage (alternate name)
        coverage_plot = output_path / "combined_coverage.png"
        if coverage_plot.exists():
            gen.add_content_slide(
                "Combined Coverage Pattern",
                image_path=str(coverage_plot),
                image_width=10.0
            )

        # 3D coverage visualization (alternate name)
        coverage_3d_plot = output_path / "coverage_3d.png"
        if coverage_3d_plot.exists():
            gen.add_content_slide(
                "3D Coverage Visualization",
                image_path=str(coverage_3d_plot),
                image_width=10.0
            )

        # Coverage gaps (alternate name)
        gaps_plot = output_path / "coverage_gaps.png"
        if gaps_plot.exists():
            gen.add_content_slide(
                "Coverage Gap Analysis",
                image_path=str(gaps_plot),
                image_width=10.0
            )
