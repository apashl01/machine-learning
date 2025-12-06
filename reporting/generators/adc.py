"""
ADC Analysis slide generator.
"""

from typing import Dict, Optional, List
from pathlib import Path
from ..core import DesignReviewGenerator


def add_adc_slides(gen: DesignReviewGenerator,
                   config: Optional[Dict] = None,
                   results: Optional[Dict] = None,
                   output_dir: Optional[str] = None):
    """
    Add ADC Analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        config: ADC configuration dict
        results: Analysis results dict
        output_dir: Directory containing output plots
    """
    gen.add_section_slide("ADC Analysis",
                          "Analog-to-Digital Converter Performance")

    # Overview slide
    if config:
        overview_bullets = []
        if 'model' in config:
            overview_bullets.append(f"ADC Model: {config['model']}")
        if 'resolution_bits' in config:
            overview_bullets.append(f"Resolution: {config['resolution_bits']} bits")
        if 'sample_rate_msps' in config:
            overview_bullets.append(f"Sample Rate: {config['sample_rate_msps']} MSPS")
        if 'input_range_vpp' in config:
            overview_bullets.append(f"Input Range: {config['input_range_vpp']} Vpp")

        if overview_bullets:
            gen.add_content_slide(
                "ADC Configuration",
                bullets=overview_bullets
            )

    # Band specifications table
    if config and 'bands' in config:
        bands = config['bands']
        headers = ["Band", "Freq Range (GHz)", "SFDR (dBc)", "SNR (dB)", "ENOB"]
        rows = []
        for band_name, band_data in bands.items():
            rows.append([
                band_name,
                f"{band_data.get('freq_min', 'N/A')} - {band_data.get('freq_max', 'N/A')}",
                f"{band_data.get('sfdr_dbc', 'N/A')}",
                f"{band_data.get('snr_db', 'N/A')}",
                f"{band_data.get('enob', 'N/A'):.1f}" if isinstance(band_data.get('enob'), (int, float)) else "N/A"
            ])

        gen.add_table_slide("Per-Band Specifications", headers, rows)

    # Key metrics
    if results:
        metrics = {}
        if 'effective_bits' in results:
            metrics['Effective Bits'] = f"{results['effective_bits']:.1f}"
        if 'sfdr_db' in results:
            metrics['SFDR'] = f"{results['sfdr_db']:.1f} dBc"
        if 'snr_db' in results:
            metrics['SNR'] = f"{results['snr_db']:.1f} dB"
        if 'dynamic_range_db' in results:
            metrics['Dynamic Range'] = f"{results['dynamic_range_db']:.1f} dB"

        if metrics:
            gen.add_metrics_slide("ADC Performance Metrics", metrics)

    # Plots
    if output_dir:
        output_path = Path(output_dir)

        # SFDR vs frequency
        sfdr_plot = output_path / "adc_sfdr.png"
        if sfdr_plot.exists():
            gen.add_content_slide(
                "SFDR vs Frequency",
                image_path=str(sfdr_plot),
                image_width=10.0
            )

        # ENOB vs frequency
        enob_plot = output_path / "adc_enob.png"
        if enob_plot.exists():
            gen.add_content_slide(
                "Effective Number of Bits",
                image_path=str(enob_plot),
                image_width=10.0
            )

        # Comparison plot
        comparison_plot = output_path / "adc_comparison.png"
        if comparison_plot.exists():
            gen.add_content_slide(
                "ADC Comparison",
                image_path=str(comparison_plot),
                image_width=10.0
            )
