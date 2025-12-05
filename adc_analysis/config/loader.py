"""
ADC Configuration Loader

Loads and validates YAML configuration for ADC analysis.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from pathlib import Path
import yaml


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _to_float(value, default: float = 0.0) -> float:
    """Convert value to float, handling strings with scientific notation."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _to_int(value, default: int = 0) -> int:
    """Convert value to int."""
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _to_float_list(value, default: List[float] = None) -> List[float]:
    """Convert value to list of floats."""
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return [_to_float(v) for v in value]
    return default


def _to_int_list(value, default: List[int] = None) -> List[int]:
    """Convert value to list of ints."""
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return [_to_int(v) for v in value]
    return default


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ADCSpec:
    """ADC specifications."""
    bits: int = 10
    enob: float = 8.0
    sample_rate_gsps: float = 64.0
    fullscale_dbm: float = -1.1
    max_input_dbm: float = 12.0
    impedance_ohm: float = 100.0
    nsd_dbfs_hz: float = -153.0
    sfdr_dbc: float = 55.0
    thd_dbc: float = -60.0
    imd3_dbc: float = -60.0
    aperture_jitter_ps: float = 0.5
    clock_jitter_fs: float = 100.0

    @property
    def nsd_dbm_hz(self) -> float:
        """ADC noise spectral density in dBm/Hz."""
        return self.nsd_dbfs_hz + self.fullscale_dbm

    @property
    def nyquist_bw_hz(self) -> float:
        """Nyquist bandwidth in Hz."""
        return self.sample_rate_gsps * 1e9 / 2


@dataclass
class LNASpec:
    """LNA specifications."""
    gain_range_db: List[float] = field(default_factory=lambda: [10, 15, 20, 25, 30])
    nf_range_db: List[float] = field(default_factory=lambda: [1.0, 2.0, 3.0])
    p1db_dbm: float = 25.0


@dataclass
class PassiveSpec:
    """Passive component specifications."""
    cable_loss_db: float = 3.0
    coupler_loss_db: float = 0.5
    switch_loss_db: float = 1.0
    filter_loss_db: float = 0.8

    @property
    def total_loss_db(self) -> float:
        """Total passive loss."""
        return (self.cable_loss_db + self.coupler_loss_db +
                self.switch_loss_db + self.filter_loss_db)


@dataclass
class AntennaSpec:
    """Antenna specifications."""
    gain_dbi: float = 2.0


@dataclass
class AnalysisParams:
    """Analysis parameters."""
    analysis_bw_mhz: float = 20.0
    effective_fs_msps: float = 50.0
    detection_threshold_db: float = 13.0
    snr_required_db: float = 10.0
    temperature_k: float = 290.0
    impedance_ohm: float = 50.0
    signal_freq_ghz: float = 10.0
    input_signal_dbm: float = -30.0
    pulse_widths_us: List[float] = field(default_factory=lambda: [0.1, 1, 10, 100])
    fft_lengths: List[int] = field(default_factory=lambda: [1024, 4096, 16384])
    ifm_delay_ns: float = 1.0
    baseline_wavelengths: float = 1.0

    @property
    def analysis_bw_hz(self) -> float:
        """Analysis bandwidth in Hz."""
        return self.analysis_bw_mhz * 1e6

    @property
    def effective_fs_hz(self) -> float:
        """Effective sample rate in Hz."""
        return self.effective_fs_msps * 1e6


@dataclass
class SaturationParams:
    """Saturation analysis parameters."""
    eirp_values_dbm: List[float] = field(
        default_factory=lambda: [20, 40, 60, 80, 90, 100, 110])
    distance_min_miles: float = 1.0
    distance_max_miles: float = 50.0
    distance_points: int = 500
    frequency_ghz: float = 5.0


@dataclass
class ADCConfig:
    """Complete ADC configuration."""
    adc: ADCSpec
    lna: LNASpec
    passive: PassiveSpec
    antenna: AntennaSpec
    analysis: AnalysisParams
    saturation: SaturationParams


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================

def _parse_adc_spec(data: dict) -> ADCSpec:
    """Parse ADC specifications from dict."""
    return ADCSpec(
        bits=_to_int(data.get('bits'), 10),
        enob=_to_float(data.get('enob'), 8.0),
        sample_rate_gsps=_to_float(data.get('sample_rate_gsps'), 64.0),
        fullscale_dbm=_to_float(data.get('fullscale_dbm'), -1.1),
        max_input_dbm=_to_float(data.get('max_input_dbm'), 12.0),
        impedance_ohm=_to_float(data.get('impedance_ohm'), 100.0),
        nsd_dbfs_hz=_to_float(data.get('nsd_dbfs_hz'), -153.0),
        sfdr_dbc=_to_float(data.get('sfdr_dbc'), 55.0),
        thd_dbc=_to_float(data.get('thd_dbc'), -60.0),
        imd3_dbc=_to_float(data.get('imd3_dbc'), -60.0),
        aperture_jitter_ps=_to_float(data.get('aperture_jitter_ps'), 0.5),
        clock_jitter_fs=_to_float(data.get('clock_jitter_fs'), 100.0)
    )


def _parse_lna_spec(data: dict) -> LNASpec:
    """Parse LNA specifications from dict."""
    return LNASpec(
        gain_range_db=_to_float_list(data.get('gain_range_db'), [10, 15, 20, 25, 30]),
        nf_range_db=_to_float_list(data.get('nf_range_db'), [1.0, 2.0, 3.0]),
        p1db_dbm=_to_float(data.get('p1db_dbm'), 25.0)
    )


def _parse_passive_spec(data: dict) -> PassiveSpec:
    """Parse passive component specifications from dict."""
    return PassiveSpec(
        cable_loss_db=_to_float(data.get('cable_loss_db'), 3.0),
        coupler_loss_db=_to_float(data.get('coupler_loss_db'), 0.5),
        switch_loss_db=_to_float(data.get('switch_loss_db'), 1.0),
        filter_loss_db=_to_float(data.get('filter_loss_db'), 0.8)
    )


def _parse_antenna_spec(data: dict) -> AntennaSpec:
    """Parse antenna specifications from dict."""
    return AntennaSpec(
        gain_dbi=_to_float(data.get('gain_dbi'), 2.0)
    )


def _parse_analysis_params(data: dict) -> AnalysisParams:
    """Parse analysis parameters from dict."""
    return AnalysisParams(
        analysis_bw_mhz=_to_float(data.get('analysis_bw_mhz'), 20.0),
        effective_fs_msps=_to_float(data.get('effective_fs_msps'), 50.0),
        detection_threshold_db=_to_float(data.get('detection_threshold_db'), 13.0),
        snr_required_db=_to_float(data.get('snr_required_db'), 10.0),
        temperature_k=_to_float(data.get('temperature_k'), 290.0),
        impedance_ohm=_to_float(data.get('impedance_ohm'), 50.0),
        signal_freq_ghz=_to_float(data.get('signal_freq_ghz'), 10.0),
        input_signal_dbm=_to_float(data.get('input_signal_dbm'), -30.0),
        pulse_widths_us=_to_float_list(data.get('pulse_widths_us'), [0.1, 1, 10, 100]),
        fft_lengths=_to_int_list(data.get('fft_lengths'), [1024, 4096, 16384]),
        ifm_delay_ns=_to_float(data.get('ifm_delay_ns'), 1.0),
        baseline_wavelengths=_to_float(data.get('baseline_wavelengths'), 1.0)
    )


def _parse_saturation_params(data: dict) -> SaturationParams:
    """Parse saturation analysis parameters from dict."""
    return SaturationParams(
        eirp_values_dbm=_to_float_list(
            data.get('eirp_values_dbm'), [20, 40, 60, 80, 90, 100, 110]),
        distance_min_miles=_to_float(data.get('distance_min_miles'), 1.0),
        distance_max_miles=_to_float(data.get('distance_max_miles'), 50.0),
        distance_points=_to_int(data.get('distance_points'), 500),
        frequency_ghz=_to_float(data.get('frequency_ghz'), 5.0)
    )


# =============================================================================
# MAIN LOADING FUNCTION
# =============================================================================

def load_adc_config(filepath: Union[str, Path] = None) -> ADCConfig:
    """
    Load ADC configuration from YAML file.

    Args:
        filepath: Path to adc_config.yaml. If None, uses default location.

    Returns:
        ADCConfig object with all specifications.
    """
    if filepath is None:
        config_dir = Path(__file__).parent
        filepath = config_dir / "adc_config.yaml"

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    return ADCConfig(
        adc=_parse_adc_spec(data.get('adc', {})),
        lna=_parse_lna_spec(data.get('lna', {})),
        passive=_parse_passive_spec(data.get('passive', {})),
        antenna=_parse_antenna_spec(data.get('antenna', {})),
        analysis=_parse_analysis_params(data.get('analysis', {})),
        saturation=_parse_saturation_params(data.get('saturation', {}))
    )


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing ADC configuration loader...")

    config = load_adc_config()

    print(f"\nADC Specifications:")
    print(f"  Bits: {config.adc.bits}")
    print(f"  ENOB: {config.adc.enob}")
    print(f"  Sample Rate: {config.adc.sample_rate_gsps} GSPS")
    print(f"  Full Scale: {config.adc.fullscale_dbm} dBm")
    print(f"  NSD: {config.adc.nsd_dbm_hz:.1f} dBm/Hz")

    print(f"\nPassive Losses:")
    print(f"  Total: {config.passive.total_loss_db} dB")

    print(f"\nAnalysis Parameters:")
    print(f"  Bandwidth: {config.analysis.analysis_bw_mhz} MHz")
    print(f"  Detection Threshold: {config.analysis.detection_threshold_db} dB")

    print("\nConfiguration loading successful!")
