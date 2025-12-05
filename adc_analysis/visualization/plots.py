"""
ADC Visualization Functions

Plotting utilities for ADC analysis results.
"""

from typing import List, Dict, Optional
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ..core.measurement import MeasurementResult
from ..core.sensitivity import SensitivityResult
from ..core.saturation import SaturationResult


# =============================================================================
# PLOT STYLE CONFIGURATION
# =============================================================================

COLORS = {
    'primary': '#3498db',
    'secondary': '#2ecc71',
    'accent': '#e74c3c',
    'warning': '#f39c12',
    'neutral': '#95a5a6',
    'danger': '#c0392b',
    'safe': '#27ae60'
}


def _setup_style():
    """Configure matplotlib style."""
    plt.style.use('seaborn-v0_8-whitegrid')


# =============================================================================
# MEASUREMENT ACCURACY PLOTS
# =============================================================================

def plot_measurement_summary(result: MeasurementResult,
                             config_params: Dict = None) -> Figure:
    """
    Plot measurement accuracy summary.

    Args:
        result: MeasurementResult from analyzer.
        config_params: Optional dict with ENOB, SFDR for display.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    # Plot 1: Phase noise contributors
    ax1 = axes[0, 0]
    contributors = [
        result.phase.phase_quantization_deg,
        result.phase.phase_thermal_deg,
        result.phase.phase_jitter_deg,
        result.phase.phase_accuracy_deg
    ]
    labels = ['Quantization', 'Thermal', 'Jitter', 'Total (RSS)']
    colors = [COLORS['primary'], COLORS['secondary'],
              COLORS['warning'], COLORS['accent']]
    ax1.bar(labels, contributors, color=colors, edgecolor='black')
    ax1.set_ylabel('Phase Error (degrees RMS)')
    ax1.set_title('Phase Noise Contributors')
    ax1.tick_params(axis='x', rotation=45)

    # Plot 2: Pulse Width Accuracy
    ax2 = axes[0, 1]
    pw_labels = [f'{pw:.1f}' for pw in result.timing.pulse_widths_us]
    ax2.barh(pw_labels, result.timing.pw_accuracies_ns,
             color=COLORS['primary'], edgecolor='black')
    ax2.set_xlabel('PW Accuracy (ns)')
    ax2.set_ylabel('Pulse Width (us)')
    ax2.set_title('Pulse Width Measurement Accuracy')

    # Plot 3: Timing breakdown
    ax3 = axes[0, 2]
    timing_vals = [
        result.timing.time_resolution_ns,
        result.timing.toa_accuracy_ns,
        result.timing.pri_accuracy_ns
    ]
    timing_labels = ['Resolution', 'TOA Accuracy', 'PRI Accuracy']
    ax3.bar(timing_labels, timing_vals, color=COLORS['secondary'], edgecolor='black')
    ax3.set_ylabel('Time (ns)')
    ax3.set_title('Timing Measurements')
    ax3.tick_params(axis='x', rotation=45)

    # Plot 4: FFT Resolution vs Length
    ax4 = axes[1, 0]
    fft_lengths = list(result.frequency.fft_accuracies_hz.keys())
    fft_res = result.frequency.fft_resolutions_hz
    ax4.semilogx(fft_lengths, fft_res, 'bo-', linewidth=2, markersize=8)
    ax4.set_xlabel('FFT Length')
    ax4.set_ylabel('Frequency Resolution (Hz)')
    ax4.set_title('FFT Frequency Resolution')
    ax4.grid(True, alpha=0.3)

    # Plot 5: TOA contributors
    ax5 = axes[1, 1]
    toa_vals = [
        result.timing.toa_snr_limited_ns,
        result.timing.toa_jitter_limited_ns,
        result.timing.toa_accuracy_ns
    ]
    toa_labels = ['SNR-Limited', 'Jitter-Limited', 'Total']
    ax5.bar(toa_labels, toa_vals, color=[COLORS['primary'],
            COLORS['warning'], COLORS['accent']], edgecolor='black')
    ax5.set_ylabel('TOA Accuracy (ns)')
    ax5.set_title('TOA Accuracy Contributors')
    ax5.tick_params(axis='x', rotation=45)

    # Plot 6: Summary text
    ax6 = axes[1, 2]
    ax6.axis('off')
    summary_text = [
        'MEASUREMENT SUMMARY',
        '',
        f'SNR: {result.snr.snr_effective_db:.1f} dB',
        f'Dynamic Range: {result.amplitude.dynamic_range_db:.1f} dB',
        f'SFDR: {result.amplitude.sfdr_db:.1f} dBc',
        '',
        'KEY ACCURACIES:',
        f'TOA: {result.timing.toa_accuracy_ns:.2f} ns',
        f'Freq (IFM): {result.frequency.ifm_accuracy_hz:.0f} Hz',
        f'Phase: {result.phase.phase_accuracy_deg:.2f} deg',
        f'AOA: {result.phase.aoa_accuracy_deg:.2f} deg',
    ]
    ax6.text(0.1, 0.5, '\n'.join(summary_text), fontsize=11,
             fontfamily='monospace', verticalalignment='center',
             transform=ax6.transAxes)

    fig.suptitle('ADC Measurement Accuracy Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


def plot_snr_vs_input(adc_fullscale_dbm: float, enob: float,
                      operating_point_dbm: float = -30) -> Figure:
    """
    Plot SNR vs input level.

    Args:
        adc_fullscale_dbm: ADC full-scale input (dBm).
        enob: Effective number of bits.
        operating_point_dbm: Current operating point to mark.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, ax = plt.subplots(figsize=(10, 6))

    # Calculate SNR curve
    snr_ideal = 6.02 * enob + 1.76
    input_levels = np.linspace(-60, adc_fullscale_dbm, 100)

    snr_vs_input = np.zeros_like(input_levels)
    for i, pin in enumerate(input_levels):
        backoff = adc_fullscale_dbm - pin
        if backoff > 0:
            snr_vs_input[i] = max(0, snr_ideal - backoff)
        else:
            snr_vs_input[i] = snr_ideal  # Clipped

    ax.plot(input_levels, snr_vs_input, 'b-', linewidth=2, label='SNR Curve')

    # Mark operating point
    op_backoff = adc_fullscale_dbm - operating_point_dbm
    op_snr = max(0, snr_ideal - op_backoff) if op_backoff > 0 else snr_ideal
    ax.plot(operating_point_dbm, op_snr, 'ro', markersize=10,
            label=f'Operating Point ({operating_point_dbm:.0f} dBm)')

    ax.set_xlabel('Input Signal Level (dBm)')
    ax.set_ylabel('SNR (dB)')
    ax.set_title('SNR vs Input Level')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig


# =============================================================================
# SENSITIVITY PLOTS
# =============================================================================

def plot_sensitivity_comparison(result: SensitivityResult) -> Figure:
    """
    Plot sensitivity comparison between LNA configurations.

    Args:
        result: SensitivityResult from analyzer.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Get unique gain and NF values
    gain_vals = sorted(set(r.gain_db for r in result.lna_results))
    nf_vals = sorted(set(r.nf_db for r in result.lna_results))

    # Plot 1: MDS vs LNA Gain for different NF values
    ax1 = axes[0, 0]
    for nf in nf_vals:
        results = [r for r in result.lna_results if r.nf_db == nf]
        gains = [r.gain_db for r in results]
        mds = [r.mds_dbm for r in results]
        ax1.plot(gains, mds, 'o-', linewidth=2, label=f'NF = {nf:.1f} dB')

    ax1.axhline(y=result.passive.mds_dbm, color='r', linestyle='--',
                linewidth=2, label='Passive Only')
    ax1.set_xlabel('LNA Gain (dB)')
    ax1.set_ylabel('MDS (dBm)')
    ax1.set_title('Minimum Detectable Signal vs LNA Gain')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # Plot 2: System NF vs LNA Gain
    ax2 = axes[0, 1]
    for nf in nf_vals:
        results = [r for r in result.lna_results if r.nf_db == nf]
        gains = [r.gain_db for r in results]
        sys_nf = [r.system_nf_db for r in results]
        ax2.plot(gains, sys_nf, 'o-', linewidth=2, label=f'NF = {nf:.1f} dB')

    ax2.axhline(y=result.passive.system_nf_db, color='r', linestyle='--',
                linewidth=2, label='Passive Only')
    ax2.set_xlabel('LNA Gain (dB)')
    ax2.set_ylabel('System NF (dB)')
    ax2.set_title('System Noise Figure vs LNA Gain')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)

    # Plot 3: Improvement vs LNA Gain
    ax3 = axes[1, 0]
    for nf in nf_vals:
        results = [r for r in result.lna_results if r.nf_db == nf]
        gains = [r.gain_db for r in results]
        improvement = [r.improvement_db for r in results]
        ax3.plot(gains, improvement, 'o-', linewidth=2, label=f'NF = {nf:.1f} dB')

    ax3.axhline(y=0, color='r', linestyle='--', linewidth=2)
    ax3.set_xlabel('LNA Gain (dB)')
    ax3.set_ylabel('Sensitivity Improvement (dB)')
    ax3.set_title('Improvement Over Passive-Only')
    ax3.legend(loc='best')
    ax3.grid(True, alpha=0.3)

    # Plot 4: Summary
    ax4 = axes[1, 1]
    ax4.axis('off')
    summary = [
        'SENSITIVITY SUMMARY',
        '',
        'Passive-Only:',
        f'  MDS: {result.passive.mds_dbm:.2f} dBm',
        f'  System NF: {result.passive.system_nf_db:.2f} dB',
        f'  Dynamic Range: {result.passive.dynamic_range_db:.1f} dB',
        '',
        'Optimal LNA:',
        f'  Gain: {result.optimal_lna.gain_db:.1f} dB',
        f'  NF: {result.optimal_lna.nf_db:.1f} dB',
        f'  MDS: {result.optimal_lna.mds_dbm:.2f} dBm',
        f'  Improvement: {result.optimal_lna.improvement_db:.2f} dB',
    ]
    ax4.text(0.1, 0.5, '\n'.join(summary), fontsize=11,
             fontfamily='monospace', verticalalignment='center',
             transform=ax4.transAxes)

    fig.suptitle('ADC Receiver Sensitivity Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


def plot_lna_heatmap(result: SensitivityResult) -> Figure:
    """
    Plot heatmap of sensitivity improvement vs LNA parameters.

    Args:
        result: SensitivityResult from analyzer.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, ax = plt.subplots(figsize=(10, 8))

    gain_vals = sorted(set(r.gain_db for r in result.lna_results))
    nf_vals = sorted(set(r.nf_db for r in result.lna_results))

    # Build improvement matrix
    improvement_matrix = np.zeros((len(nf_vals), len(gain_vals)))
    for i, nf in enumerate(nf_vals):
        for j, gain in enumerate(gain_vals):
            matching = [r for r in result.lna_results
                       if r.nf_db == nf and r.gain_db == gain]
            if matching:
                improvement_matrix[i, j] = matching[0].improvement_db

    im = ax.imshow(improvement_matrix, cmap='RdYlGn', aspect='auto',
                   origin='lower')
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Sensitivity Improvement (dB)')

    ax.set_xticks(range(len(gain_vals)))
    ax.set_xticklabels([f'{g:.0f}' for g in gain_vals])
    ax.set_yticks(range(len(nf_vals)))
    ax.set_yticklabels([f'{nf:.1f}' for nf in nf_vals])

    ax.set_xlabel('LNA Gain (dB)')
    ax.set_ylabel('LNA NF (dB)')
    ax.set_title('Sensitivity Improvement Heatmap')

    # Mark optimal
    opt_gain_idx = gain_vals.index(result.optimal_lna.gain_db)
    opt_nf_idx = nf_vals.index(result.optimal_lna.nf_db)
    ax.plot(opt_gain_idx, opt_nf_idx, 'k*', markersize=20,
            markeredgecolor='white', markeredgewidth=2)

    plt.tight_layout()
    return fig


# =============================================================================
# SATURATION PLOTS
# =============================================================================

def plot_saturation_analysis(result: SaturationResult) -> Figure:
    """
    Plot power levels vs distance for saturation analysis.

    Args:
        result: SaturationResult from analyzer.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Power at ADC vs Distance
    ax1 = axes[0, 0]
    for pl in result.power_levels:
        ax1.plot(pl.distances_miles, pl.power_at_adc_dbm, linewidth=2,
                label=f'EIRP = {pl.eirp_dbm:.0f} dBm')

    ax1.axhline(y=result.adc_fullscale_dbm, color='r', linestyle='--',
                linewidth=2, label='ADC Full-Scale')
    ax1.axhline(y=result.adc_damage_dbm, color='r', linestyle='-',
                linewidth=3, label='ADC Damage Level')
    ax1.set_xlabel('Distance (miles)')
    ax1.set_ylabel('Power at ADC (dBm)')
    ax1.set_title('Power at ADC Input vs Distance')
    ax1.legend(loc='best', fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Power at LNA Output vs Distance
    ax2 = axes[0, 1]
    for pl in result.power_levels:
        ax2.plot(pl.distances_miles, pl.power_at_lna_output_dbm, linewidth=2,
                label=f'EIRP = {pl.eirp_dbm:.0f} dBm')

    ax2.axhline(y=result.lna_p1db_dbm, color='r', linestyle='--',
                linewidth=2, label='LNA P1dB')
    ax2.set_xlabel('Distance (miles)')
    ax2.set_ylabel('Power at LNA Output (dBm)')
    ax2.set_title('Power at LNA Output vs Distance')
    ax2.legend(loc='best', fontsize=8)
    ax2.grid(True, alpha=0.3)

    # Plot 3: Power at Antenna vs Distance
    ax3 = axes[1, 0]
    for pl in result.power_levels:
        ax3.plot(pl.distances_miles, pl.power_at_antenna_dbm, linewidth=2,
                label=f'EIRP = {pl.eirp_dbm:.0f} dBm')

    ax3.set_xlabel('Distance (miles)')
    ax3.set_ylabel('Power at RX Antenna (dBm)')
    ax3.set_title('Received Power at Antenna vs Distance')
    ax3.legend(loc='best', fontsize=8)
    ax3.grid(True, alpha=0.3)

    # Plot 4: Critical distances table
    ax4 = axes[1, 1]
    ax4.axis('off')

    table_data = []
    for cd in result.critical_distances:
        lna_str = f'{cd.lna_compression_miles:.1f}' if cd.lna_compression_miles else 'N/A'
        sat_str = f'{cd.adc_saturation_miles:.1f}' if cd.adc_saturation_miles else 'N/A'
        dmg_str = f'{cd.adc_damage_miles:.1f}' if cd.adc_damage_miles else 'N/A'
        table_data.append([f'{cd.eirp_dbm:.0f}', lna_str, sat_str, dmg_str, cd.status])

    table = ax4.table(
        cellText=table_data,
        colLabels=['EIRP\n(dBm)', 'LNA Comp\n(mi)', 'ADC Sat\n(mi)',
                   'ADC Dmg\n(mi)', 'Status'],
        loc='center',
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    ax4.set_title('Critical Distances Summary')

    fig.suptitle('ADC Saturation and Damage Analysis', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


def plot_safe_operating_zones(result: SaturationResult,
                              eirp_dbm: float = None) -> Figure:
    """
    Plot safe operating zones for a specific EIRP.

    Args:
        result: SaturationResult from analyzer.
        eirp_dbm: EIRP to plot. Uses highest if None.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    # Find the power levels for specified EIRP
    if eirp_dbm is None:
        eirp_dbm = max(pl.eirp_dbm for pl in result.power_levels)

    pl = next(p for p in result.power_levels if p.eirp_dbm == eirp_dbm)
    cd = next(c for c in result.critical_distances if c.eirp_dbm == eirp_dbm)

    fig, ax = plt.subplots(figsize=(12, 8))

    distances = pl.distances_miles
    y_min = pl.power_at_adc_dbm.min() - 5
    y_max = max(result.adc_damage_dbm + 10, pl.power_at_adc_dbm.max() + 5)

    # Fill zones
    if cd.adc_damage_miles:
        ax.axvspan(distances.min(), cd.adc_damage_miles,
                   color=COLORS['danger'], alpha=0.3, label='Damage Risk')

    if cd.adc_saturation_miles:
        start = cd.adc_damage_miles if cd.adc_damage_miles else distances.min()
        ax.axvspan(start, cd.adc_saturation_miles,
                   color=COLORS['warning'], alpha=0.3, label='Saturation Zone')

    safe_start = cd.adc_saturation_miles if cd.adc_saturation_miles else distances.min()
    ax.axvspan(safe_start, distances.max(),
               color=COLORS['safe'], alpha=0.2, label='Safe Operation')

    # Plot power curve
    ax.plot(distances, pl.power_at_adc_dbm, 'b-', linewidth=3,
            label=f'Power at ADC (EIRP={eirp_dbm:.0f} dBm)')

    # Reference lines
    ax.axhline(y=result.adc_fullscale_dbm, color='r', linestyle='--',
               linewidth=2, label='Full-Scale')
    ax.axhline(y=result.adc_damage_dbm, color='r', linestyle='-',
               linewidth=2, label='Damage Level')

    # Attenuator recommendation
    if result.attenuator_recommendation.is_needed:
        atten = result.attenuator_recommendation.required_attenuation_db
        attenuated = pl.power_at_adc_dbm - atten
        ax.plot(distances, attenuated, 'g--', linewidth=2,
                label=f'With {atten:.0f} dB Attenuator')

    ax.set_xlabel('Distance (miles)')
    ax.set_ylabel('Power (dBm)')
    ax.set_title(f'Safe Operating Zones (EIRP = {eirp_dbm:.0f} dBm)')
    ax.legend(loc='upper right')
    ax.set_xlim(distances.min(), distances.max())
    ax.set_ylim(y_min, y_max)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    return fig
