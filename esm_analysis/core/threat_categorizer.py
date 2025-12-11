"""
Threat Categorizer Module

Categorizes threats based on sidelobe detectability analysis.
Determines whether threats can be detected via sidelobes (always present)
or require main beam intercept (scan scheduling needed).
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

from ..config.loader import SystemConfig, Threat, ThreatLibrary
from .snr_calculator import SNRCalculator, MultiBeamSNRResult, BeamPosition
from .detection_model import calculate_albersheim_pd


# =============================================================================
# ENUMS AND CATEGORIES
# =============================================================================

class ThreatCategory(Enum):
    """
    Threat detection category based on sidelobe analysis.

    SIDELOBE_DETECTABLE: Can detect threat via sidelobes - signal always present
                        regardless of where main beam is pointing. Low duty cycle
                        monitoring sufficient.

    MAIN_BEAM_REQUIRED: Must catch main beam to detect. Requires scan position
                       dwell scheduling to guarantee intercept.

    UNDETECTABLE: Cannot detect even with main beam pointing at us at required
                 range. May need closer range or different approach.
    """
    SIDELOBE_DETECTABLE = "sidelobe_detectable"
    MAIN_BEAM_REQUIRED = "main_beam_required"
    UNDETECTABLE = "undetectable"


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class CategorizedThreat:
    """Complete categorization result for a single threat."""
    threat: Threat
    category: ThreatCategory

    # Detection range used for analysis
    detection_range_m: float

    # SNR results for all beam positions
    snr_results: MultiBeamSNRResult

    # Detailed SNR values
    main_beam_snr_db: float
    sidelobe_snr_db: float
    back_lobe_snr_db: float

    # Detection margins (positive = detectable)
    main_beam_margin_db: float
    sidelobe_margin_db: float
    back_lobe_margin_db: float

    # Maximum detection ranges for each beam position
    max_range_main_beam_m: float = 0.0
    max_range_sidelobe_m: float = 0.0
    max_range_back_lobe_m: float = 0.0

    # Scheduling parameters (computed later if needed)
    recommended_dwell_time_us: float = 0.0
    recommended_check_interval_s: float = 0.0
    scan_positions_required: int = 0

    # Notes
    categorization_notes: str = ""

    def __str__(self) -> str:
        cat_str = self.category.value.upper().replace('_', ' ')
        return (
            f"\n{'='*60}\n"
            f"THREAT CATEGORIZATION: {self.threat.name}\n"
            f"{'='*60}\n"
            f"Category: {cat_str}\n"
            f"Detection Range: {self.detection_range_m/1000:.1f} km\n"
            f"\nSNR Analysis:\n"
            f"  Main Beam:  {self.main_beam_snr_db:+7.1f} dB "
            f"(margin: {self.main_beam_margin_db:+.1f} dB) "
            f"{'✓' if self.main_beam_margin_db >= 0 else '✗'}\n"
            f"  Sidelobe:   {self.sidelobe_snr_db:+7.1f} dB "
            f"(margin: {self.sidelobe_margin_db:+.1f} dB) "
            f"{'✓' if self.sidelobe_margin_db >= 0 else '✗'}\n"
            f"  Back Lobe:  {self.back_lobe_snr_db:+7.1f} dB "
            f"(margin: {self.back_lobe_margin_db:+.1f} dB) "
            f"{'✓' if self.back_lobe_margin_db >= 0 else '✗'}\n"
            f"\nMax Detection Ranges:\n"
            f"  Main Beam:  {self.max_range_main_beam_m/1000:.1f} km\n"
            f"  Sidelobe:   {self.max_range_sidelobe_m/1000:.1f} km\n"
            f"  Back Lobe:  {self.max_range_back_lobe_m/1000:.1f} km\n"
            f"\nNotes: {self.categorization_notes}"
        )

    @property
    def is_detectable(self) -> bool:
        """Whether threat is detectable at required range."""
        return self.category != ThreatCategory.UNDETECTABLE

    @property
    def requires_scheduling(self) -> bool:
        """Whether threat requires scan position scheduling."""
        return self.category == ThreatCategory.MAIN_BEAM_REQUIRED


@dataclass
class CategorizationSummary:
    """Summary of threat categorization results."""
    total_threats: int = 0
    sidelobe_detectable: List[CategorizedThreat] = field(default_factory=list)
    main_beam_required: List[CategorizedThreat] = field(default_factory=list)
    undetectable: List[CategorizedThreat] = field(default_factory=list)

    # Statistics
    percent_sidelobe_detectable: float = 0.0
    percent_main_beam_required: float = 0.0
    percent_undetectable: float = 0.0

    def __str__(self) -> str:
        return (
            f"\n{'='*60}\n"
            f"CATEGORIZATION SUMMARY\n"
            f"{'='*60}\n"
            f"Total Threats Analyzed: {self.total_threats}\n\n"
            f"Sidelobe Detectable: {len(self.sidelobe_detectable)} "
            f"({self.percent_sidelobe_detectable:.1f}%)\n"
            f"  - Low duty cycle monitoring sufficient\n"
            f"  - Signal always present via sidelobes\n"
            f"  {[t.threat.name for t in self.sidelobe_detectable]}\n\n"
            f"Main Beam Required: {len(self.main_beam_required)} "
            f"({self.percent_main_beam_required:.1f}%)\n"
            f"  - Requires scan position scheduling\n"
            f"  - Must catch main beam during scan\n"
            f"  {[t.threat.name for t in self.main_beam_required]}\n\n"
            f"Undetectable: {len(self.undetectable)} "
            f"({self.percent_undetectable:.1f}%)\n"
            f"  - Cannot detect at required range\n"
            f"  {[t.threat.name for t in self.undetectable]}"
        )


# =============================================================================
# THREAT CATEGORIZER CLASS
# =============================================================================

class ThreatCategorizer:
    """
    Categorize threats based on sidelobe detectability.

    The key insight is that radar antennas always have sidelobes radiating
    in all directions. If the sidelobe signal is strong enough to detect,
    we don't need to catch the main beam - we can detect the threat
    whenever we want with minimal receiver duty cycle.

    Only threats where sidelobe SNR is insufficient require us to time
    our receiver dwell to catch the main beam during its scan.
    """

    def __init__(
        self,
        system_config: SystemConfig,
        snr_calculator: SNRCalculator = None,
        verbose: bool = None
    ):
        """
        Initialize threat categorizer.

        Args:
            system_config: System configuration.
            snr_calculator: SNR calculator instance. If None, creates one.
            verbose: Enable verbose output.
        """
        self.config = system_config
        self.analysis = system_config.analysis

        self.verbose = verbose if verbose is not None else self.analysis.verbose

        if snr_calculator is None:
            snr_calculator = SNRCalculator(system_config, verbose=False)
        self.snr_calc = snr_calculator

    # -------------------------------------------------------------------------
    # SINGLE THREAT CATEGORIZATION
    # -------------------------------------------------------------------------

    def categorize_threat(
        self,
        threat: Threat,
        detection_range_m: float = None,
        snr_threshold_db: float = None
    ) -> CategorizedThreat:
        """
        Categorize a single threat based on sidelobe analysis.

        Args:
            threat: Threat to categorize.
            detection_range_m: Required detection range. If None, uses
                              threat-specific or default.
            snr_threshold_db: SNR threshold. If None, uses config default.

        Returns:
            CategorizedThreat with complete analysis.
        """
        # Determine detection range
        if detection_range_m is None:
            detection_range_m = (
                threat.required_detection_range_m or
                self.analysis.required_detection_range_m
            )

        if snr_threshold_db is None:
            snr_threshold_db = self.config.receiver.snr_threshold_db

        # Calculate SNR for all beam positions
        snr_results = self.snr_calc.calculate_multi_beam_snr(
            threat, detection_range_m, snr_threshold_db
        )

        # Extract individual results
        main_beam_snr = snr_results.main_beam_snr.snr_db
        sidelobe_snr = snr_results.sidelobe_snr.snr_db
        back_lobe_snr = snr_results.back_lobe_snr.snr_db

        main_beam_margin = snr_results.main_beam_snr.margin_db
        sidelobe_margin = snr_results.sidelobe_snr.margin_db
        back_lobe_margin = snr_results.back_lobe_snr.margin_db

        # Calculate max detection ranges
        max_range_main = self.snr_calc.calculate_max_detection_range(
            threat, BeamPosition.MAIN_BEAM, snr_threshold_db
        )
        max_range_side = self.snr_calc.calculate_max_detection_range(
            threat, BeamPosition.SIDELOBE, snr_threshold_db
        )
        max_range_back = self.snr_calc.calculate_max_detection_range(
            threat, BeamPosition.BACK_LOBE, snr_threshold_db
        )

        # Determine category
        category, notes = self._determine_category(
            snr_results, detection_range_m, snr_threshold_db
        )

        # Build result
        result = CategorizedThreat(
            threat=threat,
            category=category,
            detection_range_m=detection_range_m,
            snr_results=snr_results,
            main_beam_snr_db=main_beam_snr,
            sidelobe_snr_db=sidelobe_snr,
            back_lobe_snr_db=back_lobe_snr,
            main_beam_margin_db=main_beam_margin,
            sidelobe_margin_db=sidelobe_margin,
            back_lobe_margin_db=back_lobe_margin,
            max_range_main_beam_m=max_range_main,
            max_range_sidelobe_m=max_range_side,
            max_range_back_lobe_m=max_range_back,
            categorization_notes=notes
        )

        # Add scheduling parameters for main-beam-required threats
        if category == ThreatCategory.MAIN_BEAM_REQUIRED:
            self._compute_scheduling_parameters(result)

        if self.verbose:
            print(result)

        return result

    def _determine_category(
        self,
        snr_results: MultiBeamSNRResult,
        detection_range_m: float,
        snr_threshold_db: float
    ) -> tuple:
        """
        Determine threat category based on probability of detection (Pd).

        Task 5 Update: Uses Pd-based detection (Pd >= 50% = detectable) instead
        of simple SNR threshold comparison. This provides a probabilistic
        assessment using Albersheim's approximation.

        Returns:
            Tuple of (ThreatCategory, explanation_string)
        """
        # Calculate Pd for each beam position using Albersheim's approximation
        # Use Pfa from config (default 1e-6) and n_pulses=1 for single-pulse detection
        pfa = getattr(self.config.receiver, 'pfa', 1e-6) if hasattr(self.config, 'receiver') else 1e-6

        main_beam_pd = calculate_albersheim_pd(snr_results.main_beam_snr.snr_db, pfa=pfa)
        sidelobe_pd = calculate_albersheim_pd(snr_results.sidelobe_snr.snr_db, pfa=pfa)
        back_lobe_pd = calculate_albersheim_pd(snr_results.back_lobe_snr.snr_db, pfa=pfa)

        # Detection threshold: Pd >= 50%
        PD_THRESHOLD = 0.50

        main_beam_ok = main_beam_pd >= PD_THRESHOLD
        sidelobe_ok = sidelobe_pd >= PD_THRESHOLD
        back_lobe_ok = back_lobe_pd >= PD_THRESHOLD

        # Priority: sidelobe detection is best (lowest duty cycle)
        if sidelobe_ok:
            return (
                ThreatCategory.SIDELOBE_DETECTABLE,
                f"Sidelobe Pd ({sidelobe_pd*100:.1f}%) >= 50%. "
                f"SNR: {snr_results.sidelobe_snr.snr_db:.1f} dB. "
                f"Threat radiates continuously via sidelobes - low duty cycle monitoring sufficient."
            )

        # If only main beam works
        if main_beam_ok:
            return (
                ThreatCategory.MAIN_BEAM_REQUIRED,
                f"Sidelobe Pd ({sidelobe_pd*100:.1f}%) < 50%. "
                f"Main beam Pd ({main_beam_pd*100:.1f}%) >= 50%. "
                f"Must schedule receiver to catch main beam during scan."
            )

        # Cannot detect at all
        return (
            ThreatCategory.UNDETECTABLE,
            f"All beam positions have Pd < 50% at {detection_range_m/1000:.1f} km. "
            f"Main beam Pd: {main_beam_pd*100:.1f}%, Sidelobe Pd: {sidelobe_pd*100:.1f}%. "
            f"Need closer range or different approach."
        )

    def _compute_scheduling_parameters(self, result: CategorizedThreat):
        """
        Compute recommended scheduling parameters for main-beam-required threats.
        """
        threat = result.threat

        # Recommended dwell time: 1.5x PRI to catch at least one pulse
        result.recommended_dwell_time_us = (
            threat.pri_us * self.analysis.dwell_margin_factor
        )

        # Number of scan positions based on config default
        result.scan_positions_required = self.analysis.default_scan_positions

        # Check interval = scan_period / n_positions
        result.recommended_check_interval_s = (
            threat.scan_period_s / result.scan_positions_required
        )

    # -------------------------------------------------------------------------
    # BATCH CATEGORIZATION
    # -------------------------------------------------------------------------

    def categorize_threats(
        self,
        threats: List[Threat],
        detection_range_m: float = None
    ) -> CategorizationSummary:
        """
        Categorize multiple threats.

        Args:
            threats: List of threats to categorize.
            detection_range_m: Common detection range (or use threat-specific).

        Returns:
            CategorizationSummary with all results.
        """
        summary = CategorizationSummary()
        summary.total_threats = len(threats)

        for threat in threats:
            result = self.categorize_threat(threat, detection_range_m)

            if result.category == ThreatCategory.SIDELOBE_DETECTABLE:
                summary.sidelobe_detectable.append(result)
            elif result.category == ThreatCategory.MAIN_BEAM_REQUIRED:
                summary.main_beam_required.append(result)
            else:
                summary.undetectable.append(result)

        # Calculate percentages
        if summary.total_threats > 0:
            summary.percent_sidelobe_detectable = (
                100 * len(summary.sidelobe_detectable) / summary.total_threats
            )
            summary.percent_main_beam_required = (
                100 * len(summary.main_beam_required) / summary.total_threats
            )
            summary.percent_undetectable = (
                100 * len(summary.undetectable) / summary.total_threats
            )

        if self.verbose:
            print(summary)

        return summary

    def categorize_threat_library(
        self,
        threat_library: ThreatLibrary,
        threat_set: str = None,
        detection_range_m: float = None
    ) -> CategorizationSummary:
        """
        Categorize threats from a threat library.

        Args:
            threat_library: Threat library to analyze.
            threat_set: Name of threat set to analyze. If None, uses all.
            detection_range_m: Common detection range.

        Returns:
            CategorizationSummary with all results.
        """
        if threat_set:
            threats = threat_library.get_threat_set(threat_set)
        else:
            threats = list(threat_library)

        return self.categorize_threats(threats, detection_range_m)

    # -------------------------------------------------------------------------
    # ANALYSIS HELPERS
    # -------------------------------------------------------------------------

    def analyze_range_sensitivity(
        self,
        threat: Threat,
        range_start_m: float = 10000,
        range_end_m: float = 500000,
        num_points: int = 50
    ) -> Dict:
        """
        Analyze how threat category changes with range.

        Args:
            threat: Threat to analyze.
            range_start_m: Start of range sweep.
            range_end_m: End of range sweep.
            num_points: Number of range points.

        Returns:
            Dictionary with range sweep results.
        """
        import numpy as np

        ranges_m = np.linspace(range_start_m, range_end_m, num_points)
        categories = []
        main_beam_snr = []
        sidelobe_snr = []

        for range_m in ranges_m:
            result = self.categorize_threat(threat, range_m)
            categories.append(result.category.value)
            main_beam_snr.append(result.main_beam_snr_db)
            sidelobe_snr.append(result.sidelobe_snr_db)

        # Find category transition ranges
        transition_ranges = {}

        # Find range where sidelobe detection fails
        for i, cat in enumerate(categories):
            if cat == ThreatCategory.MAIN_BEAM_REQUIRED.value and i > 0:
                if categories[i-1] == ThreatCategory.SIDELOBE_DETECTABLE.value:
                    transition_ranges['sidelobe_to_main_beam_m'] = ranges_m[i]
                    break

        # Find range where main beam detection fails
        for i, cat in enumerate(categories):
            if cat == ThreatCategory.UNDETECTABLE.value and i > 0:
                if categories[i-1] == ThreatCategory.MAIN_BEAM_REQUIRED.value:
                    transition_ranges['main_beam_to_undetectable_m'] = ranges_m[i]
                    break

        return {
            'threat_id': threat.id,
            'threat_name': threat.name,
            'ranges_m': ranges_m.tolist(),
            'categories': categories,
            'main_beam_snr_db': main_beam_snr,
            'sidelobe_snr_db': sidelobe_snr,
            'transition_ranges': transition_ranges
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def quick_categorize(
    threat: Threat,
    system_config: SystemConfig,
    detection_range_m: float = None
) -> ThreatCategory:
    """
    Quick threat categorization without full analysis.

    Args:
        threat: Threat to categorize.
        system_config: System configuration.
        detection_range_m: Detection range.

    Returns:
        ThreatCategory enum value.
    """
    categorizer = ThreatCategorizer(system_config, verbose=False)
    result = categorizer.categorize_threat(threat, detection_range_m)
    return result.category
