"""
Jamming Analysis Visualization Module

Generates plots for:
- J/S ratio vs range
- Antenna pattern with gain profile
- EIRP vs angle
- Burn-through range analysis
"""

from typing import Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from .core import JammerConfig, RadarConfig, JammingAnalyzer, JammingResult


def plot_js_vs_range(analyzer: JammingAnalyzer,
                     range_min_km: float = 5.0,
                     range_max_km: float = 200.0,
                     off_boresight_deg: float = 0.0,
                     ax: Optional[plt.Axes] = None,
                     save_path: Optional[str] = None) -> plt.Axes:
    """
    Plot J/S ratio vs range.

    Args:
        analyzer: JammingAnalyzer instance
        range_min_km: Minimum range
        range_max_km: Maximum range
        off_boresight_deg: Fixed off-boresight angle
        ax: Optional axes to plot on
        save_path: Optional path to save figure

    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    result = analyzer.analyze_vs_range(range_min_km, range_max_km, 200, off_boresight_deg)
    range_km = np.asarray(result.range_m) / 1000

    ax.plot(range_km, result.js_ratio_db, 'b-', linewidth=2, label='J/S Ratio')

    # Threshold lines
    ax.axhline(0, color='k', linestyle='--', linewidth=1.5, label='0 dB (Equal)')
    ax.axhline(10, color='g', linestyle='--', linewidth=1.5, label='10 dB (Good)')
    ax.axhline(20, color='orange', linestyle='--', linewidth=1.5, label='20 dB (Excellent)')

    # Burn-through range
    bt_range = analyzer.calculate_burn_through_range(0, off_boresight_deg)
    ax.axvline(bt_range, color='r', linestyle=':', linewidth=2,
               label=f'Burn-through: {bt_range:.1f} km')

    ax.set_xlabel('Range (km)', fontsize=12)
    ax.set_ylabel('J/S Ratio (dB)', fontsize=12)
    ax.set_title(f'Jamming-to-Signal Ratio vs Range (θ = {off_boresight_deg}°)', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.set_xlim(range_min_km, range_max_km)

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

    return ax


def plot_antenna_pattern(jammer: JammerConfig,
                         ax: Optional[plt.Axes] = None,
                         save_path: Optional[str] = None) -> plt.Axes:
    """
    Plot jammer antenna gain pattern.

    Args:
        jammer: JammerConfig instance
        ax: Optional axes to plot on
        save_path: Optional path to save figure

    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    angles = np.linspace(-90, 90, 181)
    gains = jammer.get_gain_at_angle(angles)

    ax.plot(angles, gains, 'b-', linewidth=2)
    ax.axhline(jammer.antenna_gain_dbi - 3, color='r', linestyle='--',
               label=f'-3 dB: {jammer.antenna_gain_dbi - 3:.1f} dBi')

    # Mark beamwidth
    half_bw = jammer.beamwidth_deg / 2
    ax.axvline(-half_bw, color='g', linestyle=':', alpha=0.7)
    ax.axvline(half_bw, color='g', linestyle=':', alpha=0.7,
               label=f'Beamwidth: {jammer.beamwidth_deg}°')

    ax.set_xlabel('Off-Boresight Angle (degrees)', fontsize=12)
    ax.set_ylabel('Antenna Gain (dBi)', fontsize=12)
    ax.set_title(f'Jammer Antenna Pattern ({jammer.pattern_type.title()})', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.set_xlim(-90, 90)

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

    return ax


def plot_eirp_vs_angle(jammer: JammerConfig,
                       ax: Optional[plt.Axes] = None,
                       save_path: Optional[str] = None) -> plt.Axes:
    """
    Plot EIRP vs off-boresight angle.

    Args:
        jammer: JammerConfig instance
        ax: Optional axes to plot on
        save_path: Optional path to save figure

    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    angles = np.linspace(-90, 90, 181)
    gains = jammer.get_gain_at_angle(angles)
    eirp_dbm = jammer.input_power_dbm + gains
    eirp_watts = 10 ** (eirp_dbm / 10) / 1000

    ax.plot(angles, eirp_watts, 'r-', linewidth=2)

    # Mark peak EIRP
    ax.axhline(jammer.eirp_peak_watts, color='k', linestyle='--', alpha=0.5,
               label=f'Peak: {jammer.eirp_peak_watts:.0f} W')

    ax.set_xlabel('Off-Boresight Angle (degrees)', fontsize=12)
    ax.set_ylabel('EIRP (Watts)', fontsize=12)
    ax.set_title('Effective Isotropic Radiated Power vs Angle', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    ax.set_xlim(-90, 90)
    ax.set_ylim(0, None)

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

    return ax


def plot_js_heatmap(analyzer: JammingAnalyzer,
                    range_min_km: float = 10.0,
                    range_max_km: float = 200.0,
                    angle_range_deg: float = 60.0,
                    ax: Optional[plt.Axes] = None,
                    save_path: Optional[str] = None) -> plt.Axes:
    """
    Plot J/S ratio heatmap (range vs angle).

    Args:
        analyzer: JammingAnalyzer instance
        range_min_km: Minimum range
        range_max_km: Maximum range
        angle_range_deg: Max off-boresight angle (+/-)
        ax: Optional axes to plot on
        save_path: Optional path to save figure

    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 8))

    # Create grid
    ranges_km = np.linspace(range_min_km, range_max_km, 100)
    angles = np.linspace(-angle_range_deg, angle_range_deg, 121)
    R, A = np.meshgrid(ranges_km * 1000, angles)

    # Calculate J/S at each point
    result = analyzer.analyze(R.flatten(), A.flatten())
    js = np.asarray(result.js_ratio_db).reshape(R.shape)

    # Plot heatmap
    levels = np.arange(-30, 35, 5)
    c = ax.contourf(ranges_km, angles, js, levels=levels, cmap='RdYlGn', extend='both')
    plt.colorbar(c, ax=ax, label='J/S Ratio (dB)')

    # Add contour lines
    ax.contour(ranges_km, angles, js, levels=[0, 10, 20], colors=['k', 'b', 'purple'],
               linewidths=[2, 1.5, 1.5], linestyles=['--', '-', '-'])

    ax.set_xlabel('Range (km)', fontsize=12)
    ax.set_ylabel('Off-Boresight Angle (degrees)', fontsize=12)
    ax.set_title('J/S Ratio vs Range and Angle', fontsize=14)

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

    return ax


def plot_js_vs_rcs(analyzer: JammingAnalyzer,
                   range_km: float = 50.0,
                   rcs_min_m2: float = 0.1,
                   rcs_max_m2: float = 10.0,
                   ax: Optional[plt.Axes] = None,
                   save_path: Optional[str] = None) -> plt.Axes:
    """
    Plot J/S ratio vs platform RCS.

    Shows how reducing platform RCS improves jamming effectiveness.

    Args:
        analyzer: JammingAnalyzer instance
        range_km: Fixed range
        rcs_min_m2: Minimum RCS
        rcs_max_m2: Maximum RCS
        ax: Optional axes to plot on
        save_path: Optional path to save figure

    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    rcs_data = analyzer.analyze_vs_rcs(range_km, rcs_min_m2, rcs_max_m2, 50)

    ax.semilogx(rcs_data['rcs_m2'], rcs_data['js_ratio_db'], 'b-', linewidth=2)

    # Threshold lines
    ax.axhline(0, color='k', linestyle='--', linewidth=1.5, label='0 dB (Equal)')
    ax.axhline(10, color='g', linestyle='--', linewidth=1.5, label='10 dB (Good)')
    ax.axhline(20, color='orange', linestyle='--', linewidth=1.5, label='20 dB (Excellent)')

    # Mark current platform RCS
    current_rcs = analyzer.jammer.platform_rcs_m2
    result = analyzer.analyze(range_km * 1000, 0)
    ax.axvline(current_rcs, color='r', linestyle=':', linewidth=2,
               label=f'Platform RCS: {current_rcs} m²')
    ax.plot(current_rcs, result.js_ratio_db, 'ro', markersize=10)

    ax.set_xlabel('Platform RCS (m²)', fontsize=12)
    ax.set_ylabel('J/S Ratio (dB)', fontsize=12)
    ax.set_title(f'J/S Ratio vs Platform RCS (Range = {range_km} km)\n'
                 f'Smaller RCS = Better Jamming', fontsize=14)
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight')

    return ax


def create_jamming_summary_figure(jammer: JammerConfig,
                                   radar: RadarConfig,
                                   output_dir: Optional[str] = None) -> plt.Figure:
    """
    Create a comprehensive jamming analysis summary figure.

    Args:
        jammer: JammerConfig instance (includes platform RCS)
        radar: RadarConfig instance
        output_dir: Optional directory to save figure

    Returns:
        Matplotlib figure
    """
    analyzer = JammingAnalyzer(jammer, radar)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Antenna pattern
    plot_antenna_pattern(jammer, ax=axes[0, 0])

    # Plot 2: J/S vs RCS (shows platform RCS effect)
    plot_js_vs_rcs(analyzer, range_km=50.0, ax=axes[0, 1])

    # Plot 3: J/S vs range
    plot_js_vs_range(analyzer, ax=axes[1, 0])

    # Plot 4: J/S heatmap
    plot_js_heatmap(analyzer, ax=axes[1, 1])

    # Title
    fig.suptitle(f'Self-Protect Jamming Analysis\n'
                 f'Jammer: {jammer.input_power_dbm} dBm, {jammer.antenna_gain_dbi} dBi, '
                 f'{jammer.beamwidth_deg}° BW | '
                 f'Platform RCS: {jammer.platform_rcs_m2} m² | '
                 f'Radar: {radar.power_dbw} dBW, {radar.antenna_gain_dbi} dBi',
                 fontsize=14, fontweight='bold')

    plt.tight_layout()

    if output_dir:
        output_path = Path(output_dir) / 'jamming_summary.png'
        plt.savefig(output_path, dpi=150, bbox_inches='tight')

    return fig


if __name__ == "__main__":
    # Demo visualization
    from .core import JammerConfig, RadarConfig

    jammer = JammerConfig(
        input_power_dbm=50,
        antenna_gain_dbi=20,
        beamwidth_deg=30,
        pattern_type='gaussian',
        frequency_ghz=6.0,
        platform_rcs_m2=2.0
    )

    radar = RadarConfig(
        power_dbw=60,
        antenna_gain_dbi=35,
        frequency_ghz=6.0
    )

    fig = create_jamming_summary_figure(jammer, radar)
    plt.show()
