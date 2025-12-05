"""
ADC Saturation and Damage Analyzer

Analyzes received power vs distance for various EIRP levels.
Identifies safe operating distances to avoid ADC damage.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math
import numpy as np

from ..config import ADCConfig


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

SPEED_OF_LIGHT = 299792458  # m/s
MILES_TO_METERS = 1609.34


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PowerLevels:
    """Power levels at different stages for a given EIRP."""
    eirp_dbm: float
    distances_miles: np.ndarray
    power_at_antenna_dbm: np.ndarray
    power_at_lna_output_dbm: np.ndarray
    power_at_adc_dbm: np.ndarray


@dataclass
class CriticalDistances:
    """Critical distances for a given EIRP."""
    eirp_dbm: float
    lna_compression_miles: Optional[float]
    adc_saturation_miles: Optional[float]
    adc_damage_miles: Optional[float]
    status: str  # 'SAFE', 'CAUTION', 'DANGER'


@dataclass
class AttenuatorRecommendation:
    """Attenuator recommendation for safe operation."""
    eirp_dbm: float
    distance_miles: float
    power_at_adc_dbm: float
    target_power_dbm: float
    required_attenuation_db: float
    is_needed: bool


@dataclass
class SaturationResult:
    """Complete saturation analysis results."""
    power_levels: List[PowerLevels]
    critical_distances: List[CriticalDistances]
    attenuator_recommendation: AttenuatorRecommendation
    lna_gain_db: float
    lna_p1db_dbm: float
    adc_fullscale_dbm: float
    adc_damage_dbm: float
    passive_loss_db: float
    antenna_gain_dbi: float
    frequency_ghz: float


# =============================================================================
# ANALYZER CLASS
# =============================================================================

class SaturationAnalyzer:
    """
    Analyzer for ADC saturation and damage thresholds.

    Calculates power levels at each stage vs distance and
    identifies safe operating distances.
    """

    def __init__(self, config: ADCConfig, lna_gain_db: float = 30.0):
        """
        Initialize analyzer with configuration.

        Args:
            config: ADC configuration object.
            lna_gain_db: LNA gain to use for analysis (dB).
        """
        self.config = config
        self.adc = config.adc
        self.lna = config.lna
        self.passive = config.passive
        self.antenna = config.antenna
        self.saturation = config.saturation

        # Use specified LNA gain or first in range
        self.lna_gain_db = lna_gain_db

    def calculate_fspl(self, distance_m: np.ndarray, freq_hz: float) -> np.ndarray:
        """
        Calculate free space path loss.

        Args:
            distance_m: Distance array in meters.
            freq_hz: Frequency in Hz.

        Returns:
            FSPL in dB.
        """
        # FSPL = 20*log10(d) + 20*log10(f) + 20*log10(4*pi/c)
        return (20 * np.log10(distance_m) +
                20 * np.log10(freq_hz) +
                20 * np.log10(4 * np.pi / SPEED_OF_LIGHT))

    def calculate_power_levels(self, eirp_dbm: float,
                               distances_miles: np.ndarray) -> PowerLevels:
        """
        Calculate power levels at each stage vs distance.

        Args:
            eirp_dbm: Transmitter EIRP in dBm.
            distances_miles: Distance array in miles.

        Returns:
            PowerLevels with power at each stage.
        """
        distances_m = distances_miles * MILES_TO_METERS
        freq_hz = self.saturation.frequency_ghz * 1e9

        # Path loss
        fspl = self.calculate_fspl(distances_m, freq_hz)

        # Power at antenna
        power_at_antenna = eirp_dbm - fspl + self.antenna.gain_dbi

        # Power at LNA output
        power_at_lna_output = power_at_antenna + self.lna_gain_db

        # Power at ADC
        power_at_adc = power_at_lna_output - self.passive.total_loss_db

        return PowerLevels(
            eirp_dbm=eirp_dbm,
            distances_miles=distances_miles,
            power_at_antenna_dbm=power_at_antenna,
            power_at_lna_output_dbm=power_at_lna_output,
            power_at_adc_dbm=power_at_adc
        )

    def find_critical_distances(self, power_levels: PowerLevels) -> CriticalDistances:
        """
        Find critical distances for a given EIRP.

        Args:
            power_levels: PowerLevels object.

        Returns:
            CriticalDistances with threshold distances.
        """
        distances = power_levels.distances_miles

        # LNA compression distance
        idx_lna = np.where(power_levels.power_at_lna_output_dbm >= self.lna.p1db_dbm)[0]
        lna_compression = distances[idx_lna[-1]] if len(idx_lna) > 0 else None

        # ADC saturation distance
        idx_sat = np.where(power_levels.power_at_adc_dbm >= self.adc.fullscale_dbm)[0]
        adc_saturation = distances[idx_sat[-1]] if len(idx_sat) > 0 else None

        # ADC damage distance
        idx_dmg = np.where(power_levels.power_at_adc_dbm >= self.adc.max_input_dbm)[0]
        adc_damage = distances[idx_dmg[-1]] if len(idx_dmg) > 0 else None

        # Determine status
        if adc_damage is None:
            status = 'SAFE'
        elif adc_damage >= 50:
            status = 'CAUTION'
        else:
            status = 'DANGER'

        return CriticalDistances(
            eirp_dbm=power_levels.eirp_dbm,
            lna_compression_miles=lna_compression,
            adc_saturation_miles=adc_saturation,
            adc_damage_miles=adc_damage,
            status=status
        )

    def calculate_attenuator(self, power_levels: PowerLevels,
                             distance_miles: float = 1.0) -> AttenuatorRecommendation:
        """
        Calculate required attenuator for safe operation.

        Args:
            power_levels: PowerLevels object.
            distance_miles: Distance for attenuator calculation.

        Returns:
            AttenuatorRecommendation with required attenuation.
        """
        # Find power at specified distance
        idx = np.argmin(np.abs(power_levels.distances_miles - distance_miles))
        actual_distance = power_levels.distances_miles[idx]
        power_at_adc = power_levels.power_at_adc_dbm[idx]

        # Target: 3 dB below full-scale for safety margin
        target_power = self.adc.fullscale_dbm - 3

        # Required attenuation
        required_atten = power_at_adc - target_power
        is_needed = required_atten > 0

        return AttenuatorRecommendation(
            eirp_dbm=power_levels.eirp_dbm,
            distance_miles=actual_distance,
            power_at_adc_dbm=power_at_adc,
            target_power_dbm=target_power,
            required_attenuation_db=max(0, required_atten),
            is_needed=is_needed
        )

    def analyze(self, attenuator_distance_miles: float = 1.0) -> SaturationResult:
        """
        Perform complete saturation analysis.

        Args:
            attenuator_distance_miles: Distance for attenuator calculation.

        Returns:
            SaturationResult with all analysis results.
        """
        # Generate distance array
        distances = np.linspace(
            self.saturation.distance_min_miles,
            self.saturation.distance_max_miles,
            self.saturation.distance_points
        )

        # Analyze each EIRP
        power_levels_list = []
        critical_distances_list = []

        for eirp in self.saturation.eirp_values_dbm:
            power_levels = self.calculate_power_levels(eirp, distances)
            power_levels_list.append(power_levels)

            critical = self.find_critical_distances(power_levels)
            critical_distances_list.append(critical)

        # Calculate attenuator for highest EIRP
        max_eirp = max(self.saturation.eirp_values_dbm)
        max_eirp_idx = self.saturation.eirp_values_dbm.index(max_eirp)
        attenuator = self.calculate_attenuator(
            power_levels_list[max_eirp_idx],
            attenuator_distance_miles
        )

        return SaturationResult(
            power_levels=power_levels_list,
            critical_distances=critical_distances_list,
            attenuator_recommendation=attenuator,
            lna_gain_db=self.lna_gain_db,
            lna_p1db_dbm=self.lna.p1db_dbm,
            adc_fullscale_dbm=self.adc.fullscale_dbm,
            adc_damage_dbm=self.adc.max_input_dbm,
            passive_loss_db=self.passive.total_loss_db,
            antenna_gain_dbi=self.antenna.gain_dbi,
            frequency_ghz=self.saturation.frequency_ghz
        )

    def print_summary(self, result: SaturationResult) -> str:
        """
        Generate formatted summary of saturation analysis.

        Args:
            result: SaturationResult to summarize.

        Returns:
            Formatted string summary.
        """
        lines = [
            "=" * 70,
            "ADC SATURATION AND DAMAGE ANALYSIS",
            "=" * 70,
            "",
            "RECEIVER CONFIGURATION:",
            f"  RX Antenna Gain: {result.antenna_gain_dbi:.1f} dBi",
            f"  LNA Gain: {result.lna_gain_db:.1f} dB",
            f"  LNA P1dB: {result.lna_p1db_dbm:.1f} dBm",
            f"  Passive Losses: {result.passive_loss_db:.1f} dB",
            f"  ADC Full-Scale: {result.adc_fullscale_dbm:.1f} dBm",
            f"  ADC Max (Damage): {result.adc_damage_dbm:.1f} dBm",
            f"  Path Loss Frequency: {result.frequency_ghz:.1f} GHz",
            "",
            "CRITICAL DISTANCES:",
            f"{'EIRP(dBm)':<12} {'LNA Comp.':<15} {'ADC Sat.':<15} {'ADC Damage':<15} {'Status':<10}",
            "-" * 67
        ]

        for cd in result.critical_distances:
            lna_str = f"{cd.lna_compression_miles:.2f}" if cd.lna_compression_miles else "N/A"
            sat_str = f"{cd.adc_saturation_miles:.2f}" if cd.adc_saturation_miles else "N/A"
            dmg_str = f"{cd.adc_damage_miles:.2f}" if cd.adc_damage_miles else "N/A"

            lines.append(
                f"{cd.eirp_dbm:<12.0f} {lna_str:<15} {sat_str:<15} {dmg_str:<15} {cd.status:<10}"
            )

        lines.extend([
            "",
            "Distance values in miles. N/A = never reaches threshold.",
            "",
            "ATTENUATOR RECOMMENDATION:",
            f"  Analysis EIRP: {result.attenuator_recommendation.eirp_dbm:.0f} dBm",
            f"  Distance: {result.attenuator_recommendation.distance_miles:.1f} miles",
            f"  Power at ADC: {result.attenuator_recommendation.power_at_adc_dbm:.1f} dBm",
            f"  Target Power: {result.attenuator_recommendation.target_power_dbm:.1f} dBm",
        ])

        if result.attenuator_recommendation.is_needed:
            lines.append(
                f"  Required Attenuator: {result.attenuator_recommendation.required_attenuation_db:.0f} dB"
            )
        else:
            lines.append("  No attenuator needed at this distance.")

        lines.extend([
            "",
            "NOTES:",
            "  - LNA Compression: Distance where LNA output exceeds P1dB",
            "  - ADC Saturation: Distance where ADC clips (clipping)",
            "  - ADC Damage: Distance where ADC input exceeds max rating",
            "  - Consider limiter/attenuator for close-range operation",
            "=" * 70
        ])

        return "\n".join(lines)
