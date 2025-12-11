"""
System Noise Floor Calculator

Calculates composite system noise floor from:
- Thermal noise (kTB)
- RF chain noise figure
- ADC noise contribution

Provides:
- Frequency-dependent noise floor
- System sensitivity
- Dynamic range
- Multi-band (Low/Mid) noise floor calculations
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, Dict, List
from pathlib import Path
import yaml

from .loader import SystemConfig


# Physical constants
K_BOLTZMANN = 1.380649e-23        # Boltzmann constant (J/K)
T_REFERENCE = 290.0               # Reference temperature (K)


@dataclass
class NoiseFloorResult:
    """Result of noise floor calculation."""
    thermal_noise_dbm: float          # kTB noise
    rf_chain_noise_dbm: float         # After RF chain NF
    adc_noise_dbm: float              # ADC contribution at input
    system_noise_floor_dbm: float     # Total system noise floor
    sensitivity_dbm: float            # MDS (minimum detectable signal)
    dynamic_range_db: float           # From noise floor to damage threshold

    frequency_ghz: float
    bandwidth_hz: float
    snr_required_db: float
    band_name: str = "default"        # Band identifier (e.g., "Low", "Mid")

    def print_summary(self):
        """Print noise floor summary."""
        print(f"\nNoise Floor Analysis - {self.band_name} Band at {self.frequency_ghz:.2f} GHz:")
        print(f"  Bandwidth: {self.bandwidth_hz/1e6:.1f} MHz")
        print(f"  Thermal Noise (kTB): {self.thermal_noise_dbm:.1f} dBm")
        print(f"  After RF Chain NF: {self.rf_chain_noise_dbm:.1f} dBm")
        print(f"  ADC Contribution: {self.adc_noise_dbm:.1f} dBm")
        print(f"  System Noise Floor: {self.system_noise_floor_dbm:.1f} dBm")
        print(f"  Sensitivity (SNR={self.snr_required_db}dB): {self.sensitivity_dbm:.1f} dBm")
        print(f"  Dynamic Range: {self.dynamic_range_db:.1f} dB")


@dataclass
class MultiBandNoiseResult:
    """Result of multi-band noise floor calculation."""
    bands: Dict[str, NoiseFloorResult]

    def print_summary(self):
        """Print multi-band noise summary."""
        print("\n" + "="*60)
        print("MULTI-BAND NOISE FLOOR SUMMARY")
        print("="*60)
        for name, result in self.bands.items():
            print(f"\n{name}:")
            print(f"  Freq Range: {result.frequency_ghz:.1f} GHz")
            print(f"  Noise Floor: {result.system_noise_floor_dbm:.1f} dBm")
            print(f"  Sensitivity: {result.sensitivity_dbm:.1f} dBm")
            print(f"  Dynamic Range: {result.dynamic_range_db:.1f} dB")


def calculate_thermal_noise_dbm(bandwidth_hz: float, temperature_k: float = T_REFERENCE) -> float:
    """
    Calculate thermal noise power.

    Args:
        bandwidth_hz: Noise bandwidth in Hz
        temperature_k: Temperature in Kelvin

    Returns:
        Thermal noise power in dBm
    """
    noise_watts = K_BOLTZMANN * temperature_k * bandwidth_hz
    noise_dbm = 10 * np.log10(noise_watts) + 30  # Convert W to dBm
    return noise_dbm


def calculate_adc_noise_contribution(
    config: SystemConfig,
    frequency_ghz: float,
    bandwidth_hz: float
) -> float:
    """
    Calculate ADC noise contribution referred to RF input.

    The ADC noise is specified in dBFS/Hz or dBc/Hz. We convert this
    to an equivalent input noise power.

    Args:
        config: SystemConfig object
        frequency_ghz: Operating frequency in GHz
        bandwidth_hz: Noise bandwidth in Hz

    Returns:
        ADC noise contribution in dBm (referred to input)
    """
    adc = config.adc
    rf = config.rf_chain

    # Get ADC specs at this frequency
    noise_density_db = adc.get_noise_density_at_freq(frequency_ghz)
    band = adc.get_band_for_frequency(frequency_ghz)

    if band is None:
        # Use worst-case from last band
        full_scale_dbm = -2
    else:
        full_scale_dbm = band.full_scale_dbm

    # Convert noise density to noise power in bandwidth
    if adc.noise_format == 'dBFS/Hz':
        # dBFS/Hz: noise relative to full scale per Hz
        # Noise power = Full_Scale + Noise_Density + 10*log10(BW)
        adc_noise_at_adc_input = full_scale_dbm + noise_density_db + 10 * np.log10(bandwidth_hz)
    else:
        # dBc/Hz: noise relative to carrier per Hz
        # Need to assume some carrier level (e.g., at -10 dBFS for this spec)
        # Noise power = Carrier + Noise_Density + 10*log10(BW)
        carrier_level_dbm = full_scale_dbm - 10  # Typically spec'd at -10 dBFS
        adc_noise_at_adc_input = carrier_level_dbm + noise_density_db + 10 * np.log10(bandwidth_hz)

    # Refer ADC noise back to system input (before RF chain gain)
    adc_noise_at_input = adc_noise_at_adc_input - rf.total_gain_db

    return adc_noise_at_input


def calculate_system_noise_floor(
    config: SystemConfig,
    frequency_ghz: Optional[float] = None,
    bandwidth_hz: float = 1e6,
    snr_required_db: float = 10.0
) -> NoiseFloorResult:
    """
    Calculate complete system noise floor.

    The system noise floor combines:
    1. Thermal noise (kTB)
    2. RF chain noise figure
    3. ADC quantization/noise contribution

    Args:
        config: SystemConfig object
        frequency_ghz: Operating frequency (uses reference if None)
        bandwidth_hz: Noise bandwidth in Hz (default 1 MHz)
        snr_required_db: Required SNR for sensitivity calculation

    Returns:
        NoiseFloorResult with all noise components
    """
    if frequency_ghz is None:
        frequency_ghz = config.freq_reference_ghz

    # 1. Calculate thermal noise
    thermal_noise_dbm = calculate_thermal_noise_dbm(bandwidth_hz)

    # 2. Add RF chain noise figure
    rf_chain_noise_dbm = thermal_noise_dbm + config.rf_chain.cascade_noise_figure_db

    # 3. Calculate ADC noise contribution
    adc_noise_dbm = calculate_adc_noise_contribution(config, frequency_ghz, bandwidth_hz)

    # 4. Combine RF chain noise and ADC noise (power addition)
    # Convert to linear, add, convert back to dB
    rf_noise_linear = 10 ** (rf_chain_noise_dbm / 10)
    adc_noise_linear = 10 ** (adc_noise_dbm / 10)

    # Total noise is sum of independent noise sources
    total_noise_linear = rf_noise_linear + adc_noise_linear
    system_noise_floor_dbm = 10 * np.log10(total_noise_linear)

    # 5. Calculate sensitivity (MDS)
    sensitivity_dbm = system_noise_floor_dbm + snr_required_db

    # 6. Calculate dynamic range (Task 3.1: Use ADC Full Scale instead of Damage Threshold)
    # Get ADC band for this frequency
    band = config.adc.get_band_for_frequency(frequency_ghz)
    if band is None:
        # Use worst-case from last band
        adc_full_scale_dbm = -2
    else:
        adc_full_scale_dbm = band.full_scale_dbm

    dynamic_range_db = adc_full_scale_dbm - system_noise_floor_dbm

    return NoiseFloorResult(
        thermal_noise_dbm=thermal_noise_dbm,
        rf_chain_noise_dbm=rf_chain_noise_dbm,
        adc_noise_dbm=adc_noise_dbm,
        system_noise_floor_dbm=system_noise_floor_dbm,
        sensitivity_dbm=sensitivity_dbm,
        dynamic_range_db=dynamic_range_db,
        frequency_ghz=frequency_ghz,
        bandwidth_hz=bandwidth_hz,
        snr_required_db=snr_required_db
    )


def calculate_sensitivity(
    config: SystemConfig,
    frequency_ghz: Optional[float] = None,
    bandwidth_hz: float = 1e6,
    snr_required_db: float = 10.0
) -> float:
    """
    Calculate system sensitivity (minimum detectable signal).

    Convenience function that returns just the sensitivity value.

    Args:
        config: SystemConfig object
        frequency_ghz: Operating frequency (uses reference if None)
        bandwidth_hz: Noise bandwidth in Hz
        snr_required_db: Required SNR

    Returns:
        Sensitivity in dBm
    """
    result = calculate_system_noise_floor(config, frequency_ghz, bandwidth_hz, snr_required_db)
    return result.sensitivity_dbm


def calculate_noise_floor_vs_frequency(
    config: SystemConfig,
    frequencies_ghz: np.ndarray,
    bandwidth_hz: float = 1e6
) -> np.ndarray:
    """
    Calculate noise floor across a range of frequencies.

    Args:
        config: SystemConfig object
        frequencies_ghz: Array of frequencies to calculate
        bandwidth_hz: Noise bandwidth in Hz

    Returns:
        Array of noise floor values in dBm
    """
    noise_floors = np.zeros(len(frequencies_ghz))

    for i, freq in enumerate(frequencies_ghz):
        result = calculate_system_noise_floor(config, freq, bandwidth_hz)
        noise_floors[i] = result.system_noise_floor_dbm

    return noise_floors


def calculate_multiband_noise_floor(
    bandwidth_hz: float = 20e6,
    snr_required_db: float = 10.0
) -> MultiBandNoiseResult:
    """
    Calculate noise floor for all RX bands defined in system_config.

    Reads rf_chains from system_config.yaml and calculates noise floor
    for each RX path (Low Band <2 GHz, Mid Band 2-18 GHz).

    Args:
        bandwidth_hz: Analysis bandwidth in Hz (default 20 MHz)
        snr_required_db: Required SNR for sensitivity

    Returns:
        MultiBandNoiseResult with noise floor for each band
    """
    from .loader import load_system_config

    config = load_system_config()

    # Load rf_chains directly from YAML for multi-path data
    # Task 1.0: Updated to use centralized config/ directory
    config_path = Path(__file__).parent.parent / "config" / "system_config.yaml"
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    rf_chains = data.get('rf_chains', {})
    rx_paths = rf_chains.get('rx_paths', {})

    bands = {}

    for path_id, path_data in rx_paths.items():
        name = path_data.get('name', path_id)
        freq_range = path_data.get('freq_range_ghz', [2.0, 18.0])
        cascade_nf_db = path_data.get('cascade_noise_figure_db', 3.5)
        total_gain_db = path_data.get('total_gain_db', 30.0)
        damage_thresh_dbm = path_data.get('damage_threshold_dbm', 10)

        # Use center frequency for the band
        center_freq_ghz = (freq_range[0] + freq_range[1]) / 2

        # Calculate thermal noise
        thermal_noise_dbm = calculate_thermal_noise_dbm(bandwidth_hz)

        # Add RF chain noise figure
        rf_chain_noise_dbm = thermal_noise_dbm + cascade_nf_db

        # ADC noise contribution (use legacy config for ADC specs)
        adc_noise_dbm = calculate_adc_noise_contribution(config, center_freq_ghz, bandwidth_hz)

        # Combine noise sources
        rf_noise_linear = 10 ** (rf_chain_noise_dbm / 10)
        adc_noise_linear = 10 ** (adc_noise_dbm / 10)
        total_noise_linear = rf_noise_linear + adc_noise_linear
        system_noise_floor_dbm = 10 * np.log10(total_noise_linear)

        # Sensitivity and dynamic range (Task 3.1: Use ADC Full Scale)
        sensitivity_dbm = system_noise_floor_dbm + snr_required_db

        # Get ADC full scale for this frequency band
        band = config.adc.get_band_for_frequency(center_freq_ghz)
        if band is None:
            adc_full_scale_dbm = -2  # Worst-case default
        else:
            adc_full_scale_dbm = band.full_scale_dbm

        dynamic_range_db = adc_full_scale_dbm - system_noise_floor_dbm

        # Determine band name
        if freq_range[1] <= 2.0:
            band_name = "Low Band"
        elif freq_range[0] >= 2.0 and freq_range[1] <= 18.0:
            band_name = "Mid Band"
        else:
            band_name = name

        result = NoiseFloorResult(
            thermal_noise_dbm=thermal_noise_dbm,
            rf_chain_noise_dbm=rf_chain_noise_dbm,
            adc_noise_dbm=adc_noise_dbm,
            system_noise_floor_dbm=system_noise_floor_dbm,
            sensitivity_dbm=sensitivity_dbm,
            dynamic_range_db=dynamic_range_db,
            frequency_ghz=center_freq_ghz,
            bandwidth_hz=bandwidth_hz,
            snr_required_db=snr_required_db,
            band_name=band_name
        )

        bands[band_name] = result

    return MultiBandNoiseResult(bands=bands)
