"""
Jamming Analysis slide generator.
"""

from typing import Dict, Optional, List
from pathlib import Path
from ..core import DesignReviewGenerator


def add_jamming_slides(gen: DesignReviewGenerator,
                        jammer_config: Optional[Dict] = None,
                        emitter_config: Optional[Dict] = None,
                        output_dir: Optional[str] = None):
    """
    Add Jamming Analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        jammer_config: Optional jammer configuration dict
        emitter_config: Optional emitter configuration dict
        output_dir: Directory containing output plots
    """
    try:
        from jamming_analysis import (
            JammerConfig,
            EmitterConfig,
            JammingAnalyzer
        )
    except ImportError:
        return  # Skip if module not available

    gen.add_section_slide("Jamming Analysis",
                          "TX Chain Performance & J/S Analysis")

    # Create default configs if not provided
    if jammer_config:
        jammer = JammerConfig(**jammer_config)
    else:
        jammer = JammerConfig(
            input_power_dbm=50,
            antenna_gain_dbi=20,
            beamwidth_deg=30,
            pattern_type='gaussian',
            frequency_ghz=10.0
        )

    if emitter_config:
        emitter = EmitterConfig(**emitter_config)
    else:
        emitter = EmitterConfig(
            power_dbw=60,
            antenna_gain_dbi=35,
            frequency_ghz=10.0,
            target_rcs_m2=2.0
        )

    analyzer = JammingAnalyzer(jammer, emitter)

    # Jammer configuration slide
    jammer_bullets = [
        f"Input Power: {jammer.input_power_dbm} dBm ({jammer.input_power_watts:.0f} W)",
        f"Antenna Gain: {jammer.antenna_gain_dbi} dBi",
        f"Beamwidth: {jammer.beamwidth_deg}°",
        f"Pattern Type: {jammer.pattern_type.title()}",
        f"Operating Frequency: {jammer.frequency_ghz} GHz",
        f"Peak EIRP: {jammer.eirp_peak_dbm:.1f} dBm ({jammer.eirp_peak_watts:.0f} W)",
    ]
    gen.add_content_slide("Jammer Configuration", bullets=jammer_bullets)

    # Target emitter slide
    emitter_bullets = [
        f"Radar Power: {emitter.power_dbw} dBW ({emitter.power_watts/1e6:.2f} MW)",
        f"Antenna Gain: {emitter.antenna_gain_dbi} dBi",
        f"Operating Frequency: {emitter.frequency_ghz} GHz",
        f"Target RCS: {emitter.target_rcs_m2} m² ({emitter.target_rcs_dbsm:.1f} dBsm)",
    ]
    gen.add_content_slide("Target Emitter Parameters", bullets=emitter_bullets)

    # J/S analysis at key ranges
    headers = ["Range (km)", "J/S (dB)", "Effectiveness"]
    rows = []
    for r_km in [20, 50, 100, 150, 200]:
        result = analyzer.analyze(r_km * 1000, 0)
        js = result.js_ratio_db
        if js > 20:
            eff = "Excellent"
        elif js > 10:
            eff = "Good"
        elif js > 0:
            eff = "Marginal"
        else:
            eff = "Ineffective"
        rows.append([f"{r_km}", f"{js:.1f}", eff])

    gen.add_table_slide("J/S Ratio vs Range (On-Boresight)", headers=headers, rows=rows)

    # Burn-through analysis
    bt_0db = analyzer.calculate_burn_through_range(0)
    bt_10db = analyzer.calculate_burn_through_range(10)
    bt_20db = analyzer.calculate_burn_through_range(20)

    bt_bullets = [
        "Burn-through range: minimum range for effective jamming",
        "",
        f"J/S = 0 dB (equal power): {bt_0db:.1f} km",
        f"J/S = 10 dB (good jamming): {bt_10db:.1f} km",
        f"J/S = 20 dB (excellent jamming): {bt_20db:.1f} km",
        "",
        "J/S increases with range (jammer R^-2 vs radar R^-4)",
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

    # Add plots if available
    if output_dir:
        output_path = Path(output_dir)

        js_plot = output_path / "jamming_js_vs_range.png"
        if js_plot.exists():
            gen.add_content_slide(
                "J/S Ratio vs Range",
                image_path=str(js_plot),
                image_width=10.0
            )

        summary_plot = output_path / "jamming_summary.png"
        if summary_plot.exists():
            gen.add_content_slide(
                "Jamming Analysis Summary",
                image_path=str(summary_plot),
                image_width=10.0
            )
