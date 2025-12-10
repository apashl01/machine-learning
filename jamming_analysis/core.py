"""
Jamming Analysis Core Module

Provides J/S (Jamming-to-Signal) ratio calculations for Self-Protect Jamming (SPJ).

Self-Protect Jamming Geometry:
- The jammer is mounted on the platform being tracked by the radar
- Radar transmits → reflects off platform (based on platform RCS) → returns to radar
- Jammer transmits directly to radar (one-way path)

Key Equations:
- Jamming power at radar: P_j = EIRP_j / (4πR²) [one-way]
- Signal power at radar: P_s = P_r·G_r²·σ·λ² / ((4π)³·R⁴) [two-way radar equation]
- J/S = P_j / P_s ∝ R² / σ

This means:
- J/S INCREASES with range (jammer R^-2 vs radar R^-4)
- J/S DECREASES with larger platform RCS (smaller RCS = better jamming)

Reference: ew_mission_phase3_jamming.m
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
import numpy as np


# Physical constants
C_LIGHT = 3e8  # Speed of light (m/s)


@dataclass
class JammerConfig:
    """
    Self-protect jammer configuration.

    The jammer is mounted on the platform being protected from radar tracking.
    Platform RCS is included here because it directly affects J/S ratio.
    """
    # Power
    input_power_dbm: float = 50.0  # Power into antenna (dBm), 50 dBm = 100W

    # Antenna
    antenna_gain_dbi: float = 20.0  # Peak antenna gain (dBi)
    beamwidth_deg: float = 30.0  # 3dB beamwidth (degrees)
    pattern_type: str = "gaussian"  # 'gaussian', 'cosine_squared', 'isotropic'

    # Operating frequency
    frequency_ghz: float = 6.0

    # Platform RCS (affects radar return, thus J/S ratio)
    # Smaller RCS = better jamming effectiveness
    platform_rcs_m2: float = 2.0  # Platform radar cross section (m²)

    @property
    def input_power_dbw(self) -> float:
        """Input power in dBW."""
        return self.input_power_dbm - 30

    @property
    def input_power_watts(self) -> float:
        """Input power in Watts."""
        return 10 ** (self.input_power_dbm / 10) / 1000

    @property
    def eirp_peak_dbm(self) -> float:
        """Peak EIRP (at boresight) in dBm."""
        return self.input_power_dbm + self.antenna_gain_dbi

    @property
    def eirp_peak_watts(self) -> float:
        """Peak EIRP in Watts."""
        return 10 ** (self.eirp_peak_dbm / 10) / 1000

    @property
    def wavelength_m(self) -> float:
        """Wavelength at operating frequency."""
        return C_LIGHT / (self.frequency_ghz * 1e9)

    @property
    def platform_rcs_dbsm(self) -> float:
        """Platform RCS in dBsm."""
        return 10 * np.log10(self.platform_rcs_m2)

    def get_gain_at_angle(self, off_boresight_deg: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Calculate antenna gain at off-boresight angle.

        Args:
            off_boresight_deg: Angle(s) from boresight in degrees

        Returns:
            Gain in dBi at the specified angle(s)
        """
        angle = np.asarray(off_boresight_deg)

        if self.pattern_type == "isotropic":
            return np.full_like(angle, 0.0, dtype=float)

        elif self.pattern_type == "gaussian":
            # Gaussian beam: G(theta) = G_peak - 12 * (theta / theta_3dB)^2
            half_beamwidth = self.beamwidth_deg / 2
            gain = self.antenna_gain_dbi - 12 * (angle / half_beamwidth) ** 2
            gain = np.maximum(gain, -20.0)  # Floor at -20 dBi
            return gain

        elif self.pattern_type == "cosine_squared":
            norm_angle = angle * np.pi / (2 * self.beamwidth_deg)
            pattern_linear = np.cos(norm_angle) ** 2
            pattern_linear = np.maximum(pattern_linear, 1e-4)
            gain = self.antenna_gain_dbi + 10 * np.log10(pattern_linear)
            return gain

        else:
            raise ValueError(f"Unknown pattern type: {self.pattern_type}")


@dataclass
class RadarConfig:
    """
    Threat radar configuration.

    This is the radar that the self-protect jammer is trying to defeat.
    """
    # Power
    power_dbw: float = 60.0  # Transmit power (dBW), 60 dBW = 1 MW

    # Antenna
    antenna_gain_dbi: float = 35.0  # Antenna gain (dBi)

    # Operating frequency
    frequency_ghz: float = 6.0

    @property
    def power_watts(self) -> float:
        """Power in Watts."""
        return 10 ** (self.power_dbw / 10)

    @property
    def wavelength_m(self) -> float:
        """Wavelength at operating frequency."""
        return C_LIGHT / (self.frequency_ghz * 1e9)


# Backwards compatibility alias
EmitterConfig = RadarConfig


@dataclass
class JammingResult:
    """Result of jamming analysis at a single point or over trajectory."""
    # Input parameters
    range_m: Union[float, np.ndarray]
    off_boresight_deg: Union[float, np.ndarray]

    # Jammer performance
    jammer_gain_dbi: Union[float, np.ndarray]
    eirp_dbm: Union[float, np.ndarray]
    jammer_power_at_radar_dbw: Union[float, np.ndarray]

    # Signal (radar return) at radar receiver
    signal_power_at_radar_dbw: Union[float, np.ndarray]

    # J/S ratio
    js_ratio_db: Union[float, np.ndarray]

    # Path losses
    path_loss_one_way_db: Union[float, np.ndarray]
    path_loss_two_way_db: Union[float, np.ndarray]

    # Platform RCS used
    platform_rcs_dbsm: float = 3.0

    def print_summary(self):
        """Print formatted summary."""
        print("Self-Protect Jamming Analysis")
        print("=" * 50)

        if np.isscalar(self.range_m):
            print(f"Range: {self.range_m/1000:.1f} km")
            print(f"Off-boresight: {self.off_boresight_deg:.1f}°")
            print(f"Platform RCS: {self.platform_rcs_dbsm:.1f} dBsm")
            print(f"Jammer gain: {self.jammer_gain_dbi:.1f} dBi")
            print(f"EIRP: {self.eirp_dbm:.1f} dBm ({10**(self.eirp_dbm/10)/1000:.1f} W)")
            print(f"Path loss (one-way): {self.path_loss_one_way_db:.1f} dB")
            print(f"Jammer power at radar: {self.jammer_power_at_radar_dbw:.1f} dBW")
            print(f"Signal power at radar: {self.signal_power_at_radar_dbw:.1f} dBW")
            print(f"J/S Ratio: {self.js_ratio_db:.1f} dB")
        else:
            print(f"Range: {np.min(self.range_m)/1000:.1f} - {np.max(self.range_m)/1000:.1f} km")
            print(f"Platform RCS: {self.platform_rcs_dbsm:.1f} dBsm")
            print(f"J/S Ratio: {np.min(self.js_ratio_db):.1f} - {np.max(self.js_ratio_db):.1f} dB (mean: {np.mean(self.js_ratio_db):.1f} dB)")

            # Effectiveness statistics
            n = len(self.js_ratio_db)
            pct_above_0 = 100 * np.sum(self.js_ratio_db > 0) / n
            pct_above_10 = 100 * np.sum(self.js_ratio_db > 10) / n
            pct_above_20 = 100 * np.sum(self.js_ratio_db > 20) / n

            print()
            print("Jamming Effectiveness:")
            print(f"  J/S > 0 dB (marginal):   {pct_above_0:.1f}%")
            print(f"  J/S > 10 dB (good):      {pct_above_10:.1f}%")
            print(f"  J/S > 20 dB (excellent): {pct_above_20:.1f}%")

    def get_effectiveness_stats(self) -> Dict:
        """Get jamming effectiveness statistics."""
        js = np.asarray(self.js_ratio_db)
        n = js.size

        return {
            'mean_js_db': float(np.mean(js)),
            'min_js_db': float(np.min(js)),
            'max_js_db': float(np.max(js)),
            'pct_above_0db': 100 * np.sum(js > 0) / n,
            'pct_above_10db': 100 * np.sum(js > 10) / n,
            'pct_above_20db': 100 * np.sum(js > 20) / n,
        }


class JammingAnalyzer:
    """
    Analyzer for self-protect jamming effectiveness.

    Models the J/S ratio where:
    - J = Jammer power received at radar (one-way propagation)
    - S = Radar return from platform (two-way, depends on platform RCS)
    """

    def __init__(self, jammer: JammerConfig, radar: RadarConfig):
        """
        Initialize analyzer.

        Args:
            jammer: Self-protect jammer configuration (includes platform RCS)
            radar: Threat radar configuration
        """
        self.jammer = jammer
        self.radar = radar

    def calculate_path_loss_one_way(self, range_m: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Calculate one-way free space path loss (jammer to radar)."""
        r = np.asarray(range_m)
        lambda_m = self.jammer.wavelength_m
        return 20 * np.log10(r) + 20 * np.log10(4 * np.pi / lambda_m)

    def calculate_path_loss_two_way(self, range_m: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """Calculate two-way radar path loss (radar → platform → radar)."""
        r = np.asarray(range_m)
        lambda_m = self.radar.wavelength_m
        return 40 * np.log10(r) + 20 * np.log10(4 * np.pi / lambda_m)

    def analyze(self,
                range_m: Union[float, np.ndarray],
                off_boresight_deg: Union[float, np.ndarray] = 0.0,
                platform_rcs_m2: Optional[float] = None) -> JammingResult:
        """
        Analyze self-protect jamming effectiveness.

        J/S Calculation for Self-Protect:
        - Jammer power at radar = P_j + G_j - L_one_way
        - Signal power at radar = P_r + 2*G_r + σ_platform - L_two_way
        - J/S = Jammer power - Signal power

        Args:
            range_m: Range to radar in meters
            off_boresight_deg: Jammer antenna off-boresight angle
            platform_rcs_m2: Override platform RCS (uses jammer.platform_rcs_m2 if None)

        Returns:
            JammingResult with all calculated values
        """
        r = np.asarray(range_m)
        angle = np.asarray(off_boresight_deg)

        # Broadcast if needed
        if r.shape != angle.shape:
            r, angle = np.broadcast_arrays(r, angle)

        # Platform RCS
        rcs_m2 = platform_rcs_m2 if platform_rcs_m2 is not None else self.jammer.platform_rcs_m2
        rcs_dbsm = 10 * np.log10(rcs_m2)

        # Jammer gain at pointing angle
        jammer_gain = self.jammer.get_gain_at_angle(angle)

        # EIRP
        eirp_dbm = self.jammer.input_power_dbm + jammer_gain

        # Path losses
        path_loss_one_way = self.calculate_path_loss_one_way(r)
        path_loss_two_way = self.calculate_path_loss_two_way(r)

        # Jammer power at radar (one-way link)
        jammer_power_dbw = self.jammer.input_power_dbw + jammer_gain - path_loss_one_way

        # Signal power at radar (two-way link with platform RCS)
        # Radar equation: P_s = P_t + 2*G + σ - L_two_way
        signal_power_dbw = (self.radar.power_dbw +
                           2 * self.radar.antenna_gain_dbi +
                           rcs_dbsm -
                           path_loss_two_way)

        # J/S ratio
        js_ratio_db = jammer_power_dbw - signal_power_dbw

        return JammingResult(
            range_m=range_m,
            off_boresight_deg=off_boresight_deg,
            jammer_gain_dbi=jammer_gain,
            eirp_dbm=eirp_dbm,
            jammer_power_at_radar_dbw=jammer_power_dbw,
            signal_power_at_radar_dbw=signal_power_dbw,
            js_ratio_db=js_ratio_db,
            path_loss_one_way_db=path_loss_one_way,
            path_loss_two_way_db=path_loss_two_way,
            platform_rcs_dbsm=rcs_dbsm
        )

    def analyze_vs_range(self,
                         range_min_km: float = 10.0,
                         range_max_km: float = 200.0,
                         num_points: int = 100,
                         off_boresight_deg: float = 0.0) -> JammingResult:
        """Analyze J/S ratio vs range at fixed off-boresight angle."""
        ranges_m = np.linspace(range_min_km * 1000, range_max_km * 1000, num_points)
        angles = np.full_like(ranges_m, off_boresight_deg)
        return self.analyze(ranges_m, angles)

    def analyze_vs_angle(self,
                         range_km: float = 50.0,
                         angle_min_deg: float = -90.0,
                         angle_max_deg: float = 90.0,
                         num_points: int = 181) -> JammingResult:
        """Analyze J/S ratio vs off-boresight angle at fixed range."""
        range_m = range_km * 1000
        angles = np.linspace(angle_min_deg, angle_max_deg, num_points)
        ranges = np.full_like(angles, range_m)
        return self.analyze(ranges, angles)

    def analyze_vs_rcs(self,
                       range_km: float = 50.0,
                       rcs_min_m2: float = 0.1,
                       rcs_max_m2: float = 10.0,
                       num_points: int = 50,
                       off_boresight_deg: float = 0.0) -> Dict[str, np.ndarray]:
        """
        Analyze J/S ratio vs platform RCS.

        Shows how reducing platform RCS improves jamming effectiveness.

        Args:
            range_km: Fixed range
            rcs_min_m2: Minimum RCS
            rcs_max_m2: Maximum RCS
            num_points: Number of RCS values
            off_boresight_deg: Off-boresight angle

        Returns:
            Dict with 'rcs_m2', 'rcs_dbsm', 'js_ratio_db'
        """
        rcs_values = np.logspace(np.log10(rcs_min_m2), np.log10(rcs_max_m2), num_points)
        js_values = np.zeros_like(rcs_values)

        for i, rcs in enumerate(rcs_values):
            result = self.analyze(range_km * 1000, off_boresight_deg, platform_rcs_m2=rcs)
            js_values[i] = result.js_ratio_db

        return {
            'rcs_m2': rcs_values,
            'rcs_dbsm': 10 * np.log10(rcs_values),
            'js_ratio_db': js_values
        }

    def calculate_burn_through_range(self,
                                      js_threshold_db: float = 0.0,
                                      off_boresight_deg: float = 0.0) -> float:
        """
        Calculate the burn-through range where J/S equals threshold.

        At burn-through, the radar can "burn through" the jamming.
        For self-protect jamming, this occurs at CLOSER ranges.

        Args:
            js_threshold_db: J/S threshold (typically 0 dB)
            off_boresight_deg: Off-boresight angle

        Returns:
            Burn-through range in km
        """
        r_min, r_max = 1000, 500000  # 1 km to 500 km

        for _ in range(50):
            r_mid = (r_min + r_max) / 2
            result = self.analyze(r_mid, off_boresight_deg)

            if result.js_ratio_db < js_threshold_db:
                r_min = r_mid
            else:
                r_max = r_mid

        return r_mid / 1000


def load_jammer_from_system_config() -> JammerConfig:
    """Load jammer configuration from system_config.yaml TX paths."""
    from pathlib import Path
    import yaml

    config_path = Path(__file__).parent.parent / "system_config" / "system_config.yaml"

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    tx_paths = data.get('rf_chains', {}).get('tx_paths', {})
    tx_config = tx_paths.get('tx_2_18ghz', tx_paths.get('tx_low_band', {}))

    # Extract antenna beamwidth and gain from components
    beamwidth = 30.0
    antenna_gain = 0.0
    for component in tx_config.get('components', []):
        if 'beamwidth_deg' in component:
            beamwidth = float(component['beamwidth_deg'])
        if component.get('type') in ['horn', 'omni', 'antenna']:
            antenna_gain = float(component.get('gain_db', 0))

    freq_config = data.get('frequency', {})
    freq_ghz = float(freq_config.get('reference_ghz', 10.0))

    return JammerConfig(
        input_power_dbm=tx_config.get('source_power_dbm', 0) + tx_config.get('total_gain_db', 45) - antenna_gain,
        antenna_gain_dbi=antenna_gain,
        beamwidth_deg=beamwidth,
        pattern_type='gaussian',
        frequency_ghz=freq_ghz,
        platform_rcs_m2=2.0  # Default platform RCS
    )


def analyze_jamming_standalone(range_km: float = 50.0,
                                off_boresight_deg: float = 0.0,
                                jammer: Optional[JammerConfig] = None,
                                radar: Optional[RadarConfig] = None) -> JammingResult:
    """
    Convenience function for quick jamming analysis.

    Args:
        range_km: Range to radar in km
        off_boresight_deg: Off-boresight angle in degrees
        jammer: Jammer configuration (uses defaults if None)
        radar: Radar configuration (uses defaults if None)

    Returns:
        JammingResult with analysis
    """
    if jammer is None:
        try:
            jammer = load_jammer_from_system_config()
        except Exception:
            jammer = JammerConfig()

    if radar is None:
        radar = RadarConfig()

    analyzer = JammingAnalyzer(jammer, radar)
    return analyzer.analyze(range_km * 1000, off_boresight_deg)


if __name__ == "__main__":
    print("Self-Protect Jamming Analysis Demo")
    print("=" * 60)
    print()

    jammer = JammerConfig(
        input_power_dbm=50,
        antenna_gain_dbi=20,
        beamwidth_deg=30,
        pattern_type='gaussian',
        frequency_ghz=6.0,
        platform_rcs_m2=2.0
    )

    radar = RadarConfig(
        power_dbw=60,
        antenna_gain_dbi=35,
        frequency_ghz=6.0
    )

    print("Jammer Configuration:")
    print(f"  Input power: {jammer.input_power_dbm} dBm ({jammer.input_power_watts:.0f} W)")
    print(f"  Peak antenna gain: {jammer.antenna_gain_dbi} dBi")
    print(f"  Beamwidth: {jammer.beamwidth_deg}°")
    print(f"  Peak EIRP: {jammer.eirp_peak_dbm:.1f} dBm ({jammer.eirp_peak_watts:.0f} W)")
    print(f"  Platform RCS: {jammer.platform_rcs_m2} m² ({jammer.platform_rcs_dbsm:.1f} dBsm)")
    print()

    print("Radar Configuration:")
    print(f"  Power: {radar.power_dbw} dBW ({radar.power_watts/1e6:.1f} MW)")
    print(f"  Antenna gain: {radar.antenna_gain_dbi} dBi")
    print()

    analyzer = JammingAnalyzer(jammer, radar)

    # Single point analysis
    print("Analysis at 50 km, on-boresight:")
    result = analyzer.analyze(50000, 0)
    result.print_summary()
    print()

    # RCS sensitivity
    print("\nJ/S vs Platform RCS (at 50 km):")
    print("-" * 40)
    for rcs in [0.5, 1.0, 2.0, 5.0, 10.0]:
        r = analyzer.analyze(50000, 0, platform_rcs_m2=rcs)
        print(f"  RCS = {rcs:4.1f} m² ({10*np.log10(rcs):+5.1f} dBsm) → J/S = {r.js_ratio_db:+5.1f} dB")

    print()
    bt_range = analyzer.calculate_burn_through_range(0)
    print(f"Burn-through range (J/S = 0 dB): {bt_range:.1f} km")
