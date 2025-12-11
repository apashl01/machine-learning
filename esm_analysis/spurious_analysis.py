"""
ADC Spurious and False Alarm Analysis Module.

Provides analysis of:
1. Statistical false alarms (thermal noise crossing threshold)
2. Deterministic spurious signals (ADC spurs, intermodulation, images)

References:
- Tsui, J. "Digital Techniques for Wideband Receivers"
- ADC datasheet SFDR and ENOB specifications
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
from scipy import special


@dataclass
class ADCBandSpec:
    """ADC specifications for a frequency band."""
    freq_range_ghz: Tuple[float, float]
    noise_density_db: float  # dBFS/Hz or dBc/Hz
    sfdr_db: float  # Spurious-free dynamic range
    full_scale_dbm: float
    enob: float  # Effective number of bits


@dataclass
class SpuriousConfig:
    """Configuration for spurious analysis."""
    # ADC parameters
    sample_rate_gsps: float = 40.0
    resolution_bits: int = 12
    adc_bands: List[ADCBandSpec] = field(default_factory=list)

    # Receiver parameters
    channel_bandwidth_mhz: float = 20.0
    instantaneous_bandwidth_ghz: float = 1.0
    noise_figure_db: float = 6.0

    # Detection parameters
    threshold_snr_db: float = 10.0
    dwell_time_us: float = 100.0

    @property
    def nyquist_bandwidth_ghz(self) -> float:
        """Nyquist bandwidth = fs/2."""
        return self.sample_rate_gsps / 2

    @property
    def channel_bandwidth_hz(self) -> float:
        """Channel bandwidth in Hz."""
        return self.channel_bandwidth_mhz * 1e6

    @property
    def samples_per_dwell(self) -> int:
        """Number of samples in a dwell period."""
        return int(self.dwell_time_us * 1e-6 * self.sample_rate_gsps * 1e9)


@dataclass
class FalseAlarmResult:
    """Result of statistical false alarm analysis."""
    # Per-sample statistics
    threshold_sigma: float  # Threshold in units of noise sigma
    pfa_per_sample: float  # Probability of false alarm per sample

    # Per-dwell statistics
    samples_per_dwell: int
    expected_false_alarms_per_dwell: float
    pfa_per_dwell: float  # Probability of at least one false alarm per dwell

    # System-level
    mean_time_between_false_alarms_s: float
    false_alarm_rate_per_second: float

    def print_summary(self):
        """Print formatted summary."""
        print("Statistical False Alarm Analysis")
        print("=" * 50)
        print(f"Threshold: {self.threshold_sigma:.2f}σ above noise")
        print(f"Pfa per sample: {self.pfa_per_sample:.2e}")
        print(f"Samples per dwell: {self.samples_per_dwell:,}")
        print(f"Expected false alarms/dwell: {self.expected_false_alarms_per_dwell:.3f}")
        print(f"Pfa per dwell: {self.pfa_per_dwell:.4f}")
        print(f"False alarm rate: {self.false_alarm_rate_per_second:.2f}/second")
        print(f"Mean time between FA: {self.mean_time_between_false_alarms_s:.2f} s")


@dataclass
class SpuriousSignal:
    """Description of a spurious signal."""
    name: str
    frequency_ghz: float
    level_dbfs: float  # Level relative to full scale
    level_dbm: float  # Absolute power level
    source: str  # 'adc', 'intermod', 'image', 'lo_leakage'
    is_in_band: bool  # Within instantaneous bandwidth


@dataclass
class DeterministicSpuriousResult:
    """Result of deterministic spurious analysis."""
    spurious_signals: List[SpuriousSignal]
    sfdr_db: float  # Spurious-free dynamic range
    worst_spur_dbfs: float
    worst_spur_name: str
    num_in_band_spurs: int

    def print_summary(self):
        """Print formatted summary."""
        print("Deterministic Spurious Analysis")
        print("=" * 50)
        print(f"SFDR: {self.sfdr_db:.1f} dBc")
        print(f"Worst spur: {self.worst_spur_name} at {self.worst_spur_dbfs:.1f} dBFS")
        print(f"Total spurious signals: {len(self.spurious_signals)}")
        print(f"In-band spurs: {self.num_in_band_spurs}")
        print()
        print("Spurious Catalog:")
        print("-" * 50)
        for spur in sorted(self.spurious_signals, key=lambda x: x.level_dbfs, reverse=True)[:10]:
            band_marker = "*" if spur.is_in_band else " "
            print(f"  {band_marker} {spur.name}: {spur.frequency_ghz:.3f} GHz, "
                  f"{spur.level_dbfs:.1f} dBFS ({spur.source})")


class SpuriousAnalyzer:
    """Analyzer for ADC spurious and false alarm characteristics."""

    def __init__(self, config: SpuriousConfig):
        self.config = config

    def analyze_statistical_false_alarm(self, pfa_target: float = 1e-6) -> FalseAlarmResult:
        """
        Analyze statistical false alarm rate from thermal noise.

        The probability of false alarm for Gaussian noise is:
        Pfa = erfc(threshold / (sqrt(2) * sigma)) / 2

        For a given target Pfa, we compute the required threshold.

        Args:
            pfa_target: Target probability of false alarm per sample

        Returns:
            FalseAlarmResult with false alarm statistics
        """
        # For target Pfa, find required threshold in sigma
        # Pfa = Q(threshold/sigma) where Q is the Q-function
        # threshold/sigma = sqrt(2) * erfinv(1 - 2*Pfa)
        threshold_sigma = np.sqrt(2) * special.erfcinv(2 * pfa_target)

        # Also compute equivalent SNR threshold
        # For detection threshold, SNR_threshold = threshold_sigma^2 (in linear)
        # In dB: SNR_threshold_db = 10*log10(threshold_sigma^2) = 20*log10(threshold_sigma)

        # Samples per dwell
        samples_per_dwell = self.config.samples_per_dwell

        # Expected false alarms per dwell
        expected_fa_per_dwell = pfa_target * samples_per_dwell

        # Probability of at least one false alarm per dwell
        # P(at least 1) = 1 - P(none) = 1 - (1-Pfa)^N
        pfa_per_dwell = 1 - (1 - pfa_target) ** samples_per_dwell

        # False alarm rate per second
        dwell_rate = 1 / (self.config.dwell_time_us * 1e-6)
        fa_rate_per_second = expected_fa_per_dwell * dwell_rate

        # Mean time between false alarms
        if fa_rate_per_second > 0:
            mtbfa = 1 / fa_rate_per_second
        else:
            mtbfa = float('inf')

        return FalseAlarmResult(
            threshold_sigma=threshold_sigma,
            pfa_per_sample=pfa_target,
            samples_per_dwell=samples_per_dwell,
            expected_false_alarms_per_dwell=expected_fa_per_dwell,
            pfa_per_dwell=pfa_per_dwell,
            mean_time_between_false_alarms_s=mtbfa,
            false_alarm_rate_per_second=fa_rate_per_second
        )

    def compute_pfa_for_threshold(self, threshold_db: float,
                                   noise_floor_dbm: float) -> float:
        """
        Compute Pfa for a given threshold above noise floor.

        Args:
            threshold_db: Detection threshold above noise floor (dB)
            noise_floor_dbm: Noise floor in dBm

        Returns:
            Probability of false alarm per sample
        """
        # Threshold in units of sigma
        # threshold_db = 10*log10(threshold_linear/noise_linear)
        # threshold_sigma = sqrt(threshold_linear/noise_linear)
        threshold_sigma = 10 ** (threshold_db / 20)

        # Pfa = erfc(threshold_sigma / sqrt(2)) / 2
        pfa = special.erfc(threshold_sigma / np.sqrt(2)) / 2

        return pfa

    def analyze_deterministic_spurious(self,
                                        signal_freq_ghz: float,
                                        signal_level_dbm: float,
                                        lo_freq_ghz: Optional[float] = None,
                                        if_freq_ghz: float = 0.0) -> DeterministicSpuriousResult:
        """
        Analyze deterministic spurious signals.

        This includes:
        - ADC harmonics and spurs (limited by SFDR)
        - Intermodulation products (2nd, 3rd order)
        - Image frequencies (if superheterodyne)
        - LO leakage

        Args:
            signal_freq_ghz: Signal frequency
            signal_level_dbm: Signal power level
            lo_freq_ghz: LO frequency (if superheterodyne receiver)
            if_freq_ghz: IF frequency (if superheterodyne)

        Returns:
            DeterministicSpuriousResult with spurious catalog
        """
        spurious_signals = []

        # Get ADC band spec for this frequency
        adc_band = self._get_adc_band(signal_freq_ghz)
        sfdr_db = adc_band.sfdr_db if adc_band else 70.0
        full_scale_dbm = adc_band.full_scale_dbm if adc_band else 0.0

        # Signal level relative to full scale
        signal_dbfs = signal_level_dbm - full_scale_dbm

        # IBW limits for in-band determination
        ibw_ghz = self.config.instantaneous_bandwidth_ghz
        ibw_low = signal_freq_ghz - ibw_ghz / 2
        ibw_high = signal_freq_ghz + ibw_ghz / 2

        # ADC harmonics (2nd, 3rd)
        for n in [2, 3]:
            harm_freq = signal_freq_ghz * n
            # Fold back into Nyquist zone
            harm_freq_folded = self._fold_frequency(harm_freq)

            # Harmonic level drops with SFDR and harmonic order
            # Approximate: each harmonic is ~6 dB worse
            harm_level_dbfs = signal_dbfs - sfdr_db - (n - 2) * 6

            is_in_band = ibw_low <= harm_freq_folded <= ibw_high

            spurious_signals.append(SpuriousSignal(
                name=f"ADC {n}{'nd' if n==2 else 'rd'} Harmonic",
                frequency_ghz=harm_freq_folded,
                level_dbfs=harm_level_dbfs,
                level_dbm=harm_level_dbfs + full_scale_dbm,
                source='adc',
                is_in_band=is_in_band
            ))

        # ADC clock feedthrough (at fs and fs/2)
        for clock_mult, name in [(1.0, "Clock Feedthrough"), (0.5, "Half-Clock Spur")]:
            clock_freq = self.config.sample_rate_gsps * clock_mult
            clock_freq_folded = self._fold_frequency(clock_freq)

            # Clock spurs typically -60 to -80 dBFS
            clock_level_dbfs = -70.0
            is_in_band = ibw_low <= clock_freq_folded <= ibw_high

            spurious_signals.append(SpuriousSignal(
                name=name,
                frequency_ghz=clock_freq_folded,
                level_dbfs=clock_level_dbfs,
                level_dbm=clock_level_dbfs + full_scale_dbm,
                source='adc',
                is_in_band=is_in_band
            ))

        # Image frequency (if superheterodyne with LO)
        if lo_freq_ghz is not None:
            image_freq = 2 * lo_freq_ghz - signal_freq_ghz
            if image_freq > 0:
                # Image rejection depends on mixer balance, typically -30 to -50 dB
                image_level_dbfs = signal_dbfs - 40.0
                is_in_band = ibw_low <= image_freq <= ibw_high

                spurious_signals.append(SpuriousSignal(
                    name="Image Frequency",
                    frequency_ghz=image_freq,
                    level_dbfs=image_level_dbfs,
                    level_dbm=image_level_dbfs + full_scale_dbm,
                    source='image',
                    is_in_band=is_in_band
                ))

            # LO leakage
            lo_leakage_dbfs = -50.0  # Typical LO leakage
            is_in_band = ibw_low <= lo_freq_ghz <= ibw_high

            spurious_signals.append(SpuriousSignal(
                name="LO Leakage",
                frequency_ghz=lo_freq_ghz,
                level_dbfs=lo_leakage_dbfs,
                level_dbm=lo_leakage_dbfs + full_scale_dbm,
                source='lo_leakage',
                is_in_band=is_in_band
            ))

        # Intermodulation products (if we assume a second signal)
        # For single-signal analysis, we model self-mixing products
        # 2f1-f1 = f1 (DC mixing), 3f1-2f1 = f1, etc.
        # These are captured by ADC nonlinearity / SFDR

        # Find worst spur
        if spurious_signals:
            worst_spur = max(spurious_signals, key=lambda x: x.level_dbfs)
            worst_spur_dbfs = worst_spur.level_dbfs
            worst_spur_name = worst_spur.name
        else:
            worst_spur_dbfs = -sfdr_db
            worst_spur_name = "None"

        # Count in-band spurs
        num_in_band = sum(1 for s in spurious_signals if s.is_in_band)

        return DeterministicSpuriousResult(
            spurious_signals=spurious_signals,
            sfdr_db=sfdr_db,
            worst_spur_dbfs=worst_spur_dbfs,
            worst_spur_name=worst_spur_name,
            num_in_band_spurs=num_in_band
        )

    def analyze_two_tone_intermod(self,
                                   freq1_ghz: float,
                                   freq2_ghz: float,
                                   level1_dbm: float,
                                   level2_dbm: float,
                                   iip3_dbm: float = 20.0) -> List[SpuriousSignal]:
        """
        Analyze two-tone intermodulation products.

        Args:
            freq1_ghz, freq2_ghz: Input frequencies
            level1_dbm, level2_dbm: Input power levels
            iip3_dbm: Third-order input intercept point

        Returns:
            List of intermodulation products
        """
        spurious_signals = []

        # Get full scale reference
        adc_band = self._get_adc_band(freq1_ghz)
        full_scale_dbm = adc_band.full_scale_dbm if adc_band else 0.0

        # IBW limits
        ibw_ghz = self.config.instantaneous_bandwidth_ghz
        center_freq = (freq1_ghz + freq2_ghz) / 2
        ibw_low = center_freq - ibw_ghz / 2
        ibw_high = center_freq + ibw_ghz / 2

        # Second-order products (f1+f2, f1-f2, 2f1, 2f2)
        # IM2 = P1 + P2 - IIP2 (in dBm)
        iip2_dbm = iip3_dbm + 10  # Rough estimate
        im2_products = [
            (abs(freq1_ghz - freq2_ghz), "f1-f2"),
            (freq1_ghz + freq2_ghz, "f1+f2"),
            (2 * freq1_ghz, "2f1"),
            (2 * freq2_ghz, "2f2"),
        ]

        for freq, name in im2_products:
            freq_folded = self._fold_frequency(freq)
            # IM2 level
            im2_level = level1_dbm + level2_dbm - iip2_dbm
            is_in_band = ibw_low <= freq_folded <= ibw_high

            spurious_signals.append(SpuriousSignal(
                name=f"IM2 ({name})",
                frequency_ghz=freq_folded,
                level_dbfs=im2_level - full_scale_dbm,
                level_dbm=im2_level,
                source='intermod',
                is_in_band=is_in_band
            ))

        # Third-order products (2f1-f2, 2f2-f1)
        # IM3 = 2*P1 + P2 - 2*IIP3 for 2f1-f2
        im3_products = [
            (2 * freq1_ghz - freq2_ghz, "2f1-f2", 2 * level1_dbm + level2_dbm - 2 * iip3_dbm),
            (2 * freq2_ghz - freq1_ghz, "2f2-f1", 2 * level2_dbm + level1_dbm - 2 * iip3_dbm),
        ]

        for freq, name, im3_level in im3_products:
            if freq > 0:
                freq_folded = self._fold_frequency(freq)
                is_in_band = ibw_low <= freq_folded <= ibw_high

                spurious_signals.append(SpuriousSignal(
                    name=f"IM3 ({name})",
                    frequency_ghz=freq_folded,
                    level_dbfs=im3_level - full_scale_dbm,
                    level_dbm=im3_level,
                    source='intermod',
                    is_in_band=is_in_band
                ))

        return spurious_signals

    def _fold_frequency(self, freq_ghz: float) -> float:
        """Fold frequency back into first Nyquist zone."""
        fs = self.config.sample_rate_gsps
        # Fold into 0 to fs range, then into 0 to fs/2
        freq_mod = freq_ghz % fs
        if freq_mod > fs / 2:
            freq_mod = fs - freq_mod
        return freq_mod

    def _get_adc_band(self, freq_ghz: float) -> Optional[ADCBandSpec]:
        """Get ADC band specification for a frequency."""
        for band in self.config.adc_bands:
            if band.freq_range_ghz[0] <= freq_ghz <= band.freq_range_ghz[1]:
                return band
        return None


def load_from_system_config() -> SpuriousConfig:
    """Load spurious config from shared system_config."""
    from pathlib import Path
    import yaml

    # Load system config for ADC (Task 1.0: Updated to use centralized config/)
    sys_config_path = Path(__file__).parent.parent / "config" / "system_config.yaml"
    with open(sys_config_path, 'r') as f:
        sys_data = yaml.safe_load(f)

    # Load ESM config for receiver params
    esm_config_path = Path(__file__).parent / "config" / "system_config.yaml"
    try:
        with open(esm_config_path, 'r') as f:
            esm_data = yaml.safe_load(f)
        receiver_data = esm_data.get('receiver', {})
        ibw_ghz = float(receiver_data.get('instantaneous_bandwidth_ghz', 1.0))
        bw_raw = receiver_data.get('bandwidth_hz', 20e6)
        channel_bw_mhz = float(bw_raw) / 1e6
        noise_figure_db = float(receiver_data.get('noise_figure_db', 6.0))
        threshold_snr_db = float(receiver_data.get('snr_threshold_db', 10.0))
    except FileNotFoundError:
        ibw_ghz = 1.0
        channel_bw_mhz = 20.0
        noise_figure_db = 6.0
        threshold_snr_db = 10.0

    adc_data = sys_data.get('adc', {})

    # Parse ADC bands
    adc_bands = []
    for band_name, band_data in adc_data.get('bands', {}).items():
        adc_bands.append(ADCBandSpec(
            freq_range_ghz=tuple(band_data.get('freq_range_ghz', [2.0, 18.0])),
            noise_density_db=float(band_data.get('noise_density_db', -165)),
            sfdr_db=float(band_data.get('sfdr_db', 70)),
            full_scale_dbm=float(band_data.get('full_scale_dbm', 0)),
            enob=float(band_data.get('enob', 10))
        ))

    return SpuriousConfig(
        sample_rate_gsps=float(adc_data.get('sample_rate_gsps', 40.0)),
        resolution_bits=int(adc_data.get('resolution_bits', 12)),
        adc_bands=adc_bands,
        channel_bandwidth_mhz=channel_bw_mhz,
        instantaneous_bandwidth_ghz=ibw_ghz,
        noise_figure_db=noise_figure_db,
        threshold_snr_db=threshold_snr_db
    )


def analyze_spurious(signal_freq_ghz: float = 10.0,
                     signal_level_dbm: float = -30.0,
                     pfa_target: float = 1e-6) -> Dict:
    """
    Convenience function for quick spurious analysis.

    Args:
        signal_freq_ghz: Signal frequency in GHz
        signal_level_dbm: Signal level in dBm
        pfa_target: Target false alarm probability

    Returns:
        Dict with 'false_alarm' and 'spurious' results
    """
    config = load_from_system_config()
    analyzer = SpuriousAnalyzer(config)

    fa_result = analyzer.analyze_statistical_false_alarm(pfa_target)
    spur_result = analyzer.analyze_deterministic_spurious(signal_freq_ghz, signal_level_dbm)

    return {
        'false_alarm': fa_result,
        'spurious': spur_result
    }


if __name__ == "__main__":
    # Demo analysis
    print("ADC Spurious and False Alarm Analysis Demo")
    print("=" * 60)
    print()

    results = analyze_spurious(signal_freq_ghz=10.0, signal_level_dbm=-30.0)

    results['false_alarm'].print_summary()
    print()
    results['spurious'].print_summary()
