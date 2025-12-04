"""
Visualization Module for ESM Detection Analysis

Provides plotting functions for ESM detection range analysis,
dwell scheduling, and Monte Carlo results.

Matches output style of MATLAB radar_range_analysis.m
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import LinearSegmentedColormap
from typing import List, Dict, Optional, Tuple
from esm_detection import (
    RadarParameters, ReceiverParameters, ESMDetector,
    compare_to_radar_range, monte_carlo_analysis
)
from dwell_scheduler import (
    DwellScheduler, DwellSchedule, EmitterModel, ScanPosition
)


# Set default style
plt.style.use('seaborn-v0_8-whitegrid')


def plot_detection_range_comparison(comparison_results: List[Dict],
                                     target_labels: Optional[List[str]] = None,
                                     figsize: Tuple[int, int] = (14, 6)) -> plt.Figure:
    """
    Plot comparison of radar vs ESM detection ranges.

    Similar to MATLAB subplot comparing ranges by target type.

    Args:
        comparison_results: List of dicts from compare_to_radar_range()
        target_labels: Optional list of target names
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    fig, axes = plt.subplots(1, 2, figsize=figsize)

    n_targets = len(comparison_results)

    if target_labels is None:
        target_labels = [f"Target {i+1}" for i in range(n_targets)]

    # Plot 1: Range comparison bar chart
    ax1 = axes[0]
    x = np.arange(n_targets)
    width = 0.35

    radar_ranges = [r['radar_detection_range_km'] for r in comparison_results]
    esm_ranges = [r['esm_detection_range_km'] for r in comparison_results]

    bars1 = ax1.bar(x - width/2, radar_ranges, width, label='Radar Detection Range',
                    color='#CC6666', edgecolor='black')
    bars2 = ax1.bar(x + width/2, esm_ranges, width, label='ESM Detection Range',
                    color='#66CC66', edgecolor='black')

    ax1.set_xlabel('Target Type')
    ax1.set_ylabel('Detection Range (km)')
    ax1.set_title('Radar vs ESM Detection Ranges', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(target_labels, rotation=45, ha='right')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Add value labels
    for bar in bars1:
        height = bar.get_height()
        ax1.annotate(f'{height:.0f}',
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points",
                     ha='center', va='bottom', fontsize=8)

    for bar in bars2:
        height = bar.get_height()
        ax1.annotate(f'{height:.0f}',
                     xy=(bar.get_x() + bar.get_width() / 2, height),
                     xytext=(0, 3), textcoords="offset points",
                     ha='center', va='bottom', fontsize=8)

    # Plot 2: Range multiplier
    ax2 = axes[1]
    multipliers = [r['range_multiplier'] for r in comparison_results]
    bars = ax2.barh(target_labels, multipliers, color='#6699CC', edgecolor='black')

    ax2.set_xlabel('Range Multiplier (ESM/Radar)')
    ax2.set_title('ESM Advantage: Range Multiplier', fontweight='bold')
    ax2.axvline(x=1, color='red', linestyle='--', linewidth=2, label='Equal Range')
    ax2.grid(True, alpha=0.3)

    # Add value labels
    for bar, mult in zip(bars, multipliers):
        ax2.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height()/2,
                f'{mult:.1f}x', va='center', fontsize=9)

    plt.tight_layout()
    fig.suptitle('ESM vs Radar Detection Analysis', fontsize=14, fontweight='bold', y=1.02)

    return fig


def plot_sensitivity_sweep(receiver: ReceiverParameters,
                            radar: RadarParameters,
                            figsize: Tuple[int, int] = (14, 10)) -> plt.Figure:
    """
    Plot sensitivity analysis: detection range vs various parameters.

    Similar to MATLAB radar_range_analysis.m subplots.

    Args:
        receiver: ReceiverParameters
        radar: RadarParameters
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    from esm_detection import sensitivity_analysis

    fig, axes = plt.subplots(2, 3, figsize=figsize)

    detector = ESMDetector(receiver)
    baseline_range = detector.calculate_detection_range(radar)

    # Sweep 1: Noise Figure
    nf_range = np.linspace(1, 25, 50)
    nf_results = sensitivity_analysis(receiver, radar, 'noise_figure_dB', nf_range)
    ax = axes[0, 0]
    ax.plot(nf_results['parameter_values'], nf_results['detection_range_km'],
            'b-', linewidth=2)
    ax.axhline(baseline_range, color='r', linestyle='--', label='Baseline')
    ax.axvline(receiver.noise_figure_dB, color='g', linestyle=':', label='Current')
    ax.set_xlabel('Noise Figure (dB)')
    ax.set_ylabel('Detection Range (km)')
    ax.set_title('Range vs Noise Figure', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Sweep 2: Bandwidth
    bw_range = np.logspace(0, 2, 50)  # 1 to 100 MHz
    bw_results = sensitivity_analysis(receiver, radar, 'bandwidth_MHz', bw_range)
    ax = axes[0, 1]
    ax.semilogx(bw_results['parameter_values'], bw_results['detection_range_km'],
                'g-', linewidth=2)
    ax.axhline(baseline_range, color='r', linestyle='--', label='Baseline')
    ax.axvline(receiver.bandwidth_MHz, color='b', linestyle=':', label='Current')
    ax.set_xlabel('Bandwidth (MHz)')
    ax.set_ylabel('Detection Range (km)')
    ax.set_title('Range vs Bandwidth', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Sweep 3: System Loss
    loss_range = np.linspace(0, 15, 50)
    loss_results = sensitivity_analysis(receiver, radar, 'system_loss_dB', loss_range)
    ax = axes[0, 2]
    ax.plot(loss_results['parameter_values'], loss_results['detection_range_km'],
            'r-', linewidth=2)
    ax.axhline(baseline_range, color='b', linestyle='--', label='Baseline')
    ax.axvline(receiver.system_loss_dB, color='g', linestyle=':', label='Current')
    ax.set_xlabel('System Loss (dB)')
    ax.set_ylabel('Detection Range (km)')
    ax.set_title('Range vs System Loss', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Sweep 4: Antenna Gain
    gain_range = np.linspace(-10, 20, 50)
    gain_results = sensitivity_analysis(receiver, radar, 'antenna_gain_dB', gain_range)
    ax = axes[1, 0]
    ax.plot(gain_results['parameter_values'], gain_results['detection_range_km'],
            'm-', linewidth=2)
    ax.axhline(baseline_range, color='r', linestyle='--', label='Baseline')
    ax.axvline(receiver.antenna_gain_dB, color='g', linestyle=':', label='Current')
    ax.set_xlabel('Antenna Gain (dB)')
    ax.set_ylabel('Detection Range (km)')
    ax.set_title('Range vs Antenna Gain', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Sweep 5: Required SNR
    snr_range = np.linspace(3, 20, 50)
    snr_results = sensitivity_analysis(receiver, radar, 'snr_required_dB', snr_range)
    ax = axes[1, 1]
    ax.plot(snr_results['parameter_values'], snr_results['detection_range_km'],
            'c-', linewidth=2)
    ax.axhline(baseline_range, color='r', linestyle='--', label='Baseline')
    ax.axvline(receiver.snr_required_dB, color='g', linestyle=':', label='Current')
    ax.set_xlabel('Required SNR (dB)')
    ax.set_ylabel('Detection Range (km)')
    ax.set_title('Range vs Required SNR', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Panel 6: Summary text
    ax = axes[1, 2]
    ax.axis('off')

    summary_text = (
        f"ESM RECEIVER SUMMARY\n"
        f"{'='*30}\n\n"
        f"Noise Figure: {receiver.noise_figure_dB:.1f} dB\n"
        f"Bandwidth: {receiver.bandwidth_MHz:.1f} MHz\n"
        f"System Loss: {receiver.system_loss_dB:.1f} dB\n"
        f"Antenna Gain: {receiver.antenna_gain_dB:.1f} dB\n"
        f"Required SNR: {receiver.snr_required_dB:.1f} dB\n\n"
        f"Noise Floor: {receiver.noise_floor_dBm:.1f} dBm\n"
        f"Sensitivity: {receiver.sensitivity_dBm:.1f} dBm\n\n"
        f"{'='*30}\n"
        f"RADAR EMITTER\n\n"
        f"EIRP: {radar.eirp_dBW:.1f} dBW\n"
        f"Frequency: {radar.freq_GHz:.1f} GHz\n\n"
        f"{'='*30}\n"
        f"DETECTION RANGE: {baseline_range:.1f} km"
    )

    ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    fig.suptitle('ESM Detection Sensitivity Analysis', fontsize=14, fontweight='bold', y=1.02)

    return fig


def plot_monte_carlo_results(mc_results: Dict,
                              figsize: Tuple[int, int] = (14, 10)) -> plt.Figure:
    """
    Plot Monte Carlo analysis results.

    Similar to MATLAB radar_range_analysis.m Monte Carlo plots.

    Args:
        mc_results: Results from monte_carlo_analysis()
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    fig, axes = plt.subplots(2, 3, figsize=figsize)

    stats = mc_results['statistics']
    corrs = mc_results['correlations']

    # Plot 1: Histogram of detection ranges
    ax = axes[0, 0]
    ax.hist(mc_results['detection_range_km'], bins=50, color='steelblue',
            edgecolor='black', alpha=0.7)
    ax.axvline(stats['median'], color='r', linestyle='--', linewidth=2,
               label=f"Median: {stats['median']:.0f} km")
    ax.axvline(stats['p5'], color='orange', linestyle=':', linewidth=2,
               label=f"5th %ile: {stats['p5']:.0f} km")
    ax.axvline(stats['p95'], color='green', linestyle=':', linewidth=2,
               label=f"95th %ile: {stats['p95']:.0f} km")
    ax.set_xlabel('Detection Range (km)')
    ax.set_ylabel('Count')
    ax.set_title('Distribution of Detection Ranges', fontweight='bold')
    ax.legend(fontsize=8)
    ax.grid(True, alpha=0.3)

    # Plot 2: Correlation bar chart (sorted)
    ax = axes[0, 1]
    sorted_corrs = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)
    param_names = [c[0].replace('_', '\n') for c in sorted_corrs]
    corr_values = [c[1] for c in sorted_corrs]
    colors = ['green' if c > 0 else 'red' for c in corr_values]

    bars = ax.barh(param_names, corr_values, color=colors, edgecolor='black')
    ax.axvline(0, color='black', linewidth=1)
    ax.set_xlabel('Correlation with Detection Range')
    ax.set_title('Parameter Sensitivity (Correlation)', fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Add impact labels
    for bar, corr in zip(bars, corr_values):
        impact = 'HIGH' if abs(corr) > 0.5 else ('MOD' if abs(corr) > 0.2 else 'LOW')
        ax.text(0.02 if corr < 0 else corr + 0.02,
                bar.get_y() + bar.get_height()/2,
                f'{impact}', va='center', fontsize=8)

    # Plot 3: Statistics summary
    ax = axes[0, 2]
    ax.axis('off')

    n_iter = len(mc_results['detection_range_km'])
    summary_text = (
        f"MONTE CARLO RESULTS\n"
        f"{'='*30}\n\n"
        f"Iterations: {n_iter:,}\n\n"
        f"Detection Range Statistics:\n"
        f"  Mean: {stats['mean']:.1f} km\n"
        f"  Median: {stats['median']:.1f} km\n"
        f"  Std Dev: {stats['std']:.1f} km\n"
        f"  5th %ile: {stats['p5']:.1f} km\n"
        f"  95th %ile: {stats['p95']:.1f} km\n"
        f"  Min: {stats['min']:.1f} km\n"
        f"  Max: {stats['max']:.1f} km\n\n"
        f"{'='*30}\n"
        f"KEY INSIGHTS:\n\n"
        f"One-way propagation (R^2)\n"
        f"gives ESM significant\n"
        f"advantage over radar (R^4)"
    )

    ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightcyan', alpha=0.5))

    # Plots 4-6: Scatter plots for top 3 parameters
    sorted_params = sorted(corrs.items(), key=lambda x: abs(x[1]), reverse=True)[:3]

    for idx, (param, corr) in enumerate(sorted_params):
        ax = axes[1, idx]
        x_data = mc_results['samples'].get(param, np.zeros(len(mc_results['detection_range_km'])))
        y_data = mc_results['detection_range_km']

        ax.scatter(x_data, y_data, alpha=0.3, s=5, c='steelblue')
        ax.set_xlabel(param.replace('_', ' ').title())
        ax.set_ylabel('Detection Range (km)')
        ax.set_title(f'{param} (ρ={corr:.2f})', fontweight='bold')
        ax.grid(True, alpha=0.3)

        # Add trend line
        z = np.polyfit(x_data, y_data, 1)
        p = np.poly1d(z)
        x_line = np.linspace(x_data.min(), x_data.max(), 100)
        ax.plot(x_line, p(x_line), 'r-', linewidth=2, label='Trend')
        ax.legend()

    plt.tight_layout()
    fig.suptitle('Monte Carlo Analysis Results', fontsize=14, fontweight='bold', y=1.02)

    return fig


def plot_dwell_schedule(schedule: DwellSchedule,
                         threats: Optional[List[EmitterModel]] = None,
                         figsize: Tuple[int, int] = (14, 8)) -> plt.Figure:
    """
    Visualize dwell schedule across frequency.

    Args:
        schedule: DwellSchedule to visualize
        threats: Optional list of threats to overlay
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    fig, axes = plt.subplots(2, 2, figsize=figsize)

    positions = schedule.positions

    # Extract data
    freqs = [p.center_freq_GHz for p in positions]
    dwells = [p.dwell_time_ms for p in positions]
    priorities = [p.priority for p in positions]

    # Plot 1: Dwell time vs frequency (bar chart)
    ax = axes[0, 0]
    bars = ax.bar(freqs, dwells, width=positions[0].bandwidth_MHz/1000 * 0.9,
                  color='steelblue', edgecolor='black', alpha=0.7)

    # Overlay threats if provided
    if threats:
        for threat in threats:
            ax.axvline(threat.radar.freq_GHz, color='red', linestyle='--',
                      linewidth=2, alpha=0.7)

    ax.set_xlabel('Frequency (GHz)')
    ax.set_ylabel('Dwell Time (ms)')
    ax.set_title(f'Dwell Time Distribution ({schedule.strategy.value})', fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Plot 2: Cumulative scan timeline
    ax = axes[0, 1]
    times = [0]
    for p in positions:
        times.append(times[-1] + p.dwell_time_ms)

    for i, p in enumerate(positions):
        ax.barh(p.center_freq_GHz, p.dwell_time_ms, left=times[i],
                height=p.bandwidth_MHz/1000 * 0.9, color=plt.cm.viridis(i/len(positions)),
                edgecolor='none', alpha=0.7)

    ax.set_xlabel('Time (ms)')
    ax.set_ylabel('Frequency (GHz)')
    ax.set_title('Scan Timeline', fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Plot 3: Priority distribution
    ax = axes[1, 0]
    ax.fill_between(freqs, priorities, alpha=0.5, color='green')
    ax.plot(freqs, priorities, 'g-', linewidth=2)
    ax.set_xlabel('Frequency (GHz)')
    ax.set_ylabel('Priority Weight')
    ax.set_title('Channel Priority', fontweight='bold')
    ax.grid(True, alpha=0.3)

    # Plot 4: Schedule summary
    ax = axes[1, 1]
    ax.axis('off')

    summary_text = (
        f"DWELL SCHEDULE SUMMARY\n"
        f"{'='*35}\n\n"
        f"Strategy: {schedule.strategy.value}\n"
        f"Number of Positions: {schedule.n_positions}\n\n"
        f"Total Scan Time: {schedule.total_scan_time_ms:.1f} ms\n"
        f"Scan Revisit Rate: {1/schedule.scan_revisit_time_s:.2f} Hz\n\n"
        f"Dwell Time Stats:\n"
        f"  Min: {min(dwells):.1f} ms\n"
        f"  Max: {max(dwells):.1f} ms\n"
        f"  Mean: {np.mean(dwells):.1f} ms\n"
        f"  Std Dev: {np.std(dwells):.1f} ms\n"
    )

    if schedule.poi_estimates:
        summary_text += f"\nPOI Estimates:\n"
        for name, poi in schedule.poi_estimates.items():
            summary_text += f"  {name}: {poi:.1%}\n"

    ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.5))

    plt.tight_layout()
    fig.suptitle('ESM Dwell Schedule Visualization', fontsize=14, fontweight='bold', y=1.02)

    return fig


def plot_schedule_evaluation(evaluation_results: Dict,
                              figsize: Tuple[int, int] = (14, 6)) -> plt.Figure:
    """
    Plot schedule evaluation results against threats.

    Args:
        evaluation_results: Results from DwellScheduler.evaluate_schedule()
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    fig, axes = plt.subplots(1, 3, figsize=figsize)

    threats = evaluation_results['threats']
    summary = evaluation_results['summary']

    # Plot 1: POI by threat
    ax = axes[0]
    threat_ids = [t['threat_id'] for t in threats]
    pois = [t['poi_per_scan'] for t in threats]
    freqs = [t['freq_GHz'] for t in threats]

    colors = ['green' if p > 0.9 else ('orange' if p > 0.5 else 'red') for p in pois]
    bars = ax.bar(threat_ids, pois, color=colors, edgecolor='black')

    ax.axhline(0.9, color='green', linestyle='--', linewidth=2, label='90% Goal')
    ax.axhline(0.5, color='orange', linestyle='--', linewidth=1, label='50% Warning')

    ax.set_xlabel('Threat ID')
    ax.set_ylabel('POI per Scan')
    ax.set_title('Probability of Intercept by Threat', fontweight='bold')
    ax.set_ylim(0, 1.1)
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Add frequency labels
    for bar, freq in zip(bars, freqs):
        ax.text(bar.get_x() + bar.get_width()/2, 0.05,
                f'{freq:.1f}\nGHz', ha='center', va='bottom', fontsize=8)

    # Plot 2: Time to intercept
    ax = axes[1]
    ttis = [min(t['time_to_intercept_s'], 100) for t in threats]  # Cap for display
    colors = ['green' if t < 5 else ('orange' if t < 30 else 'red') for t in ttis]

    bars = ax.barh(threat_ids, ttis, color=colors, edgecolor='black')
    ax.axvline(5, color='green', linestyle='--', linewidth=2, label='5s Goal')
    ax.axvline(30, color='orange', linestyle='--', linewidth=1, label='30s Warning')

    ax.set_xlabel('Time to Intercept (s)')
    ax.set_ylabel('Threat ID')
    ax.set_title('Time to 90% POI', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Summary
    ax = axes[2]
    ax.axis('off')

    summary_text = (
        f"SCHEDULE EVALUATION\n"
        f"{'='*30}\n\n"
        f"Scan Revisit: {evaluation_results['scan_revisit_time_s']:.2f} s\n"
        f"Positions: {evaluation_results['n_positions']}\n\n"
        f"POI Statistics:\n"
        f"  Min: {summary['min_poi']:.1%}\n"
        f"  Mean: {summary['mean_poi']:.1%}\n\n"
        f"Time to Intercept:\n"
        f"  Max: {summary['max_tti_s']:.1f} s\n"
        f"  Mean: {summary['mean_tti_s']:.1f} s\n\n"
        f"{'='*30}\n"
    )

    # Status assessment
    if summary['min_poi'] >= 0.9:
        status = "MEETS REQUIREMENTS"
        color = 'green'
    elif summary['min_poi'] >= 0.5:
        status = "PARTIAL COVERAGE"
        color = 'orange'
    else:
        status = "INSUFFICIENT"
        color = 'red'

    summary_text += f"\nSTATUS: {status}"

    ax.text(0.1, 0.9, summary_text, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))

    # Add colored status indicator
    ax.add_patch(Rectangle((0.1, 0.05), 0.8, 0.1, transform=ax.transAxes,
                            facecolor=color, alpha=0.5))
    ax.text(0.5, 0.1, status, transform=ax.transAxes,
            ha='center', va='center', fontsize=12, fontweight='bold')

    plt.tight_layout()
    fig.suptitle('Schedule Performance Evaluation', fontsize=14, fontweight='bold', y=1.02)

    return fig


def plot_range_vs_frequency(receiver: ReceiverParameters,
                             eirp_dBW_list: List[float] = [40, 50, 60, 70, 80],
                             freq_range_GHz: Tuple[float, float] = (2, 18),
                             figsize: Tuple[int, int] = (10, 6)) -> plt.Figure:
    """
    Plot detection range vs frequency for various EIRP levels.

    Args:
        receiver: ReceiverParameters
        eirp_dBW_list: List of EIRP values to plot
        freq_range_GHz: Frequency range to sweep
        figsize: Figure size

    Returns:
        matplotlib Figure object
    """
    fig, ax = plt.subplots(figsize=figsize)

    freqs = np.linspace(freq_range_GHz[0], freq_range_GHz[1], 100)

    detector = ESMDetector(receiver)

    for eirp in eirp_dBW_list:
        ranges = []
        for freq in freqs:
            radar = RadarParameters(eirp_dBW=eirp, freq_GHz=freq)
            ranges.append(detector.calculate_detection_range(radar))

        ax.semilogy(freqs, ranges, linewidth=2, label=f'EIRP = {eirp} dBW')

    ax.set_xlabel('Frequency (GHz)')
    ax.set_ylabel('Detection Range (km)')
    ax.set_title('ESM Detection Range vs Frequency and EIRP', fontweight='bold')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xlim(freq_range_GHz)

    plt.tight_layout()

    return fig
