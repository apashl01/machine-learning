"""
RF Chain Analyzer

Cascaded analysis of RF receiver and transmitter chains.
Matches MATLAB analyze_rf_chain.m functionality including:
- Cascaded gain calculation across frequency
- Cascaded noise figure (Friis formula)
- TX mode: Power tracking with saturation detection
- RX mode: Damage threshold analysis
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import math
import numpy as np

from ..config.loader import (
    ChainConfig, Component, ComponentType,
    CableComponent, AmplifierComponent, AttenuatorComponent, AntennaComponent
)


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

BOLTZMANN_K = 1.380649e-23  # J/K
T0 = 290.0  # Reference temperature in Kelvin


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ComponentContribution:
    """Component performance at a specific frequency."""
    name: str
    gain_db: float
    nf_db: Optional[float] = None
    output_power_dbm: Optional[float] = None
    output_power_watts: Optional[float] = None
    saturated: bool = False
    power_at_threshold_dbm: Optional[float] = None


@dataclass
class MidFreqSummary:
    """Performance summary at middle frequency."""
    frequency_ghz: float
    total_gain_db: float
    cascaded_nf_db: Optional[float] = None

    # TX mode
    input_power_dbm: Optional[float] = None
    output_power_dbm: Optional[float] = None
    output_power_watts: Optional[float] = None
    saturated_amplifiers: List[str] = field(default_factory=list)

    # RX mode
    damage_level_dbm: Optional[float] = None
    min_safe_input_power_dbm: Optional[float] = None
    adc_input_power_at_threshold_dbm: Optional[float] = None
    power_through_chain_at_threshold: Optional[np.ndarray] = None

    # Component breakdown
    component_contributions: Dict[str, ComponentContribution] = field(default_factory=dict)


@dataclass
class ChainAnalysisResults:
    """
    Complete RF chain analysis results.

    Matches MATLAB analyze_rf_chain.m output structure.
    """
    # Frequency data
    freq_ghz: np.ndarray
    n_freq: int
    n_components: int

    # Cascaded results vs frequency
    total_gain_db: np.ndarray
    cascaded_nf_db: np.ndarray
    component_gains: np.ndarray  # [n_components, n_freq]
    component_nfs: np.ndarray    # [n_components, n_freq]
    component_names: List[str]

    # Summary at mid-frequency
    mid_freq_summary: MidFreqSummary

    # Flags
    has_nf_data: bool
    is_transmit: bool
    has_power_tracking: bool
    has_rx_sweep: bool

    # TX mode results (if applicable)
    power_through_chain_dbm: Optional[np.ndarray] = None  # [n_components+1, n_freq]
    power_through_chain_watts: Optional[np.ndarray] = None
    final_output_power_dbm: Optional[np.ndarray] = None
    final_output_power_watts: Optional[np.ndarray] = None
    saturation_flags: Optional[np.ndarray] = None  # [n_components, n_freq]

    # RX mode results (if applicable)
    damage_level_dbm: Optional[float] = None
    min_damage_threshold_dbm: Optional[np.ndarray] = None  # vs frequency
    input_power_range_dbm: Optional[List[float]] = None

    # Reference to original config
    chain_config: Optional[ChainConfig] = None


# =============================================================================
# ANALYZER CLASS
# =============================================================================

class RFChainAnalyzer:
    """
    Analyzer for cascaded RF chain performance.

    Matches MATLAB analyze_rf_chain.m functionality.
    """

    def __init__(self, n_freq_points: int = 200):
        """
        Initialize analyzer.

        Args:
            n_freq_points: Number of frequency points for analysis.
        """
        self.n_freq_points = n_freq_points

    def analyze(self, chain: ChainConfig) -> ChainAnalysisResults:
        """
        Analyze RF chain across frequency range.

        Matches MATLAB analyze_rf_chain(chain_config) function.

        Args:
            chain: ChainConfig to analyze.

        Returns:
            ChainAnalysisResults with all analysis data.
        """
        # Get frequency range and create vector
        freq_min = chain.get_freq_min()
        freq_max = chain.get_freq_max()
        freq_ghz = np.linspace(freq_min, freq_max, self.n_freq_points)
        n_freq = len(freq_ghz)

        # Get ordered components
        components = chain.get_components_ordered()
        n_components = len(components)
        component_names = [c.name for c in components]

        # Pre-allocate arrays
        component_gains = np.zeros((n_components, n_freq))
        component_nfs = np.full((n_components, n_freq), np.nan)
        component_psat = np.full(n_components, np.nan)

        # Compute performance for each component at each frequency
        for idx, comp in enumerate(components):
            for f_idx, freq in enumerate(freq_ghz):
                # Get gain
                if isinstance(comp, AttenuatorComponent):
                    gain = comp.get_gain_at_freq(freq, freq_min, freq_max)
                    nf = comp.get_nf_at_freq(freq, freq_min, freq_max)
                else:
                    gain = comp.get_gain_at_freq(freq)
                    nf = comp.get_nf_at_freq(freq)

                component_gains[idx, f_idx] = gain

                # Get noise figure
                if nf is not None:
                    component_nfs[idx, f_idx] = nf

            # Get Psat for amplifiers
            if isinstance(comp, AmplifierComponent) and comp.psat_dbm is not None:
                component_psat[idx] = comp.psat_dbm

        # Compute cascaded total gain
        total_gain_db = np.sum(component_gains, axis=0)

        # Calculate mid-frequency index
        mid_freq_ghz = (freq_min + freq_max) / 2
        mid_idx = np.argmin(np.abs(freq_ghz - mid_freq_ghz))

        # Determine chain type and analysis mode
        is_transmit = chain.is_transmit
        do_rx_power_sweep = (not is_transmit and chain.has_damage_threshold)

        # TX mode: Track power through chain with saturation checking
        has_power_tracking = False
        power_through_chain_dbm = None
        power_through_chain_watts = None
        final_output_power_dbm = None
        final_output_power_watts = None
        saturation_flags = None

        if is_transmit:
            has_power_tracking = True
            power_through_chain_dbm = np.zeros((n_components + 1, n_freq))
            saturation_flags = np.zeros((n_components, n_freq), dtype=bool)

            # Initial power (source)
            power_through_chain_dbm[0, :] = chain.source_power_dbm

            # Track power through each component
            for comp_idx, comp in enumerate(components):
                power_after = power_through_chain_dbm[comp_idx, :] + component_gains[comp_idx, :]

                # Check for amplifier saturation
                if isinstance(comp, AmplifierComponent) and not np.isnan(component_psat[comp_idx]):
                    saturated = power_after > component_psat[comp_idx]
                    saturation_flags[comp_idx, saturated] = True
                    power_after[saturated] = component_psat[comp_idx]

                power_through_chain_dbm[comp_idx + 1, :] = power_after

            final_output_power_dbm = power_through_chain_dbm[-1, :]
            final_output_power_watts = self._dbm_to_watts(final_output_power_dbm)
            power_through_chain_watts = self._dbm_to_watts(power_through_chain_dbm)

        # RX mode: Damage threshold analysis
        has_rx_sweep = False
        damage_level_dbm = None
        min_damage_threshold_dbm = None
        power_through_chain_at_threshold = None

        if do_rx_power_sweep:
            has_rx_sweep = True
            damage_level_dbm = chain.damage_level_dbm

            # For each frequency, find max input power before output exceeds damage level
            min_damage_threshold_dbm = np.zeros(n_freq)

            for f_idx in range(n_freq):
                # Total gain through entire chain
                total_chain_gain = np.sum(component_gains[:, f_idx])
                # Max safe input = damage level - total gain
                min_damage_threshold_dbm[f_idx] = damage_level_dbm - total_chain_gain

            # Compute power through chain at mid-frequency with max safe input
            mid_safe_power = min_damage_threshold_dbm[mid_idx]
            power_through_chain_at_threshold = np.zeros(n_components + 2)  # +2 for input and ADC
            power_through_chain_at_threshold[0] = mid_safe_power

            for comp_idx in range(n_components):
                power_through_chain_at_threshold[comp_idx + 1] = \
                    power_through_chain_at_threshold[comp_idx] + component_gains[comp_idx, mid_idx]

            # ADC input = output of last component
            power_through_chain_at_threshold[-1] = power_through_chain_at_threshold[n_components]

        # Compute cascaded noise figure using Friis formula
        cascaded_nf_db, has_nf_data = self._compute_cascaded_nf(
            component_gains, component_nfs, n_freq, n_components
        )

        # Build mid-frequency summary
        mid_freq_summary = self._build_mid_freq_summary(
            freq_ghz=freq_ghz,
            mid_idx=mid_idx,
            total_gain_db=total_gain_db,
            cascaded_nf_db=cascaded_nf_db,
            has_nf_data=has_nf_data,
            component_gains=component_gains,
            component_nfs=component_nfs,
            component_names=component_names,
            components=components,
            chain=chain,
            has_power_tracking=has_power_tracking,
            power_through_chain_dbm=power_through_chain_dbm,
            power_through_chain_watts=power_through_chain_watts,
            saturation_flags=saturation_flags,
            has_rx_sweep=has_rx_sweep,
            damage_level_dbm=damage_level_dbm,
            min_damage_threshold_dbm=min_damage_threshold_dbm,
            power_through_chain_at_threshold=power_through_chain_at_threshold
        )

        return ChainAnalysisResults(
            freq_ghz=freq_ghz,
            n_freq=n_freq,
            n_components=n_components,
            total_gain_db=total_gain_db,
            cascaded_nf_db=cascaded_nf_db,
            component_gains=component_gains,
            component_nfs=component_nfs,
            component_names=component_names,
            mid_freq_summary=mid_freq_summary,
            has_nf_data=has_nf_data,
            is_transmit=is_transmit,
            has_power_tracking=has_power_tracking,
            has_rx_sweep=has_rx_sweep,
            power_through_chain_dbm=power_through_chain_dbm,
            power_through_chain_watts=power_through_chain_watts,
            final_output_power_dbm=final_output_power_dbm,
            final_output_power_watts=final_output_power_watts,
            saturation_flags=saturation_flags,
            damage_level_dbm=damage_level_dbm,
            min_damage_threshold_dbm=min_damage_threshold_dbm,
            input_power_range_dbm=chain.input_power_range_dbm,
            chain_config=chain
        )

    def _compute_cascaded_nf(self, component_gains: np.ndarray, component_nfs: np.ndarray,
                              n_freq: int, n_components: int) -> tuple:
        """
        Compute cascaded noise figure using Friis formula.

        NF_total = NF1 + (NF2-1)/G1 + (NF3-1)/(G1*G2) + ...
        """
        cascaded_nf_linear = np.zeros(n_freq)
        has_nf_data = False

        for f_idx in range(n_freq):
            nf_total_linear = 0.0
            gain_product_linear = 1.0  # Cumulative gain up to current stage

            for comp_idx in range(n_components):
                nf_db = component_nfs[comp_idx, f_idx]
                gain_db = component_gains[comp_idx, f_idx]

                if not np.isnan(nf_db):
                    has_nf_data = True
                    nf_linear = 10 ** (nf_db / 10)

                    # Add this stage's contribution
                    if comp_idx == 0:
                        nf_total_linear = nf_linear
                    else:
                        nf_total_linear = nf_total_linear + (nf_linear - 1) / gain_product_linear

                # Update cumulative gain for next stage
                gain_linear = 10 ** (gain_db / 10)
                gain_product_linear = gain_product_linear * gain_linear

            cascaded_nf_linear[f_idx] = nf_total_linear

        # Convert back to dB
        if has_nf_data:
            cascaded_nf_db = 10 * np.log10(np.maximum(cascaded_nf_linear, 1e-10))
        else:
            cascaded_nf_db = np.full(n_freq, np.nan)

        return cascaded_nf_db, has_nf_data

    def _build_mid_freq_summary(self, **kwargs) -> MidFreqSummary:
        """Build mid-frequency summary structure."""
        freq_ghz = kwargs['freq_ghz']
        mid_idx = kwargs['mid_idx']
        total_gain_db = kwargs['total_gain_db']
        cascaded_nf_db = kwargs['cascaded_nf_db']
        has_nf_data = kwargs['has_nf_data']
        component_gains = kwargs['component_gains']
        component_nfs = kwargs['component_nfs']
        component_names = kwargs['component_names']
        components = kwargs['components']
        chain = kwargs['chain']
        has_power_tracking = kwargs['has_power_tracking']
        power_through_chain_dbm = kwargs['power_through_chain_dbm']
        power_through_chain_watts = kwargs['power_through_chain_watts']
        saturation_flags = kwargs['saturation_flags']
        has_rx_sweep = kwargs['has_rx_sweep']
        damage_level_dbm = kwargs['damage_level_dbm']
        min_damage_threshold_dbm = kwargs['min_damage_threshold_dbm']
        power_through_chain_at_threshold = kwargs['power_through_chain_at_threshold']

        summary = MidFreqSummary(
            frequency_ghz=freq_ghz[mid_idx],
            total_gain_db=total_gain_db[mid_idx],
            cascaded_nf_db=cascaded_nf_db[mid_idx] if has_nf_data else None
        )

        # TX mode specifics
        if has_power_tracking:
            summary.input_power_dbm = chain.source_power_dbm
            summary.output_power_dbm = power_through_chain_dbm[-1, mid_idx]
            summary.output_power_watts = power_through_chain_watts[-1, mid_idx]

            # Find saturated amplifiers
            saturated_indices = np.where(saturation_flags[:, mid_idx])[0]
            summary.saturated_amplifiers = [component_names[i] for i in saturated_indices]

        # RX mode specifics
        if has_rx_sweep:
            summary.damage_level_dbm = damage_level_dbm
            summary.min_safe_input_power_dbm = min_damage_threshold_dbm[mid_idx]
            summary.adc_input_power_at_threshold_dbm = power_through_chain_at_threshold[-1]
            summary.power_through_chain_at_threshold = power_through_chain_at_threshold

        # Component contributions
        for idx, comp_name in enumerate(component_names):
            # Make safe field name
            safe_name = comp_name.replace('.', 'p').replace('-', '_')

            contrib = ComponentContribution(
                name=comp_name,
                gain_db=component_gains[idx, mid_idx]
            )

            if not np.isnan(component_nfs[idx, mid_idx]):
                contrib.nf_db = component_nfs[idx, mid_idx]

            if has_power_tracking:
                contrib.output_power_dbm = power_through_chain_dbm[idx + 1, mid_idx]
                contrib.output_power_watts = power_through_chain_watts[idx + 1, mid_idx]
                if saturation_flags[idx, mid_idx]:
                    contrib.saturated = True

            if has_rx_sweep:
                contrib.power_at_threshold_dbm = power_through_chain_at_threshold[idx + 1]

            summary.component_contributions[safe_name] = contrib

        return summary

    @staticmethod
    def _dbm_to_watts(dbm: np.ndarray) -> np.ndarray:
        """Convert dBm to Watts."""
        return 10 ** ((dbm - 30) / 10)

    @staticmethod
    def _watts_to_dbm(watts: np.ndarray) -> np.ndarray:
        """Convert Watts to dBm."""
        return 10 * np.log10(watts) + 30


# =============================================================================
# ANALYSIS FUNCTION (matches MATLAB calling convention)
# =============================================================================

def analyze_rf_chain(chain_config: ChainConfig, n_freq_points: int = 200) -> ChainAnalysisResults:
    """
    Analyze RF chain performance.

    Matches MATLAB: results = analyze_rf_chain(chain_config)

    Args:
        chain_config: ChainConfig from load_chain_config().
        n_freq_points: Number of frequency points (default 200).

    Returns:
        ChainAnalysisResults with all analysis data.
    """
    analyzer = RFChainAnalyzer(n_freq_points=n_freq_points)
    return analyzer.analyze(chain_config)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def calculate_noise_temperature(nf_db: float) -> float:
    """
    Convert noise figure to equivalent noise temperature.

    Args:
        nf_db: Noise figure in dB.

    Returns:
        Equivalent noise temperature in Kelvin.
    """
    nf_linear = 10 ** (nf_db / 10)
    return T0 * (nf_linear - 1)


def print_results_summary(results: ChainAnalysisResults) -> str:
    """
    Generate formatted summary of analysis results.

    Args:
        results: ChainAnalysisResults to summarize.

    Returns:
        Formatted string summary.
    """
    lines = [
        "=" * 60,
        f"RF CHAIN ANALYSIS RESULTS",
        "=" * 60,
        "",
        f"Chain Type: {'Transmit' if results.is_transmit else 'Receive'}",
        f"Frequency Range: {results.freq_ghz[0]:.1f} - {results.freq_ghz[-1]:.1f} GHz",
        f"Components: {results.n_components}",
        "",
        f"=== Performance at Mid-Frequency ({results.mid_freq_summary.frequency_ghz:.2f} GHz) ===",
    ]

    if results.has_power_tracking:
        lines.append(f"Input Power: {results.mid_freq_summary.input_power_dbm:.2f} dBm")
        lines.append(f"Output Power: {results.mid_freq_summary.output_power_dbm:.2f} dBm "
                    f"({results.mid_freq_summary.output_power_watts:.4f} W)")

    lines.append(f"Total Gain: {results.mid_freq_summary.total_gain_db:.2f} dB")

    if results.has_nf_data and results.mid_freq_summary.cascaded_nf_db is not None:
        lines.append(f"Cascaded NF: {results.mid_freq_summary.cascaded_nf_db:.2f} dB")

    # RX damage threshold
    if results.has_rx_sweep:
        lines.extend([
            "",
            "=== Damage Threshold Analysis ===",
            f"Damage Level (at ADC): {results.mid_freq_summary.damage_level_dbm:.1f} dBm",
            f"Maximum Safe Input Power: {results.mid_freq_summary.min_safe_input_power_dbm:.1f} dBm",
            f"ADC Input Power @ Threshold: {results.mid_freq_summary.adc_input_power_at_threshold_dbm:.1f} dBm"
        ])

    # TX saturation warnings
    if results.has_power_tracking and results.mid_freq_summary.saturated_amplifiers:
        lines.extend([
            "",
            "*** SATURATION WARNING ***",
            "The following amplifiers are saturated:"
        ])
        for amp in results.mid_freq_summary.saturated_amplifiers:
            lines.append(f"  - {amp}")

    # Component contributions
    lines.extend(["", "Component Contributions:"])
    for safe_name, contrib in results.mid_freq_summary.component_contributions.items():
        line = f"  {contrib.name}: Gain = {contrib.gain_db:.2f} dB"
        if contrib.nf_db is not None:
            line += f", NF = {contrib.nf_db:.2f} dB"
        if results.has_power_tracking:
            line += f", Pout = {contrib.output_power_dbm:.2f} dBm ({contrib.output_power_watts:.4f} W)"
            if contrib.saturated:
                line += " [SATURATED]"
        elif results.has_rx_sweep:
            line += f", Pout@Threshold = {contrib.power_at_threshold_dbm:.1f} dBm"
        lines.append(line)

    lines.append("=" * 60)
    return "\n".join(lines)


def print_gain_breakdown_table(results: ChainAnalysisResults) -> str:
    """
    Generate gain breakdown table across frequency.

    Args:
        results: ChainAnalysisResults.

    Returns:
        Formatted table string.
    """
    # Test frequencies: first, mid, last
    test_freqs = [results.freq_ghz[0], results.mid_freq_summary.frequency_ghz, results.freq_ghz[-1]]

    lines = [
        "=== Gain Breakdown Across Frequency ===",
        ""
    ]

    # Header
    header = f"{'Component':<20}"
    for f in test_freqs:
        header += f"{f:>12.1f} GHz"
    lines.append(header)
    lines.append("-" * 60)

    # Component rows
    for i, name in enumerate(results.component_names):
        row = f"{name:<20}"
        for f in test_freqs:
            f_idx = np.argmin(np.abs(results.freq_ghz - f))
            row += f"{results.component_gains[i, f_idx]:>12.2f} dB "
        lines.append(row)

    # Total row
    lines.append("-" * 60)
    row = f"{'TOTAL':<20}"
    for f in test_freqs:
        f_idx = np.argmin(np.abs(results.freq_ghz - f))
        row += f"{results.total_gain_db[f_idx]:>12.2f} dB "
    lines.append(row)

    return "\n".join(lines)
