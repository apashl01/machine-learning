"""
Pulse Parameter Measurement Accuracy Analysis

Models the accuracy of ESM pulse parameter measurements including:
- Frequency measurement (DLFM - Delay Line Frequency Measurement)
- Time of Arrival (TOA)
- Pulse Width (PW)
- Pulse Repetition Interval (PRI)

The analysis accounts for the digital signal processing chain:
ADC (40 GSPS) → DDC → Narrowband Channelizer (20 MHz)

Key concept: Process Gain
The channelizer bandwidth (20 MHz) is much narrower than the ADC bandwidth,
providing noise rejection (NOT coherent integration gain). This improves
effective SNR at the measurement point.

Process Gain = 10 * log10(BW_adc / BW_channel)
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

    # Instantaneous bandwidth (how much spectrum observed at once)
    instantaneous_bandwidth_ghz: float = 1.0

    # Channelizer parameters (narrowband analysis channel)
    channel_bandwidth_mhz: float = 20.0

    # DLFM parameters
    dlfm_delay_ns: float = 50.0  # Delay line length (nanoseconds)
    dlfm_phase_quantization_bits: int = 12

    # Timing parameters
    timing_resolution_ns: float = 0.025  # 1/40 GHz = 25 ps

    @property
    def instantaneous_bandwidth_hz(self) -> float:
        """Instantaneous bandwidth being processed."""
        return self.instantaneous_bandwidth_ghz * 1e9

    @property
    def channel_bandwidth_hz(self) -> float:
        return self.channel_bandwidth_mhz * 1e6

    @property
    def process_gain_db(self) -> float:
        """
        Noise rejection gain from channelizer.

        This is NOT coherent integration - it's bandwidth reduction
        that rejects out-of-band noise within the IBW.

        Process gain = 10 * log10(IBW / Channel_BW)
        For 1 GHz IBW and 20 MHz channel: 10*log10(50) ≈ 17 dB
        """
        return 10 * np.log10(self.instantaneous_bandwidth_hz / self.channel_bandwidth_hz)

    @property
    def dlfm_delay_s(self) -> float:
        return self.dlfm_delay_ns * 1e-9


@dataclass
class MeasurementResult:
    """Results of measurement accuracy analysis."""
    # Input conditions
    snr_input_db: float
    snr_effective_db: float  # After process gain

    # Frequency measurement
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
        print(f"Input SNR: {self.snr_input_db:.1f} dB")
        print(f"Effective SNR (after process gain): {self.snr_effective_db:.1f} dB")
        print(f"Process Gain: {self.config.process_gain_db:.1f} dB")
        print(f"\nFrequency (DLFM):")
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

    Models measurement errors as functions of SNR, accounting for:
    - DLFM physics for frequency measurement
    - Rise time / bandwidth limitations for TOA
    - Propagation of TOA errors to pulse width
    """

    def __init__(self, config: Optional[MeasurementConfig] = None):
        self.config = config or MeasurementConfig()

    def calculate_effective_snr(self, snr_input_db: float) -> float:
        """
        Calculate effective SNR at measurement point.

        The channelizer rejects noise outside its bandwidth, improving
        the effective SNR for measurements made in the narrow channel.

        Args:
            snr_input_db: Input SNR at ADC (wideband)

        Returns:
            Effective SNR in dB after channelizer filtering
        """
        # Process gain from bandwidth reduction
        # Note: This assumes signal is within the channel bandwidth
        process_gain = self.config.process_gain_db

        return snr_input_db + process_gain

    def calculate_frequency_accuracy_dlfm(self, snr_db: float) -> Tuple[float, float]:
        """
        Calculate frequency measurement accuracy using DLFM model.

        Delay Line Frequency Measurement works by measuring phase shift
        across a known delay. Frequency accuracy is:

        σ_f = 1 / (2π · τ_delay · SNR_linear)

        Longer delays improve accuracy but risk ambiguity for wideband signals.

        Args:
            snr_db: Effective SNR in dB

        Returns:
            Tuple of (accuracy_mhz, resolution_mhz)
        """
        snr_linear = 10 ** (snr_db / 10)
        tau = self.config.dlfm_delay_s

        # DLFM accuracy (Cramer-Rao bound)
        # σ_f = 1 / (2π · τ · √(2 · SNR))
        sigma_f_hz = 1 / (2 * np.pi * tau * np.sqrt(2 * snr_linear))

        # Also consider phase quantization limit
        # Phase resolution = 2π / 2^N_bits
        # Frequency resolution = phase_resolution / (2π · τ)
        phase_resolution = 2 * np.pi / (2 ** self.config.dlfm_phase_quantization_bits)
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
        σ_TOA = rise_time / (2 · √SNR)

        where rise_time ≈ 0.35 / BW for a typical filter.

        Args:
            snr_db: Effective SNR in dB
            pulse_width_us: Pulse width in microseconds (affects short pulses)

        Returns:
            TOA accuracy in nanoseconds (RMS)
        """
        snr_linear = 10 ** (snr_db / 10)

        # Rise time from channel bandwidth
        # Using 10-90% rise time ≈ 0.35 / BW
        rise_time_s = 0.35 / self.config.channel_bandwidth_hz
        rise_time_ns = rise_time_s * 1e9

        # Timing accuracy from SNR
        # σ_t = rise_time / (2 · √SNR)
        sigma_toa_ns = rise_time_ns / (2 * np.sqrt(snr_linear))

        # For very short pulses, accuracy may be limited by pulse width itself
        pulse_width_ns = pulse_width_us * 1000
        if pulse_width_ns < rise_time_ns * 2:
            # Short pulse - use pulse width dependent model
            sigma_toa_ns = max(sigma_toa_ns, pulse_width_ns / (4 * np.sqrt(snr_linear)))

        # Also limited by timing resolution
        timing_floor_ns = self.config.timing_resolution_ns

        return np.sqrt(sigma_toa_ns**2 + timing_floor_ns**2)

    def calculate_pulse_width_accuracy(self, snr_db: float,
                                        pulse_width_us: float = 1.0) -> Tuple[float, float]:
        """
        Calculate pulse width measurement accuracy.

        Pulse width is measured as the difference between leading edge TOA
        and trailing edge TOA. The variance adds:

        σ_PW = √2 · σ_TOA

        Args:
            snr_db: Effective SNR in dB
            pulse_width_us: Actual pulse width in microseconds

        Returns:
            Tuple of (accuracy_ns, accuracy_percent)
        """
        # TOA accuracy for leading and trailing edges
        sigma_toa = self.calculate_toa_accuracy(snr_db, pulse_width_us)

        # Pulse width is difference of two TOA measurements
        # Assuming independent measurements: σ_PW = √(σ_leading² + σ_trailing²) = √2 · σ_TOA
        sigma_pw_ns = np.sqrt(2) * sigma_toa

        # Relative accuracy
        pulse_width_ns = pulse_width_us * 1000
        sigma_pw_percent = (sigma_pw_ns / pulse_width_ns) * 100

        return sigma_pw_ns, sigma_pw_percent

    def calculate_pri_accuracy(self, snr_db: float) -> float:
        """
        Calculate PRI (Pulse Repetition Interval) accuracy.

        PRI is measured as time between consecutive pulse TOAs.
        Similar to pulse width, variance adds for two TOA measurements.

        Args:
            snr_db: Effective SNR in dB

        Returns:
            PRI accuracy in nanoseconds (RMS)
        """
        # Use a typical pulse width for TOA calculation
        sigma_toa = self.calculate_toa_accuracy(snr_db, pulse_width_us=1.0)

        # PRI variance from two TOA measurements
        sigma_pri_ns = np.sqrt(2) * sigma_toa

        return sigma_pri_ns

    def analyze(self, snr_input_db: float,
                pulse_width_us: float = 1.0) -> MeasurementResult:
        """
        Perform complete measurement accuracy analysis.

        Args:
            snr_input_db: Input SNR at ADC in dB
            pulse_width_us: Pulse width in microseconds

        Returns:
            MeasurementResult with all accuracy metrics
        """
        # Calculate effective SNR after channelizer
        snr_effective = self.calculate_effective_snr(snr_input_db)

        # Frequency accuracy (DLFM)
        freq_acc, freq_res = self.calculate_frequency_accuracy_dlfm(snr_effective)

        # TOA accuracy
        toa_acc = self.calculate_toa_accuracy(snr_effective, pulse_width_us)

        # Pulse width accuracy
        pw_acc_ns, pw_acc_pct = self.calculate_pulse_width_accuracy(
            snr_effective, pulse_width_us
        )

        # PRI accuracy
        pri_acc = self.calculate_pri_accuracy(snr_effective)

        return MeasurementResult(
            snr_input_db=snr_input_db,
            snr_effective_db=snr_effective,
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
            snr_range_db: Array of input SNR values in dB
            pulse_width_us: Pulse width in microseconds

        Returns:
            Dict with arrays of accuracy values for each metric
        """
        results = {
            'snr_input_db': snr_range_db,
            'snr_effective_db': np.zeros_like(snr_range_db),
            'frequency_accuracy_mhz': np.zeros_like(snr_range_db),
            'toa_accuracy_ns': np.zeros_like(snr_range_db),
            'pulse_width_accuracy_ns': np.zeros_like(snr_range_db),
            'pri_accuracy_ns': np.zeros_like(snr_range_db),
        }

        for i, snr in enumerate(snr_range_db):
            result = self.analyze(snr, pulse_width_us)
            results['snr_effective_db'][i] = result.snr_effective_db
            results['frequency_accuracy_mhz'][i] = result.frequency_accuracy_mhz
            results['toa_accuracy_ns'][i] = result.toa_accuracy_ns
            results['pulse_width_accuracy_ns'][i] = result.pulse_width_accuracy_ns
            results['pri_accuracy_ns'][i] = result.pri_accuracy_ns

        return results


def load_from_system_config() -> MeasurementConfig:
    """Load measurement config from shared system_config and ESM config."""
    from pathlib import Path
    import yaml

    # Load system config for ADC
    sys_config_path = Path(__file__).parent.parent / "system_config" / "system_config.yaml"
    with open(sys_config_path, 'r') as f:
        sys_data = yaml.safe_load(f)

    # Load ESM config for IBW
    esm_config_path = Path(__file__).parent / "config" / "system_config.yaml"
    try:
        with open(esm_config_path, 'r') as f:
            esm_data = yaml.safe_load(f)
        receiver_data = esm_data.get('receiver', {})
        ibw_ghz = float(receiver_data.get('instantaneous_bandwidth_ghz', 1.0))
        # Handle scientific notation strings (YAML parses "20.0e6" as string)
        bw_raw = receiver_data.get('bandwidth_hz', 20e6)
        channel_bw_mhz = float(bw_raw) / 1e6
    except FileNotFoundError:
        ibw_ghz = 1.0
        channel_bw_mhz = 20.0

    adc_data = sys_data.get('adc', {})

    return MeasurementConfig(
        adc_sample_rate_gsps=adc_data.get('sample_rate_gsps', 40.0),
        instantaneous_bandwidth_ghz=ibw_ghz,
        channel_bandwidth_mhz=channel_bw_mhz,
        dlfm_delay_ns=50.0,  # Typical DLFM delay
    )


# Convenience function
def analyze_measurement_accuracy(snr_db: float,
                                  pulse_width_us: float = 1.0) -> MeasurementResult:
    """
    Quick analysis of measurement accuracy at given SNR.

    Args:
        snr_db: Input SNR in dB
        pulse_width_us: Pulse width in microseconds

    Returns:
        MeasurementResult
    """
    config = load_from_system_config()
    analyzer = MeasurementAccuracyAnalyzer(config)
    return analyzer.analyze(snr_db, pulse_width_us)
