"""
RF ADC Analyzer

Comprehensive RF ADC performance analysis matching MATLAB analyze_rf_adc.m.
Handles both dBc/Hz and dBFS/Hz noise specifications.
"""

from dataclasses import dataclass
from typing import Optional
import math

from ..config.loader import ADCSpecs, AnalysisConfig


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

THERMAL_NOISE_DBM_HZ = -174.0  # dBm/Hz at 290K


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ADCResults:
    """
    Comprehensive ADC analysis results.

    Matches MATLAB analyze_rf_adc output structure.
    """
    # Echo inputs
    specs: ADCSpecs
    config: AnalysisConfig

    # Operating conditions
    operating_band: list  # [start_ghz, end_ghz]
    operating_band_ghz: str  # Formatted string

    # Key performance metrics
    full_scale_dbm: float
    noise_floor_dbm: float
    noise_floor_dbfs: float
    sensitivity_dbm: float
    snr_at_full_scale_db: float
    sfdr_db: float
    dynamic_range_db: float
    noise_limited_dr_db: float
    sfdr_limited_dr_db: float
    equivalent_noise_figure_db: float
    thd_db: float
    thd_percent: float
    im3_dbc: float

    # Intermediate values
    full_scale_vrms: float
    noise_density_used: float
    bw_factor_db: float


# =============================================================================
# ANALYZER FUNCTION
# =============================================================================

def analyze_rf_adc(adc_specs: ADCSpecs, config: AnalysisConfig) -> ADCResults:
    """
    Comprehensive RF ADC performance analysis.

    Analyzes RF ADC performance including noise floor, dynamic range,
    sensitivity, and distortion characteristics. Handles both dBc/Hz and
    dBFS/Hz noise specifications.

    Matches MATLAB: adc_results = analyze_rf_adc(adc_specs, config)

    Args:
        adc_specs: ADCSpecs from load_adc_specs().
        config: AnalysisConfig with analysis parameters.

    Returns:
        ADCResults with comprehensive analysis.

    Raises:
        ValueError: If RF frequency is outside ADC specified range.
    """
    # Select appropriate frequency band
    rf_freq_ghz = config.rf_input_freq_hz / 1e9

    band_idx = adc_specs.get_band_index(rf_freq_ghz)
    if band_idx is None:
        raise ValueError(f"RF frequency {rf_freq_ghz:.2f} GHz is outside ADC specified range")

    # Extract specs for the selected band
    fs_mvppd = adc_specs.full_scale_mvppd[band_idx]
    sfdr_db = adc_specs.sfdr_db[band_idx]
    noise_density = adc_specs.noise_density[band_idx]
    thd_percent_list = adc_specs.get_thd_percent_per_band()
    thd_percent = thd_percent_list[band_idx]
    im3_dbc = adc_specs.im3_dbc[band_idx]

    # Get impedance from config or specs
    input_impedance = config.input_impedance_ohm

    # Convert full scale to dBm
    # Vppd to Vrms: Vrms = Vppd / (2 * sqrt(2))
    fs_vrms = (fs_mvppd / 1000) / (2 * math.sqrt(2))

    # Power in dBm: P = V^2 / R, then 10*log10(P/0.001)
    fs_power_watts = fs_vrms ** 2 / input_impedance
    full_scale_dbm = 10 * math.log10(fs_power_watts / 0.001)

    # Calculate noise floor in analysis bandwidth
    # Get reference level for noise measurement (default -10 dBFS if not specified)
    noise_ref_dbfs = adc_specs.noise_ref_level_dbfs

    # Convert noise density to noise in analysis bandwidth
    # Noise in BW = Noise_density + 10*log10(BW)
    bw_factor_db = 10 * math.log10(config.analysis_bw_hz)

    if adc_specs.noise_units == 'dBc/Hz':
        # Noise relative to carrier (at noise_ref_dbfs level)
        # Total noise in BW relative to reference carrier
        noise_rel_carrier_db = noise_density + bw_factor_db

        # Convert to dBFS: noise was measured with ref level input
        # So noise in dBFS = noise_ref_dbfs + noise_rel_carrier
        noise_floor_dbfs = noise_ref_dbfs + noise_rel_carrier_db

    elif adc_specs.noise_units == 'dBFS/Hz':
        # Noise already relative to full scale
        noise_floor_dbfs = noise_density + bw_factor_db

    else:
        raise ValueError(f"Unknown noise units: {adc_specs.noise_units}. "
                        f"Must be dBc/Hz or dBFS/Hz")

    # Convert noise floor to dBm
    noise_floor_dbm = full_scale_dbm + noise_floor_dbfs

    # Calculate SNR at full scale
    # SNR = Full_scale - Noise_floor (in dBFS)
    snr_at_full_scale_db = 0 - noise_floor_dbfs  # 0 dBFS is full scale

    # Calculate sensitivity (minimum detectable signal)
    # Typically defined as noise floor + some margin (e.g., 10 dB SNR required)
    snr_required_db = 10.0
    sensitivity_dbm = noise_floor_dbm + snr_required_db

    # Calculate dynamic range
    # Limited by both noise floor and SFDR
    # Noise-limited DR: from noise floor to full scale
    noise_limited_dr_db = snr_at_full_scale_db

    # SFDR-limited DR: from largest spur to full scale
    sfdr_limited_dr_db = sfdr_db

    # Effective DR is the smaller of the two
    dynamic_range_db = min(noise_limited_dr_db, sfdr_limited_dr_db)

    # Calculate equivalent noise figure
    # NF allows integration into RF link budget calculations
    # Thermal noise floor at room temp: -174 dBm/Hz

    # Noise in analysis bandwidth
    thermal_noise_in_bw_dbm = THERMAL_NOISE_DBM_HZ + bw_factor_db

    # ADC adds noise above thermal noise
    # Equivalent NF = (Total_noise) - (Thermal_noise)
    equivalent_nf_db = noise_floor_dbm - thermal_noise_in_bw_dbm

    # Convert THD to dB
    thd_db = 20 * math.log10(thd_percent / 100) if thd_percent > 0 else -100.0

    # Format operating band string
    operating_band = adc_specs.freq_bands[band_idx]
    operating_band_ghz = f"{operating_band[0]:.1f} - {operating_band[1]:.1f} GHz"

    return ADCResults(
        specs=adc_specs,
        config=config,
        operating_band=operating_band,
        operating_band_ghz=operating_band_ghz,
        full_scale_dbm=full_scale_dbm,
        noise_floor_dbm=noise_floor_dbm,
        noise_floor_dbfs=noise_floor_dbfs,
        sensitivity_dbm=sensitivity_dbm,
        snr_at_full_scale_db=snr_at_full_scale_db,
        sfdr_db=sfdr_db,
        dynamic_range_db=dynamic_range_db,
        noise_limited_dr_db=noise_limited_dr_db,
        sfdr_limited_dr_db=sfdr_limited_dr_db,
        equivalent_noise_figure_db=equivalent_nf_db,
        thd_db=thd_db,
        thd_percent=thd_percent,
        im3_dbc=im3_dbc,
        full_scale_vrms=fs_vrms,
        noise_density_used=noise_density,
        bw_factor_db=bw_factor_db
    )


def print_results_summary(results: ADCResults) -> str:
    """
    Generate formatted summary of ADC analysis results.

    Args:
        results: ADCResults to summarize.

    Returns:
        Formatted string summary.
    """
    lines = [
        "=" * 60,
        f"ADC ANALYSIS RESULTS: {results.specs.name}",
        "=" * 60,
        "",
        f"Operating Frequency: {results.config.rf_input_freq_hz/1e9:.2f} GHz",
        f"Operating Band: {results.operating_band_ghz}",
        f"Analysis Bandwidth: {results.config.analysis_bw_hz/1e6:.1f} MHz",
        "",
        "KEY PERFORMANCE METRICS:",
        f"  Full Scale Power: {results.full_scale_dbm:.2f} dBm",
        f"  Noise Floor: {results.noise_floor_dbm:.2f} dBm ({results.noise_floor_dbfs:.2f} dBFS)",
        f"  Sensitivity (MDS): {results.sensitivity_dbm:.2f} dBm",
        f"  SNR at Full Scale: {results.snr_at_full_scale_db:.2f} dB",
        "",
        "DYNAMIC RANGE:",
        f"  Noise-Limited DR: {results.noise_limited_dr_db:.2f} dB",
        f"  SFDR-Limited DR: {results.sfdr_limited_dr_db:.2f} dB",
        f"  Effective DR: {results.dynamic_range_db:.2f} dB",
        "",
        "DISTORTION:",
        f"  SFDR: {results.sfdr_db:.2f} dB",
        f"  THD: {results.thd_db:.2f} dB ({results.thd_percent:.2f}%)",
        f"  IM3: {results.im3_dbc:.2f} dBc",
        "",
        "LINK BUDGET INTEGRATION:",
        f"  Equivalent NF: {results.equivalent_noise_figure_db:.2f} dB",
        "=" * 60
    ]
    return "\n".join(lines)


def compare_adcs(specs_list: list, config: AnalysisConfig) -> dict:
    """
    Compare multiple ADCs at the same operating conditions.

    Args:
        specs_list: List of ADCSpecs to compare.
        config: Common analysis configuration.

    Returns:
        Dictionary mapping ADC name to results.
    """
    results = {}
    for specs in specs_list:
        try:
            results[specs.name] = analyze_rf_adc(specs, config)
        except ValueError as e:
            print(f"Warning: {specs.name} - {e}")
    return results


def print_comparison_table(results_dict: dict) -> str:
    """
    Generate comparison table for multiple ADCs.

    Args:
        results_dict: Dictionary from compare_adcs().

    Returns:
        Formatted comparison table.
    """
    if not results_dict:
        return "No results to compare"

    lines = [
        "=" * 80,
        "ADC COMPARISON",
        "=" * 80,
        "",
        f"{'Metric':<30} " + " ".join([f"{name:>15}" for name in results_dict.keys()]),
        "-" * 80
    ]

    metrics = [
        ("Full Scale (dBm)", "full_scale_dbm", ".2f"),
        ("Noise Floor (dBm)", "noise_floor_dbm", ".2f"),
        ("Sensitivity (dBm)", "sensitivity_dbm", ".2f"),
        ("SNR @ FS (dB)", "snr_at_full_scale_db", ".2f"),
        ("Dynamic Range (dB)", "dynamic_range_db", ".2f"),
        ("SFDR (dB)", "sfdr_db", ".2f"),
        ("THD (dB)", "thd_db", ".2f"),
        ("IM3 (dBc)", "im3_dbc", ".2f"),
        ("Equiv. NF (dB)", "equivalent_noise_figure_db", ".2f"),
    ]

    for label, attr, fmt in metrics:
        values = []
        for name, result in results_dict.items():
            val = getattr(result, attr)
            values.append(f"{val:{fmt}}")
        lines.append(f"{label:<30} " + " ".join([f"{v:>15}" for v in values]))

    lines.append("=" * 80)
    return "\n".join(lines)
