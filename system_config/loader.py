"""
System Configuration Loader

Loads and validates the shared system configuration from YAML.
Provides dataclasses for type-safe access to configuration parameters.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml
import numpy as np


@dataclass
class ADCBandConfig:
    """Configuration for a single ADC frequency band."""
    freq_range_ghz: Tuple[float, float]
    noise_density_db: float       # dBFS/Hz or dBc/Hz
    sfdr_db: float
    full_scale_dbm: float
    enob: float

    @property
    def freq_min_ghz(self) -> float:
        return self.freq_range_ghz[0]

    @property
    def freq_max_ghz(self) -> float:
        return self.freq_range_ghz[1]


@dataclass
class ADCConfig:
    """ADC configuration."""
    model: str
    sample_rate_gsps: float
    resolution_bits: int
    noise_format: str             # 'dBFS/Hz' or 'dBc/Hz'
    bands: Dict[str, ADCBandConfig]
    input_impedance_ohm: float

    def get_band_for_frequency(self, freq_ghz: float) -> Optional[ADCBandConfig]:
        """Get the ADC band configuration for a given frequency."""
        for band in self.bands.values():
            if band.freq_min_ghz <= freq_ghz <= band.freq_max_ghz:
                return band
        return None

    def get_noise_density_at_freq(self, freq_ghz: float) -> float:
        """Get noise density (dB) at a specific frequency."""
        band = self.get_band_for_frequency(freq_ghz)
        if band:
            return band.noise_density_db
        # Extrapolate from nearest band
        all_bands = list(self.bands.values())
        if freq_ghz < all_bands[0].freq_min_ghz:
            return all_bands[0].noise_density_db
        return all_bands[-1].noise_density_db

    def get_enob_at_freq(self, freq_ghz: float) -> float:
        """Get ENOB at a specific frequency."""
        band = self.get_band_for_frequency(freq_ghz)
        if band:
            return band.enob
        all_bands = list(self.bands.values())
        if freq_ghz < all_bands[0].freq_min_ghz:
            return all_bands[0].enob
        return all_bands[-1].enob


@dataclass
class RFChainComponent:
    """Single RF chain component."""
    name: str
    type: str
    gain_db: float
    noise_figure_db: float


@dataclass
class RFChainConfig:
    """RF chain configuration."""
    cascade_noise_figure_db: float
    total_gain_db: float
    damage_threshold_dbm: float
    components: List[RFChainComponent] = field(default_factory=list)

    def calculate_cascade_nf(self) -> float:
        """Calculate cascade noise figure from components using Friis formula."""
        if not self.components:
            return self.cascade_noise_figure_db

        # Friis cascade noise figure formula
        # F_total = F1 + (F2-1)/G1 + (F3-1)/(G1*G2) + ...
        f_total = 1.0
        g_cumulative = 1.0

        for i, comp in enumerate(self.components):
            f_linear = 10 ** (comp.noise_figure_db / 10)
            g_linear = 10 ** (comp.gain_db / 10)

            if i == 0:
                f_total = f_linear
            else:
                f_total += (f_linear - 1) / g_cumulative

            g_cumulative *= g_linear

        return 10 * np.log10(f_total)


@dataclass
class InterferometerMounting:
    """Interferometer mounting configuration."""
    offset_body_m: np.ndarray     # [X, Y, Z] in meters
    orientation_deg: np.ndarray   # [Roll, Pitch, Yaw] in degrees


@dataclass
class InterferometerConfig:
    """Interferometer configuration - single source of truth."""
    n_elements: int
    freq_range_ghz: Tuple[float, float]  # Task 3: [min, max] operating frequency
    c_light_in_per_ns: float
    element_positions: np.ndarray  # inches
    phase_error_high_snr_deg: float
    max_incident_angle_deg: float
    mounting: InterferometerMounting

    @property
    def freq_min_ghz(self) -> float:
        """Minimum operating frequency (GHz)."""
        return self.freq_range_ghz[0]

    @property
    def freq_max_ghz(self) -> float:
        """Maximum operating frequency (GHz)."""
        return self.freq_range_ghz[1]

    @property
    def baselines(self) -> np.ndarray:
        """Calculate all unique baselines from element positions."""
        baselines = []
        for i in range(self.n_elements):
            for j in range(i + 1, self.n_elements):
                baselines.append(self.element_positions[j] - self.element_positions[i])
        return np.unique(baselines)

    @property
    def max_baseline(self) -> float:
        """Maximum baseline length (inches)."""
        return float(np.max(self.baselines))

    @property
    def min_baseline(self) -> float:
        """Minimum baseline length (inches)."""
        return float(np.min(self.baselines))


@dataclass
class PlatformAntenna:
    """Platform antenna configuration (legacy format)."""
    name: str
    type: str
    position: str
    orientation_deg: float
    peak_gain_dbi: float


@dataclass
class DetailedAntenna:
    """Detailed antenna specification with position coordinates."""
    name: str
    position: List[float]         # [x, y, z] in meters
    orientation: List[float]       # [azimuth, elevation] in degrees
    freq_band: str
    antenna_type: str
    peak_gain_dbi: float
    beamwidth_deg: float


@dataclass
class PlatformConfig:
    """Platform configuration (Task 1.1)."""
    name: str
    length_m: float
    width_m: float
    altitude_m: float
    speed_mps: float
    rcs_m2: float = 2.0  # Platform RCS for dynamic detection range requirement


@dataclass
class AntennaConfig:
    """Antenna configuration (Task 1.1: Updated structure)."""
    esm_type: str
    esm_beamwidth_deg: float
    esm_peak_gain_dbi: float
    esm_polarization: str
    esm_front_to_back_db: float = 15.0

    # Detailed antenna arrays (Task 1.1)
    rx_antennas: List[DetailedAntenna] = field(default_factory=list)
    tx_antennas: List[DetailedAntenna] = field(default_factory=list)

    # Legacy platform antennas (for backward compatibility)
    platform_antennas: List[PlatformAntenna] = field(default_factory=list)


@dataclass
class SystemConfig:
    """Complete system configuration."""
    # Frequency range
    freq_min_ghz: float
    freq_max_ghz: float
    freq_reference_ghz: float

    # Subsystem configurations
    adc: ADCConfig
    rf_chain: RFChainConfig
    interferometer: InterferometerConfig
    antennas: AntennaConfig
    platform: Optional[PlatformConfig] = None  # Task 1.1: Platform config

    def print_summary(self):
        """Print configuration summary."""
        print("=" * 70)
        print("EW SYSTEM CONFIGURATION")
        print("=" * 70)

        print(f"\nFrequency Range: {self.freq_min_ghz} - {self.freq_max_ghz} GHz")

        print(f"\nADC Configuration:")
        print(f"  Model: {self.adc.model}")
        print(f"  Sample Rate: {self.adc.sample_rate_gsps} GSPS")
        print(f"  Resolution: {self.adc.resolution_bits} bits")
        print(f"  Noise Format: {self.adc.noise_format}")
        print(f"  Bands: {len(self.adc.bands)}")

        print(f"\nRF Chain Configuration:")
        print(f"  Cascade NF: {self.rf_chain.cascade_noise_figure_db} dB")
        print(f"  Total Gain: {self.rf_chain.total_gain_db} dB")
        print(f"  Damage Threshold: {self.rf_chain.damage_threshold_dbm} dBm")

        print(f"\nInterferometer Configuration:")
        print(f"  Elements: {self.interferometer.n_elements}")
        print(f"  Element Positions: {self.interferometer.element_positions} inches")
        print(f"  Max Baseline: {self.interferometer.max_baseline:.2f} inches")
        print(f"  Phase Error (high SNR): {self.interferometer.phase_error_high_snr_deg} deg")

        print()


def load_system_config(config_path: Optional[str] = None) -> SystemConfig:
    """
    Load system configuration from YAML file.

    Args:
        config_path: Path to YAML config file. If None, uses default.

    Returns:
        SystemConfig object
    """
    if config_path is None:
        # Task 1.0: Updated to use centralized config/ directory
        config_path = Path(__file__).parent.parent / "config" / "system_config.yaml"
    else:
        config_path = Path(config_path)

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    # Parse frequency config
    freq = data['frequency']

    # Parse ADC config
    adc_data = data['adc']
    adc_bands = {}
    for band_name, band_data in adc_data['bands'].items():
        adc_bands[band_name] = ADCBandConfig(
            freq_range_ghz=tuple(band_data['freq_range_ghz']),
            noise_density_db=float(band_data['noise_density_db']),
            sfdr_db=float(band_data['sfdr_db']),
            full_scale_dbm=float(band_data['full_scale_dbm']),
            enob=float(band_data['enob'])
        )

    adc = ADCConfig(
        model=adc_data['model'],
        sample_rate_gsps=float(adc_data['sample_rate_gsps']),
        resolution_bits=int(adc_data['resolution_bits']),
        noise_format=adc_data['noise_format'],
        bands=adc_bands,
        input_impedance_ohm=float(adc_data['input_impedance_ohm'])
    )

    # Parse RF chain config from rf_chains.rx_paths (use primary RX path)
    rf_chains_data = data.get('rf_chains', {})
    rx_paths = rf_chains_data.get('rx_paths', {})

    # Get primary RX path (2-18 GHz) or first available
    primary_rx_key = 'rx_2_18ghz'
    if primary_rx_key not in rx_paths and rx_paths:
        primary_rx_key = list(rx_paths.keys())[0]

    rf_data = rx_paths.get(primary_rx_key, {})
    rf_components = []
    for comp_data in rf_data.get('components', []):
        rf_components.append(RFChainComponent(
            name=comp_data['name'],
            type=comp_data['type'],
            gain_db=float(comp_data.get('gain_db', 0)),
            noise_figure_db=float(comp_data.get('noise_figure_db', 0))
        ))

    # Calculate total gain dynamically from components (Task 3 fix)
    total_gain_db = sum(comp.gain_db for comp in rf_components) if rf_components else 30.0

    rf_chain = RFChainConfig(
        cascade_noise_figure_db=float(rf_data.get('cascade_noise_figure_db', 3.5)),
        total_gain_db=total_gain_db,  # Now calculated dynamically
        damage_threshold_dbm=float(rf_data.get('damage_threshold_dbm', 10)),
        components=rf_components
    )

    # Parse interferometer config
    interf_data = data['interferometer']
    mounting_data = interf_data['mounting']

    interferometer = InterferometerConfig(
        n_elements=int(interf_data['n_elements']),
        freq_range_ghz=tuple(interf_data['freq_range_ghz']),  # Task 3
        c_light_in_per_ns=float(interf_data['c_light_in_per_ns']),
        element_positions=np.array(interf_data['element_positions']),
        phase_error_high_snr_deg=float(interf_data['phase_error_high_snr_deg']),
        max_incident_angle_deg=float(interf_data['max_incident_angle_deg']),
        mounting=InterferometerMounting(
            offset_body_m=np.array(mounting_data['offset_body_m']),
            orientation_deg=np.array(mounting_data['orientation_deg'])
        )
    )

    # Parse antenna config (Task 1.1: Updated to support new flattened structure)
    ant_data = data['antennas']

    # ESM antenna parameters (now flattened in YAML)
    if 'esm_antenna' in ant_data:
        # Old structure (backward compatibility)
        esm_ant = ant_data['esm_antenna']
        esm_type = esm_ant['type']
        esm_beamwidth = float(esm_ant['beamwidth_deg'])
        esm_gain = float(esm_ant['peak_gain_dbi'])
        esm_pol = esm_ant['polarization']
        esm_ftb = float(esm_ant.get('front_to_back_db', 15.0))
    else:
        # New flattened structure (Task 1.1)
        esm_type = ant_data.get('esm_type', 'spiral')
        esm_beamwidth = float(ant_data.get('esm_beamwidth_deg', 70))
        esm_gain = float(ant_data.get('esm_peak_gain_dbi', 3.0))
        esm_pol = ant_data.get('esm_polarization', 'LHCP')
        esm_ftb = float(ant_data.get('esm_front_to_back_db', 15.0))

    # Parse RX antennas (Task 1.1)
    rx_antennas = []
    for rx_data in ant_data.get('rx_antennas', []):
        rx_antennas.append(DetailedAntenna(
            name=rx_data['name'],
            position=rx_data['position'],
            orientation=rx_data['orientation'],
            freq_band=rx_data.get('freq_band', '2-18 GHz'),
            antenna_type=rx_data.get('type', 'spiral'),
            peak_gain_dbi=float(rx_data.get('peak_gain_dbi', esm_gain)),
            beamwidth_deg=float(rx_data.get('beamwidth_deg', esm_beamwidth))
        ))

    # Parse TX antennas (Task 1.1)
    tx_antennas = []
    for tx_data in ant_data.get('tx_antennas', []):
        tx_antennas.append(DetailedAntenna(
            name=tx_data['name'],
            position=tx_data['position'],
            orientation=tx_data['orientation'],
            freq_band=tx_data.get('freq_band', '2-18 GHz'),
            antenna_type=tx_data.get('type', 'horn'),
            peak_gain_dbi=float(tx_data.get('peak_gain_dbi', 12.0)),
            beamwidth_deg=float(tx_data.get('beamwidth_deg', 30.0))
        ))

    # Parse legacy platform antennas (backward compatibility)
    platform_antennas = []
    for pa_data in ant_data.get('platform_antennas', []):
        platform_antennas.append(PlatformAntenna(
            name=pa_data['name'],
            type=pa_data['type'],
            position=pa_data['position'],
            orientation_deg=float(pa_data['orientation_deg']),
            peak_gain_dbi=float(pa_data['peak_gain_dbi'])
        ))

    antennas = AntennaConfig(
        esm_type=esm_type,
        esm_beamwidth_deg=esm_beamwidth,
        esm_peak_gain_dbi=esm_gain,
        esm_polarization=esm_pol,
        esm_front_to_back_db=esm_ftb,
        rx_antennas=rx_antennas,
        tx_antennas=tx_antennas,
        platform_antennas=platform_antennas
    )

    # Parse platform config (Task 1.1)
    platform = None
    if 'platform' in data:
        plat_data = data['platform']
        geom_data = plat_data.get('geometry', {})
        platform = PlatformConfig(
            name=plat_data.get('name', 'UAV Platform'),
            length_m=float(geom_data.get('length_m', 2.0)),
            width_m=float(geom_data.get('width_m', 2.5)),
            altitude_m=float(plat_data.get('altitude_m', 5000)),
            speed_mps=float(plat_data.get('speed_mps', 100)),
            rcs_m2=float(plat_data.get('rcs_m2', 2.0))
        )

    return SystemConfig(
        freq_min_ghz=float(freq['min_ghz']),
        freq_max_ghz=float(freq['max_ghz']),
        freq_reference_ghz=float(freq['reference_ghz']),
        adc=adc,
        rf_chain=rf_chain,
        interferometer=interferometer,
        antennas=antennas,
        platform=platform  # Task 1.1
    )
