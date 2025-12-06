"""
Plotting Module for ESM Analysis

Generates visualizations for SNR analysis, threat categorization,
detection ranges, and scheduling results.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from ..config.loader import SystemConfig, Threat, ThreatLibrary
from ..core.snr_calculator import SNRCalculator, BeamPosition
from ..core.threat_categorizer import (
    ThreatCategorizer, ThreatCategory, CategorizedThreat, CategorizationSummary
)
from ..scheduling.dwell_scheduler import DwellScheduler, SchedulingSummary, ThreatSchedule


# =============================================================================
# PLOT STYLE CONFIGURATION
# =============================================================================

# Color scheme for threat categories
CATEGORY_COLORS = {
    ThreatCategory.SIDELOBE_DETECTABLE: '#2ecc71',   # Green
    ThreatCategory.MAIN_BEAM_REQUIRED: '#f39c12',     # Orange
    ThreatCategory.UNDETECTABLE: '#e74c3c'            # Red
}

# Color scheme for beam positions
BEAM_COLORS = {
    BeamPosition.MAIN_BEAM: '#3498db',   # Blue
    BeamPosition.SIDELOBE: '#9b59b6',    # Purple
    BeamPosition.BACK_LOBE: '#95a5a6'    # Gray
}

# Default figure style
plt.style.use('seaborn-v0_8-whitegrid')


# =============================================================================
# ESM PLOTTER CLASS
# =============================================================================

class ESMPlotter:
    """
    Plotting utilities for ESM analysis results.

    Provides methods for generating standard analysis plots including:
    - SNR vs range curves
    - Threat categorization summaries
    - Detection range comparisons
    - Duty cycle analysis
    - Scheduling timelines
    """

    def __init__(
        self,
        system_config: SystemConfig,
        output_dir: str = None,
        save_plots: bool = True,
        plot_format: str = 'png',
        dpi: int = 150
    ):
        """
        Initialize ESM plotter.

        Args:
            system_config: System configuration.
            output_dir: Directory to save plots. If None, uses config.
            save_plots: Whether to save plots to files.
            plot_format: Image format (png, pdf, svg).
            dpi: Resolution for raster formats.
        """
        self.config = system_config

        if output_dir is None:
            output_dir = system_config.output.results_dir
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.save_plots = save_plots
        self.plot_format = plot_format
        self.dpi = dpi

        # Create calculators
        self.snr_calc = SNRCalculator(system_config, verbose=False)

    def _save_figure(self, fig: plt.Figure, name: str):
        """Save figure to file if enabled."""
        if self.save_plots:
            filepath = self.output_dir / f"{name}.{self.plot_format}"
            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
            print(f"Saved: {filepath}")

    # -------------------------------------------------------------------------
    # SNR ANALYSIS PLOTS
    # -------------------------------------------------------------------------

    def plot_snr_vs_range(
        self,
        threat: Threat,
        range_start_m: float = 10000,
        range_end_m: float = 500000,
        num_points: int = 100,
        show_threshold: bool = True,
        ax: plt.Axes = None
    ) -> plt.Figure:
        """
        Plot SNR vs range for all beam positions of a threat.

        Args:
            threat: Threat to analyze.
            range_start_m: Start of range sweep.
            range_end_m: End of range sweep.
            num_points: Number of range points.
            show_threshold: Show detection threshold line.
            ax: Existing axes to plot on. If None, creates new figure.

        Returns:
            matplotlib Figure object.
        """
        ranges_m = np.linspace(range_start_m, range_end_m, num_points)
        ranges_km = ranges_m / 1000

        # Calculate SNR for each beam position
        snr_data = {beam: [] for beam in BeamPosition}

        for range_m in ranges_m:
            for beam in BeamPosition:
                result = self.snr_calc.calculate_snr(threat, range_m, beam)
                snr_data[beam].append(result.snr_db)

        # Create plot
        if ax is None:
            fig, ax = plt.subplots(figsize=(10, 6))
        else:
            fig = ax.get_figure()

        # Plot each beam position
        for beam, color in BEAM_COLORS.items():
            label = beam.value.replace('_', ' ').title()
            ax.plot(ranges_km, snr_data[beam], color=color, linewidth=2, label=label)

        # Show threshold
        if show_threshold:
            threshold = self.config.receiver.snr_threshold_db
            ax.axhline(y=threshold, color='red', linestyle='--', linewidth=1.5,
                       label=f'Detection Threshold ({threshold:.0f} dB)')

        # Mark required detection range if specified
        if threat.required_detection_range_m:
            req_range_km = threat.required_detection_range_m / 1000
            ax.axvline(x=req_range_km, color='gray', linestyle=':', linewidth=1.5,
                       label=f'Required Range ({req_range_km:.0f} km)')

        ax.set_xlabel('Range (km)', fontsize=12)
        ax.set_ylabel('SNR (dB)', fontsize=12)
        ax.set_title(f'SNR vs Range: {threat.name}\n'
                     f'({threat.frequency_hz/1e9:.1f} GHz, '
                     f'{threat.peak_power_w/1000:.0f} kW)', fontsize=14)
        ax.legend(loc='upper right')
        ax.grid(True, alpha=0.3)

        self._save_figure(fig, f'snr_vs_range_{threat.id}')
        return fig

    def plot_multi_threat_snr(
        self,
        threats: List[Threat],
        range_m: float = None,
        beam_position: BeamPosition = BeamPosition.MAIN_BEAM
    ) -> plt.Figure:
        """
        Plot SNR comparison for multiple threats at specific range.

        Args:
            threats: List of threats to compare.
            range_m: Range for comparison. If None, uses required range.
            beam_position: Which beam position to show.

        Returns:
            matplotlib Figure object.
        """
        fig, ax = plt.subplots(figsize=(12, 6))

        threat_names = []
        snr_values = []
        colors = []

        threshold = self.config.receiver.snr_threshold_db

        for threat in threats:
            r = range_m or threat.required_detection_range_m or \
                self.config.analysis.required_detection_range_m

            result = self.snr_calc.calculate_snr(threat, r, beam_position)
            threat_names.append(threat.name)
            snr_values.append(result.snr_db)

            # Color based on detection status
            if result.snr_db >= threshold:
                colors.append('#2ecc71')  # Green
            else:
                colors.append('#e74c3c')  # Red

        # Create bar chart
        bars = ax.bar(range(len(threats)), snr_values, color=colors)

        # Add threshold line
        ax.axhline(y=threshold, color='red', linestyle='--', linewidth=2,
                   label=f'Threshold ({threshold:.0f} dB)')

        ax.set_xticks(range(len(threats)))
        ax.set_xticklabels(threat_names, rotation=45, ha='right')
        ax.set_ylabel('SNR (dB)', fontsize=12)
        ax.set_title(f'SNR Comparison ({beam_position.value.replace("_", " ").title()})',
                     fontsize=14)
        ax.legend()
        ax.grid(True, alpha=0.3, axis='y')

        # Add value labels on bars
        for bar, snr in zip(bars, snr_values):
            height = bar.get_height()
            ax.annotate(f'{snr:.1f}',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3), textcoords="offset points",
                        ha='center', va='bottom', fontsize=9)

        plt.tight_layout()
        self._save_figure(fig, 'multi_threat_snr_comparison')
        return fig

    # -------------------------------------------------------------------------
    # CATEGORIZATION PLOTS
    # -------------------------------------------------------------------------

    def plot_categorization_summary(
        self,
        summary: CategorizationSummary
    ) -> plt.Figure:
        """
        Plot pie chart and summary of threat categorization.

        Args:
            summary: CategorizationSummary from ThreatCategorizer.

        Returns:
            matplotlib Figure object.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Pie chart of categories
        sizes = [
            len(summary.sidelobe_detectable),
            len(summary.main_beam_required),
            len(summary.undetectable)
        ]
        labels = ['Sidelobe\nDetectable', 'Main Beam\nRequired', 'Undetectable']
        colors = [
            CATEGORY_COLORS[ThreatCategory.SIDELOBE_DETECTABLE],
            CATEGORY_COLORS[ThreatCategory.MAIN_BEAM_REQUIRED],
            CATEGORY_COLORS[ThreatCategory.UNDETECTABLE]
        ]

        # Remove zero-size wedges
        non_zero = [(s, l, c) for s, l, c in zip(sizes, labels, colors) if s > 0]
        if non_zero:
            sizes, labels, colors = zip(*non_zero)
            wedges, texts, autotexts = ax1.pie(
                sizes, labels=labels, colors=colors, autopct='%1.1f%%',
                startangle=90, explode=[0.02]*len(sizes)
            )
            ax1.set_title('Threat Categorization', fontsize=14)

        # Bar chart with threat details
        all_threats = (
            summary.sidelobe_detectable +
            summary.main_beam_required +
            summary.undetectable
        )

        if all_threats:
            threat_names = [t.threat.name for t in all_threats]
            margins = [t.sidelobe_margin_db for t in all_threats]
            bar_colors = [CATEGORY_COLORS[t.category] for t in all_threats]

            bars = ax2.barh(range(len(all_threats)), margins, color=bar_colors)

            # Add threshold line at 0 (margin = 0 means SNR = threshold)
            ax2.axvline(x=0, color='red', linestyle='--', linewidth=2)

            ax2.set_yticks(range(len(all_threats)))
            ax2.set_yticklabels(threat_names)
            ax2.set_xlabel('Sidelobe SNR Margin (dB)', fontsize=12)
            ax2.set_title('Sidelobe Detection Margin', fontsize=14)
            ax2.grid(True, alpha=0.3, axis='x')

            # Custom legend
            legend_elements = [
                Patch(facecolor=CATEGORY_COLORS[ThreatCategory.SIDELOBE_DETECTABLE],
                      label='Sidelobe Detectable'),
                Patch(facecolor=CATEGORY_COLORS[ThreatCategory.MAIN_BEAM_REQUIRED],
                      label='Main Beam Required'),
                Patch(facecolor=CATEGORY_COLORS[ThreatCategory.UNDETECTABLE],
                      label='Undetectable')
            ]
            ax2.legend(handles=legend_elements, loc='lower right')

        plt.tight_layout()
        self._save_figure(fig, 'categorization_summary')
        return fig

    def plot_detection_ranges(
        self,
        categorized_threats: List[CategorizedThreat]
    ) -> plt.Figure:
        """
        Plot maximum detection ranges for each beam position.

        Args:
            categorized_threats: List of categorized threats.

        Returns:
            matplotlib Figure object.
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        n_threats = len(categorized_threats)
        x = np.arange(n_threats)
        width = 0.25

        main_beam_ranges = [t.max_range_main_beam_m / 1000 for t in categorized_threats]
        sidelobe_ranges = [t.max_range_sidelobe_m / 1000 for t in categorized_threats]
        back_lobe_ranges = [t.max_range_back_lobe_m / 1000 for t in categorized_threats]
        required_ranges = [
            (t.threat.required_detection_range_m or
             self.config.analysis.required_detection_range_m) / 1000
            for t in categorized_threats
        ]

        # Create grouped bars
        bars1 = ax.bar(x - width, main_beam_ranges, width, label='Main Beam',
                       color=BEAM_COLORS[BeamPosition.MAIN_BEAM])
        bars2 = ax.bar(x, sidelobe_ranges, width, label='Sidelobe',
                       color=BEAM_COLORS[BeamPosition.SIDELOBE])
        bars3 = ax.bar(x + width, back_lobe_ranges, width, label='Back Lobe',
                       color=BEAM_COLORS[BeamPosition.BACK_LOBE])

        # Add required range markers
        for i, (cat_threat, req_range) in enumerate(zip(categorized_threats, required_ranges)):
            ax.plot([i - width*1.5, i + width*1.5], [req_range, req_range],
                    'r-', linewidth=2, marker='|', markersize=10)

        # Add custom legend entry for required range
        legend_elements = [
            Patch(facecolor=BEAM_COLORS[BeamPosition.MAIN_BEAM], label='Main Beam'),
            Patch(facecolor=BEAM_COLORS[BeamPosition.SIDELOBE], label='Sidelobe'),
            Patch(facecolor=BEAM_COLORS[BeamPosition.BACK_LOBE], label='Back Lobe'),
            Line2D([0], [0], color='red', linewidth=2, label='Required Range')
        ]

        ax.set_xlabel('Threat', fontsize=12)
        ax.set_ylabel('Max Detection Range (km)', fontsize=12)
        ax.set_title('Maximum Detection Range by Beam Position', fontsize=14)
        ax.set_xticks(x)
        ax.set_xticklabels([t.threat.name for t in categorized_threats],
                          rotation=45, ha='right')
        ax.legend(handles=legend_elements, loc='upper right')
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        self._save_figure(fig, 'detection_ranges')
        return fig

    # -------------------------------------------------------------------------
    # SCHEDULING PLOTS
    # -------------------------------------------------------------------------

    def plot_duty_cycle_comparison(
        self,
        summary: SchedulingSummary
    ) -> plt.Figure:
        """
        Plot duty cycle comparison (optimized vs naive).

        Args:
            summary: SchedulingSummary from DwellScheduler.

        Returns:
            matplotlib Figure object.
        """
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Stacked bar chart for duty cycle breakdown
        categories = ['Optimized', 'Naive\n(All Main Beam)']
        sidelobe_duty = [summary.sidelobe_duty_cycle_percent, 0]
        main_beam_duty = [
            summary.main_beam_duty_cycle_percent,
            summary.naive_duty_cycle_percent
        ]

        ax1.bar(categories, sidelobe_duty, label='Sidelobe Threats',
                color=CATEGORY_COLORS[ThreatCategory.SIDELOBE_DETECTABLE])
        ax1.bar(categories, main_beam_duty, bottom=sidelobe_duty,
                label='Main Beam Threats',
                color=CATEGORY_COLORS[ThreatCategory.MAIN_BEAM_REQUIRED])

        ax1.set_ylabel('Duty Cycle (%)', fontsize=12)
        ax1.set_title('Receiver Duty Cycle Comparison', fontsize=14)
        ax1.legend(loc='upper right')
        ax1.grid(True, alpha=0.3, axis='y')

        # Add percentage labels
        for i, (sl, mb) in enumerate(zip(sidelobe_duty, main_beam_duty)):
            total = sl + mb
            if total > 0:
                ax1.annotate(f'{total:.3f}%',
                             xy=(i, total), xytext=(0, 5),
                             textcoords='offset points',
                             ha='center', fontsize=11, fontweight='bold')

        # Savings annotation
        if summary.duty_cycle_savings_percent > 0:
            ax1.annotate(
                f'Savings: {summary.duty_cycle_savings_percent:.1f}%',
                xy=(0.5, 0.95), xycoords='axes fraction',
                ha='center', fontsize=12, fontweight='bold',
                bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.7)
            )

        # Per-threat duty cycle breakdown
        all_schedules = summary.sidelobe_threats + summary.main_beam_threats
        if all_schedules:
            threat_names = [s.threat_name for s in all_schedules]
            duty_cycles = [s.duty_cycle_percent for s in all_schedules]
            colors = [
                CATEGORY_COLORS[s.category] for s in all_schedules
            ]

            bars = ax2.barh(range(len(all_schedules)), duty_cycles, color=colors)
            ax2.set_yticks(range(len(all_schedules)))
            ax2.set_yticklabels(threat_names)
            ax2.set_xlabel('Duty Cycle (%)', fontsize=12)
            ax2.set_title('Per-Threat Duty Cycle', fontsize=14)
            ax2.grid(True, alpha=0.3, axis='x')

            # Add value labels
            for bar, duty in zip(bars, duty_cycles):
                width = bar.get_width()
                ax2.annotate(f'{duty:.4f}%',
                             xy=(width, bar.get_y() + bar.get_height()/2),
                             xytext=(3, 0), textcoords='offset points',
                             ha='left', va='center', fontsize=9)

        plt.tight_layout()
        self._save_figure(fig, 'duty_cycle_comparison')
        return fig

    def plot_scheduling_timeline(
        self,
        threat_schedules: List[ThreatSchedule],
        duration_s: float = 5.0
    ) -> plt.Figure:
        """
        Plot scheduling timeline showing dwells over time.

        Args:
            threat_schedules: List of threat schedules.
            duration_s: Duration to show.

        Returns:
            matplotlib Figure object.
        """
        fig, ax = plt.subplots(figsize=(14, 8))

        # Generate timeline
        scheduler = DwellScheduler(self.config, verbose=False)
        dwells = scheduler.generate_dwell_timeline(threat_schedules, duration_s)

        # Group dwells by threat
        threat_ids = list(set(d.associated_threat_id for d in dwells))
        threat_y = {tid: i for i, tid in enumerate(threat_ids)}

        # Plot dwells as rectangles
        for dwell in dwells:
            y = threat_y[dwell.associated_threat_id]
            width = dwell.dwell_duration_s

            # Find threat schedule for color
            schedule = next(
                (s for s in threat_schedules if s.threat_id == dwell.associated_threat_id),
                None
            )
            if schedule:
                color = CATEGORY_COLORS.get(schedule.category, '#3498db')
            else:
                color = '#3498db'

            rect = plt.Rectangle(
                (dwell.start_time_s, y - 0.3), width, 0.6,
                facecolor=color, edgecolor='black', linewidth=0.5
            )
            ax.add_patch(rect)

        ax.set_xlim(0, duration_s)
        ax.set_ylim(-0.5, len(threat_ids) - 0.5)
        ax.set_yticks(range(len(threat_ids)))
        ax.set_yticklabels([
            next((s.threat_name for s in threat_schedules if s.threat_id == tid), tid)
            for tid in threat_ids
        ])
        ax.set_xlabel('Time (s)', fontsize=12)
        ax.set_ylabel('Threat', fontsize=12)
        ax.set_title(f'Receiver Dwell Timeline ({duration_s:.1f}s window)', fontsize=14)
        ax.grid(True, alpha=0.3, axis='x')

        # Custom legend
        legend_elements = [
            Patch(facecolor=CATEGORY_COLORS[ThreatCategory.SIDELOBE_DETECTABLE],
                  label='Sidelobe Detectable'),
            Patch(facecolor=CATEGORY_COLORS[ThreatCategory.MAIN_BEAM_REQUIRED],
                  label='Main Beam Required')
        ]
        ax.legend(handles=legend_elements, loc='upper right')

        plt.tight_layout()
        self._save_figure(fig, 'scheduling_timeline')
        return fig

    # -------------------------------------------------------------------------
    # COMPREHENSIVE REPORT PLOTS
    # -------------------------------------------------------------------------

    def generate_full_report(
        self,
        categorized_threats: List[CategorizedThreat],
        scheduling_summary: SchedulingSummary
    ) -> List[plt.Figure]:
        """
        Generate all standard plots for a complete analysis report.

        Args:
            categorized_threats: List of categorized threats.
            scheduling_summary: Scheduling summary.

        Returns:
            List of generated Figure objects.
        """
        figures = []

        # 1. SNR vs range for each threat
        for cat_threat in categorized_threats:
            fig = self.plot_snr_vs_range(cat_threat.threat)
            figures.append(fig)

        # 2. Categorization summary
        summary = CategorizationSummary(
            total_threats=len(categorized_threats),
            sidelobe_detectable=[t for t in categorized_threats
                                 if t.category == ThreatCategory.SIDELOBE_DETECTABLE],
            main_beam_required=[t for t in categorized_threats
                               if t.category == ThreatCategory.MAIN_BEAM_REQUIRED],
            undetectable=[t for t in categorized_threats
                         if t.category == ThreatCategory.UNDETECTABLE]
        )
        fig = self.plot_categorization_summary(summary)
        figures.append(fig)

        # 3. Detection ranges
        fig = self.plot_detection_ranges(categorized_threats)
        figures.append(fig)

        # 4. Duty cycle comparison
        fig = self.plot_duty_cycle_comparison(scheduling_summary)
        figures.append(fig)

        # Note: Scheduling timeline removed - not useful for design review

        return figures


# =============================================================================
# STANDALONE PLOTTING FUNCTIONS
# =============================================================================

def plot_snr_vs_range(
    threat: Threat,
    system_config: SystemConfig,
    range_start_m: float = 10000,
    range_end_m: float = 500000,
    save_path: str = None
) -> plt.Figure:
    """
    Standalone function to plot SNR vs range.

    Args:
        threat: Threat to analyze.
        system_config: System configuration.
        range_start_m: Start of range sweep.
        range_end_m: End of range sweep.
        save_path: Path to save figure.

    Returns:
        matplotlib Figure object.
    """
    plotter = ESMPlotter(system_config, save_plots=False)
    fig = plotter.plot_snr_vs_range(threat, range_start_m, range_end_m)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig


def plot_duty_cycle_comparison(
    scheduling_summary: SchedulingSummary,
    system_config: SystemConfig,
    save_path: str = None
) -> plt.Figure:
    """
    Standalone function to plot duty cycle comparison.

    Args:
        scheduling_summary: Scheduling summary.
        system_config: System configuration.
        save_path: Path to save figure.

    Returns:
        matplotlib Figure object.
    """
    plotter = ESMPlotter(system_config, save_plots=False)
    fig = plotter.plot_duty_cycle_comparison(scheduling_summary)

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')

    return fig
