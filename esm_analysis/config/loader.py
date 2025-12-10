"""
Configuration Loader Module

Loads and validates YAML configuration files for ESM analysis.
Provides dataclass-based configuration objects with validation.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import yaml


# =============================================================================
# DATA CLASSES FOR CONFIGURATION
# =============================================================================

@dataclass
class AntennaConfig:
    """ESM receiver antenna configuration."""
    gain_dbi: float = 2.0
    pattern_type: str = "omnidirectional"
    azimuth_coverage_deg: float = 360.0
    elevation_coverage_deg: float = 120.0


@dataclass
class ReceiverConfig:
    """ESM receiver parameters."""
    freq_min_hz: float = 2.0e9
    freq_max_hz: float = 18.0e9
    antenna: AntennaConfig = field(default_factory=AntennaConfig)
    noise_figure_db: float = 6.0
    bandwidth_hz: float = 20.0e6  # Channelizer bandwidth for noise calculations
    instantaneous_bandwidth_ghz: float = 1.0  # IBW for scanning (1 GHz)
    system_losses_db: float = 3.0
    snr_threshold_db: float = 10.0
    pfa: float = 1e-6  # Probability of false alarm (default 10^-6)
    tune_time_us: float = 50.0
    settling_time_us: float = 10.0

    @property
    def total_losses_db(self) -> float:
        """Total system losses including implementation."""
        return self.system_losses_db

    @property
    def instantaneous_bandwidth_mhz(self) -> float:
        """Instantaneous bandwidth in MHz."""
        return self.instantaneous_bandwidth_ghz * 1000


@dataclass
class PlatformConfig:
    """Platform configuration."""
    name: str = "UAV Platform"
    altitude_m: float = 5000.0
    speed_mps: float = 100.0
    antenna_positions: List[Dict] = field(default_factory=list)


@dataclass
class EnvironmentConfig:
    """Environmental parameters."""
    temperature_k: float = 290.0
    propagation_model: str = "free_space"
    include_atmospheric_loss: bool = False


@dataclass
class SidelobeConfig:
    """Sidelobe level configuration."""
    main_beam_offset_db: float = 0.0
    first_sidelobe_db: float = -20.0
    back_lobe_db: float = -30.0


@dataclass
class AnalysisConfig:
    """Analysis requirements configuration."""
    required_detection_range_m: float = 100000.0
    sidelobe_levels: SidelobeConfig = field(default_factory=SidelobeConfig)
    default_scan_positions: int = 8
    dwell_margin_factor: float = 1.5
    sidelobe_check_interval_s: float = 60.0
    verbose: bool = True
    debug_output: bool = True
    generate_plots: bool = True


@dataclass
class OutputConfig:
    """Output configuration."""
    results_dir: str = "./results"
    save_csv: bool = True
    save_json: bool = True
    plot_format: str = "png"
    plot_dpi: int = 150


@dataclass
class SystemConfig:
    """Complete system configuration container."""
    name: str = "ESM Receiver System"
    description: str = ""
    version: str = "1.0"
    receiver: ReceiverConfig = field(default_factory=ReceiverConfig)
    platform: PlatformConfig = field(default_factory=PlatformConfig)
    environment: EnvironmentConfig = field(default_factory=EnvironmentConfig)
    analysis: AnalysisConfig = field(default_factory=AnalysisConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    def __str__(self) -> str:
        return (
            f"SystemConfig: {self.name}\n"
            f"  Frequency: {self.receiver.freq_min_hz/1e9:.1f} - "
            f"{self.receiver.freq_max_hz/1e9:.1f} GHz\n"
            f"  SNR Threshold: {self.receiver.snr_threshold_db:.1f} dB\n"
            f"  Required Detection Range: "
            f"{self.analysis.required_detection_range_m/1000:.1f} km"
        )


# =============================================================================
# THREAT DATA CLASSES
# =============================================================================

@dataclass
class Threat:
    """Single threat definition."""
    id: str
    name: str
    category: str = "unknown"
    priority: int = 3

    # RF Parameters
    frequency_hz: float = 10.0e9
    peak_power_w: float = 100000.0
    antenna_gain_dbi: float = 30.0

    # Sidelobe levels (relative to main beam)
    first_sidelobe_db: float = -20.0
    back_lobe_db: float = -30.0

    # Pulse Parameters
    pri_us: float = 1000.0
    pulse_width_us: float = 1.0
    duty_cycle: float = 0.001

    # Scan Parameters
    scan_type: str = "rotating"
    scan_period_s: float = 5.0
    scan_sector_deg: float = 360.0

    # Requirements
    required_detection_range_m: Optional[float] = None

    # Additional info
    notes: str = ""
    polarization: str = "horizontal"

    @property
    def peak_power_dbw(self) -> float:
        """Peak power in dBW."""
        return 10 * _safe_log10(self.peak_power_w)

    @property
    def peak_power_dbm(self) -> float:
        """Peak power in dBm."""
        return self.peak_power_dbw + 30

    @property
    def pri_s(self) -> float:
        """PRI in seconds."""
        return self.pri_us * 1e-6

    @property
    def frequency_ghz(self) -> float:
        """Frequency in GHz."""
        return self.frequency_hz / 1e9

    @property
    def eirp_dbw(self) -> float:
        """Effective Isotropic Radiated Power (main beam) in dBW."""
        return self.peak_power_dbw + self.antenna_gain_dbi

    @property
    def sidelobe_gain_dbi(self) -> float:
        """Effective sidelobe gain in dBi."""
        return self.antenna_gain_dbi + self.first_sidelobe_db

    @property
    def backlobe_gain_dbi(self) -> float:
        """Effective back lobe gain in dBi."""
        return self.antenna_gain_dbi + self.back_lobe_db

    def __str__(self) -> str:
        return (
            f"Threat: {self.name} ({self.id})\n"
            f"  Category: {self.category}, Priority: {self.priority}\n"
            f"  Frequency: {self.frequency_ghz:.2f} GHz\n"
            f"  Peak Power: {self.peak_power_w/1000:.1f} kW "
            f"({self.peak_power_dbw:.1f} dBW)\n"
            f"  Antenna Gain: {self.antenna_gain_dbi:.1f} dBi "
            f"(SL: {self.first_sidelobe_db:.1f} dB, BL: {self.back_lobe_db:.1f} dB)\n"
            f"  EIRP: {self.eirp_dbw:.1f} dBW (main beam)\n"
            f"  Scan: {self.scan_type}, Period: {self.scan_period_s:.2f} s, "
            f"Sector: {self.scan_sector_deg:.0f}°\n"
            f"  PRI: {self.pri_us:.1f} µs"
        )


@dataclass
class ThreatLibrary:
    """Collection of threat definitions."""
    threats: Dict[str, Threat] = field(default_factory=dict)
    threat_sets: Dict[str, List[str]] = field(default_factory=dict)
    defaults: Dict[str, Any] = field(default_factory=dict)

    def get_threat(self, threat_id: str) -> Optional[Threat]:
        """Get a threat by ID."""
        return self.threats.get(threat_id)

    def get_threats_by_category(self, category: str) -> List[Threat]:
        """Get all threats in a category."""
        return [t for t in self.threats.values() if t.category == category]

    def get_threats_by_priority(self, max_priority: int = 3) -> List[Threat]:
        """Get threats up to specified priority level."""
        return [t for t in self.threats.values() if t.priority <= max_priority]

    def get_threat_set(self, set_name: str) -> List[Threat]:
        """Get threats in a named threat set."""
        if set_name not in self.threat_sets:
            return []
        threat_ids = self.threat_sets[set_name]
        if threat_ids == "all":
            return list(self.threats.values())
        return [self.threats[tid] for tid in threat_ids if tid in self.threats]

    def list_threats(self) -> List[str]:
        """List all threat IDs."""
        return list(self.threats.keys())

    def list_categories(self) -> List[str]:
        """List all unique categories."""
        return list(set(t.category for t in self.threats.values()))

    def __len__(self) -> int:
        return len(self.threats)

    def __iter__(self):
        return iter(self.threats.values())


# =============================================================================
# ANALYSIS REQUIREMENTS
# =============================================================================

@dataclass
class AnalysisRequirements:
    """Requirements for a specific analysis run."""
    threat_ids: List[str] = field(default_factory=list)
    detection_range_m: Optional[float] = None
    snr_threshold_db: Optional[float] = None
    include_sidelobe_analysis: bool = True
    include_scheduling: bool = True
    generate_report: bool = True

    def __str__(self) -> str:
        return (
            f"Analysis Requirements:\n"
            f"  Threats: {len(self.threat_ids)} selected\n"
            f"  Detection Range: {self.detection_range_m/1000 if self.detection_range_m else 'default'} km\n"
            f"  SNR Threshold: {self.snr_threshold_db if self.snr_threshold_db else 'default'} dB"
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _safe_log10(x: float) -> float:
    """Safe log10 that handles zero/negative values."""
    import math
    if x <= 0:
        return -100.0  # Floor value
    return math.log10(x)


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


def _nested_get(data: dict, keys: List[str], default: Any = None) -> Any:
    """Get nested dictionary value safely."""
    for key in keys:
        if isinstance(data, dict):
            data = data.get(key, default)
        else:
            return default
    return data


def _parse_antenna_config(data: dict) -> AntennaConfig:
    """Parse antenna configuration from dict."""
    return AntennaConfig(
        gain_dbi=data.get('gain_dbi', 2.0),
        pattern_type=data.get('pattern_type', 'omnidirectional'),
        azimuth_coverage_deg=data.get('azimuth_coverage_deg', 360.0),
        elevation_coverage_deg=data.get('elevation_coverage_deg', 120.0)
    )


def _parse_receiver_config(data: dict) -> ReceiverConfig:
    """Parse receiver configuration from dict."""
    antenna_data = data.get('antenna', {})
    return ReceiverConfig(
        freq_min_hz=_to_float(data.get('freq_min_hz'), 2.0e9),
        freq_max_hz=_to_float(data.get('freq_max_hz'), 18.0e9),
        antenna=_parse_antenna_config(antenna_data),
        noise_figure_db=_to_float(data.get('noise_figure_db'), 6.0),
        bandwidth_hz=_to_float(data.get('bandwidth_hz'), 20.0e6),
        instantaneous_bandwidth_ghz=_to_float(data.get('instantaneous_bandwidth_ghz'), 1.0),
        system_losses_db=_to_float(data.get('system_losses_db'), 3.0),
        snr_threshold_db=_to_float(data.get('snr_threshold_db'), 10.0),
        pfa=_to_float(data.get('pfa'), 1e-6),
        tune_time_us=_to_float(data.get('tune_time_us'), 50.0),
        settling_time_us=_to_float(data.get('settling_time_us'), 10.0)
    )


def _parse_platform_config(data: dict) -> PlatformConfig:
    """Parse platform configuration from dict."""
    return PlatformConfig(
        name=data.get('name', 'UAV Platform'),
        altitude_m=_to_float(data.get('altitude_m'), 5000.0),
        speed_mps=_to_float(data.get('speed_mps'), 100.0),
        antenna_positions=data.get('antenna_positions', [])
    )


def _parse_environment_config(data: dict) -> EnvironmentConfig:
    """Parse environment configuration from dict."""
    return EnvironmentConfig(
        temperature_k=_to_float(data.get('temperature_k'), 290.0),
        propagation_model=data.get('propagation_model', 'free_space'),
        include_atmospheric_loss=data.get('include_atmospheric_loss', False)
    )


def _parse_sidelobe_config(data: dict) -> SidelobeConfig:
    """Parse sidelobe configuration from dict."""
    return SidelobeConfig(
        main_beam_offset_db=_to_float(data.get('main_beam_offset_db'), 0.0),
        first_sidelobe_db=_to_float(data.get('first_sidelobe_db'), -20.0),
        back_lobe_db=_to_float(data.get('back_lobe_db'), -30.0)
    )


def _parse_analysis_config(data: dict) -> AnalysisConfig:
    """Parse analysis configuration from dict."""
    sidelobe_data = data.get('sidelobe_levels', {})
    return AnalysisConfig(
        required_detection_range_m=_to_float(data.get('required_detection_range_m'), 100000.0),
        sidelobe_levels=_parse_sidelobe_config(sidelobe_data),
        default_scan_positions=_to_int(data.get('default_scan_positions'), 8),
        dwell_margin_factor=_to_float(data.get('dwell_margin_factor'), 1.5),
        sidelobe_check_interval_s=_to_float(data.get('sidelobe_check_interval_s'), 60.0),
        verbose=data.get('verbose', True),
        debug_output=data.get('debug_output', True),
        generate_plots=data.get('generate_plots', True)
    )


def _parse_output_config(data: dict) -> OutputConfig:
    """Parse output configuration from dict."""
    return OutputConfig(
        results_dir=data.get('results_dir', './results'),
        save_csv=data.get('save_csv', True),
        save_json=data.get('save_json', True),
        plot_format=data.get('plot_format', 'png'),
        plot_dpi=data.get('plot_dpi', 150)
    )


def _parse_system_config(data: dict) -> SystemConfig:
    """Parse complete system configuration from dict."""
    system_info = data.get('system', {})
    return SystemConfig(
        name=system_info.get('name', 'ESM Receiver System'),
        description=system_info.get('description', ''),
        version=system_info.get('version', '1.0'),
        receiver=_parse_receiver_config(data.get('receiver', {})),
        platform=_parse_platform_config(data.get('platform', {})),
        environment=_parse_environment_config(data.get('environment', {})),
        analysis=_parse_analysis_config(data.get('analysis', {})),
        output=_parse_output_config(data.get('output', {}))
    )


def _parse_threat(threat_id: str, data: dict, defaults: dict) -> Threat:
    """Parse a single threat definition."""
    # Merge defaults with threat-specific data
    merged = {**defaults, **data}

    # Handle required_detection_range_m which can be None
    req_range = merged.get('required_detection_range_m')
    if req_range is not None:
        req_range = _to_float(req_range, None)

    return Threat(
        id=threat_id,
        name=merged.get('name', threat_id),
        category=merged.get('category', 'unknown'),
        priority=_to_int(merged.get('priority'), 3),
        frequency_hz=_to_float(merged.get('frequency_hz'), 10.0e9),
        peak_power_w=_to_float(merged.get('peak_power_w'), 100000.0),
        antenna_gain_dbi=_to_float(merged.get('antenna_gain_dbi'), 30.0),
        first_sidelobe_db=_to_float(merged.get('first_sidelobe_db'), -20.0),
        back_lobe_db=_to_float(merged.get('back_lobe_db'), -30.0),
        pri_us=_to_float(merged.get('pri_us'), 1000.0),
        pulse_width_us=_to_float(merged.get('pulse_width_us'), 1.0),
        duty_cycle=_to_float(merged.get('duty_cycle'), 0.001),
        scan_type=merged.get('scan_type', 'rotating'),
        scan_period_s=_to_float(merged.get('scan_period_s'), 5.0),
        scan_sector_deg=_to_float(merged.get('scan_sector_deg'), 360.0),
        required_detection_range_m=req_range,
        notes=merged.get('notes', ''),
        polarization=merged.get('polarization', 'horizontal')
    )


def _parse_threat_library(data: dict) -> ThreatLibrary:
    """Parse threat library from dict."""
    defaults = data.get('defaults', {})
    threats_data = data.get('threats', {})
    threat_sets_data = data.get('threat_sets', {})

    threats = {}
    for threat_id, threat_data in threats_data.items():
        threats[threat_id] = _parse_threat(threat_id, threat_data, defaults)

    threat_sets = {}
    for set_name, set_data in threat_sets_data.items():
        if isinstance(set_data, dict):
            threat_ids = set_data.get('threats', [])
        else:
            threat_ids = set_data
        threat_sets[set_name] = threat_ids

    return ThreatLibrary(
        threats=threats,
        threat_sets=threat_sets,
        defaults=defaults
    )


# =============================================================================
# MAIN LOADING FUNCTIONS
# =============================================================================

def load_yaml_file(filepath: Union[str, Path]) -> dict:
    """Load a YAML file and return as dict."""
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Configuration file not found: {filepath}")

    with open(filepath, 'r') as f:
        return yaml.safe_load(f) or {}


def load_system_config(filepath: Union[str, Path] = None) -> SystemConfig:
    """
    Load system configuration from YAML file.

    Args:
        filepath: Path to system_config.yaml. If None, uses default location.

    Returns:
        SystemConfig object with all system parameters.
    """
    if filepath is None:
        # Default to config directory relative to this file
        config_dir = Path(__file__).parent
        filepath = config_dir / "system_config.yaml"

    data = load_yaml_file(filepath)
    return _parse_system_config(data)


def load_threat_library(filepath: Union[str, Path] = None) -> ThreatLibrary:
    """
    Load threat library from YAML file.

    Args:
        filepath: Path to threats.yaml. If None, uses default location.

    Returns:
        ThreatLibrary object with all threat definitions.
    """
    if filepath is None:
        config_dir = Path(__file__).parent
        filepath = config_dir / "threats.yaml"

    data = load_yaml_file(filepath)
    return _parse_threat_library(data)


def load_config(
    system_config_path: Union[str, Path] = None,
    threats_path: Union[str, Path] = None
) -> tuple:
    """
    Load all configuration files.

    Args:
        system_config_path: Path to system configuration YAML.
        threats_path: Path to threats library YAML.

    Returns:
        Tuple of (SystemConfig, ThreatLibrary)
    """
    system_config = load_system_config(system_config_path)
    threat_library = load_threat_library(threats_path)

    return system_config, threat_library


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def get_default_config_dir() -> Path:
    """Get the default configuration directory path."""
    return Path(__file__).parent


def create_analysis_requirements(
    threat_ids: List[str] = None,
    threat_set: str = None,
    threat_library: ThreatLibrary = None,
    detection_range_m: float = None,
    snr_threshold_db: float = None
) -> AnalysisRequirements:
    """
    Create analysis requirements from various inputs.

    Args:
        threat_ids: List of specific threat IDs to analyze.
        threat_set: Name of a threat set (alternative to threat_ids).
        threat_library: ThreatLibrary to resolve threat set.
        detection_range_m: Override detection range.
        snr_threshold_db: Override SNR threshold.

    Returns:
        AnalysisRequirements object.
    """
    if threat_ids is None:
        threat_ids = []

    if threat_set and threat_library:
        set_threats = threat_library.get_threat_set(threat_set)
        threat_ids = [t.id for t in set_threats]

    return AnalysisRequirements(
        threat_ids=threat_ids,
        detection_range_m=detection_range_m,
        snr_threshold_db=snr_threshold_db
    )


# =============================================================================
# DYNAMIC PFA DERIVATION
# =============================================================================

def compute_dynamic_pfa(snr_threshold_db: float, noise_floor_dbm: float = None,
                         bandwidth_hz: float = 20.0e6,
                         noise_figure_db: float = 6.0) -> float:
    """
    Compute probability of false alarm (Pfa) from SNR threshold.

    This ensures Pfa is derived from the user-specified threshold setting
    rather than using a hardcoded value. Changes to snr_threshold_db will
    automatically propagate to affect detection probability calculations.

    Args:
        snr_threshold_db: SNR threshold in dB above noise floor
        noise_floor_dbm: Noise floor in dBm. If None, calculated from bandwidth/NF.
        bandwidth_hz: Receiver bandwidth for noise floor calculation
        noise_figure_db: System noise figure in dB

    Returns:
        Probability of false alarm per sample
    """
    import math
    from scipy import special

    # Calculate noise floor if not provided
    if noise_floor_dbm is None:
        # Noise floor (dBm) = kTB + NF = -174 + 10*log10(B) + NF
        noise_floor_dbm = -174 + 10 * math.log10(bandwidth_hz) + noise_figure_db

    # Convert SNR threshold to sigma (standard deviations of noise)
    # threshold_db = 20*log10(threshold_sigma) => threshold_sigma = 10^(threshold_db/20)
    threshold_sigma = 10 ** (snr_threshold_db / 20)

    # Pfa for Gaussian noise = erfc(threshold_sigma / sqrt(2)) / 2
    pfa = special.erfc(threshold_sigma / math.sqrt(2)) / 2

    return float(pfa)


# =============================================================================
# SHARED SYSTEM CONFIG INTEGRATION
# =============================================================================

def load_receiver_from_system_config(
    bandwidth_hz: float = 20.0e6,
    snr_threshold_db: float = 10.0
) -> ReceiverConfig:
    """
    Load receiver configuration from shared system_config.

    This integrates with the centralized system configuration to ensure
    the ESM analysis uses consistent noise floor and sensitivity values
    calculated from ADC + RF chain specifications.

    Phase 2 Update: Now calculates Pfa dynamically from SNR threshold
    using compute_dynamic_pfa(). Changes to snr_threshold_db will
    automatically propagate to detection probability calculations.

    Args:
        bandwidth_hz: Receiver bandwidth for noise calculations
        snr_threshold_db: Required SNR threshold for detection

    Returns:
        ReceiverConfig with sensitivity and Pfa derived from shared system config
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from system_config import load_system_config, calculate_sensitivity

    # Load shared config
    shared = load_system_config()

    # Calculate sensitivity at reference frequency
    sensitivity_dbm = calculate_sensitivity(
        shared,
        frequency_ghz=shared.freq_reference_ghz,
        bandwidth_hz=bandwidth_hz,
        snr_required_db=snr_threshold_db
    )

    # Get antenna configuration
    ant = shared.antennas
    noise_figure_db = shared.rf_chain.cascade_noise_figure_db

    # Calculate Pfa dynamically from SNR threshold
    pfa = compute_dynamic_pfa(
        snr_threshold_db=snr_threshold_db,
        bandwidth_hz=bandwidth_hz,
        noise_figure_db=noise_figure_db
    )

    return ReceiverConfig(
        freq_min_hz=shared.freq_min_ghz * 1e9,
        freq_max_hz=shared.freq_max_ghz * 1e9,
        antenna=AntennaConfig(
            gain_dbi=ant.esm_peak_gain_dbi,
            pattern_type=ant.esm_type,
            azimuth_coverage_deg=ant.esm_beamwidth_deg,
            elevation_coverage_deg=90.0
        ),
        noise_figure_db=noise_figure_db,
        bandwidth_hz=bandwidth_hz,
        system_losses_db=3.0,  # Implementation losses
        snr_threshold_db=snr_threshold_db,
        pfa=pfa  # Dynamic Pfa derived from SNR threshold
    )


def get_system_sensitivity_dbm(
    frequency_ghz: float = None,
    bandwidth_hz: float = 20.0e6,
    snr_required_db: float = 10.0
) -> float:
    """
    Get system sensitivity in dBm from shared system config.

    This calculates sensitivity based on:
    - Thermal noise (kTB)
    - RF chain cascade noise figure
    - ADC noise contribution
    - Required SNR

    Args:
        frequency_ghz: Operating frequency. If None, uses reference frequency.
        bandwidth_hz: Receiver bandwidth
        snr_required_db: Required SNR for detection

    Returns:
        Sensitivity in dBm
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    from system_config import load_system_config, calculate_sensitivity

    shared = load_system_config()

    if frequency_ghz is None:
        frequency_ghz = shared.freq_reference_ghz

    return calculate_sensitivity(
        shared,
        frequency_ghz=frequency_ghz,
        bandwidth_hz=bandwidth_hz,
        snr_required_db=snr_required_db
    )


# =============================================================================
# MODULE TEST
# =============================================================================

if __name__ == "__main__":
    # Test loading configurations
    print("Testing configuration loader...")

    try:
        system_config, threat_library = load_config()

        print("\n" + "="*60)
        print("SYSTEM CONFIGURATION")
        print("="*60)
        print(system_config)

        print("\n" + "="*60)
        print("THREAT LIBRARY")
        print("="*60)
        print(f"Total threats: {len(threat_library)}")
        print(f"Categories: {threat_library.list_categories()}")
        print(f"Threat IDs: {threat_library.list_threats()}")

        print("\n--- Sample Threat ---")
        sample = list(threat_library.threats.values())[0]
        print(sample)

        print("\nConfiguration loading successful!")

    except Exception as e:
        print(f"Error loading configuration: {e}")
        raise
