"""
RF Chain Analyzer

Cascaded analysis of RF receiver and transmitter chains including:
- Cascaded gain calculation
- Cascaded noise figure (Friis formula)
- Sensitivity calculation
- Power tracking through chain
- Dynamic range analysis
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import math
import numpy as np

from ..config import RFChain, Component, AnalysisSettings, ChainType


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

BOLTZMANN_K = 1.380649e-23  # J/K
T0 = 290.0  # Reference temperature in Kelvin


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class PowerPoint:
    """Power level at a point in the chain."""
    component_name: str
    order: int
    input_power_dbm: float
    output_power_dbm: float
    gain_db: float
    cumulative_gain_db: float
    is_compressed: bool = False
    compression_db: float = 0.0


@dataclass
class CascadeResult:
    """Results of cascaded chain analysis at a single frequency."""
    freq_ghz: float

    # Cascaded parameters
    total_gain_db: float
    total_nf_db: float

    # Sensitivity
    thermal_noise_floor_dbm: float
    sensitivity_dbm: float

    # Dynamic range
    min_input_dbm: float  # Sensitivity
    max_input_dbm: float  # Input at 1dB compression
    dynamic_range_db: float

    # Component-by-component breakdown
    component_gains: List[float] = field(default_factory=list)
    component_nfs: List[float] = field(default_factory=list)
    cumulative_gains: List[float] = field(default_factory=list)
    cumulative_nfs: List[float] = field(default_factory=list)
    component_names: List[str] = field(default_factory=list)


@dataclass
class FrequencyAnalysis:
    """Analysis results across frequency range."""
    frequencies_ghz: np.ndarray
    gains_db: np.ndarray
    noise_figures_db: np.ndarray
    sensitivities_dbm: np.ndarray
    dynamic_ranges_db: np.ndarray


# =============================================================================
# ANALYZER CLASS
# =============================================================================

class RFChainAnalyzer:
    """
    Analyzer for cascaded RF chain performance.

    Implements Friis formula for cascaded noise figure and tracks
    power levels through the chain for compression analysis.
    """

    def __init__(self, settings: Optional[AnalysisSettings] = None):
        """
        Initialize analyzer with settings.

        Args:
            settings: Analysis configuration. Uses defaults if None.
        """
        self.settings = settings or AnalysisSettings()

    def analyze_cascade(self, chain: RFChain, freq_ghz: float) -> CascadeResult:
        """
        Perform cascaded analysis at a single frequency.

        Args:
            chain: RF chain to analyze.
            freq_ghz: Analysis frequency in GHz.

        Returns:
            CascadeResult with all cascade calculations.
        """
        components = chain.get_components_ordered()

        if not components:
            return self._empty_result(freq_ghz)

        # Initialize arrays
        n = len(components)
        gains_db = np.zeros(n)
        nfs_db = np.zeros(n)
        cumulative_gains_db = np.zeros(n)
        cumulative_nfs_db = np.zeros(n)
        names = []

        # Calculate individual component parameters
        for i, comp in enumerate(components):
            gains_db[i] = comp.get_gain_at_freq(freq_ghz)
            nfs_db[i] = comp.get_nf_at_freq(freq_ghz)
            names.append(comp.name)

        # Calculate cumulative gain (simple sum in dB)
        cumulative_gains_db[0] = gains_db[0]
        for i in range(1, n):
            cumulative_gains_db[i] = cumulative_gains_db[i-1] + gains_db[i]

        # Calculate cumulative noise figure using Friis formula
        # NF_cascade = NF1 + (NF2-1)/G1 + (NF3-1)/(G1*G2) + ...
        # Working in linear domain for noise factors
        cumulative_nfs_db[0] = nfs_db[0]

        for i in range(1, n):
            # Convert to linear
            f_cascade = self._db_to_linear(cumulative_nfs_db[i-1])
            f_new = self._db_to_linear(nfs_db[i])
            g_prev = self._db_to_linear(cumulative_gains_db[i-1])

            # Friis: F_new_cascade = F_old_cascade + (F_component - 1) / G_preceding
            if g_prev > 0:
                f_cascade_new = f_cascade + (f_new - 1) / g_prev
            else:
                # If gain is very low/negative, NF degrades significantly
                f_cascade_new = f_cascade + (f_new - 1) * 1e6

            cumulative_nfs_db[i] = self._linear_to_db(max(f_cascade_new, 1.0))

        # Total cascade results
        total_gain_db = cumulative_gains_db[-1]
        total_nf_db = cumulative_nfs_db[-1]

        # Thermal noise floor
        # N = kTB in dBm = 10*log10(kTB) + 30
        bandwidth_hz = self.settings.bandwidth_hz
        temp_k = self.settings.temperature_k
        thermal_noise_w = BOLTZMANN_K * temp_k * bandwidth_hz
        thermal_noise_dbm = 10 * math.log10(thermal_noise_w) + 30

        # Sensitivity = Noise floor + NF + SNR_required
        sensitivity_dbm = thermal_noise_dbm + total_nf_db + self.settings.snr_required_db

        # Find system input compression point
        # Work backwards from each component's P1dB
        max_input_dbm = self._calculate_max_input(chain, freq_ghz)

        # Dynamic range
        dynamic_range_db = max_input_dbm - sensitivity_dbm

        return CascadeResult(
            freq_ghz=freq_ghz,
            total_gain_db=total_gain_db,
            total_nf_db=total_nf_db,
            thermal_noise_floor_dbm=thermal_noise_dbm,
            sensitivity_dbm=sensitivity_dbm,
            min_input_dbm=sensitivity_dbm,
            max_input_dbm=max_input_dbm,
            dynamic_range_db=dynamic_range_db,
            component_gains=gains_db.tolist(),
            component_nfs=nfs_db.tolist(),
            cumulative_gains=cumulative_gains_db.tolist(),
            cumulative_nfs=cumulative_nfs_db.tolist(),
            component_names=names
        )

    def analyze_frequency_range(self, chain: RFChain) -> FrequencyAnalysis:
        """
        Analyze chain across its frequency range.

        Args:
            chain: RF chain to analyze.

        Returns:
            FrequencyAnalysis with results at all frequency points.
        """
        freq_min, freq_max = chain.freq_range_ghz
        frequencies = np.linspace(freq_min, freq_max, self.settings.frequency_points)

        gains = np.zeros(len(frequencies))
        nfs = np.zeros(len(frequencies))
        sensitivities = np.zeros(len(frequencies))
        dynamic_ranges = np.zeros(len(frequencies))

        for i, freq in enumerate(frequencies):
            result = self.analyze_cascade(chain, freq)
            gains[i] = result.total_gain_db
            nfs[i] = result.total_nf_db
            sensitivities[i] = result.sensitivity_dbm
            dynamic_ranges[i] = result.dynamic_range_db

        return FrequencyAnalysis(
            frequencies_ghz=frequencies,
            gains_db=gains,
            noise_figures_db=nfs,
            sensitivities_dbm=sensitivities,
            dynamic_ranges_db=dynamic_ranges
        )

    def track_power(self, chain: RFChain, freq_ghz: float,
                    input_power_dbm: float) -> List[PowerPoint]:
        """
        Track power level through the chain.

        Args:
            chain: RF chain to analyze.
            freq_ghz: Frequency in GHz.
            input_power_dbm: Input power in dBm.

        Returns:
            List of PowerPoint objects showing power at each stage.
        """
        components = chain.get_components_ordered()
        power_points = []

        current_power = input_power_dbm
        cumulative_gain = 0.0

        for i, comp in enumerate(components):
            gain_db = comp.get_gain_at_freq(freq_ghz)
            output_power = current_power + gain_db
            cumulative_gain += gain_db

            # Check for compression
            is_compressed = False
            compression = 0.0
            if output_power > comp.p1db_dbm:
                is_compressed = True
                compression = output_power - comp.p1db_dbm
                # Limit output to saturation
                output_power = min(output_power, comp.psat_dbm)

            power_points.append(PowerPoint(
                component_name=comp.name,
                order=i,
                input_power_dbm=current_power,
                output_power_dbm=output_power,
                gain_db=gain_db,
                cumulative_gain_db=cumulative_gain,
                is_compressed=is_compressed,
                compression_db=compression
            ))

            current_power = output_power

        return power_points

    def analyze_tx_chain(self, chain: RFChain, freq_ghz: float) -> Dict[str, Any]:
        """
        Analyze transmit chain including EIRP calculation.

        Args:
            chain: TX chain to analyze.
            freq_ghz: Frequency in GHz.

        Returns:
            Dictionary with TX analysis results.
        """
        # Track power through chain
        power_points = self.track_power(chain, freq_ghz, chain.source_power_dbm)

        # Get output power (before antenna)
        if power_points:
            output_power_dbm = power_points[-1].output_power_dbm
        else:
            output_power_dbm = chain.source_power_dbm

        # Total gain
        cascade = self.analyze_cascade(chain, freq_ghz)

        return {
            'source_power_dbm': chain.source_power_dbm,
            'total_gain_db': cascade.total_gain_db,
            'output_power_dbm': output_power_dbm,
            'power_points': power_points,
            'any_compression': any(p.is_compressed for p in power_points)
        }

    def _calculate_max_input(self, chain: RFChain, freq_ghz: float) -> float:
        """
        Calculate maximum input power before compression.

        Works backwards from each component's P1dB to find the
        limiting input level.
        """
        components = chain.get_components_ordered()
        if not components:
            return 0.0

        # Calculate cumulative gain to each component
        cumulative_gains = []
        total = 0.0
        for comp in components:
            total += comp.get_gain_at_freq(freq_ghz)
            cumulative_gains.append(total)

        # For each component, calculate what input would cause compression
        max_inputs = []
        gain_before = 0.0
        for i, comp in enumerate(components):
            if i > 0:
                gain_before = cumulative_gains[i-1]

            # Input power that gives P1dB at this component's output
            # P1dB = Pin + Gain_before + Gain_component
            # Pin = P1dB - Gain_before - Gain_component
            # But we want input that causes compression at INPUT to this stage
            # So: P_in_to_comp = P1dB - Gain_component
            # And: P_system_in = P_in_to_comp - Gain_before

            comp_gain = comp.get_gain_at_freq(freq_ghz)
            if comp.p1db_dbm < 100:  # Only if P1dB is specified
                p_in_to_comp = comp.p1db_dbm - comp_gain
                p_system_in = p_in_to_comp - gain_before
                max_inputs.append(p_system_in)

        if max_inputs:
            return min(max_inputs)
        else:
            return 10.0  # Default if no P1dB specified

    def _empty_result(self, freq_ghz: float) -> CascadeResult:
        """Return empty result for chains with no components."""
        return CascadeResult(
            freq_ghz=freq_ghz,
            total_gain_db=0.0,
            total_nf_db=0.0,
            thermal_noise_floor_dbm=-174.0,
            sensitivity_dbm=-164.0,
            min_input_dbm=-164.0,
            max_input_dbm=0.0,
            dynamic_range_db=164.0
        )

    @staticmethod
    def _db_to_linear(db_value: float) -> float:
        """Convert dB to linear power ratio."""
        return 10 ** (db_value / 10)

    @staticmethod
    def _linear_to_db(linear_value: float) -> float:
        """Convert linear power ratio to dB."""
        if linear_value <= 0:
            return -200.0
        return 10 * math.log10(linear_value)

    def print_cascade_summary(self, result: CascadeResult) -> str:
        """
        Generate formatted summary of cascade results.

        Args:
            result: CascadeResult to summarize.

        Returns:
            Formatted string summary.
        """
        lines = [
            f"\n{'='*60}",
            f"CASCADE ANALYSIS @ {result.freq_ghz:.2f} GHz",
            f"{'='*60}",
            "",
            "COMPONENT BREAKDOWN:",
            f"{'Component':<25} {'Gain(dB)':>10} {'NF(dB)':>10} {'Cum.Gain':>10} {'Cum.NF':>10}",
            "-" * 65
        ]

        for i, name in enumerate(result.component_names):
            lines.append(
                f"{name:<25} {result.component_gains[i]:>10.2f} "
                f"{result.component_nfs[i]:>10.2f} "
                f"{result.cumulative_gains[i]:>10.2f} "
                f"{result.cumulative_nfs[i]:>10.2f}"
            )

        lines.extend([
            "",
            "SYSTEM PARAMETERS:",
            f"  Total Gain:           {result.total_gain_db:>10.2f} dB",
            f"  Total Noise Figure:   {result.total_nf_db:>10.2f} dB",
            f"  Thermal Noise Floor:  {result.thermal_noise_floor_dbm:>10.2f} dBm",
            f"  Sensitivity:          {result.sensitivity_dbm:>10.2f} dBm",
            "",
            "DYNAMIC RANGE:",
            f"  Min Input (MDS):      {result.min_input_dbm:>10.2f} dBm",
            f"  Max Input (P1dB):     {result.max_input_dbm:>10.2f} dBm",
            f"  Dynamic Range:        {result.dynamic_range_db:>10.2f} dB",
            f"{'='*60}"
        ])

        return "\n".join(lines)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def compare_chains(analyzer: RFChainAnalyzer, chains: List[RFChain],
                   freq_ghz: float) -> Dict[str, CascadeResult]:
    """
    Compare multiple chains at the same frequency.

    Args:
        analyzer: RFChainAnalyzer instance.
        chains: List of chains to compare.
        freq_ghz: Comparison frequency.

    Returns:
        Dictionary mapping chain ID to CascadeResult.
    """
    results = {}
    for chain in chains:
        results[chain.id] = analyzer.analyze_cascade(chain, freq_ghz)
    return results


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
