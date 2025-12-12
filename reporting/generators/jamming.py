"""
Jamming Analysis slide generator.

Generates slides for Self-Protect Jamming (SPJ) analysis including:
- Jammer and radar configuration
- Platform RCS effects on J/S ratio
- J/S vs range analysis
- Burn-through range calculations
- Visualizations
"""

from typing import Dict, Optional, List
from pathlib import Path
import numpy as np
from ..core import DesignReviewGenerator


def add_jamming_slides(gen: DesignReviewGenerator,
                        jammer_config: Optional[Dict] = None,
                        radar_config: Optional[Dict] = None,
                        output_dir: Optional[str] = None,
                        title_suffix: Optional[str] = None):
    """
    Add Jamming Analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        jammer_config: Optional jammer configuration dict (includes platform_rcs_m2)
        radar_config: Optional radar configuration dict
        output_dir: Directory containing output plots
        title_suffix: Optional suffix to add to slide titles (e.g., "Mid-Band")
    """
    try:
        from jamming_analysis import (
            JammerConfig,
            RadarConfig,
            JammingAnalyzer
        )
        from jamming_analysis.visualization import (
            plot_js_vs_range,
            plot_antenna_pattern,
            plot_js_vs_rcs,
            create_jamming_summary_figure
        )
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return  # Skip if module not available

    # Build section title with optional suffix
    section_title = "Self-Protect Jamming Analysis"
    if title_suffix:
        section_title += f" - {title_suffix}"

    gen.add_section_slide(section_title, "TX Chain Performance & J/S Analysis")

    # Create default configs if not provided
    if jammer_config:
        jammer = JammerConfig(**jammer_config)
    else:
        jammer = JammerConfig(
            input_power_dbm=50,
            antenna_gain_dbi=20,
            beamwidth_deg=30,
            pattern_type='gaussian',
            frequency_ghz=10.0,
            platform_rcs_m2=2.0
        )

    if radar_config:
        radar = RadarConfig(**radar_config)
    else:
        radar = RadarConfig(
            power_dbw=60,
            antenna_gain_dbi=35,
            frequency_ghz=10.0
        )

    analyzer = JammingAnalyzer(jammer, radar)

    # Jammer configuration slide (includes platform RCS)
    jammer_bullets = [
        f"Input Power: {jammer.input_power_dbm} dBm ({jammer.input_power_watts:.0f} W)",
        f"Antenna Gain: {jammer.antenna_gain_dbi} dBi",
        f"Beamwidth: {jammer.beamwidth_deg}°",
        f"Pattern Type: {jammer.pattern_type.title()}",
        f"Operating Frequency: {jammer.frequency_ghz} GHz",
        f"Peak EIRP: {jammer.eirp_peak_dbm:.1f} dBm ({jammer.eirp_peak_watts:.0f} W)",
        "",
        f"Platform RCS: {jammer.platform_rcs_m2} m² ({jammer.platform_rcs_dbsm:.1f} dBsm)",
        "   (Platform RCS affects radar return → smaller = better jamming)",
    ]
    gen.add_content_slide("Jammer & Platform Configuration", bullets=jammer_bullets)

    # Threat radar slide
    radar_bullets = [
        f"Radar Power: {radar.power_dbw} dBW ({radar.power_watts/1e6:.2f} MW)",
        f"Antenna Gain: {radar.antenna_gain_dbi} dBi",
        f"Operating Frequency: {radar.frequency_ghz} GHz",
        "",
        "Self-Protect Jamming Geometry:",
        "   • Radar transmits → reflects off platform → returns to radar",
        "   • Jammer transmits directly to radar (one-way path)",
        "   • J/S = Jammer power / Radar return",
    ]
    gen.add_content_slide("Threat Radar Parameters", bullets=radar_bullets)

    # Self-protect jamming physics slide
    physics_bullets = [
        "Self-Protect Jamming (SPJ) Physics:",
        "",
        "   Jammer power at radar: P_j ∝ R^(-2)  (one-way)",
        "   Radar return at radar: P_s ∝ R^(-4)  (two-way)",
        "",
        "   J/S Ratio ∝ R² / σ_platform",
        "",
        "Key Insights:",
        "   • J/S INCREASES with range (favorable at standoff)",
        "   • J/S DECREASES with larger RCS (smaller platform = better)",
        "   • Burn-through occurs at CLOSER ranges",
    ]
    gen.add_content_slide("Self-Protect Jamming Physics", bullets=physics_bullets)

    # J/S vs Platform RCS table
    headers_rcs = ["Platform RCS (m²)", "RCS (dBsm)", "J/S at 50km (dB)", "J/S at 100km (dB)"]
    rows_rcs = []
    for rcs in [0.5, 1.0, 2.0, 5.0, 10.0]:
        rcs_dbsm = 10 * np.log10(rcs)
        result_50 = analyzer.analyze(50000, 0, platform_rcs_m2=rcs)
        result_100 = analyzer.analyze(100000, 0, platform_rcs_m2=rcs)
        rows_rcs.append([f"{rcs:.1f}", f"{rcs_dbsm:.1f}",
                         f"{result_50.js_ratio_db:.1f}", f"{result_100.js_ratio_db:.1f}"])

    gen.add_table_slide("J/S Ratio vs Platform RCS", headers=headers_rcs, rows=rows_rcs)

    # Burn-through analysis
    bt_0db = analyzer.calculate_burn_through_range(0)
    bt_10db = analyzer.calculate_burn_through_range(10)
    bt_20db = analyzer.calculate_burn_through_range(20)

    bt_bullets = [
        "Burn-through range: minimum range where J/S meets threshold",
        "(At closer ranges, radar can 'burn through' the jamming)",
        "",
        f"J/S = 0 dB (equal power):      {bt_0db:.1f} km",
        f"J/S = 10 dB (good jamming):    {bt_10db:.1f} km",
        f"J/S = 20 dB (excellent):       {bt_20db:.1f} km",
        "",
        f"Platform RCS: {jammer.platform_rcs_m2} m² - reducing RCS lowers burn-through range",
    ]
    gen.add_content_slide("Burn-Through Range Analysis", bullets=bt_bullets)

    # Off-boresight effects
    headers2 = ["Off-Boresight (°)", "Gain (dBi)", "EIRP (dBm)", "J/S at 100km"]
    rows2 = []
    for angle in [0, 15, 30, 45, 60]:
        gain = jammer.get_gain_at_angle(angle)
        eirp = jammer.input_power_dbm + gain
        result = analyzer.analyze(100000, angle)
        rows2.append([f"{angle}", f"{gain:.1f}", f"{eirp:.1f}", f"{result.js_ratio_db:.1f}"])

    gen.add_table_slide("Off-Boresight Performance", headers=headers2, rows=rows2)

    # Generate plots if output directory provided
    if output_dir:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Generate J/S vs Range plot
        js_plot = output_path / "jamming_js_vs_range.png"
        fig1, ax1 = plt.subplots(figsize=(10, 6))
        plot_js_vs_range(analyzer, ax=ax1, save_path=str(js_plot))
        plt.close(fig1)

        if js_plot.exists():
            gen.add_content_slide(
                "J/S Ratio vs Range",
                image_path=str(js_plot),
                image_width=10.0
            )

        # Generate antenna pattern plot
        pattern_plot = output_path / "jamming_antenna_pattern.png"
        fig2, ax2 = plt.subplots(figsize=(10, 6))
        plot_antenna_pattern(jammer, ax=ax2, save_path=str(pattern_plot))
        plt.close(fig2)

        if pattern_plot.exists():
            gen.add_content_slide(
                "Jammer Antenna Pattern",
                image_path=str(pattern_plot),
                image_width=10.0
            )

        # Generate J/S vs RCS plot
        rcs_plot = output_path / "jamming_js_vs_rcs.png"
        fig3, ax3 = plt.subplots(figsize=(10, 6))
        plot_js_vs_rcs(analyzer, range_km=50.0, ax=ax3, save_path=str(rcs_plot))
        plt.close(fig3)

        if rcs_plot.exists():
            gen.add_content_slide(
                "J/S Ratio vs Platform RCS",
                image_path=str(rcs_plot),
                image_width=10.0
            )

        # Generate summary figure
        summary_plot = output_path / "jamming_summary.png"
        fig4 = create_jamming_summary_figure(jammer, radar, str(output_path))
        plt.close(fig4)

        if summary_plot.exists():
            gen.add_content_slide(
                "Self-Protect Jamming Analysis Summary",
                image_path=str(summary_plot),
                image_width=10.0
            )
