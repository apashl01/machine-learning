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
        # Show frequency range instead of single frequency
        overview_bullets.append("Frequency Range: 0.5 - 18.0 GHz")
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

        # Antenna placement and 3D model slide
        # Show only placement diagram and 3D model (if available)
        placement_plot = output_path / "antenna_placement.png"
        model_plot = output_path / "uav_model_view.png"

        if placement_plot.exists():
            gen.add_content_slide(
                "Antenna Placement & Model",
                image_path=str(placement_plot),
                image_width=10.0
            )
        elif model_plot.exists():
            # If only 3D model exists, show that
            gen.add_content_slide(
                "Antenna Placement & Model",
                image_path=str(model_plot),
                image_width=10.0
            )

        # Task 2: Multi-band coverage plots
        # Coverage comparison (overview of all bands)
        comparison_plot = output_path / "coverage_comparison.png"
        if comparison_plot.exists():
            gen.add_content_slide(
                "Multi-Band Coverage Comparison",
                image_path=str(comparison_plot),
                image_width=10.0
            )

        # RX Mid-Band coverage
        rx_mid_plot = output_path / "coverage_rx_mid.png"
        if rx_mid_plot.exists():
            gen.add_content_slide(
                "RX Coverage - Mid Band (2-18 GHz)",
                image_path=str(rx_mid_plot),
                image_width=10.0
            )

        # RX Low-Band coverage
        rx_low_plot = output_path / "coverage_rx_low.png"
        if rx_low_plot.exists():
            gen.add_content_slide(
                "RX Coverage - Low Band (<2 GHz)",
                image_path=str(rx_low_plot),
                image_width=10.0
            )

        # TX Mid-Band coverage
        tx_mid_plot = output_path / "coverage_tx_mid.png"
        if tx_mid_plot.exists():
            gen.add_content_slide(
                "TX Coverage - Mid Band (2-18 GHz)",
                image_path=str(tx_mid_plot),
                image_width=10.0
            )

        # TX Low-Band coverage
        tx_low_plot = output_path / "coverage_tx_low.png"
        if tx_low_plot.exists():
            gen.add_content_slide(
                "TX Coverage - Low Band (<2 GHz)",
                image_path=str(tx_low_plot),
                image_width=10.0
            )
