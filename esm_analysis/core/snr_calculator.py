"""
SNR Calculator Module

Calculates Signal-to-Noise Ratio for ESM detection scenarios.
Handles one-way propagation (passive receiver), sidelobe analysis,
and link budget calculations.
"""

import math
from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum

from ..config.loader import SystemConfig, Threat


# =============================================================================
# CONSTANTS
# =============================================================================

BOLTZMANN_K = 1.380649e-23  # Boltzmann constant (J/K)
SPEED_OF_LIGHT = 299792458  # Speed of light (m/s)


# =============================================================================
# DATA CLASSES
# =============================================================================

class BeamPosition(Enum):
    """Threat antenna beam position relative to ESM receiver."""
    MAIN_BEAM = "main_beam"
    SIDELOBE = "sidelobe"
    BACK_LOBE = "back_lobe"


@dataclass
class SNRResult:
    """Result of SNR calculation for a single scenario."""
    threat_id: str
    threat_name: str
    beam_position: BeamPosition
    range_m: float

    # Link budget components (all in dB)
    eirp_dbw: float           # Effective Isotropic Radiated Power
    path_loss_db: float       # Free space path loss
    atmospheric_loss_db: float  # Atmospheric attenuation
    rx_antenna_gain_dbi: float  # Receiver antenna gain
    system_losses_db: float   # Cable, filter, implementation losses
    received_power_dbw: float # Power at receiver input

    # Noise components
    noise_power_dbw: float    # Thermal noise power
    noise_figure_db: float    # Receiver noise figure

    # Results
    snr_db: float             # Signal-to-Noise Ratio
    threshold_db: float       # Detection threshold
    margin_db: float          # SNR margin above threshold

    # Detection verdict
    detected: bool            # Whether SNR exceeds threshold

    def __str__(self) -> str:
        status = "DETECTED" if self.detected else "NOT DETECTED"
        return (
            f"SNR Result: {self.threat_name} @ {self.range_m/1000:.1f} km "
            f"({self.beam_position.value})\n"
            f"  EIRP: {self.eirp_dbw:.1f} dBW\n"
            f"  Path Loss: {self.path_loss_db:.1f} dB\n"
            f"  Received Power: {self.received_power_dbw:.1f} dBW "
            f"({self.received_power_dbw + 30:.1f} dBm)\n"
            f"  Noise Power: {self.noise_power_dbw:.1f} dBW\n"
            f"  SNR: {self.snr_db:.1f} dB (threshold: {self.threshold_db:.1f} dB)\n"
            f"  Margin: {self.margin_db:+.1f} dB -> {status}"
        )


@dataclass
class MultiBeamSNRResult:
    """SNR results for all beam positions of a threat."""
    threat_id: str
    threat_name: str
    range_m: float

    main_beam_snr: SNRResult
    sidelobe_snr: SNRResult
    back_lobe_snr: SNRResult

    # Summary
    best_snr_db: float
    worst_snr_db: float

    # Categorization inputs
    main_beam_detected: bool
    sidelobe_detected: bool
    back_lobe_detected: bool

    def __str__(self) -> str:
        return (
            f"Multi-Beam SNR: {self.threat_name} @ {self.range_m/1000:.1f} km\n"
            f"  Main Beam:  {self.main_beam_snr.snr_db:+6.1f} dB "
            f"({'✓' if self.main_beam_detected else '✗'})\n"
            f"  Sidelobe:   {self.sidelobe_snr.snr_db:+6.1f} dB "
            f"({'✓' if self.sidelobe_detected else '✗'})\n"
            f"  Back Lobe:  {self.back_lobe_snr.snr_db:+6.1f} dB "
            f"({'✓' if self.back_lobe_detected else '✗'})"
        )


# =============================================================================
# SNR CALCULATOR CLASS
# =============================================================================

class SNRCalculator:
    """
    Calculate SNR for ESM detection scenarios.

    This class implements the one-way radar equation for passive ESM receivers:
        Pr = EIRP - FSPL - L_atm + Gr - L_sys

    Where:
        Pr = Received power (dBW)
        EIRP = Effective Isotropic Radiated Power (dBW)
        FSPL = Free Space Path Loss (dB)
        L_atm = Atmospheric loss (dB)
        Gr = Receiver antenna gain (dBi)
        L_sys = System losses (dB)
    """

    def __init__(self, system_config: SystemConfig, verbose: bool = None):
        """
        Initialize SNR calculator.

        Args:
            system_config: System configuration parameters.
            verbose: Enable verbose output. If None, uses config setting.
        """
        self.config = system_config
        self.receiver = system_config.receiver
        self.environment = system_config.environment
        self.analysis = system_config.analysis

        self.verbose = verbose if verbose is not None else self.analysis.verbose

    # -------------------------------------------------------------------------
    # LINK BUDGET CALCULATIONS
    # -------------------------------------------------------------------------

    def calculate_fspl(self, frequency_hz: float, range_m: float) -> float:
        """
        Calculate Free Space Path Loss.

        FSPL (dB) = 20*log10(d) + 20*log10(f) + 20*log10(4π/c)
                  = 20*log10(d) + 20*log10(f) - 147.55

        Args:
            frequency_hz: Signal frequency in Hz.
            range_m: Distance in meters.

        Returns:
            Path loss in dB (positive value).
        """
        if range_m <= 0 or frequency_hz <= 0:
            return 0.0

        # FSPL = (4*pi*d*f/c)^2 in linear, convert to dB
        fspl_db = (
            20 * math.log10(range_m) +
            20 * math.log10(frequency_hz) +
            20 * math.log10(4 * math.pi / SPEED_OF_LIGHT)
        )
        return fspl_db

    def calculate_atmospheric_loss(
        self,
        frequency_hz: float,
        range_m: float,
        altitude_m: float = None
    ) -> float:
        """
        Calculate atmospheric attenuation loss.

        Simplified ITU-R P.676 model for oxygen and water vapor absorption.

        Args:
            frequency_hz: Signal frequency in Hz.
            range_m: Slant range in meters.
            altitude_m: Platform altitude (for atmospheric density).

        Returns:
            Atmospheric loss in dB.
        """
        if not self.environment.include_atmospheric_loss:
            return 0.0

        if altitude_m is None:
            altitude_m = self.config.platform.altitude_m

        frequency_ghz = frequency_hz / 1e9
        range_km = range_m / 1000

        # Simplified model: specific attenuation varies with frequency
        # At sea level, approximate values:
        #   < 10 GHz: ~0.01 dB/km
        #   10-20 GHz: ~0.02 dB/km (increasing toward 22 GHz water line)
        #   22 GHz: ~0.2 dB/km (water vapor resonance)
        #   60 GHz: ~15 dB/km (oxygen resonance)

        if frequency_ghz < 10:
            gamma = 0.01
        elif frequency_ghz < 20:
            gamma = 0.01 + (frequency_ghz - 10) * 0.002
        elif frequency_ghz < 25:
            # Approach 22 GHz water vapor line
            gamma = 0.03 + (frequency_ghz - 20) * 0.034
        else:
            gamma = 0.05

        # Altitude correction (density decreases with altitude)
        altitude_factor = math.exp(-altitude_m / 8500)  # Scale height ~8.5 km

        return gamma * range_km * altitude_factor

    def calculate_thermal_noise(self, bandwidth_hz: float = None) -> float:
        """
        Calculate thermal noise power.

        N = k * T * B (Watts)
        N (dBW) = -228.6 + 10*log10(T) + 10*log10(B)

        Args:
            bandwidth_hz: Noise bandwidth. If None, uses receiver bandwidth.

        Returns:
            Noise power in dBW.
        """
        if bandwidth_hz is None:
            bandwidth_hz = self.receiver.bandwidth_hz

        temp_k = self.environment.temperature_k

        # N = kTB in dBW
        noise_dbw = (
            10 * math.log10(BOLTZMANN_K) +
            10 * math.log10(temp_k) +
            10 * math.log10(bandwidth_hz)
        )
        return noise_dbw

    def calculate_eirp(
        self,
        threat: Threat,
        beam_position: BeamPosition = BeamPosition.MAIN_BEAM
    ) -> float:
        """
        Calculate Effective Isotropic Radiated Power.

        EIRP = Pt + Gt (in dB)

        Args:
            threat: Threat parameters.
            beam_position: Which part of threat antenna pattern.

        Returns:
            EIRP in dBW.
        """
        pt_dbw = threat.peak_power_dbw

        if beam_position == BeamPosition.MAIN_BEAM:
            gt_dbi = threat.antenna_gain_dbi
        elif beam_position == BeamPosition.SIDELOBE:
            gt_dbi = threat.sidelobe_gain_dbi
        else:  # BACK_LOBE
            gt_dbi = threat.backlobe_gain_dbi

        return pt_dbw + gt_dbi

    # -------------------------------------------------------------------------
    # SNR CALCULATION
    # -------------------------------------------------------------------------

    def calculate_snr(
        self,
        threat: Threat,
        range_m: float,
        beam_position: BeamPosition = BeamPosition.MAIN_BEAM,
        snr_threshold_db: float = None
    ) -> SNRResult:
        """
        Calculate SNR for a single threat scenario.

        Args:
            threat: Threat parameters.
            range_m: Detection range in meters.
            beam_position: Threat antenna beam position.
            snr_threshold_db: Detection threshold. If None, uses config.

        Returns:
            SNRResult with complete link budget breakdown.
        """
        if snr_threshold_db is None:
            snr_threshold_db = self.receiver.snr_threshold_db

        # EIRP calculation
        eirp_dbw = self.calculate_eirp(threat, beam_position)

        # Path losses
        fspl_db = self.calculate_fspl(threat.frequency_hz, range_m)
        atm_loss_db = self.calculate_atmospheric_loss(
            threat.frequency_hz,
            range_m,
            self.config.platform.altitude_m
        )

        # Receiver parameters
        rx_gain_dbi = self.receiver.antenna.gain_dbi
        sys_loss_db = self.receiver.system_losses_db
        nf_db = self.receiver.noise_figure_db

        # Received power
        # Pr = EIRP - FSPL - L_atm + Gr - L_sys
        received_power_dbw = (
            eirp_dbw
            - fspl_db
            - atm_loss_db
            + rx_gain_dbi
            - sys_loss_db
        )

        # Noise power (including noise figure)
        thermal_noise_dbw = self.calculate_thermal_noise()
        noise_power_dbw = thermal_noise_dbw + nf_db

        # SNR calculation
        snr_db = received_power_dbw - noise_power_dbw

        # Detection margin
        margin_db = snr_db - snr_threshold_db
        detected = snr_db >= snr_threshold_db

        result = SNRResult(
            threat_id=threat.id,
            threat_name=threat.name,
            beam_position=beam_position,
            range_m=range_m,
            eirp_dbw=eirp_dbw,
            path_loss_db=fspl_db,
            atmospheric_loss_db=atm_loss_db,
            rx_antenna_gain_dbi=rx_gain_dbi,
            system_losses_db=sys_loss_db,
            received_power_dbw=received_power_dbw,
            noise_power_dbw=noise_power_dbw,
            noise_figure_db=nf_db,
            snr_db=snr_db,
            threshold_db=snr_threshold_db,
            margin_db=margin_db,
            detected=detected
        )

        if self.verbose and self.analysis.debug_output:
            self._debug_snr_calculation(threat, range_m, beam_position, result)

        return result

    def calculate_multi_beam_snr(
        self,
        threat: Threat,
        range_m: float,
        snr_threshold_db: float = None
    ) -> MultiBeamSNRResult:
        """
        Calculate SNR for all beam positions of a threat.

        This is the primary analysis for sidelobe detection categorization.

        Args:
            threat: Threat parameters.
            range_m: Detection range in meters.
            snr_threshold_db: Detection threshold.

        Returns:
            MultiBeamSNRResult with all three beam position results.
        """
        main_beam = self.calculate_snr(
            threat, range_m, BeamPosition.MAIN_BEAM, snr_threshold_db
        )
        sidelobe = self.calculate_snr(
            threat, range_m, BeamPosition.SIDELOBE, snr_threshold_db
        )
        back_lobe = self.calculate_snr(
            threat, range_m, BeamPosition.BACK_LOBE, snr_threshold_db
        )

        return MultiBeamSNRResult(
            threat_id=threat.id,
            threat_name=threat.name,
            range_m=range_m,
            main_beam_snr=main_beam,
            sidelobe_snr=sidelobe,
            back_lobe_snr=back_lobe,
            best_snr_db=max(main_beam.snr_db, sidelobe.snr_db, back_lobe.snr_db),
            worst_snr_db=min(main_beam.snr_db, sidelobe.snr_db, back_lobe.snr_db),
            main_beam_detected=main_beam.detected,
            sidelobe_detected=sidelobe.detected,
            back_lobe_detected=back_lobe.detected
        )

    # -------------------------------------------------------------------------
    # RANGE CALCULATIONS
    # -------------------------------------------------------------------------

    def calculate_max_detection_range(
        self,
        threat: Threat,
        beam_position: BeamPosition = BeamPosition.MAIN_BEAM,
        snr_threshold_db: float = None,
        max_range_m: float = 1e6,
        tolerance_m: float = 100
    ) -> float:
        """
        Calculate maximum detection range for a threat.

        Uses binary search to find range where SNR = threshold.

        Args:
            threat: Threat parameters.
            beam_position: Threat antenna beam position.
            snr_threshold_db: Detection threshold.
            max_range_m: Maximum range to search.
            tolerance_m: Search tolerance in meters.

        Returns:
            Maximum detection range in meters.
        """
        if snr_threshold_db is None:
            snr_threshold_db = self.receiver.snr_threshold_db

        # Binary search for detection range
        low = 0.0
        high = max_range_m

        # Check if detection possible at minimum range
        result = self.calculate_snr(threat, 1000.0, beam_position, snr_threshold_db)
        if not result.detected:
            return 0.0  # Cannot detect even at 1 km

        # Check if detection possible at maximum range
        result = self.calculate_snr(threat, max_range_m, beam_position, snr_threshold_db)
        if result.detected:
            return max_range_m  # Can detect beyond max range

        while (high - low) > tolerance_m:
            mid = (low + high) / 2
            result = self.calculate_snr(threat, mid, beam_position, snr_threshold_db)

            if result.detected:
                low = mid
            else:
                high = mid

        return (low + high) / 2

    def calculate_range_for_snr(
        self,
        threat: Threat,
        target_snr_db: float,
        beam_position: BeamPosition = BeamPosition.MAIN_BEAM,
        max_range_m: float = 1e6,
        tolerance_m: float = 100
    ) -> float:
        """
        Calculate range at which specific SNR is achieved.

        Args:
            threat: Threat parameters.
            target_snr_db: Target SNR in dB.
            beam_position: Threat antenna beam position.
            max_range_m: Maximum range to search.
            tolerance_m: Search tolerance.

        Returns:
            Range in meters where SNR equals target.
        """
        # Use same binary search but with custom threshold
        return self.calculate_max_detection_range(
            threat, beam_position, target_snr_db, max_range_m, tolerance_m
        )

    # -------------------------------------------------------------------------
    # BATCH ANALYSIS
    # -------------------------------------------------------------------------

    def analyze_threats(
        self,
        threats: List[Threat],
        detection_range_m: float = None
    ) -> Dict[str, MultiBeamSNRResult]:
        """
        Analyze multiple threats at specified detection range.

        Args:
            threats: List of threats to analyze.
            detection_range_m: Detection range. If None, uses threat-specific
                              or default from config.

        Returns:
            Dictionary mapping threat_id to MultiBeamSNRResult.
        """
        results = {}

        for threat in threats:
            # Use threat-specific range, or provided range, or default
            range_m = (
                detection_range_m or
                threat.required_detection_range_m or
                self.analysis.required_detection_range_m
            )

            results[threat.id] = self.calculate_multi_beam_snr(threat, range_m)

        return results

    # -------------------------------------------------------------------------
    # DEBUG OUTPUT
    # -------------------------------------------------------------------------

    def _debug_snr_calculation(
        self,
        threat: Threat,
        range_m: float,
        beam_position: BeamPosition,
        result: SNRResult
    ):
        """Print detailed debug output for SNR calculation."""
        print(f"\n{'='*60}")
        print(f"SNR CALCULATION DEBUG: {threat.name}")
        print(f"{'='*60}")
        print(f"Beam Position: {beam_position.value}")
        print(f"Range: {range_m/1000:.2f} km ({range_m:.0f} m)")
        print()

        print("TRANSMITTER:")
        print(f"  Peak Power: {threat.peak_power_w/1000:.1f} kW "
              f"({threat.peak_power_dbw:.1f} dBW)")
        print(f"  Frequency: {threat.frequency_ghz:.2f} GHz")

        if beam_position == BeamPosition.MAIN_BEAM:
            gt = threat.antenna_gain_dbi
        elif beam_position == BeamPosition.SIDELOBE:
            gt = threat.sidelobe_gain_dbi
        else:
            gt = threat.backlobe_gain_dbi

        print(f"  Antenna Gain ({beam_position.value}): {gt:.1f} dBi")
        print(f"  EIRP: {result.eirp_dbw:.1f} dBW")
        print()

        print("PATH LOSSES:")
        print(f"  Free Space Path Loss: {result.path_loss_db:.1f} dB")
        print(f"  Atmospheric Loss: {result.atmospheric_loss_db:.2f} dB")
        print()

        print("RECEIVER:")
        print(f"  Antenna Gain: {result.rx_antenna_gain_dbi:.1f} dBi")
        print(f"  System Losses: {result.system_losses_db:.1f} dB")
        print(f"  Noise Figure: {result.noise_figure_db:.1f} dB")
        print(f"  Bandwidth: {self.receiver.bandwidth_hz/1e6:.1f} MHz")
        print()

        print("RESULTS:")
        print(f"  Received Power: {result.received_power_dbw:.1f} dBW "
              f"({result.received_power_dbw + 30:.1f} dBm)")
        print(f"  Noise Power: {result.noise_power_dbw:.1f} dBW")
        print(f"  SNR: {result.snr_db:.1f} dB")
        print(f"  Threshold: {result.threshold_db:.1f} dB")
        print(f"  Margin: {result.margin_db:+.1f} dB")
        print(f"  Detection: {'YES' if result.detected else 'NO'}")
        print(f"{'='*60}\n")


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_one_way_path_loss(frequency_hz: float, range_m: float) -> float:
    """
    Calculate one-way free space path loss.

    Standalone function for quick calculations.

    Args:
        frequency_hz: Signal frequency in Hz.
        range_m: Range in meters.

    Returns:
        Path loss in dB.
    """
    if range_m <= 0 or frequency_hz <= 0:
        return 0.0

    return (
        20 * math.log10(range_m) +
        20 * math.log10(frequency_hz) +
        20 * math.log10(4 * math.pi / SPEED_OF_LIGHT)
    )


def dbw_to_dbm(power_dbw: float) -> float:
    """Convert dBW to dBm."""
    return power_dbw + 30


def dbm_to_dbw(power_dbm: float) -> float:
    """Convert dBm to dBW."""
    return power_dbm - 30


def watts_to_dbw(power_w: float) -> float:
    """Convert Watts to dBW."""
    if power_w <= 0:
        return -100.0
    return 10 * math.log10(power_w)


def dbw_to_watts(power_dbw: float) -> float:
    """Convert dBW to Watts."""
    return 10 ** (power_dbw / 10)
