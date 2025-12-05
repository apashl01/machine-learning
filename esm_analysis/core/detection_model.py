"""
Detection Model Module

Implements the binary (deterministic) detection model for ESM systems.
Detection is based on hard SNR threshold - not probabilistic.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum

from ..config.loader import SystemConfig, Threat
from .snr_calculator import SNRCalculator, BeamPosition


# =============================================================================
# DATA CLASSES
# =============================================================================

class DetectionStatus(Enum):
    """Detection status based on binary threshold model."""
    DETECTED = "detected"           # SNR >= threshold -> Pd ≈ 99.99%
    NOT_DETECTED = "not_detected"   # SNR < threshold -> Pd = 0%


@dataclass
class DetectionResult:
    """
    Result of binary detection model.

    In the binary model:
    - If SNR >= threshold: Detection is essentially guaranteed (Pd ≈ 99.99%)
    - If SNR < threshold: Detection is not possible (Pd = 0%)

    This is a deterministic model, not a gradual probability curve.
    """
    threat_id: str
    threat_name: str
    range_m: float
    beam_position: BeamPosition

    # SNR values
    snr_db: float
    threshold_db: float
    margin_db: float

    # Detection verdict
    status: DetectionStatus
    detection_probability: float  # 0.0 or ~1.0 (binary)

    # Explanation
    explanation: str = ""

    def __str__(self) -> str:
        prob_str = f"{self.detection_probability*100:.2f}%"
        return (
            f"Detection Result: {self.threat_name}\n"
            f"  Range: {self.range_m/1000:.1f} km\n"
            f"  Beam: {self.beam_position.value}\n"
            f"  SNR: {self.snr_db:.1f} dB (threshold: {self.threshold_db:.1f} dB)\n"
            f"  Margin: {self.margin_db:+.1f} dB\n"
            f"  Status: {self.status.value.upper()}\n"
            f"  Pd: {prob_str}\n"
            f"  {self.explanation}"
        )

    @property
    def is_detected(self) -> bool:
        return self.status == DetectionStatus.DETECTED


@dataclass
class ThreatDetectionSummary:
    """Summary of detection analysis for a threat across all beam positions."""
    threat_id: str
    threat_name: str
    range_m: float

    main_beam_result: DetectionResult
    sidelobe_result: DetectionResult
    back_lobe_result: DetectionResult

    # Overall assessment
    any_detection_possible: bool
    best_beam_for_detection: BeamPosition
    best_snr_margin_db: float

    # Recommendations
    detection_approach: str
    notes: str = ""

    def __str__(self) -> str:
        mb = "✓" if self.main_beam_result.is_detected else "✗"
        sl = "✓" if self.sidelobe_result.is_detected else "✗"
        bl = "✓" if self.back_lobe_result.is_detected else "✗"

        return (
            f"\n{'='*50}\n"
            f"Detection Summary: {self.threat_name}\n"
            f"Range: {self.range_m/1000:.1f} km\n"
            f"{'='*50}\n"
            f"Main Beam:  {mb} SNR: {self.main_beam_result.snr_db:+6.1f} dB\n"
            f"Sidelobe:   {sl} SNR: {self.sidelobe_result.snr_db:+6.1f} dB\n"
            f"Back Lobe:  {bl} SNR: {self.back_lobe_result.snr_db:+6.1f} dB\n"
            f"\nApproach: {self.detection_approach}\n"
            f"Notes: {self.notes}"
        )


# =============================================================================
# DETECTION MODEL CLASS
# =============================================================================

class DetectionModel:
    """
    Binary (deterministic) detection model.

    This model implements a hard threshold approach:
    - SNR >= threshold: Detection guaranteed (Pd ≈ 99.99%)
    - SNR < threshold: No detection (Pd = 0%)

    This differs from probabilistic models that use gradual Pd curves.
    The binary approach is appropriate for digital receivers with
    well-defined detection thresholds.
    """

    # Detection probabilities for binary model
    PD_ABOVE_THRESHOLD = 0.9999  # Essentially guaranteed
    PD_BELOW_THRESHOLD = 0.0     # Cannot detect

    def __init__(
        self,
        system_config: SystemConfig,
        snr_calculator: SNRCalculator = None,
        verbose: bool = None
    ):
        """
        Initialize detection model.

        Args:
            system_config: System configuration.
            snr_calculator: SNR calculator. If None, creates one.
            verbose: Enable verbose output.
        """
        self.config = system_config
        self.verbose = verbose if verbose is not None else system_config.analysis.verbose

        if snr_calculator is None:
            snr_calculator = SNRCalculator(system_config, verbose=False)
        self.snr_calc = snr_calculator

    # -------------------------------------------------------------------------
    # DETECTION EVALUATION
    # -------------------------------------------------------------------------

    def evaluate_detection(
        self,
        threat: Threat,
        range_m: float,
        beam_position: BeamPosition = BeamPosition.MAIN_BEAM,
        threshold_db: float = None
    ) -> DetectionResult:
        """
        Evaluate detection for a single scenario.

        Args:
            threat: Threat parameters.
            range_m: Detection range.
            beam_position: Threat antenna beam position.
            threshold_db: SNR threshold. If None, uses config.

        Returns:
            DetectionResult with binary detection verdict.
        """
        if threshold_db is None:
            threshold_db = self.config.receiver.snr_threshold_db

        # Calculate SNR
        snr_result = self.snr_calc.calculate_snr(
            threat, range_m, beam_position, threshold_db
        )

        # Binary decision
        if snr_result.snr_db >= threshold_db:
            status = DetectionStatus.DETECTED
            pd = self.PD_ABOVE_THRESHOLD
            explanation = (
                f"SNR ({snr_result.snr_db:.1f} dB) exceeds threshold "
                f"({threshold_db:.1f} dB) by {snr_result.margin_db:.1f} dB. "
                f"Detection essentially guaranteed."
            )
        else:
            status = DetectionStatus.NOT_DETECTED
            pd = self.PD_BELOW_THRESHOLD
            explanation = (
                f"SNR ({snr_result.snr_db:.1f} dB) below threshold "
                f"({threshold_db:.1f} dB) by {abs(snr_result.margin_db):.1f} dB. "
                f"Detection not possible - signal below noise floor."
            )

        result = DetectionResult(
            threat_id=threat.id,
            threat_name=threat.name,
            range_m=range_m,
            beam_position=beam_position,
            snr_db=snr_result.snr_db,
            threshold_db=threshold_db,
            margin_db=snr_result.margin_db,
            status=status,
            detection_probability=pd,
            explanation=explanation
        )

        if self.verbose:
            print(result)

        return result

    def evaluate_all_beams(
        self,
        threat: Threat,
        range_m: float,
        threshold_db: float = None
    ) -> ThreatDetectionSummary:
        """
        Evaluate detection for all beam positions.

        Args:
            threat: Threat parameters.
            range_m: Detection range.
            threshold_db: SNR threshold.

        Returns:
            ThreatDetectionSummary with complete analysis.
        """
        main_beam = self.evaluate_detection(
            threat, range_m, BeamPosition.MAIN_BEAM, threshold_db
        )
        sidelobe = self.evaluate_detection(
            threat, range_m, BeamPosition.SIDELOBE, threshold_db
        )
        back_lobe = self.evaluate_detection(
            threat, range_m, BeamPosition.BACK_LOBE, threshold_db
        )

        # Determine best approach
        any_detection = (
            main_beam.is_detected or
            sidelobe.is_detected or
            back_lobe.is_detected
        )

        # Find best beam position
        margins = {
            BeamPosition.MAIN_BEAM: main_beam.margin_db,
            BeamPosition.SIDELOBE: sidelobe.margin_db,
            BeamPosition.BACK_LOBE: back_lobe.margin_db
        }
        best_beam = max(margins, key=margins.get)
        best_margin = margins[best_beam]

        # Determine recommended approach
        if sidelobe.is_detected:
            approach = (
                "SIDELOBE MONITORING: Low duty cycle sufficient. "
                "Threat signal present continuously via sidelobes."
            )
        elif main_beam.is_detected:
            approach = (
                "MAIN BEAM INTERCEPT: Scan position scheduling required. "
                "Must time receiver dwell to catch main beam during scan."
            )
        else:
            approach = (
                "NOT DETECTABLE: Cannot detect at this range. "
                "Need closer range or improved receiver sensitivity."
            )

        # Generate notes
        notes = self._generate_detection_notes(
            threat, range_m, main_beam, sidelobe, back_lobe
        )

        return ThreatDetectionSummary(
            threat_id=threat.id,
            threat_name=threat.name,
            range_m=range_m,
            main_beam_result=main_beam,
            sidelobe_result=sidelobe,
            back_lobe_result=back_lobe,
            any_detection_possible=any_detection,
            best_beam_for_detection=best_beam,
            best_snr_margin_db=best_margin,
            detection_approach=approach,
            notes=notes
        )

    def _generate_detection_notes(
        self,
        threat: Threat,
        range_m: float,
        main_beam: DetectionResult,
        sidelobe: DetectionResult,
        back_lobe: DetectionResult
    ) -> str:
        """Generate detailed notes about detection analysis."""
        notes = []

        # Frequency band note
        freq_ghz = threat.frequency_hz / 1e9
        if freq_ghz < 2:
            band = "VHF/UHF"
        elif freq_ghz < 4:
            band = "S-band"
        elif freq_ghz < 8:
            band = "C-band"
        elif freq_ghz < 12:
            band = "X-band"
        elif freq_ghz < 18:
            band = "Ku-band"
        else:
            band = "K-band+"
        notes.append(f"Frequency: {freq_ghz:.2f} GHz ({band})")

        # Power note
        power_kw = threat.peak_power_w / 1000
        notes.append(f"Peak power: {power_kw:.1f} kW")

        # Sidelobe analysis
        sl_diff = threat.first_sidelobe_db
        notes.append(f"Sidelobe level: {sl_diff:.0f} dB from main beam")

        # Detection margin analysis
        if main_beam.margin_db > 20:
            notes.append("STRONG: Large margin allows detection at extended range")
        elif main_beam.margin_db > 10:
            notes.append("GOOD: Comfortable margin for reliable detection")
        elif main_beam.margin_db > 0:
            notes.append("MARGINAL: Close to threshold, may be affected by fading")
        else:
            notes.append("INSUFFICIENT: Below threshold at required range")

        return "; ".join(notes)

    # -------------------------------------------------------------------------
    # BATCH ANALYSIS
    # -------------------------------------------------------------------------

    def evaluate_threat_list(
        self,
        threats: List[Threat],
        range_m: float = None
    ) -> List[ThreatDetectionSummary]:
        """
        Evaluate detection for multiple threats.

        Args:
            threats: List of threats.
            range_m: Common range, or use threat-specific.

        Returns:
            List of ThreatDetectionSummary objects.
        """
        results = []

        for threat in threats:
            r = range_m or threat.required_detection_range_m or \
                self.config.analysis.required_detection_range_m
            results.append(self.evaluate_all_beams(threat, r))

        return results

    # -------------------------------------------------------------------------
    # RANGE ANALYSIS
    # -------------------------------------------------------------------------

    def find_detection_ranges(
        self,
        threat: Threat,
        threshold_db: float = None
    ) -> Dict[BeamPosition, float]:
        """
        Find maximum detection range for each beam position.

        Args:
            threat: Threat parameters.
            threshold_db: SNR threshold.

        Returns:
            Dictionary mapping beam position to max range.
        """
        if threshold_db is None:
            threshold_db = self.config.receiver.snr_threshold_db

        ranges = {}
        for beam in BeamPosition:
            ranges[beam] = self.snr_calc.calculate_max_detection_range(
                threat, beam, threshold_db
            )

        return ranges

    def generate_detection_table(
        self,
        threats: List[Threat],
        ranges_m: List[float] = None
    ) -> Dict:
        """
        Generate a detection matrix for threats vs ranges.

        Args:
            threats: List of threats.
            ranges_m: List of ranges to evaluate.

        Returns:
            Dictionary with detection matrix data.
        """
        if ranges_m is None:
            ranges_m = [50e3, 100e3, 150e3, 200e3, 300e3]  # Default ranges

        threshold_db = self.config.receiver.snr_threshold_db

        # Build detection matrix
        matrix = {}
        for threat in threats:
            matrix[threat.id] = {
                'name': threat.name,
                'ranges': {}
            }
            for range_m in ranges_m:
                result = self.evaluate_all_beams(threat, range_m, threshold_db)
                matrix[threat.id]['ranges'][range_m] = {
                    'main_beam': result.main_beam_result.is_detected,
                    'sidelobe': result.sidelobe_result.is_detected,
                    'main_beam_snr': result.main_beam_result.snr_db,
                    'sidelobe_snr': result.sidelobe_result.snr_db
                }

        return {
            'threshold_db': threshold_db,
            'ranges_m': ranges_m,
            'threats': matrix
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def is_detectable(
    threat: Threat,
    range_m: float,
    system_config: SystemConfig,
    beam_position: BeamPosition = BeamPosition.MAIN_BEAM
) -> bool:
    """
    Quick check if threat is detectable.

    Args:
        threat: Threat parameters.
        range_m: Detection range.
        system_config: System configuration.
        beam_position: Which beam to check.

    Returns:
        True if detectable, False otherwise.
    """
    model = DetectionModel(system_config, verbose=False)
    result = model.evaluate_detection(threat, range_m, beam_position)
    return result.is_detected


def get_max_detection_range(
    threat: Threat,
    system_config: SystemConfig,
    beam_position: BeamPosition = BeamPosition.MAIN_BEAM
) -> float:
    """
    Get maximum detection range for a threat.

    Args:
        threat: Threat parameters.
        system_config: System configuration.
        beam_position: Which beam to use.

    Returns:
        Maximum detection range in meters.
    """
    model = DetectionModel(system_config, verbose=False)
    ranges = model.find_detection_ranges(threat)
    return ranges[beam_position]
