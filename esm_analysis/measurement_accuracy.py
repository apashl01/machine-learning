"""
Pulse Parameter Measurement Accuracy Analysis

Models the accuracy of ESM pulse parameter measurements including:
- Frequency measurement (DLFD - Digital Delay Line Frequency Discriminator)
- Time of Arrival (TOA)
- Pulse Width (PW)
- Pulse Repetition Interval (PRI)

Key Concept: Threshold-Based SNR
The detection threshold is set to guarantee a minimum SNR for all detected pulses.
Measurement accuracy is computed based on this guaranteed SNR at the detector.
There is NO process gain - the input SNR is the measurement SNR.

DLFD Frequency Measurement:
The Digital Delay Line Frequency Discriminator measures phase shift across a
known delay to determine instantaneous frequency:
  φ = 2π × f × τ_delay
  σ_f = 1 / (2π × τ_delay × √(2 × SNR))
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple


# Physical constants
C = 3e8  # Speed of light (m/s)


@dataclass
class MeasurementConfig:
    """Configuration for measurement accuracy analysis."""
    # ADC parameters
    adc_sample_rate_gsps: float = 40.0

    # Channel bandwidth (detection bandwidth)
    channel_bandwidth_mhz: float = 20.0

    # DLFD parameters (Digital Delay Line Frequency Discriminator)
    dlfd_delay_ns: float = 50.0  # Delay line length (nanoseconds)
    dlfd_phase_quantization_bits: int = 12

    # Timing parameters
    timing_resolution_ns: float = 0.025  # 1/40 GHz = 25 ps

    @property
    def channel_bandwidth_hz(self) -> float:
        return self.channel_bandwidth_mhz * 1e6

    @property
    def dlfd_delay_s(self) -> float:
        return self.dlfd_delay_ns * 1e-9


@dataclass
class MeasurementResult:
    """Results of measurement accuracy analysis."""
    # Input conditions
    snr_db: float  # Detection/measurement SNR (guaranteed by threshold)

    # Frequency measurement (DLFD)
    frequency_accuracy_mhz: float
    frequency_resolution_mhz: float

    # Time of Arrival
    toa_accuracy_ns: float

    # Pulse Width
    pulse_width_accuracy_ns: float
    pulse_width_accuracy_percent: float  # Relative to actual PW

    # PRI measurement
    pri_accuracy_ns: float

    # Configuration used
    config: MeasurementConfig = field(default_factory=MeasurementConfig)

    def print_summary(self):
        """Print measurement accuracy summary."""
        print(f"\nMeasurement Accuracy Analysis")
        print(f"=" * 50)
        print(f"Detection SNR (threshold): {self.snr_db:.1f} dB")
        print(f"\nFrequency (DLFD):")
        print(f"  Accuracy (RMS): {self.frequency_accuracy_mhz:.3f} MHz")
        print(f"  Resolution: {self.frequency_resolution_mhz:.3f} MHz")
        print(f"\nTime of Arrival:")
        print(f"  Accuracy (RMS): {self.toa_accuracy_ns:.2f} ns")
        print(f"\nPulse Width:")
        print(f"  Accuracy (RMS): {self.pulse_width_accuracy_ns:.2f} ns")
        print(f"  Relative: {self.pulse_width_accuracy_percent:.1f}%")
        print(f"\nPRI:")
        print(f"  Accuracy (RMS): {self.pri_accuracy_ns:.2f} ns")


class MeasurementAccuracyAnalyzer:
    """
    Analyzer for ESM pulse parameter measurement accuracy.

    Models measurement errors as functions of SNR, where SNR is the
    guaranteed detection SNR (threshold-based).

    Key models:
    - DLFD: σ_f = 1 / (2π × τ × √(2×SNR))
    - TOA: σ_t = rise_time / (2 × √SNR)
    - PW: σ_pw = √2 × σ_toa (two TOA measurements)
    """

    def __init__(self, config: Optional[MeasurementConfig] = None):
        self.config = config or MeasurementConfig()

    def calculate_frequency_accuracy_dlfd(self, snr_db: float) -> Tuple[float, float]:
        """
        Calculate frequency measurement accuracy using DLFD model.

        Digital Delay Line Frequency Discriminator:
        - Measures phase difference across delay line
        - Phase = 2π × f × τ_delay
        - Frequency = phase / (2π × τ_delay)

        Accuracy (Cramer-Rao bound):
        σ_f = 1 / (2π × τ_delay × √(2 × SNR))

        Args:
            snr_db: Detection SNR in dB (guaranteed by threshold)

        Returns:
            Tuple of (accuracy_mhz, resolution_mhz)
        """
        snr_linear = 10 ** (snr_db / 10)
        tau = self.config.dlfd_delay_s

        # DLFD accuracy (Cramer-Rao bound)
        sigma_f_hz = 1 / (2 * np.pi * tau * np.sqrt(2 * snr_linear))

        # Phase quantization limit
        # Phase resolution = 2π / 2^N_bits
        # Frequency resolution = phase_resolution / (2π × τ)
        phase_resolution = 2 * np.pi / (2 ** self.config.dlfd_phase_quantization_bits)
        freq_resolution_hz = phase_resolution / (2 * np.pi * tau)

        # Total accuracy is RSS of noise-limited and quantization-limited
        sigma_f_total = np.sqrt(sigma_f_hz**2 + (freq_resolution_hz/2)**2)

        return sigma_f_total / 1e6, freq_resolution_hz / 1e6

    def calculate_toa_accuracy(self, snr_db: float, pulse_width_us: float = 1.0) -> float:
        """
        Calculate Time of Arrival accuracy.

        TOA accuracy is limited by:
        1. Rise time (determined by channel bandwidth)
        2. SNR (timing jitter)

        For a pulse with bandwidth-limited rise time:
        σ_TOA = rise_time / (2 × √SNR)

        where rise_time ≈ 0.35 / BW for a typical filter.

        Args:
            snr_db: Detection SNR in dB
            pulse_width_us: Pulse width in microseconds

        Returns:
            TOA accuracy in nanoseconds (RMS)
        """
        snr_linear = 10 ** (snr_db / 10)

        # Rise time from channel bandwidth
        # Using 10-90% rise time ≈ 0.35 / BW
        rise_time_s = 0.35 / self.config.channel_bandwidth_hz
        rise_time_ns = rise_time_s * 1e9

        # Timing accuracy from SNR
        sigma_toa_ns = rise_time_ns / (2 * np.sqrt(snr_linear))

        # For very short pulses, accuracy may be limited by pulse width
        pulse_width_ns = pulse_width_us * 1000
        if pulse_width_ns < rise_time_ns * 2:
            sigma_toa_ns = max(sigma_toa_ns, pulse_width_ns / (4 * np.sqrt(snr_linear)))

        # Also limited by timing resolution
        timing_floor_ns = self.config.timing_resolution_ns

        return np.sqrt(sigma_toa_ns**2 + timing_floor_ns**2)

    def calculate_pulse_width_accuracy(self, snr_db: float,
                                        pulse_width_us: float = 1.0) -> Tuple[float, float]:
        """
        Calculate pulse width measurement accuracy.

        Pulse width = trailing_edge_TOA - leading_edge_TOA
        σ_PW = √(σ_leading² + σ_trailing²) = √2 × σ_TOA

        Args:
            snr_db: Detection SNR in dB
            pulse_width_us: Actual pulse width in microseconds

        Returns:
            Tuple of (accuracy_ns, accuracy_percent)
        """
        sigma_toa = self.calculate_toa_accuracy(snr_db, pulse_width_us)

        # Two independent TOA measurements
        sigma_pw_ns = np.sqrt(2) * sigma_toa

        # Relative accuracy
        pulse_width_ns = pulse_width_us * 1000
        sigma_pw_percent = (sigma_pw_ns / pulse_width_ns) * 100

        return sigma_pw_ns, sigma_pw_percent

    def calculate_pri_accuracy(self, snr_db: float) -> float:
        """
        Calculate PRI (Pulse Repetition Interval) accuracy.

        PRI = time between consecutive pulse TOAs
        σ_PRI = √2 × σ_TOA (two TOA measurements)

        Args:
            snr_db: Detection SNR in dB

        Returns:
            PRI accuracy in nanoseconds (RMS)
        """
        sigma_toa = self.calculate_toa_accuracy(snr_db, pulse_width_us=1.0)
        return np.sqrt(2) * sigma_toa

    def analyze(self, snr_db: float,
                pulse_width_us: float = 1.0) -> MeasurementResult:
        """
        Perform complete measurement accuracy analysis.

        Args:
            snr_db: Detection SNR in dB (guaranteed by threshold)
            pulse_width_us: Pulse width in microseconds

        Returns:
            MeasurementResult with all accuracy metrics
        """
        # Frequency accuracy (DLFD)
        freq_acc, freq_res = self.calculate_frequency_accuracy_dlfd(snr_db)

        # TOA accuracy
        toa_acc = self.calculate_toa_accuracy(snr_db, pulse_width_us)

        # Pulse width accuracy
        pw_acc_ns, pw_acc_pct = self.calculate_pulse_width_accuracy(
            snr_db, pulse_width_us
        )

        # PRI accuracy
        pri_acc = self.calculate_pri_accuracy(snr_db)

        return MeasurementResult(
            snr_db=snr_db,
            frequency_accuracy_mhz=freq_acc,
            frequency_resolution_mhz=freq_res,
            toa_accuracy_ns=toa_acc,
            pulse_width_accuracy_ns=pw_acc_ns,
            pulse_width_accuracy_percent=pw_acc_pct,
            pri_accuracy_ns=pri_acc,
            config=self.config
        )

    def analyze_vs_snr(self, snr_range_db: np.ndarray,
                       pulse_width_us: float = 1.0) -> Dict[str, np.ndarray]:
        """
        Analyze measurement accuracy across a range of SNR values.

        Args:
            snr_range_db: Array of SNR values in dB
            pulse_width_us: Pulse width in microseconds

        Returns:
            Dict with arrays of accuracy values for each metric
        """
        results = {
            'snr_db': snr_range_db,
            'frequency_accuracy_mhz': np.zeros_like(snr_range_db),
            'toa_accuracy_ns': np.zeros_like(snr_range_db),
            'pulse_width_accuracy_ns': np.zeros_like(snr_range_db),
            'pri_accuracy_ns': np.zeros_like(snr_range_db),
        }

        for i, snr in enumerate(snr_range_db):
            result = self.analyze(snr, pulse_width_us)
            results['frequency_accuracy_mhz'][i] = result.frequency_accuracy_mhz
            results['toa_accuracy_ns'][i] = result.toa_accuracy_ns
            results['pulse_width_accuracy_ns'][i] = result.pulse_width_accuracy_ns
            results['pri_accuracy_ns'][i] = result.pri_accuracy_ns

        return results


def load_from_system_config() -> MeasurementConfig:
    """Load measurement config from shared system_config and ESM config."""
    from pathlib import Path
    import yaml

    # Load system config for ADC (Task 1.0: Updated to use centralized config/)
    sys_config_path = Path(__file__).parent.parent / "config" / "system_config.yaml"
    with open(sys_config_path, 'r') as f:
        sys_data = yaml.safe_load(f)

    # Load ESM config for channel bandwidth
    esm_config_path = Path(__file__).parent / "config" / "system_config.yaml"
    try:
        with open(esm_config_path, 'r') as f:
            esm_data = yaml.safe_load(f)
        receiver_data = esm_data.get('receiver', {})
        # Handle scientific notation strings (YAML parses "20.0e6" as string)
        bw_raw = receiver_data.get('bandwidth_hz', 20e6)
        channel_bw_mhz = float(bw_raw) / 1e6
    except FileNotFoundError:
        channel_bw_mhz = 20.0

    adc_data = sys_data.get('adc', {})

    return MeasurementConfig(
        adc_sample_rate_gsps=adc_data.get('sample_rate_gsps', 40.0),
        channel_bandwidth_mhz=channel_bw_mhz,
        dlfd_delay_ns=50.0,  # 50 ns delay line
    )


# Convenience function
def analyze_measurement_accuracy(snr_db: float,
                                  pulse_width_us: float = 1.0) -> MeasurementResult:
    """
    Quick analysis of measurement accuracy at given SNR.

    Args:
        snr_db: Detection SNR in dB (guaranteed by threshold)
        pulse_width_us: Pulse width in microseconds

    Returns:
        MeasurementResult
    """
    config = load_from_system_config()
    analyzer = MeasurementAccuracyAnalyzer(config)
    return analyzer.analyze(snr_db, pulse_width_us)
