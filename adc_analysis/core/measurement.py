"""
ADC Measurement Accuracy Analyzer

Analyzes measurement accuracy for pulse descriptor words (PDW)
based on ADC characteristics and processing methods.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import math
import numpy as np

from ..config import ADCConfig


# =============================================================================
# PHYSICAL CONSTANTS
# =============================================================================

SPEED_OF_LIGHT = 299792458  # m/s


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SNRResult:
    """SNR calculation results."""
    snr_ideal_db: float
    snr_effective_db: float
    snr_linear: float
    signal_backoff_db: float


@dataclass
class AmplitudeAccuracy:
    """Amplitude measurement accuracy results."""
    resolution_db: float       # 1 LSB resolution in dB
    accuracy_rms_db: float     # RMS accuracy in dB
    dynamic_range_db: float    # Full dynamic range
    sfdr_db: float             # Spurious-free dynamic range


@dataclass
class TimingAccuracy:
    """Timing measurement accuracy results."""
    time_resolution_ns: float        # Sample period
    toa_accuracy_ns: float           # TOA accuracy (RMS)
    toa_snr_limited_ns: float        # SNR-limited TOA
    toa_jitter_limited_ns: float     # Jitter-limited TOA
    pri_accuracy_ns: float           # PRI accuracy (RMS)
    pw_accuracies_ns: List[float]    # PW accuracy for each pulse width
    pulse_widths_us: List[float]     # Corresponding pulse widths


@dataclass
class FrequencyAccuracy:
    """Frequency measurement accuracy results."""
    # FFT method
    fft_resolutions_hz: List[float]
    fft_accuracies_hz: Dict[int, Dict[float, float]]  # fft_len -> {pw_us: accuracy}
    fft_times_us: List[float]

    # IFM method
    ifm_accuracy_hz: float
    ifm_range_mhz: float
    ifm_latency_ns: float


@dataclass
class PhaseAccuracy:
    """Phase and AOA measurement accuracy results."""
    phase_accuracy_deg: float
    phase_quantization_deg: float
    phase_thermal_deg: float
    phase_jitter_deg: float
    aoa_accuracy_deg: float
    baseline_m: float
    wavelength_m: float


@dataclass
class MeasurementResult:
    """Complete measurement accuracy results."""
    snr: SNRResult
    amplitude: AmplitudeAccuracy
    timing: TimingAccuracy
    frequency: FrequencyAccuracy
    phase: PhaseAccuracy


# =============================================================================
# ANALYZER CLASS
# =============================================================================

class MeasurementAnalyzer:
    """
    Analyzer for ADC measurement accuracy.

    Calculates accuracy for amplitude, timing, frequency, and phase
    measurements based on ADC specifications.
    """

    def __init__(self, config: ADCConfig):
        """
        Initialize analyzer with configuration.

        Args:
            config: ADC configuration object.
        """
        self.config = config
        self.adc = config.adc
        self.analysis = config.analysis

    def calculate_snr(self, input_power_dbm: Optional[float] = None) -> SNRResult:
        """
        Calculate SNR from ENOB and input level.

        Args:
            input_power_dbm: Input signal power. Uses config default if None.

        Returns:
            SNRResult with SNR calculations.
        """
        if input_power_dbm is None:
            input_power_dbm = self.analysis.input_signal_dbm

        # Ideal SNR from ENOB
        snr_ideal_db = 6.02 * self.adc.enob + 1.76

        # Signal backoff from full-scale
        signal_backoff_db = self.adc.fullscale_dbm - input_power_dbm

        # Effective SNR (accounts for input level)
        if signal_backoff_db > 0:
            snr_effective_db = snr_ideal_db - signal_backoff_db
        else:
            snr_effective_db = 0  # Clipping

        snr_effective_db = max(0, snr_effective_db)
        snr_linear = 10 ** (snr_effective_db / 10)

        return SNRResult(
            snr_ideal_db=snr_ideal_db,
            snr_effective_db=snr_effective_db,
            snr_linear=snr_linear,
            signal_backoff_db=signal_backoff_db
        )

    def analyze_amplitude(self, snr: SNRResult) -> AmplitudeAccuracy:
        """
        Analyze amplitude measurement accuracy.

        Args:
            snr: SNR calculation results.

        Returns:
            AmplitudeAccuracy with amplitude accuracy metrics.
        """
        # Full-scale voltage (assuming 50 ohm)
        fullscale_w = 10 ** (self.adc.fullscale_dbm / 10) / 1000
        fullscale_v = math.sqrt(fullscale_w * self.analysis.impedance_ohm)

        # LSB voltage
        lsb_voltage = fullscale_v / (2 ** self.adc.bits)

        # Quantization noise RMS
        quantization_noise_rms = lsb_voltage / math.sqrt(12)

        # Amplitude resolution (1 LSB)
        amp_resolution_db = 20 * math.log10(1 + 1 / (2 ** self.adc.enob))

        # Amplitude accuracy (RMS error from quantization)
        amp_accuracy_db = 20 * math.log10(quantization_noise_rms / fullscale_v)

        return AmplitudeAccuracy(
            resolution_db=amp_resolution_db,
            accuracy_rms_db=amp_accuracy_db,
            dynamic_range_db=snr.snr_ideal_db,
            sfdr_db=self.adc.sfdr_dbc
        )

    def analyze_timing(self, snr: SNRResult) -> TimingAccuracy:
        """
        Analyze timing measurement accuracy.

        Args:
            snr: SNR calculation results.

        Returns:
            TimingAccuracy with timing accuracy metrics.
        """
        # Sample period
        sample_period_ns = 1e9 / self.analysis.effective_fs_hz
        time_resolution_ns = sample_period_ns

        # Signal frequency
        signal_freq_hz = self.analysis.signal_freq_ghz * 1e9

        # TOA accuracy (SNR-limited)
        # sigma_TOA = 1/(2*pi*f * sqrt(SNR))
        toa_snr_limited_ns = 1e9 / (2 * math.pi * signal_freq_hz * math.sqrt(snr.snr_linear))

        # Jitter-limited TOA
        toa_jitter_limited_ns = self.adc.aperture_jitter_ps / 1000  # ps to ns

        # Total TOA accuracy (RSS)
        toa_accuracy_ns = math.sqrt(toa_snr_limited_ns**2 + toa_jitter_limited_ns**2)

        # PRI accuracy (essentially TOA accuracy for each pulse)
        pri_accuracy_ns = toa_accuracy_ns

        # Pulse width accuracy for each pulse width
        pulse_widths_us = self.analysis.pulse_widths_us
        pw_accuracies_ns = []

        for pw_us in pulse_widths_us:
            pw_ns = pw_us * 1000
            n_samples = pw_ns / sample_period_ns

            if n_samples >= 10:
                # PW accuracy improves with more samples
                pw_acc = max(2 * sample_period_ns,
                             sample_period_ns / math.sqrt(snr.snr_linear))
            else:
                # Limited by sample rate
                pw_acc = 2 * sample_period_ns

            pw_accuracies_ns.append(pw_acc)

        return TimingAccuracy(
            time_resolution_ns=time_resolution_ns,
            toa_accuracy_ns=toa_accuracy_ns,
            toa_snr_limited_ns=toa_snr_limited_ns,
            toa_jitter_limited_ns=toa_jitter_limited_ns,
            pri_accuracy_ns=pri_accuracy_ns,
            pw_accuracies_ns=pw_accuracies_ns,
            pulse_widths_us=pulse_widths_us
        )

    def analyze_frequency(self, snr: SNRResult) -> FrequencyAccuracy:
        """
        Analyze frequency measurement accuracy.

        Args:
            snr: SNR calculation results.

        Returns:
            FrequencyAccuracy with frequency accuracy metrics.
        """
        fs_hz = self.analysis.effective_fs_hz
        fft_lengths = self.analysis.fft_lengths
        pulse_widths_us = self.analysis.pulse_widths_us

        # FFT method
        fft_resolutions_hz = []
        fft_times_us = []
        fft_accuracies = {}

        for n_fft in fft_lengths:
            # Frequency resolution
            freq_res = fs_hz / n_fft
            fft_resolutions_hz.append(freq_res)

            # Processing time required
            fft_time = n_fft / fs_hz * 1e6
            fft_times_us.append(fft_time)

            # Accuracy for each pulse width
            fft_accuracies[n_fft] = {}
            for pw_us in pulse_widths_us:
                if pw_us >= fft_time:
                    # Pulse long enough - accuracy improves with SNR
                    acc = freq_res / (2 * math.sqrt(snr.snr_linear))
                    fft_accuracies[n_fft][pw_us] = acc
                else:
                    # Pulse too short
                    fft_accuracies[n_fft][pw_us] = float('nan')

        # IFM method
        ifm_delay_s = self.analysis.ifm_delay_ns * 1e-9
        signal_freq_hz = self.analysis.signal_freq_ghz * 1e9

        # Unambiguous frequency range
        ifm_range_mhz = 1 / (2 * ifm_delay_s) / 1e6

        # Frequency accuracy (SNR-limited)
        freq_ifm_snr_hz = 1 / (2 * math.pi * ifm_delay_s * math.sqrt(snr.snr_linear))

        # Jitter contribution
        clock_jitter_s = self.adc.clock_jitter_fs * 1e-15
        phase_noise_rad = 2 * math.pi * signal_freq_hz * clock_jitter_s
        freq_ifm_jitter_hz = phase_noise_rad * signal_freq_hz / (2 * math.pi)

        # Total IFM accuracy
        ifm_accuracy_hz = math.sqrt(freq_ifm_snr_hz**2 + freq_ifm_jitter_hz**2)

        # IFM latency
        ifm_latency_ns = self.analysis.ifm_delay_ns * 2

        return FrequencyAccuracy(
            fft_resolutions_hz=fft_resolutions_hz,
            fft_accuracies_hz=fft_accuracies,
            fft_times_us=fft_times_us,
            ifm_accuracy_hz=ifm_accuracy_hz,
            ifm_range_mhz=ifm_range_mhz,
            ifm_latency_ns=ifm_latency_ns
        )

    def analyze_phase(self, snr: SNRResult) -> PhaseAccuracy:
        """
        Analyze phase and AOA measurement accuracy.

        Args:
            snr: SNR calculation results.

        Returns:
            PhaseAccuracy with phase and AOA accuracy metrics.
        """
        signal_freq_hz = self.analysis.signal_freq_ghz * 1e9

        # Phase noise from multiple sources
        phase_quantization_rad = 1 / (2 ** self.adc.enob * math.sqrt(6))
        phase_thermal_rad = 1 / math.sqrt(2 * snr.snr_linear)

        aperture_jitter_s = self.adc.aperture_jitter_ps * 1e-12
        phase_jitter_rad = 2 * math.pi * signal_freq_hz * aperture_jitter_s

        # Total phase accuracy (RSS)
        phase_accuracy_rad = math.sqrt(
            phase_quantization_rad**2 +
            phase_thermal_rad**2 +
            phase_jitter_rad**2
        )

        # Convert to degrees
        phase_accuracy_deg = math.degrees(phase_accuracy_rad)
        phase_quantization_deg = math.degrees(phase_quantization_rad)
        phase_thermal_deg = math.degrees(phase_thermal_rad)
        phase_jitter_deg = math.degrees(phase_jitter_rad)

        # Wavelength and baseline
        wavelength_m = SPEED_OF_LIGHT / signal_freq_hz
        baseline_m = self.analysis.baseline_wavelengths * wavelength_m

        # AOA accuracy: delta_theta = lambda/(2*pi*d) * delta_phi
        aoa_accuracy_rad = (wavelength_m / (2 * math.pi * baseline_m)) * phase_accuracy_rad
        aoa_accuracy_deg = math.degrees(aoa_accuracy_rad)

        return PhaseAccuracy(
            phase_accuracy_deg=phase_accuracy_deg,
            phase_quantization_deg=phase_quantization_deg,
            phase_thermal_deg=phase_thermal_deg,
            phase_jitter_deg=phase_jitter_deg,
            aoa_accuracy_deg=aoa_accuracy_deg,
            baseline_m=baseline_m,
            wavelength_m=wavelength_m
        )

    def analyze(self, input_power_dbm: Optional[float] = None) -> MeasurementResult:
        """
        Perform complete measurement accuracy analysis.

        Args:
            input_power_dbm: Input signal power. Uses config default if None.

        Returns:
            MeasurementResult with all accuracy metrics.
        """
        snr = self.calculate_snr(input_power_dbm)
        amplitude = self.analyze_amplitude(snr)
        timing = self.analyze_timing(snr)
        frequency = self.analyze_frequency(snr)
        phase = self.analyze_phase(snr)

        return MeasurementResult(
            snr=snr,
            amplitude=amplitude,
            timing=timing,
            frequency=frequency,
            phase=phase
        )

    def print_summary(self, result: MeasurementResult) -> str:
        """
        Generate formatted summary of measurement accuracy.

        Args:
            result: MeasurementResult to summarize.

        Returns:
            Formatted string summary.
        """
        lines = [
            "=" * 60,
            "ADC MEASUREMENT ACCURACY ANALYSIS",
            "=" * 60,
            "",
            "SNR ANALYSIS:",
            f"  Ideal SNR (from ENOB): {result.snr.snr_ideal_db:.1f} dB",
            f"  Full-Scale Backoff: {result.snr.signal_backoff_db:.1f} dB",
            f"  Effective SNR: {result.snr.snr_effective_db:.1f} dB",
            "",
            "AMPLITUDE MEASUREMENTS:",
            f"  Resolution: {result.amplitude.resolution_db:.3f} dB (1 LSB)",
            f"  Accuracy (RMS): {result.amplitude.accuracy_rms_db:.2f} dB",
            f"  Dynamic Range: {result.amplitude.dynamic_range_db:.1f} dB",
            f"  SFDR: {result.amplitude.sfdr_db:.1f} dBc",
            "",
            "TIMING MEASUREMENTS:",
            f"  Time Resolution: {result.timing.time_resolution_ns:.2f} ns",
            f"  TOA Accuracy: {result.timing.toa_accuracy_ns:.3f} ns (RMS)",
            f"    - SNR-limited: {result.timing.toa_snr_limited_ns:.3f} ns",
            f"    - Jitter-limited: {result.timing.toa_jitter_limited_ns:.3f} ns",
            f"  PRI Accuracy: {result.timing.pri_accuracy_ns:.3f} ns (RMS)",
            "  Pulse Width Accuracy:"
        ]

        for i, pw_us in enumerate(result.timing.pulse_widths_us):
            lines.append(f"    - PW = {pw_us:.1f} us: {result.timing.pw_accuracies_ns[i]:.2f} ns")

        lines.extend([
            "",
            "FREQUENCY MEASUREMENTS:",
            f"  IFM Accuracy: {result.frequency.ifm_accuracy_hz:.1f} Hz",
            f"  IFM Range: +/-{result.frequency.ifm_range_mhz:.1f} MHz",
            f"  IFM Latency: ~{result.frequency.ifm_latency_ns:.1f} ns",
            "",
            "PHASE MEASUREMENTS:",
            f"  Phase Accuracy: {result.phase.phase_accuracy_deg:.3f} deg (RMS)",
            f"    - Quantization: {result.phase.phase_quantization_deg:.3f} deg",
            f"    - Thermal: {result.phase.phase_thermal_deg:.3f} deg",
            f"    - Jitter: {result.phase.phase_jitter_deg:.3f} deg",
            f"  AOA Accuracy: {result.phase.aoa_accuracy_deg:.2f} deg",
            f"    (Baseline: {result.phase.baseline_m:.3f} m)",
            "=" * 60
        ])

        return "\n".join(lines)
