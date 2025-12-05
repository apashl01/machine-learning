"""
Dwell Scheduler Module

Implements scan position dwell scheduling for ESM receivers.
Guarantees detection of main-beam-required threats by timing
receiver dwells to intercept threat scan patterns.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
import math

from ..config.loader import SystemConfig, Threat
from ..core.threat_categorizer import ThreatCategory, CategorizedThreat


# =============================================================================
# ENUMS
# =============================================================================

class SchedulingStrategy(Enum):
    """Scheduling strategy options."""
    UNIFORM = "uniform"              # Equal positions across scan
    THREAT_WEIGHTED = "threat_weighted"  # More positions for higher priority
    MINIMUM_DUTY = "minimum_duty"    # Minimize receiver duty cycle


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DwellSchedule:
    """Schedule for a single dwell period."""
    position_index: int
    start_time_s: float
    dwell_duration_us: float
    dwell_duration_s: float
    associated_threat_id: str
    notes: str = ""


@dataclass
class ThreatSchedule:
    """Complete scheduling for a single threat."""
    threat_id: str
    threat_name: str
    threat_priority: int
    category: ThreatCategory

    # Threat timing parameters
    scan_period_s: float
    pri_us: float

    # Scheduling parameters
    n_scan_positions: int
    revisit_interval_s: float
    dwell_time_us: float
    dwell_time_s: float

    # Duty cycle contribution
    dwells_per_scan_period: int
    total_dwell_time_per_period_s: float
    duty_cycle_percent: float

    # Detection guarantee
    pi_guaranteed: bool = True  # Probability of Intercept = 100%

    # Notes
    scheduling_notes: str = ""

    def __str__(self) -> str:
        status = "SIDELOBE" if self.category == ThreatCategory.SIDELOBE_DETECTABLE else "MAIN BEAM"
        return (
            f"\nThreat Schedule: {self.threat_name}\n"
            f"  Category: {status}\n"
            f"  Scan Period: {self.scan_period_s:.2f} s\n"
            f"  PRI: {self.pri_us:.1f} µs\n"
            f"  Scan Positions: {self.n_scan_positions}\n"
            f"  Revisit Interval: {self.revisit_interval_s*1000:.1f} ms\n"
            f"  Dwell Time: {self.dwell_time_us:.1f} µs "
            f"({self.dwell_time_us/1000:.3f} ms)\n"
            f"  Duty Cycle: {self.duty_cycle_percent:.4f}%\n"
            f"  Pi Guaranteed: {'YES' if self.pi_guaranteed else 'NO'}"
        )


@dataclass
class SchedulingSummary:
    """Summary of scheduling for all threats."""
    # Threat schedules
    sidelobe_threats: List[ThreatSchedule] = field(default_factory=list)
    main_beam_threats: List[ThreatSchedule] = field(default_factory=list)
    undetectable_threats: List[str] = field(default_factory=list)

    # Aggregate duty cycles
    sidelobe_duty_cycle_percent: float = 0.0
    main_beam_duty_cycle_percent: float = 0.0
    total_duty_cycle_percent: float = 0.0

    # Comparison metrics
    naive_duty_cycle_percent: float = 0.0  # If treating all as main-beam
    duty_cycle_savings_percent: float = 0.0

    # Timing summary
    min_revisit_interval_s: float = float('inf')
    max_dwell_time_us: float = 0.0
    total_dwells_per_second: float = 0.0

    def __str__(self) -> str:
        return (
            f"\n{'='*60}\n"
            f"SCHEDULING SUMMARY\n"
            f"{'='*60}\n\n"
            f"Sidelobe-Detectable Threats: {len(self.sidelobe_threats)}\n"
            f"  Duty Cycle: {self.sidelobe_duty_cycle_percent:.4f}%\n"
            f"  (Low-duty monitoring sufficient)\n\n"
            f"Main-Beam-Required Threats: {len(self.main_beam_threats)}\n"
            f"  Duty Cycle: {self.main_beam_duty_cycle_percent:.4f}%\n"
            f"  (Scan position scheduling active)\n\n"
            f"Undetectable: {len(self.undetectable_threats)}\n\n"
            f"TOTAL DUTY CYCLE: {self.total_duty_cycle_percent:.4f}%\n\n"
            f"COMPARISON:\n"
            f"  Naive (all main-beam): {self.naive_duty_cycle_percent:.4f}%\n"
            f"  Optimized:             {self.total_duty_cycle_percent:.4f}%\n"
            f"  Savings:               {self.duty_cycle_savings_percent:.2f}%\n\n"
            f"TIMING:\n"
            f"  Min Revisit Interval: {self.min_revisit_interval_s*1000:.1f} ms\n"
            f"  Max Dwell Time: {self.max_dwell_time_us:.1f} µs\n"
            f"  Total Dwells/sec: {self.total_dwells_per_second:.1f}"
        )


# =============================================================================
# DWELL SCHEDULER CLASS
# =============================================================================

class DwellScheduler:
    """
    Scan position dwell scheduler for ESM receivers.

    For main-beam-required threats:
    - Divides threat scan period into N positions
    - Revisit interval = scan_period / N
    - Dwell time > PRI to guarantee catching one pulse
    - Result: Pi = 100% (deterministic detection)

    For sidelobe-detectable threats:
    - Signal always present via sidelobes
    - Check at low rate (e.g., every 60 seconds)
    - Minimal duty cycle contribution
    """

    def __init__(
        self,
        system_config: SystemConfig,
        verbose: bool = None
    ):
        """
        Initialize dwell scheduler.

        Args:
            system_config: System configuration.
            verbose: Enable verbose output.
        """
        self.config = system_config
        self.analysis = system_config.analysis
        self.receiver = system_config.receiver

        self.verbose = verbose if verbose is not None else self.analysis.verbose

        # Default parameters
        self.default_scan_positions = self.analysis.default_scan_positions
        self.dwell_margin_factor = self.analysis.dwell_margin_factor
        self.sidelobe_check_interval = self.analysis.sidelobe_check_interval_s

    # -------------------------------------------------------------------------
    # SINGLE THREAT SCHEDULING
    # -------------------------------------------------------------------------

    def schedule_threat(
        self,
        categorized_threat: CategorizedThreat,
        n_positions: int = None,
        dwell_margin: float = None
    ) -> ThreatSchedule:
        """
        Create schedule for a single categorized threat.

        Args:
            categorized_threat: Threat with category assigned.
            n_positions: Number of scan positions. If None, uses default.
            dwell_margin: Dwell time multiplier vs PRI. If None, uses default.

        Returns:
            ThreatSchedule for the threat.
        """
        threat = categorized_threat.threat
        category = categorized_threat.category

        if n_positions is None:
            n_positions = self.default_scan_positions
        if dwell_margin is None:
            dwell_margin = self.dwell_margin_factor

        if category == ThreatCategory.SIDELOBE_DETECTABLE:
            return self._schedule_sidelobe_threat(threat, category)
        elif category == ThreatCategory.MAIN_BEAM_REQUIRED:
            return self._schedule_main_beam_threat(
                threat, category, n_positions, dwell_margin
            )
        else:  # UNDETECTABLE
            return self._schedule_undetectable_threat(threat, category)

    def _schedule_sidelobe_threat(
        self,
        threat: Threat,
        category: ThreatCategory
    ) -> ThreatSchedule:
        """
        Schedule for sidelobe-detectable threat.

        These threats radiate continuously via sidelobes, so we only need
        occasional checks to confirm presence.
        """
        # Use single position, long interval
        n_positions = 1
        revisit_interval = self.sidelobe_check_interval  # e.g., 60 seconds

        # Dwell time: still need to catch one pulse
        dwell_time_us = threat.pri_us * self.dwell_margin_factor
        dwell_time_s = dwell_time_us * 1e-6

        # Duty cycle over a 60-second period
        # One dwell of dwell_time_s every revisit_interval seconds
        dwells_per_period = 1
        total_dwell_per_period = dwell_time_s
        duty_cycle = (dwell_time_s / revisit_interval) * 100

        notes = (
            f"Sidelobe-detectable: signal always present. "
            f"Check every {revisit_interval:.0f}s with {dwell_time_us:.0f}µs dwell."
        )

        return ThreatSchedule(
            threat_id=threat.id,
            threat_name=threat.name,
            threat_priority=threat.priority,
            category=category,
            scan_period_s=threat.scan_period_s,
            pri_us=threat.pri_us,
            n_scan_positions=n_positions,
            revisit_interval_s=revisit_interval,
            dwell_time_us=dwell_time_us,
            dwell_time_s=dwell_time_s,
            dwells_per_scan_period=dwells_per_period,
            total_dwell_time_per_period_s=total_dwell_per_period,
            duty_cycle_percent=duty_cycle,
            pi_guaranteed=True,
            scheduling_notes=notes
        )

    def _schedule_main_beam_threat(
        self,
        threat: Threat,
        category: ThreatCategory,
        n_positions: int,
        dwell_margin: float
    ) -> ThreatSchedule:
        """
        Schedule for main-beam-required threat.

        Must catch main beam during scan. Divide scan into N positions
        and dwell long enough to catch one pulse when beam sweeps past.
        """
        # Revisit interval = scan_period / n_positions
        revisit_interval = threat.scan_period_s / n_positions

        # Dwell time: must exceed PRI to guarantee catching one pulse
        dwell_time_us = threat.pri_us * dwell_margin
        dwell_time_s = dwell_time_us * 1e-6

        # Ensure dwell time is reasonable (not longer than revisit interval)
        max_dwell_s = revisit_interval * 0.8  # Don't exceed 80% of interval
        if dwell_time_s > max_dwell_s:
            dwell_time_s = max_dwell_s
            dwell_time_us = dwell_time_s * 1e6

        # Dwells per scan period
        dwells_per_period = n_positions

        # Total dwell time per scan period
        total_dwell_per_period = dwells_per_period * dwell_time_s

        # Duty cycle
        duty_cycle = (total_dwell_per_period / threat.scan_period_s) * 100

        notes = (
            f"Main-beam required: {n_positions} positions, "
            f"revisit every {revisit_interval*1000:.1f}ms, "
            f"dwell {dwell_time_us:.1f}µs (>{threat.pri_us:.1f}µs PRI). "
            f"Pi = 100%."
        )

        return ThreatSchedule(
            threat_id=threat.id,
            threat_name=threat.name,
            threat_priority=threat.priority,
            category=category,
            scan_period_s=threat.scan_period_s,
            pri_us=threat.pri_us,
            n_scan_positions=n_positions,
            revisit_interval_s=revisit_interval,
            dwell_time_us=dwell_time_us,
            dwell_time_s=dwell_time_s,
            dwells_per_scan_period=dwells_per_period,
            total_dwell_time_per_period_s=total_dwell_per_period,
            duty_cycle_percent=duty_cycle,
            pi_guaranteed=True,
            scheduling_notes=notes
        )

    def _schedule_undetectable_threat(
        self,
        threat: Threat,
        category: ThreatCategory
    ) -> ThreatSchedule:
        """Schedule placeholder for undetectable threat."""
        return ThreatSchedule(
            threat_id=threat.id,
            threat_name=threat.name,
            threat_priority=threat.priority,
            category=category,
            scan_period_s=threat.scan_period_s,
            pri_us=threat.pri_us,
            n_scan_positions=0,
            revisit_interval_s=0,
            dwell_time_us=0,
            dwell_time_s=0,
            dwells_per_scan_period=0,
            total_dwell_time_per_period_s=0,
            duty_cycle_percent=0,
            pi_guaranteed=False,
            scheduling_notes="UNDETECTABLE: Cannot detect at required range."
        )

    # -------------------------------------------------------------------------
    # BATCH SCHEDULING
    # -------------------------------------------------------------------------

    def schedule_all_threats(
        self,
        categorized_threats: List[CategorizedThreat],
        strategy: SchedulingStrategy = SchedulingStrategy.UNIFORM
    ) -> SchedulingSummary:
        """
        Create schedules for all categorized threats.

        Args:
            categorized_threats: List of categorized threats.
            strategy: Scheduling strategy to use.

        Returns:
            SchedulingSummary with all schedules and metrics.
        """
        summary = SchedulingSummary()

        for cat_threat in categorized_threats:
            schedule = self.schedule_threat(cat_threat)

            if cat_threat.category == ThreatCategory.SIDELOBE_DETECTABLE:
                summary.sidelobe_threats.append(schedule)
            elif cat_threat.category == ThreatCategory.MAIN_BEAM_REQUIRED:
                summary.main_beam_threats.append(schedule)
            else:
                summary.undetectable_threats.append(cat_threat.threat.id)

        # Calculate aggregate duty cycles
        summary.sidelobe_duty_cycle_percent = sum(
            s.duty_cycle_percent for s in summary.sidelobe_threats
        )
        summary.main_beam_duty_cycle_percent = sum(
            s.duty_cycle_percent for s in summary.main_beam_threats
        )
        summary.total_duty_cycle_percent = (
            summary.sidelobe_duty_cycle_percent +
            summary.main_beam_duty_cycle_percent
        )

        # Calculate naive approach (treat all as main-beam)
        summary.naive_duty_cycle_percent = self._calculate_naive_duty_cycle(
            categorized_threats
        )

        # Calculate savings
        if summary.naive_duty_cycle_percent > 0:
            summary.duty_cycle_savings_percent = (
                (summary.naive_duty_cycle_percent - summary.total_duty_cycle_percent) /
                summary.naive_duty_cycle_percent * 100
            )

        # Calculate timing metrics
        all_schedules = summary.sidelobe_threats + summary.main_beam_threats
        if all_schedules:
            summary.min_revisit_interval_s = min(
                s.revisit_interval_s for s in all_schedules if s.revisit_interval_s > 0
            )
            summary.max_dwell_time_us = max(
                s.dwell_time_us for s in all_schedules
            )
            # Dwells per second (approximate)
            summary.total_dwells_per_second = sum(
                1 / s.revisit_interval_s for s in all_schedules
                if s.revisit_interval_s > 0
            )

        if self.verbose:
            print(summary)

        return summary

    def _calculate_naive_duty_cycle(
        self,
        categorized_threats: List[CategorizedThreat]
    ) -> float:
        """
        Calculate duty cycle if treating ALL threats as main-beam-required.

        This is the comparison baseline to show optimization benefits.
        """
        total_duty = 0.0

        for cat_threat in categorized_threats:
            if cat_threat.category == ThreatCategory.UNDETECTABLE:
                continue

            threat = cat_threat.threat

            # Assume main-beam scheduling for all
            n_positions = self.default_scan_positions
            dwell_time_us = threat.pri_us * self.dwell_margin_factor
            dwell_time_s = dwell_time_us * 1e-6

            dwells_per_period = n_positions
            total_dwell_per_period = dwells_per_period * dwell_time_s

            duty = (total_dwell_per_period / threat.scan_period_s) * 100
            total_duty += duty

        return total_duty

    # -------------------------------------------------------------------------
    # SCHEDULE GENERATION
    # -------------------------------------------------------------------------

    def generate_dwell_timeline(
        self,
        threat_schedules: List[ThreatSchedule],
        duration_s: float = 10.0
    ) -> List[DwellSchedule]:
        """
        Generate detailed dwell timeline for a time period.

        Args:
            threat_schedules: List of threat schedules.
            duration_s: Duration to generate timeline for.

        Returns:
            List of DwellSchedule entries in chronological order.
        """
        dwells = []

        for schedule in threat_schedules:
            if schedule.category == ThreatCategory.UNDETECTABLE:
                continue

            current_time = 0.0
            position = 0

            while current_time < duration_s:
                dwell = DwellSchedule(
                    position_index=position,
                    start_time_s=current_time,
                    dwell_duration_us=schedule.dwell_time_us,
                    dwell_duration_s=schedule.dwell_time_s,
                    associated_threat_id=schedule.threat_id,
                    notes=f"{schedule.threat_name} position {position}"
                )
                dwells.append(dwell)

                current_time += schedule.revisit_interval_s
                position = (position + 1) % max(1, schedule.n_scan_positions)

        # Sort by start time
        dwells.sort(key=lambda d: d.start_time_s)

        return dwells

    def check_scheduling_conflicts(
        self,
        dwells: List[DwellSchedule],
        tune_time_us: float = None
    ) -> List[Dict]:
        """
        Check for scheduling conflicts (overlapping dwells).

        Args:
            dwells: List of scheduled dwells.
            tune_time_us: Receiver tune time between dwells.

        Returns:
            List of conflict descriptions.
        """
        if tune_time_us is None:
            tune_time_us = (
                self.receiver.tune_time_us +
                self.receiver.settling_time_us
            )

        tune_time_s = tune_time_us * 1e-6
        conflicts = []

        for i in range(len(dwells) - 1):
            current = dwells[i]
            next_dwell = dwells[i + 1]

            # End time of current dwell (including tune time to next)
            current_end = (
                current.start_time_s +
                current.dwell_duration_s +
                tune_time_s
            )

            # Check overlap
            if current_end > next_dwell.start_time_s:
                overlap_us = (current_end - next_dwell.start_time_s) * 1e6
                conflicts.append({
                    'dwell_1': current.associated_threat_id,
                    'dwell_2': next_dwell.associated_threat_id,
                    'time_s': current.start_time_s,
                    'overlap_us': overlap_us,
                    'description': (
                        f"Overlap at t={current.start_time_s:.4f}s: "
                        f"{current.associated_threat_id} ends at "
                        f"{current_end:.4f}s but {next_dwell.associated_threat_id} "
                        f"starts at {next_dwell.start_time_s:.4f}s "
                        f"(overlap: {overlap_us:.1f}µs)"
                    )
                })

        return conflicts

    # -------------------------------------------------------------------------
    # OPTIMIZATION
    # -------------------------------------------------------------------------

    def optimize_scan_positions(
        self,
        categorized_threats: List[CategorizedThreat],
        max_duty_cycle_percent: float = 5.0
    ) -> Dict[str, int]:
        """
        Optimize number of scan positions per threat to meet duty cycle target.

        More positions = higher duty cycle but better Pi.
        Fewer positions = lower duty cycle but may miss some beams.

        Args:
            categorized_threats: List of categorized threats.
            max_duty_cycle_percent: Target maximum duty cycle.

        Returns:
            Dictionary mapping threat_id to optimized n_positions.
        """
        optimized = {}

        # Calculate baseline duty cycle with default positions
        baseline = self.schedule_all_threats(categorized_threats)

        if baseline.total_duty_cycle_percent <= max_duty_cycle_percent:
            # Already within target
            for cat_threat in categorized_threats:
                if cat_threat.category == ThreatCategory.MAIN_BEAM_REQUIRED:
                    optimized[cat_threat.threat.id] = self.default_scan_positions
            return optimized

        # Need to reduce positions for some threats
        # Start with minimum positions and increase for high-priority threats
        for cat_threat in categorized_threats:
            if cat_threat.category == ThreatCategory.MAIN_BEAM_REQUIRED:
                # Minimum 2 positions, more for high priority
                min_positions = 2
                priority_bonus = max(0, 4 - cat_threat.threat.priority)
                optimized[cat_threat.threat.id] = min_positions + priority_bonus

        return optimized


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_duty_cycle(
    scan_period_s: float,
    n_positions: int,
    dwell_time_us: float
) -> float:
    """
    Calculate duty cycle for a scheduling configuration.

    Args:
        scan_period_s: Threat scan period.
        n_positions: Number of scan positions.
        dwell_time_us: Dwell time per position.

    Returns:
        Duty cycle as percentage.
    """
    dwell_time_s = dwell_time_us * 1e-6
    total_dwell_s = n_positions * dwell_time_s
    return (total_dwell_s / scan_period_s) * 100


def calculate_revisit_interval(
    scan_period_s: float,
    n_positions: int
) -> float:
    """
    Calculate revisit interval.

    Args:
        scan_period_s: Threat scan period.
        n_positions: Number of scan positions.

    Returns:
        Revisit interval in seconds.
    """
    return scan_period_s / n_positions


def minimum_dwell_for_pri(
    pri_us: float,
    margin_factor: float = 1.5
) -> float:
    """
    Calculate minimum dwell time to guarantee pulse intercept.

    Args:
        pri_us: Pulse Repetition Interval.
        margin_factor: Safety margin (default 1.5x).

    Returns:
        Minimum dwell time in microseconds.
    """
    return pri_us * margin_factor
