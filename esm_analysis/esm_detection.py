"""
ESM (Electronic Support Measures) Detection Analysis

This module implements passive receiver detection range calculations
for ESM systems detecting radar emitters. Uses one-way propagation (R^2)
unlike radar detection which uses two-way propagation (R^4).

Ported from MATLAB radar_range_analysis.m
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
import warnings


# Physical Constants
C = 3e8                     # Speed of light (m/s)
KB = 1.380649e-23           # Boltzmann constant (J/K)
T0 = 290                    # Reference temperature (K)


@dataclass
class RadarParameters:
    """Parameters describing a radar emitter to be detected."""

    eirp_dBW: float = 50.0          # Effective Isotropic Radiated Power (dBW)
    freq_GHz: float = 10.0          # Operating frequency (GHz)
    antenna_gain_dB: float = 35.0   # Transmit antenna gain (dB)
    bandwidth_MHz: float = 1.0      # Radar bandwidth (MHz)
    pulse_width_us: float = 1.0     # Pulse width (microseconds)
    pri_us: float = 1000.0          # Pulse repetition interval (microseconds)
    scan_period_s: float = 10.0     # Antenna scan period (seconds)
    beam_dwell_ms: float = 50.0     # Beam dwell time on target (ms)

    @property
    def wavelength_m(self) -> float:
        """Calculate wavelength in meters."""
        return C / (self.freq_GHz * 1e9)

    @property
    def eirp_W(self) -> float:
        """Convert EIRP to Watts."""
        return 10 ** (self.eirp_dBW / 10)

    @property
    def prf_Hz(self) -> float:
        """Pulse repetition frequency."""
        return 1e6 / self.pri_us

    @property
    def duty_cycle(self) -> float:
        """Radar duty cycle."""
        return self.pulse_width_us / self.pri_us


@dataclass
class ReceiverParameters:
    """Parameters describing the ESM receiver."""

    antenna_gain_dB: float = 0.0    # Receiver antenna gain (dB)
    noise_figure_dB: float = 5.0    # System noise figure (dB)
    bandwidth_MHz: float = 20.0     # Analysis/channelizer bandwidth (MHz)
    snr_required_dB: float = 13.0   # Required SNR for detection (dB)
    system_loss_dB: float = 6.0     # Total system losses (dB)

    # Scan parameters
    freq_min_GHz: float = 2.0       # Minimum scan frequency (GHz)
    freq_max_GHz: float = 18.0      # Maximum scan frequency (GHz)
    n_channels: int = 1             # Number of parallel channels

    @property
    def antenna_gain_linear(self) -> float:
        return 10 ** (self.antenna_gain_dB / 10)

    @property
    def noise_figure_linear(self) -> float:
        return 10 ** (self.noise_figure_dB / 10)

    @property
    def bandwidth_Hz(self) -> float:
        return self.bandwidth_MHz * 1e6

    @property
    def snr_required_linear(self) -> float:
        return 10 ** (self.snr_required_dB / 10)

    @property
    def system_loss_linear(self) -> float:
        return 10 ** (self.system_loss_dB / 10)

    @property
    def noise_floor_dBm(self) -> float:
        """Calculate receiver noise floor in dBm."""
        noise_power_W = KB * T0 * self.bandwidth_Hz * self.noise_figure_linear
        return 10 * np.log10(noise_power_W) + 30

    @property
    def sensitivity_dBm(self) -> float:
        """Calculate receiver sensitivity (MDS) in dBm."""
        return self.noise_floor_dBm + self.snr_required_dB

    @property
    def scan_bandwidth_GHz(self) -> float:
        """Total frequency range to scan."""
        return self.freq_max_GHz - self.freq_min_GHz


@dataclass
class DetectionResult:
    """Results of ESM detection analysis."""

    detection_range_km: float
    received_power_dBm: float
    snr_dB: float
    detection_probability: float
    time_to_intercept_s: float
    details: Dict = field(default_factory=dict)


class ESMDetector:
    """
    ESM Detection Analysis Engine

    Calculates passive receiver detection ranges and probabilities
    for detecting radar emitters using one-way propagation (R^2).
    """

    def __init__(self, receiver: ReceiverParameters):
        """
        Initialize ESM detector with receiver parameters.

        Args:
            receiver: ReceiverParameters object defining the ESM receiver
        """
        self.receiver = receiver

    def calculate_detection_range(self, radar: RadarParameters) -> float:
        """
        Calculate maximum detection range for a given radar emitter.

        Uses one-way link budget: R = sqrt[(Pt * Gt * Gr * lambda^2) /
                                          ((4*pi)^2 * kTB * NF * SNR * L)]

        Args:
            radar: RadarParameters object describing the emitter

        Returns:
            Maximum detection range in km
        """
        numerator = (radar.eirp_W *
                     self.receiver.antenna_gain_linear *
                     radar.wavelength_m ** 2)

        denominator = ((4 * np.pi) ** 2 *
                       KB * T0 *
                       self.receiver.bandwidth_Hz *
                       self.receiver.noise_figure_linear *
                       self.receiver.snr_required_linear *
                       self.receiver.system_loss_linear)

        range_m = np.sqrt(numerator / denominator)
        return range_m / 1000  # Convert to km

    def calculate_received_power(self, radar: RadarParameters,
                                  range_km: float) -> float:
        """
        Calculate received power at a given range.

        Args:
            radar: RadarParameters object describing the emitter
            range_km: Range to emitter in km

        Returns:
            Received power in dBm
        """
        range_m = range_km * 1000

        # Free space path loss
        fspl_linear = (4 * np.pi * range_m / radar.wavelength_m) ** 2

        # Received power
        pr_W = (radar.eirp_W * self.receiver.antenna_gain_linear /
                (fspl_linear * self.receiver.system_loss_linear))

        return 10 * np.log10(pr_W) + 30  # Convert to dBm

    def calculate_snr(self, radar: RadarParameters, range_km: float) -> float:
        """
        Calculate SNR at a given range.

        Args:
            radar: RadarParameters object describing the emitter
            range_km: Range to emitter in km

        Returns:
            SNR in dB
        """
        received_power_dBm = self.calculate_received_power(radar, range_km)
        return received_power_dBm - self.receiver.noise_floor_dBm

    def calculate_detection_probability(self, radar: RadarParameters,
                                         range_km: float,
                                         n_pulses: int = 1) -> float:
        """
        Calculate probability of detection using Albersheim's approximation.

        Args:
            radar: RadarParameters object describing the emitter
            range_km: Range to emitter in km
            n_pulses: Number of pulses integrated

        Returns:
            Probability of detection (0-1)
        """
        snr_dB = self.calculate_snr(radar, range_km)
        snr_linear = 10 ** (snr_dB / 10)

        # Integration gain (non-coherent)
        integration_gain = np.sqrt(n_pulses)
        effective_snr = snr_linear * integration_gain

        # Albersheim's approximation for Pd
        # Pd = 0.5 * erfc(sqrt(-ln(Pfa)) - sqrt(SNR + 0.5))
        # Assuming Pfa = 1e-6
        pfa = 1e-6

        if effective_snr <= 0:
            return 0.0

        a = np.sqrt(-2 * np.log(pfa))
        b = np.sqrt(2 * effective_snr)

        from scipy.special import erfc
        pd = 0.5 * erfc((a - b) / np.sqrt(2))

        return min(max(pd, 0.0), 1.0)

    def analyze_detection(self, radar: RadarParameters,
                          range_km: Optional[float] = None,
                          n_pulses: int = 1) -> DetectionResult:
        """
        Perform complete detection analysis.

        Args:
            radar: RadarParameters object describing the emitter
            range_km: Range to analyze (if None, uses max detection range)
            n_pulses: Number of pulses integrated

        Returns:
            DetectionResult object with analysis results
        """
        max_range_km = self.calculate_detection_range(radar)

        if range_km is None:
            range_km = max_range_km

        received_power_dBm = self.calculate_received_power(radar, range_km)
        snr_dB = self.calculate_snr(radar, range_km)
        pd = self.calculate_detection_probability(radar, range_km, n_pulses)

        # Calculate time to intercept (depends on scan strategy - placeholder)
        time_to_intercept = 0.0  # Will be calculated by dwell scheduler

        return DetectionResult(
            detection_range_km=max_range_km,
            received_power_dBm=received_power_dBm,
            snr_dB=snr_dB,
            detection_probability=pd,
            time_to_intercept_s=time_to_intercept,
            details={
                'range_km': range_km,
                'n_pulses': n_pulses,
                'noise_floor_dBm': self.receiver.noise_floor_dBm,
                'sensitivity_dBm': self.receiver.sensitivity_dBm,
            }
        )

    def sweep_range(self, radar: RadarParameters,
                    range_min_km: float = 10.0,
                    range_max_km: float = 1000.0,
                    n_points: int = 100) -> Dict[str, np.ndarray]:
        """
        Sweep over range and calculate detection metrics.

        Args:
            radar: RadarParameters object
            range_min_km: Minimum range to analyze
            range_max_km: Maximum range to analyze
            n_points: Number of points in sweep

        Returns:
            Dictionary with range, SNR, Pd arrays
        """
        ranges = np.logspace(np.log10(range_min_km),
                             np.log10(range_max_km), n_points)
        snrs = np.array([self.calculate_snr(radar, r) for r in ranges])
        pds = np.array([self.calculate_detection_probability(radar, r)
                        for r in ranges])
        powers = np.array([self.calculate_received_power(radar, r)
                          for r in ranges])

        return {
            'range_km': ranges,
            'snr_dB': snrs,
            'detection_probability': pds,
            'received_power_dBm': powers,
            'noise_floor_dBm': self.receiver.noise_floor_dBm,
            'sensitivity_dBm': self.receiver.sensitivity_dBm,
        }


def compare_to_radar_range(radar: RadarParameters,
                           receiver: ReceiverParameters,
                           target_rcs_m2: float = 5.0,
                           radar_processing_gain_dB: float = 20.0) -> Dict:
    """
    Compare ESM detection range to radar's detection range.

    This demonstrates the R^2 vs R^4 advantage of passive detection.

    Args:
        radar: RadarParameters for the radar emitter
        receiver: ReceiverParameters for the ESM receiver
        target_rcs_m2: Target radar cross section for radar's detection
        radar_processing_gain_dB: Radar processing gain

    Returns:
        Dictionary with comparison results
    """
    # Calculate radar detection range (R^4)
    radar_bw_Hz = radar.bandwidth_MHz * 1e6
    radar_nf = 10 ** (3.0 / 10)  # Assume 3 dB NF for radar
    radar_snr_req = 10 ** (13.0 / 10)
    radar_loss = 10 ** (6.0 / 10)
    proc_gain = 10 ** (radar_processing_gain_dB / 10)

    # Assume monostatic radar (Gt = Gr)
    Gt = 10 ** (radar.antenna_gain_dB / 10)
    Gr = Gt
    Pt_W = radar.eirp_W / Gt

    numerator = (Pt_W * Gt * Gr * radar.wavelength_m ** 2 *
                 target_rcs_m2 * proc_gain)
    denominator = ((4 * np.pi) ** 3 * KB * T0 * radar_bw_Hz *
                   radar_nf * radar_snr_req * radar_loss)

    radar_range_km = (numerator / denominator) ** 0.25 / 1000

    # Calculate ESM detection range (R^2)
    detector = ESMDetector(receiver)
    esm_range_km = detector.calculate_detection_range(radar)

    # Calculate multiplier
    multiplier = esm_range_km / radar_range_km

    return {
        'radar_detection_range_km': radar_range_km,
        'esm_detection_range_km': esm_range_km,
        'range_multiplier': multiplier,
        'target_rcs_m2': target_rcs_m2,
        'radar_processing_gain_dB': radar_processing_gain_dB,
    }


def sensitivity_analysis(receiver: ReceiverParameters,
                         radar: RadarParameters,
                         param_name: str,
                         param_range: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Analyze sensitivity of detection range to a parameter.

    Args:
        receiver: Base ReceiverParameters
        radar: RadarParameters for the emitter
        param_name: Name of parameter to vary
            ('noise_figure_dB', 'bandwidth_MHz', 'system_loss_dB',
             'antenna_gain_dB', 'snr_required_dB')
        param_range: Array of parameter values to sweep

    Returns:
        Dictionary with parameter values and corresponding ranges
    """
    import copy

    ranges = []
    for val in param_range:
        rx_copy = copy.deepcopy(receiver)
        setattr(rx_copy, param_name, val)
        detector = ESMDetector(rx_copy)
        ranges.append(detector.calculate_detection_range(radar))

    return {
        'parameter_values': param_range,
        'detection_range_km': np.array(ranges),
        'parameter_name': param_name,
    }


# Monte Carlo analysis removed - not needed for design review
