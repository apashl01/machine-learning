"""
RF Chain Visualization Functions

Plotting utilities for RF chain analysis results.
"""

from typing import List, Dict, Optional
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

# Note: The plot functions in this module are not currently used.
# RF chain plots are generated manually in generate_design_review.py


# =============================================================================
# PLOT STYLE CONFIGURATION
# =============================================================================

COLORS = {
    'gain': '#2ecc71',      # Green
    'nf': '#e74c3c',        # Red
    'sensitivity': '#3498db', # Blue
    'power': '#9b59b6',     # Purple
    'compression': '#e67e22', # Orange
    'grid': '#bdc3c7'
}


def _setup_style():
    """Configure matplotlib style."""
    plt.style.use('seaborn-v0_8-whitegrid')


# =============================================================================
# CASCADE BREAKDOWN PLOTS
# =============================================================================

def plot_cascade_breakdown(result: CascadeResult,
                           title: Optional[str] = None) -> Figure:
    """
    Plot component-by-component cascade breakdown.

    Shows individual and cumulative gain/NF for each component.

    Args:
        result: CascadeResult from analyzer.
        title: Optional custom title.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    names = result.component_names
    x = np.arange(len(names))
    width = 0.35

    # Component gains
    ax1 = axes[0, 0]
    colors = [COLORS['gain'] if g >= 0 else COLORS['nf']
              for g in result.component_gains]
    ax1.bar(x, result.component_gains, width, color=colors, edgecolor='black')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.set_xlabel('Component')
    ax1.set_ylabel('Gain (dB)')
    ax1.set_title('Individual Component Gain/Loss')
    ax1.set_xticks(x)
    ax1.set_xticklabels(names, rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)

    # Component noise figures
    ax2 = axes[0, 1]
    ax2.bar(x, result.component_nfs, width, color=COLORS['nf'],
            edgecolor='black', alpha=0.8)
    ax2.set_xlabel('Component')
    ax2.set_ylabel('Noise Figure (dB)')
    ax2.set_title('Individual Component Noise Figure')
    ax2.set_xticks(x)
    ax2.set_xticklabels(names, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)

    # Cumulative gain
    ax3 = axes[1, 0]
    ax3.plot(x, result.cumulative_gains, 'o-', color=COLORS['gain'],
             linewidth=2, markersize=8, label='Cumulative Gain')
    ax3.fill_between(x, 0, result.cumulative_gains, alpha=0.3,
                     color=COLORS['gain'])
    ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax3.set_xlabel('Component')
    ax3.set_ylabel('Cumulative Gain (dB)')
    ax3.set_title('Cumulative Gain Through Chain')
    ax3.set_xticks(x)
    ax3.set_xticklabels(names, rotation=45, ha='right')
    ax3.grid(True, alpha=0.3)
    ax3.legend()

    # Cumulative noise figure
    ax4 = axes[1, 1]
    ax4.plot(x, result.cumulative_nfs, 's-', color=COLORS['nf'],
             linewidth=2, markersize=8, label='Cumulative NF')
    ax4.fill_between(x, 0, result.cumulative_nfs, alpha=0.3,
                     color=COLORS['nf'])
    ax4.set_xlabel('Component')
    ax4.set_ylabel('Cumulative Noise Figure (dB)')
    ax4.set_title('Cumulative Noise Figure (Friis)')
    ax4.set_xticks(x)
    ax4.set_xticklabels(names, rotation=45, ha='right')
    ax4.grid(True, alpha=0.3)
    ax4.legend()

    if title:
        fig.suptitle(title, fontsize=14, fontweight='bold')
    else:
        fig.suptitle(f'Cascade Breakdown @ {result.freq_ghz:.2f} GHz',
                     fontsize=14, fontweight='bold')

    plt.tight_layout()
    return fig


# =============================================================================
# FREQUENCY RESPONSE PLOTS
# =============================================================================

def plot_frequency_response(analysis: FrequencyAnalysis,
                            chain_name: str = "RF Chain") -> Figure:
    """
    Plot gain, NF, and sensitivity vs frequency.

    Args:
        analysis: FrequencyAnalysis from analyzer.
        chain_name: Name for plot title.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    freq = analysis.frequencies_ghz

    # Gain vs frequency
    ax1 = axes[0, 0]
    ax1.plot(freq, analysis.gains_db, '-', color=COLORS['gain'],
             linewidth=2, label='Total Gain')
    ax1.set_xlabel('Frequency (GHz)')
    ax1.set_ylabel('Gain (dB)')
    ax1.set_title('System Gain vs Frequency')
    ax1.grid(True, alpha=0.3)
    ax1.legend()

    # Noise figure vs frequency
    ax2 = axes[0, 1]
    ax2.plot(freq, analysis.noise_figures_db, '-', color=COLORS['nf'],
             linewidth=2, label='System NF')
    ax2.set_xlabel('Frequency (GHz)')
    ax2.set_ylabel('Noise Figure (dB)')
    ax2.set_title('System Noise Figure vs Frequency')
    ax2.grid(True, alpha=0.3)
    ax2.legend()

    # Sensitivity vs frequency
    ax3 = axes[1, 0]
    ax3.plot(freq, analysis.sensitivities_dbm, '-', color=COLORS['sensitivity'],
             linewidth=2, label='Sensitivity')
    ax3.set_xlabel('Frequency (GHz)')
    ax3.set_ylabel('Sensitivity (dBm)')
    ax3.set_title('System Sensitivity vs Frequency')
    ax3.grid(True, alpha=0.3)
    ax3.legend()
    ax3.invert_yaxis()  # More negative = better sensitivity

    # Dynamic range vs frequency
    ax4 = axes[1, 1]
    ax4.plot(freq, analysis.dynamic_ranges_db, '-', color=COLORS['power'],
             linewidth=2, label='Dynamic Range')
    ax4.set_xlabel('Frequency (GHz)')
    ax4.set_ylabel('Dynamic Range (dB)')
    ax4.set_title('System Dynamic Range vs Frequency')
    ax4.grid(True, alpha=0.3)
    ax4.legend()

    fig.suptitle(f'{chain_name} Frequency Response', fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


# =============================================================================
# POWER TRACKING PLOTS
# =============================================================================

def plot_power_tracking(power_points: List[PowerPoint],
                        input_power_dbm: float,
                        chain_name: str = "RF Chain") -> Figure:
    """
    Plot power levels through the chain.

    Args:
        power_points: List of PowerPoint from track_power().
        input_power_dbm: System input power.
        chain_name: Name for plot title.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, ax = plt.subplots(figsize=(12, 6))

    names = [p.component_name for p in power_points]
    input_powers = [p.input_power_dbm for p in power_points]
    output_powers = [p.output_power_dbm for p in power_points]

    x = np.arange(len(names) + 1)

    # Create power trajectory
    power_trace = [input_power_dbm] + output_powers

    # Plot power trace
    ax.plot(x, power_trace, 'o-', color=COLORS['power'],
            linewidth=2, markersize=10, label='Signal Power')

    # Mark compressed stages
    for i, p in enumerate(power_points):
        if p.is_compressed:
            ax.plot(i + 1, p.output_power_dbm, 's', color=COLORS['compression'],
                    markersize=15, markeredgecolor='black', markeredgewidth=2,
                    label='Compression' if i == 0 else '')

    # Add component names
    labels = ['Input'] + names
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha='right')

    ax.set_xlabel('Stage')
    ax.set_ylabel('Power Level (dBm)')
    ax.set_title(f'{chain_name} Power Tracking (Input: {input_power_dbm:.1f} dBm)')
    ax.grid(True, alpha=0.3)
    ax.legend()

    plt.tight_layout()
    return fig


# =============================================================================
# CHAIN COMPARISON PLOTS
# =============================================================================

def plot_chain_comparison(results: Dict[str, CascadeResult],
                          freq_ghz: float) -> Figure:
    """
    Compare multiple chains side-by-side.

    Args:
        results: Dictionary mapping chain ID to CascadeResult.
        freq_ghz: Frequency used for comparison.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    chain_names = list(results.keys())
    n_chains = len(chain_names)

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    x = np.arange(n_chains)
    width = 0.6

    # Total gain comparison
    ax1 = axes[0, 0]
    gains = [results[c].total_gain_db for c in chain_names]
    colors = [COLORS['gain'] if g >= 0 else COLORS['nf'] for g in gains]
    ax1.bar(x, gains, width, color=colors, edgecolor='black')
    ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
    ax1.set_xlabel('Chain')
    ax1.set_ylabel('Total Gain (dB)')
    ax1.set_title('Total Gain Comparison')
    ax1.set_xticks(x)
    ax1.set_xticklabels(chain_names, rotation=45, ha='right')
    ax1.grid(True, alpha=0.3)

    # Noise figure comparison
    ax2 = axes[0, 1]
    nfs = [results[c].total_nf_db for c in chain_names]
    ax2.bar(x, nfs, width, color=COLORS['nf'], edgecolor='black')
    ax2.set_xlabel('Chain')
    ax2.set_ylabel('Noise Figure (dB)')
    ax2.set_title('Noise Figure Comparison')
    ax2.set_xticks(x)
    ax2.set_xticklabels(chain_names, rotation=45, ha='right')
    ax2.grid(True, alpha=0.3)

    # Sensitivity comparison
    ax3 = axes[1, 0]
    sens = [results[c].sensitivity_dbm for c in chain_names]
    ax3.bar(x, sens, width, color=COLORS['sensitivity'], edgecolor='black')
    ax3.set_xlabel('Chain')
    ax3.set_ylabel('Sensitivity (dBm)')
    ax3.set_title('Sensitivity Comparison (lower is better)')
    ax3.set_xticks(x)
    ax3.set_xticklabels(chain_names, rotation=45, ha='right')
    ax3.grid(True, alpha=0.3)

    # Dynamic range comparison
    ax4 = axes[1, 1]
    dr = [results[c].dynamic_range_db for c in chain_names]
    ax4.bar(x, dr, width, color=COLORS['power'], edgecolor='black')
    ax4.set_xlabel('Chain')
    ax4.set_ylabel('Dynamic Range (dB)')
    ax4.set_title('Dynamic Range Comparison')
    ax4.set_xticks(x)
    ax4.set_xticklabels(chain_names, rotation=45, ha='right')
    ax4.grid(True, alpha=0.3)

    fig.suptitle(f'Chain Comparison @ {freq_ghz:.2f} GHz',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    return fig


# =============================================================================
# DYNAMIC RANGE VISUALIZATION
# =============================================================================

def plot_dynamic_range(result: CascadeResult, chain_name: str = "RF Chain") -> Figure:
    """
    Visualize dynamic range as a level diagram.

    Args:
        result: CascadeResult from analyzer.
        chain_name: Name for plot title.

    Returns:
        Matplotlib Figure object.
    """
    _setup_style()

    fig, ax = plt.subplots(figsize=(8, 10))

    # Create vertical bar showing dynamic range
    min_power = result.min_input_dbm - 20
    max_power = result.max_input_dbm + 20

    # Background
    ax.axhspan(min_power, max_power, color='#ecf0f1', alpha=0.5)

    # Noise floor
    ax.axhline(y=result.thermal_noise_floor_dbm, color='gray',
               linestyle='--', linewidth=2, label='Thermal Noise Floor')

    # Sensitivity (MDS)
    ax.axhline(y=result.sensitivity_dbm, color=COLORS['sensitivity'],
               linestyle='-', linewidth=3, label=f'Sensitivity: {result.sensitivity_dbm:.1f} dBm')

    # Dynamic range band
    ax.axhspan(result.min_input_dbm, result.max_input_dbm,
               color=COLORS['gain'], alpha=0.3, label='Operating Range')

    # Max input (P1dB)
    ax.axhline(y=result.max_input_dbm, color=COLORS['compression'],
               linestyle='-', linewidth=3, label=f'Max Input: {result.max_input_dbm:.1f} dBm')

    # Add annotations
    mid_range = (result.min_input_dbm + result.max_input_dbm) / 2
    ax.annotate(f'Dynamic Range\n{result.dynamic_range_db:.1f} dB',
                xy=(0.5, mid_range), fontsize=14, fontweight='bold',
                ha='center', va='center',
                bbox=dict(boxstyle='round', facecolor='white', edgecolor='black'))

    ax.set_xlim(-1, 1)
    ax.set_ylim(min_power, max_power)
    ax.set_ylabel('Power Level (dBm)')
    ax.set_title(f'{chain_name} Dynamic Range @ {result.freq_ghz:.2f} GHz')

    # Remove x-axis
    ax.set_xticks([])

    ax.legend(loc='upper right')
    ax.grid(True, axis='y', alpha=0.3)

    plt.tight_layout()
    return fig
