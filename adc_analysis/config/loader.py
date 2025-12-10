"""
ADC Configuration Loader

Loads and validates YAML configuration for ADC analysis.
Matches MATLAB adc_specs_model*.m structure.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Union
from pathlib import Path
import yaml
import math


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


def _to_float_list(value, default: List[float] = None) -> List[float]:
    """Convert value to list of floats."""
    if default is None:
        default = []
    if value is None:
        return default
    if isinstance(value, list):
        return [_to_float(v) for v in value]
    return default


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ADCSpecs:
    """
    ADC Specifications matching MATLAB adc_specs structure.

    Supports both dBc/Hz and dBFS/Hz noise specifications.
    """
    name: str
    description: str

    # Sample rate
    sample_rate_gsps: float

    # Noise specification format
    noise_units: str  # 'dBc/Hz' or 'dBFS/Hz'

    # Frequency bands [N x 2] - [start_ghz, end_ghz] for each band
    freq_bands: List[List[float]]

    # Full scale amplitude per band (mVppd)
    full_scale_mvppd: List[float]

    # Input impedance (differential)
    input_impedance_ohm: float = 50.0

    # SFDR per band (dB)
    sfdr_db: List[float] = field(default_factory=list)

    # Noise density per band (dBc/Hz or dBFS/Hz)
    noise_density: List[float] = field(default_factory=list)
    noise_ref_level_dbfs: float = -10.0  # Reference level for noise measurement

    # THD per band (percent) - for dBc/Hz format
    thd_percent: Optional[List[float]] = None

    # THD per band (dBc) - for dBFS/Hz format
    thd_dbc: Optional[List[float]] = None
    thd_ref_level_dbfs: float = -1.0

    # IM3 per band (dBc)
    im3_dbc: List[float] = field(default_factory=list)
    im3_ref_level_dbfs: float = -7.0

    # Optional fields
    input_bandwidth_ghz: Optional[float] = None
    return_loss_db: Optional[List[float]] = None
    mode: Optional[str] = None
    decimation_factor: Optional[int] = None
    notes: List[str] = field(default_factory=list)

    @property
    def n_bands(self) -> int:
        """Number of frequency bands."""
        return len(self.freq_bands)

    def get_band_index(self, freq_ghz: float) -> Optional[int]:
        """Get the band index for a given frequency."""
        for i, (start, end) in enumerate(self.freq_bands):
            if start <= freq_ghz <= end:
                return i
        return None

    def get_thd_percent_per_band(self) -> List[float]:
        """
        Get THD in percent per band.

        Converts from dBc if needed.
        """
        if self.thd_percent is not None:
            return self.thd_percent
        elif self.thd_dbc is not None:
            # Convert dBc to percent: THD(%) = 10^(THD_dBc/20) * 100
            return [10 ** (thd / 20) * 100 for thd in self.thd_dbc]
        else:
            return [0.0] * self.n_bands


@dataclass
class AnalysisConfig:
    """Analysis configuration parameters."""
    rf_input_freq_hz: float  # RF input frequency in Hz
    analysis_bw_hz: float = 20e6  # Analysis bandwidth (default 20 MHz)
    input_impedance_ohm: float = 50.0  # Input impedance


# =============================================================================
# LOADING FUNCTIONS
# =============================================================================

def load_adc_specs(filepath: Union[str, Path] = None, model: str = "model1") -> ADCSpecs:
    """
    Load ADC specifications from YAML file.

    Matches MATLAB adc_specs_model*() function.

    Args:
        filepath: Path to spec YAML. If None, uses default based on model.
        model: Model name ("model1" or "model2") if filepath not specified.

    Returns:
        ADCSpecs object with all specifications.
    """
    if filepath is None:
        config_dir = Path(__file__).parent
        filepath = config_dir / f"adc_specs_{model}.yaml"

    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Specification file not found: {filepath}")

    with open(filepath, 'r') as f:
        data = yaml.safe_load(f) or {}

    # Parse frequency bands
    freq_bands_raw = data.get('freq_bands', [[0.1, 36]])
    freq_bands = [[_to_float(b[0]), _to_float(b[1])] for b in freq_bands_raw]

    # Parse THD - support both percent and dBc formats
    thd_percent = None
    thd_dbc = None
    if 'thd_percent' in data:
        thd_percent = _to_float_list(data.get('thd_percent'))
    if 'thd_dbc' in data:
        thd_dbc = _to_float_list(data.get('thd_dbc'))

    return ADCSpecs(
        name=data.get('name', 'Unknown'),
        description=data.get('description', ''),
        sample_rate_gsps=_to_float(data.get('sample_rate_gsps'), 4.0),
        noise_units=data.get('noise_units', 'dBc/Hz'),
        freq_bands=freq_bands,
        full_scale_mvppd=_to_float_list(data.get('full_scale_mvppd')),
        input_impedance_ohm=_to_float(data.get('input_impedance_ohm'), 50.0),
        sfdr_db=_to_float_list(data.get('sfdr_db')),
        noise_density=_to_float_list(data.get('noise_density')),
        noise_ref_level_dbfs=_to_float(data.get('noise_ref_level_dbfs'), -10.0),
        thd_percent=thd_percent,
        thd_dbc=thd_dbc,
        thd_ref_level_dbfs=_to_float(data.get('thd_ref_level_dbfs'), -1.0),
        im3_dbc=_to_float_list(data.get('im3_dbc')),
        im3_ref_level_dbfs=_to_float(data.get('im3_ref_level_dbfs'), -7.0),
        input_bandwidth_ghz=data.get('input_bandwidth_ghz'),
        return_loss_db=_to_float_list(data.get('return_loss_db')) if 'return_loss_db' in data else None,
        mode=data.get('mode'),
        decimation_factor=data.get('decimation_factor'),
        notes=data.get('notes', [])
    )


def load_model1_specs() -> ADCSpecs:
    """Load ADC Model 1 specifications."""
    return load_adc_specs(model="model1")


def load_model2_specs() -> ADCSpecs:
    """Load ADC Model 2 specifications."""
    return load_adc_specs(model="model2")


def load_from_system_config() -> ADCSpecs:
    """
    Load ADC specifications from shared system_config.yaml.

    This ensures consistency with the central system design.
    The system_config defines the actual ADC used in the system.

    Returns:
        ADCSpecs object with parameters from system_config
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from system_config import load_system_config

    sys_config = load_system_config()
    adc = sys_config.adc

    # Convert system_config bands to local format
    freq_bands = []
    sfdr_db = []
    noise_density = []
    full_scale_mvppd = []
    im3_dbc = []

    for band_name, band in adc.bands.items():
        freq_bands.append([band.freq_min_ghz, band.freq_max_ghz])
        sfdr_db.append(band.sfdr_db)
        noise_density.append(band.noise_density_db)
        # Convert full_scale_dbm to mVppd (approximate)
        # P_dbm = 10*log10(V^2/R) + 30, for 50 ohm: V_rms = sqrt(10^((P-30)/10) * 50)
        # V_ppd = V_rms * 2 * sqrt(2) * 1000 (for differential)
        p_watts = 10 ** ((band.full_scale_dbm - 30) / 10)
        v_rms = (p_watts * adc.input_impedance_ohm) ** 0.5
        v_ppd_mv = v_rms * 2 * (2 ** 0.5) * 1000
        full_scale_mvppd.append(v_ppd_mv)
        im3_dbc.append(-70.0)  # Default IM3

    return ADCSpecs(
        name=adc.model,
        description=f"ADC from system_config ({adc.model})",
        sample_rate_gsps=adc.sample_rate_gsps,
        noise_units=adc.noise_format,
        freq_bands=freq_bands,
        full_scale_mvppd=full_scale_mvppd,
        input_impedance_ohm=adc.input_impedance_ohm,
        sfdr_db=sfdr_db,
        noise_density=noise_density,
        noise_ref_level_dbfs=-10.0,
        thd_percent=None,
        thd_dbc=None,
        thd_ref_level_dbfs=-1.0,
        im3_dbc=im3_dbc,
        im3_ref_level_dbfs=-7.0,
        input_bandwidth_ghz=None,
        return_loss_db=None,
        mode=None,
        decimation_factor=None,
        notes=[f"Loaded from system_config.yaml - {adc.resolution_bits} bit ADC"]
    )


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing ADC specification loader...")

    for model in ["model1", "model2"]:
        print(f"\n{'='*60}")
        print(f"ADC {model.upper()} Specifications:")
        print('='*60)

        specs = load_adc_specs(model=model)

        print(f"  Name: {specs.name}")
        print(f"  Description: {specs.description}")
        print(f"  Sample Rate: {specs.sample_rate_gsps} GSPS")
        print(f"  Noise Units: {specs.noise_units}")
        print(f"  Number of bands: {specs.n_bands}")

        for i, (start, end) in enumerate(specs.freq_bands):
            print(f"\n  Band {i+1}: {start:.1f} - {end:.1f} GHz")
            print(f"    Full Scale: {specs.full_scale_mvppd[i]} mVppd")
            print(f"    SFDR: {specs.sfdr_db[i]} dB")
            print(f"    Noise Density: {specs.noise_density[i]} {specs.noise_units}")
            print(f"    IM3: {specs.im3_dbc[i]} dBc")

    print("\n\nConfiguration loading successful!")
