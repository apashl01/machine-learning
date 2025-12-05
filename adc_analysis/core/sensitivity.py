"""
ADC Receiver Sensitivity Analyzer

Compares passive-only vs LNA configurations and optimizes
LNA selection for best sensitivity.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import math
import numpy as np

from ..config import ADCConfig


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

BOLTZMANN_K = 1.380649e-23  # J/K
T0 = 290.0  # Reference temperature in Kelvin
THERMAL_NOISE_DBM_HZ = -174.0  # dBm/Hz at 290K


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class LNAConfig:
    """LNA configuration for analysis."""
    gain_db: float
    nf_db: float


@dataclass
class PassiveResult:
    """Results for passive-only configuration."""
    thermal_at_adc_dbm_hz: float
    adc_noise_dbm_hz: float
    total_noise_dbm_hz: float
    noise_power_20mhz_dbm: float
    signal_required_dbm: float
    mds_dbm: float
    system_nf_db: float
    dynamic_range_db: float


@dataclass
class LNAResult:
    """Results for a specific LNA configuration."""
    gain_db: float
    nf_db: float
    system_nf_db: float
    mds_dbm: float
    improvement_db: float
    rf_noise_at_adc_dbm_hz: float
    total_noise_at_adc_dbm_hz: float
    noise_floor_20mhz_dbm: float
    dynamic_range_db: float


@dataclass
class SensitivityResult:
    """Complete sensitivity analysis results."""
    passive: PassiveResult
    lna_results: List[LNAResult]
    optimal_lna: LNAResult
    passive_loss_db: float
    adc_fullscale_dbm: float
    analysis_bw_mhz: float


# =============================================================================
# ANALYZER CLASS
# =============================================================================

class SensitivityAnalyzer:
    """
    Analyzer for ADC receiver sensitivity.

    Compares passive-only vs LNA configurations and finds
    optimal LNA settings for best sensitivity.
    """

    def __init__(self, config: ADCConfig):
        """
        Initialize analyzer with configuration.

        Args:
            config: ADC configuration object.
        """
        self.config = config
        self.adc = config.adc
        self.lna = config.lna
        self.passive = config.passive
        self.analysis = config.analysis

    def analyze_passive_only(self) -> PassiveResult:
        """
        Analyze passive-only configuration (no LNA).

        Returns:
            PassiveResult with sensitivity analysis.
        """
        total_passive_loss = self.passive.total_loss_db
        analysis_bw_hz = self.analysis.analysis_bw_hz
        detection_threshold = self.analysis.detection_threshold_db

        # Thermal noise attenuated by passive losses at ADC input
        thermal_at_adc = THERMAL_NOISE_DBM_HZ - total_passive_loss

        # ADC noise at ADC input
        adc_noise = self.adc.nsd_dbm_hz

        # Total noise at ADC (RSS combination)
        total_noise = 10 * math.log10(
            10 ** (thermal_at_adc / 10) + 10 ** (adc_noise / 10)
        )

        # Noise power in analysis bandwidth
        noise_power_20mhz = total_noise + 10 * math.log10(analysis_bw_hz)

        # Signal required at ADC for detection
        signal_required = noise_power_20mhz + detection_threshold

        # MDS at antenna (add back passive losses)
        mds = signal_required + total_passive_loss

        # System NF (refer noise back to antenna)
        system_nsd_at_antenna = total_noise + total_passive_loss
        system_nf = system_nsd_at_antenna - THERMAL_NOISE_DBM_HZ

        # Dynamic range (noise-limited)
        dr_noise_limited = self.adc.fullscale_dbm - noise_power_20mhz
        dr_sfdr_limited = self.adc.sfdr_dbc
        dynamic_range = min(dr_noise_limited, dr_sfdr_limited)

        return PassiveResult(
            thermal_at_adc_dbm_hz=thermal_at_adc,
            adc_noise_dbm_hz=adc_noise,
            total_noise_dbm_hz=total_noise,
            noise_power_20mhz_dbm=noise_power_20mhz,
            signal_required_dbm=signal_required,
            mds_dbm=mds,
            system_nf_db=system_nf,
            dynamic_range_db=dynamic_range
        )

    def analyze_with_lna(self, lna_gain_db: float, lna_nf_db: float,
                         passive_mds: float) -> LNAResult:
        """
        Analyze configuration with specific LNA.

        Args:
            lna_gain_db: LNA gain in dB.
            lna_nf_db: LNA noise figure in dB.
            passive_mds: MDS of passive-only config for comparison.

        Returns:
            LNAResult with sensitivity analysis.
        """
        total_passive_loss = self.passive.total_loss_db
        analysis_bw_hz = self.analysis.analysis_bw_hz
        detection_threshold = self.analysis.detection_threshold_db

        # Convert to linear
        f_lna = 10 ** (lna_nf_db / 10)
        g_lna = 10 ** (lna_gain_db / 10)
        l_passive = 10 ** (total_passive_loss / 10)
        g_passive = 1 / l_passive
        f_passive = l_passive  # NF = Loss for passive

        # Cascaded NF through LNA -> Passive (Friis)
        f_rf_chain = f_lna + (f_passive - 1) / g_lna

        # RF chain noise at ADC input (dBm/Hz)
        rf_noise_at_adc = (THERMAL_NOISE_DBM_HZ +
                          10 * math.log10(f_rf_chain) +
                          lna_gain_db - total_passive_loss)

        # ADC noise (dBm/Hz)
        adc_noise = self.adc.nsd_dbm_hz

        # Total noise at ADC (RSS)
        total_noise_at_adc = 10 * math.log10(
            10 ** (rf_noise_at_adc / 10) + 10 ** (adc_noise / 10)
        )

        # Noise power in 20 MHz
        noise_floor_20mhz = total_noise_at_adc + 10 * math.log10(analysis_bw_hz)

        # Signal required at ADC
        signal_required = noise_floor_20mhz + detection_threshold

        # MDS at antenna
        mds = signal_required - lna_gain_db + total_passive_loss

        # System NF
        total_noise_at_antenna = total_noise_at_adc - lna_gain_db + total_passive_loss
        system_nf = total_noise_at_antenna - THERMAL_NOISE_DBM_HZ

        # Improvement over passive
        improvement = passive_mds - mds

        # Dynamic range
        dr_noise_limited = self.adc.fullscale_dbm - noise_floor_20mhz
        dr_sfdr_limited = self.adc.sfdr_dbc
        dynamic_range = min(dr_noise_limited, dr_sfdr_limited)

        return LNAResult(
            gain_db=lna_gain_db,
            nf_db=lna_nf_db,
            system_nf_db=system_nf,
            mds_dbm=mds,
            improvement_db=improvement,
            rf_noise_at_adc_dbm_hz=rf_noise_at_adc,
            total_noise_at_adc_dbm_hz=total_noise_at_adc,
            noise_floor_20mhz_dbm=noise_floor_20mhz,
            dynamic_range_db=dynamic_range
        )

    def analyze(self) -> SensitivityResult:
        """
        Perform complete sensitivity analysis.

        Analyzes passive-only and all LNA configurations,
        identifies optimal LNA.

        Returns:
            SensitivityResult with all analysis results.
        """
        # Analyze passive-only
        passive_result = self.analyze_passive_only()

        # Analyze all LNA configurations
        lna_results = []
        for gain_db in self.lna.gain_range_db:
            for nf_db in self.lna.nf_range_db:
                result = self.analyze_with_lna(
                    gain_db, nf_db, passive_result.mds_dbm
                )
                lna_results.append(result)

        # Find optimal LNA (best improvement)
        optimal = max(lna_results, key=lambda r: r.improvement_db)

        return SensitivityResult(
            passive=passive_result,
            lna_results=lna_results,
            optimal_lna=optimal,
            passive_loss_db=self.passive.total_loss_db,
            adc_fullscale_dbm=self.adc.fullscale_dbm,
            analysis_bw_mhz=self.analysis.analysis_bw_mhz
        )

    def get_results_by_gain(self, result: SensitivityResult,
                            gain_db: float) -> List[LNAResult]:
        """Get all LNA results for a specific gain value."""
        return [r for r in result.lna_results if r.gain_db == gain_db]

    def get_results_by_nf(self, result: SensitivityResult,
                          nf_db: float) -> List[LNAResult]:
        """Get all LNA results for a specific NF value."""
        return [r for r in result.lna_results if r.nf_db == nf_db]

    def print_summary(self, result: SensitivityResult) -> str:
        """
        Generate formatted summary of sensitivity analysis.

        Args:
            result: SensitivityResult to summarize.

        Returns:
            Formatted string summary.
        """
        lines = [
            "=" * 70,
            "ADC RECEIVER SENSITIVITY ANALYSIS",
            "=" * 70,
            "",
            "PASSIVE-ONLY CONFIGURATION:",
            f"  Passive Losses: {result.passive_loss_db:.1f} dB",
            f"  Thermal Noise at ADC: {result.passive.thermal_at_adc_dbm_hz:.2f} dBm/Hz",
            f"  ADC Noise: {result.passive.adc_noise_dbm_hz:.2f} dBm/Hz",
            f"  Total Noise at ADC: {result.passive.total_noise_dbm_hz:.2f} dBm/Hz",
            f"  Noise Floor (20 MHz): {result.passive.noise_power_20mhz_dbm:.2f} dBm",
            f"  System NF: {result.passive.system_nf_db:.2f} dB",
            f"  MDS: {result.passive.mds_dbm:.2f} dBm",
            f"  Dynamic Range: {result.passive.dynamic_range_db:.1f} dB",
            "",
            "LNA CONFIGURATION SWEEP:",
            f"{'Gain(dB)':<10} {'NF(dB)':<10} {'Sys NF':<12} {'MDS(dBm)':<12} {'Improvement':<12}",
            "-" * 60
        ]

        for r in result.lna_results:
            lines.append(
                f"{r.gain_db:<10.1f} {r.nf_db:<10.1f} {r.system_nf_db:<12.2f} "
                f"{r.mds_dbm:<12.2f} {r.improvement_db:<12.2f}"
            )

        lines.extend([
            "",
            "OPTIMAL LNA CONFIGURATION:",
            f"  Gain: {result.optimal_lna.gain_db:.1f} dB",
            f"  NF: {result.optimal_lna.nf_db:.1f} dB",
            f"  System NF: {result.optimal_lna.system_nf_db:.2f} dB",
            f"  MDS: {result.optimal_lna.mds_dbm:.2f} dBm",
            f"  Improvement: {result.optimal_lna.improvement_db:.2f} dB",
            f"  Dynamic Range: {result.optimal_lna.dynamic_range_db:.1f} dB",
            "",
            "RECOMMENDATION:"
        ])

        if result.optimal_lna.improvement_db > 3:
            lines.append(f"  Adding an LNA improves sensitivity significantly.")
            lines.append(f"  Suggested: Gain >= {result.optimal_lna.gain_db:.0f} dB, "
                        f"NF <= {result.optimal_lna.nf_db:.1f} dB")
        elif result.optimal_lna.improvement_db > 0:
            lines.append(f"  LNA provides modest improvement ({result.optimal_lna.improvement_db:.1f} dB).")
            lines.append("  Consider cost/complexity trade-offs.")
        else:
            lines.append("  Passive-only configuration is optimal.")

        lines.append("=" * 70)

        return "\n".join(lines)
