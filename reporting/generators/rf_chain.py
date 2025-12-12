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

    # Overview slide - multi-path summary
    if config:
        overview_bullets = []
        if 'n_rx_paths' in config:
            overview_bullets.append(f"Total RX Paths: {config['n_rx_paths']}")
        if 'n_tx_paths' in config:
            overview_bullets.append(f"Total TX Paths: {config['n_tx_paths']}")

        # Add path details
        if 'rx_paths' in config:
            for p in config['rx_paths']:
                freq = p.get('freq_range_ghz', [0, 0])
                overview_bullets.append(
                    f"RX {p['name']}: {p['num_paths']} path(s), {freq[0]}-{freq[1]} GHz"
                )
        if 'tx_paths' in config:
            for p in config['tx_paths']:
                freq = p.get('freq_range_ghz', [0, 0])
                overview_bullets.append(
                    f"TX {p['name']}: {p['num_paths']} path(s), {freq[0]}-{freq[1]} GHz"
                )

        if overview_bullets:
            gen.add_content_slide(
                "RF Path Configuration",
                bullets=overview_bullets
            )

    # RX Paths table
    if config and 'rx_paths' in config and config['rx_paths']:
        headers = ["Path", "Count", "Freq Range", "Gain (dB)", "NF (dB)"]
        rows = []
        for p in config['rx_paths']:
            freq = p.get('freq_range_ghz', [0, 0])
            rows.append([
                p.get('name', 'Unknown'),
                str(p.get('num_paths', 1)),
                f"{freq[0]}-{freq[1]} GHz",
                f"{p.get('total_gain_db', 0):.1f}",
                f"{p.get('cascade_nf_db', 0):.1f}"
            ])
        gen.add_table_slide("RX Path Summary", headers, rows)

    # TX Paths table
    if config and 'tx_paths' in config and config['tx_paths']:
        headers = ["Path", "Count", "Freq Range", "Gain (dB)", "Output (dBm)"]
        rows = []
        for p in config['tx_paths']:
            freq = p.get('freq_range_ghz', [0, 0])
            rows.append([
                p.get('name', 'Unknown'),
                str(p.get('num_paths', 1)),
                f"{freq[0]}-{freq[1]} GHz",
                f"{p.get('total_gain_db', 0):.1f}",
                f"{p.get('output_power_dbm', 0):.1f}"
            ])
        gen.add_table_slide("TX Path Summary", headers, rows)

    # Legacy components table (fallback)
    elif config and 'components' in config:
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

        # Main analysis plot
        analysis_plot = output_path / "rf_chain_analysis.png"
        if analysis_plot.exists():
            gen.add_content_slide(
                "RF Chain Analysis",
                image_path=str(analysis_plot),
                image_width=10.0
            )

        # Power vs frequency (alternate name)
        power_plot = output_path / "rf_chain_power.png"
        if power_plot.exists():
            gen.add_content_slide(
                "Power Budget Analysis",
                image_path=str(power_plot),
                image_width=10.0
            )

        # Component cascade (alternate name)
        cascade_plot = output_path / "rf_chain_cascade.png"
        if cascade_plot.exists():
            gen.add_content_slide(
                "Component Cascade",
                image_path=str(cascade_plot),
                image_width=10.0
            )

        # System RF Architecture
        # Display single comprehensive architecture diagram
        arch_diagram = output_path / "system_architecture.png"
        if arch_diagram.exists():
            gen.add_content_slide(
                "System RF Architecture",
                image_path=str(arch_diagram),
                image_width=10.0
            )
        else:
            # Fallback to SVG if PNG not available
            arch_diagram_svg = output_path / "system_architecture.svg"
            if arch_diagram_svg.exists():
                gen.add_content_slide(
                    "System RF Architecture",
                    image_path=str(arch_diagram_svg),
                    image_width=10.0
                )
