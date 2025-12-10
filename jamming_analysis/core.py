"""
Jamming Analysis Core Module

Provides J/S (Jamming-to-Signal) ratio calculations for:
1. Standalone parametric analysis (EIRP, J/S vs range)
2. Trajectory-based mission analysis

Key Equations:
- EIRP = P_tx + G_tx (dBm + dBi = dBm)
- Path Loss (one-way) = 20*log10(R) + 20*log10(4*pi/lambda)
- Path Loss (two-way radar) = 40*log10(R) + 20*log10(4*pi/lambda)
- J/S = P_jammer_at_target - P_signal_at_target

Reference: ew_mission_phase3_jamming.m
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
import numpy as np


# Physical constants
C_LIGHT = 3e8  # Speed of light (m/s)


@dataclass
class JammerConfig:
    """Jammer system configuration."""
    # Power
    input_power_dbm: float = 50.0  # Power into antenna (dBm), 50 dBm = 100W

    # Antenna
    antenna_gain_dbi: float = 20.0  # Peak antenna gain (dBi)
    beamwidth_deg: float = 30.0  # 3dB beamwidth (degrees)
    pattern_type: str = "gaussian"  # 'gaussian', 'cosine_squared', 'isotropic'

    # Operating frequency
    frequency_ghz: float = 6.0

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
            # This gives -3 dB at theta_3dB/2 (half-power beamwidth)
            half_beamwidth = self.beamwidth_deg / 2
            gain = self.antenna_gain_dbi - 12 * (angle / half_beamwidth) ** 2
            # Floor at -20 dBi (typical sidelobe/backlobe level)
            gain = np.maximum(gain, -20.0)
            return gain

        elif self.pattern_type == "cosine_squared":
            # Cosine-squared pattern: G(theta) = G_peak * cos^2(theta * pi / beamwidth)
            # Normalized to give -3 dB at half-beamwidth
            norm_angle = angle * np.pi / (2 * self.beamwidth_deg)
            pattern_linear = np.cos(norm_angle) ** 2
            pattern_linear = np.maximum(pattern_linear, 1e-4)  # Floor
            gain = self.antenna_gain_dbi + 10 * np.log10(pattern_linear)
            return gain

        else:
            raise ValueError(f"Unknown pattern type: {self.pattern_type}")


@dataclass
class EmitterConfig:
    """Target emitter (radar) configuration."""
    # Power
    power_dbw: float = 60.0  # Transmit power (dBW), 60 dBW = 1 MW

    # Antenna
    antenna_gain_dbi: float = 35.0  # Antenna gain (dBi)

    # Operating frequency
    frequency_ghz: float = 6.0

    # Target (UAV) parameters for radar return calculation
    target_rcs_m2: float = 2.0  # Radar cross section (m²)

    @property
    def power_watts(self) -> float:
        """Power in Watts."""
        return 10 ** (self.power_dbw / 10)

    @property
    def target_rcs_dbsm(self) -> float:
        """Target RCS in dBsm."""
        return 10 * np.log10(self.target_rcs_m2)

    @property
    def wavelength_m(self) -> float:
        """Wavelength at operating frequency."""
        return C_LIGHT / (self.frequency_ghz * 1e9)


@dataclass
class JammingResult:
    """Result of jamming analysis at a single point or over trajectory."""
    # Input parameters
    range_m: Union[float, np.ndarray]
    off_boresight_deg: Union[float, np.ndarray]

    # Jammer performance
    jammer_gain_dbi: Union[float, np.ndarray]
    eirp_dbm: Union[float, np.ndarray]
    jammer_power_at_target_dbw: Union[float, np.ndarray]

    # Signal (radar return) at target
    signal_power_at_target_dbw: Union[float, np.ndarray]

    # J/S ratio
    js_ratio_db: Union[float, np.ndarray]

    # Path losses
    path_loss_one_way_db: Union[float, np.ndarray]
    path_loss_two_way_db: Union[float, np.ndarray]

    def print_summary(self):
        """Print formatted summary."""
        print("Jamming Analysis Results")
        print("=" * 50)

        if np.isscalar(self.range_m):
            print(f"Range: {self.range_m/1000:.1f} km")
            print(f"Off-boresight: {self.off_boresight_deg:.1f}°")
            print(f"Jammer gain: {self.jammer_gain_dbi:.1f} dBi")
            print(f"EIRP: {self.eirp_dbm:.1f} dBm ({10**(self.eirp_dbm/10)/1000:.1f} W)")
            print(f"Path loss (one-way): {self.path_loss_one_way_db:.1f} dB")
            print(f"Jammer power at target: {self.jammer_power_at_target_dbw:.1f} dBW")
            print(f"Signal power at target: {self.signal_power_at_target_dbw:.1f} dBW")
            print(f"J/S Ratio: {self.js_ratio_db:.1f} dB")
        else:
            print(f"Range: {np.min(self.range_m)/1000:.1f} - {np.max(self.range_m)/1000:.1f} km")
            print(f"Off-boresight: {np.min(self.off_boresight_deg):.1f}° - {np.max(self.off_boresight_deg):.1f}°")
            print(f"Jammer gain: {np.min(self.jammer_gain_dbi):.1f} - {np.max(self.jammer_gain_dbi):.1f} dBi")
            print(f"Mean EIRP: {np.mean(self.eirp_dbm):.1f} dBm")
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
    Analyzer for jamming effectiveness calculations.

    Supports:
    - Standalone J/S analysis at specific range/angle
    - Parametric J/S vs range curves
    - Trajectory-based mission analysis
    """

    def __init__(self, jammer: JammerConfig, emitter: EmitterConfig):
        """
        Initialize analyzer with jammer and emitter configurations.

        Args:
            jammer: Jammer system configuration
            emitter: Target emitter configuration
        """
        self.jammer = jammer
        self.emitter = emitter

    def calculate_path_loss_one_way(self, range_m: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Calculate one-way free space path loss.

        L = 20*log10(R) + 20*log10(4*pi/lambda)

        Args:
            range_m: Range in meters

        Returns:
            Path loss in dB
        """
        r = np.asarray(range_m)
        lambda_m = self.jammer.wavelength_m
        return 20 * np.log10(r) + 20 * np.log10(4 * np.pi / lambda_m)

    def calculate_path_loss_two_way(self, range_m: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
        """
        Calculate two-way (radar) path loss.

        L = 40*log10(R) + 20*log10(4*pi/lambda)

        Args:
            range_m: Range in meters

        Returns:
            Path loss in dB
        """
        r = np.asarray(range_m)
        lambda_m = self.emitter.wavelength_m
        return 40 * np.log10(r) + 20 * np.log10(4 * np.pi / lambda_m)

    def analyze(self,
                range_m: Union[float, np.ndarray],
                off_boresight_deg: Union[float, np.ndarray] = 0.0) -> JammingResult:
        """
        Analyze jamming effectiveness at given range and angle.

        J/S Calculation:
        - Jammer power at target = P_tx + G_tx - L_one_way
        - Signal power at target = P_radar + 2*G_radar + RCS - L_two_way
        - J/S = Jammer power - Signal power

        Args:
            range_m: Range to target in meters (scalar or array)
            off_boresight_deg: Off-boresight angle in degrees (scalar or array)

        Returns:
            JammingResult with all calculated values
        """
        r = np.asarray(range_m)
        angle = np.asarray(off_boresight_deg)

        # Broadcast if needed
        if r.shape != angle.shape:
            r, angle = np.broadcast_arrays(r, angle)

        # Jammer gain at pointing angle
        jammer_gain = self.jammer.get_gain_at_angle(angle)

        # EIRP
        eirp_dbm = self.jammer.input_power_dbm + jammer_gain

        # Path losses
        path_loss_one_way = self.calculate_path_loss_one_way(r)
        path_loss_two_way = self.calculate_path_loss_two_way(r)

        # Jammer power at target (one-way link)
        # P_j = P_tx(dBW) + G_tx - L
        jammer_power_dbw = self.jammer.input_power_dbw + jammer_gain - path_loss_one_way

        # Signal power at target (two-way radar link)
        # Radar receives its own echo: P_s = P_t + 2*G + RCS - L_two_way
        signal_power_dbw = (self.emitter.power_dbw +
                           2 * self.emitter.antenna_gain_dbi +
                           self.emitter.target_rcs_dbsm -
                           path_loss_two_way)

        # J/S ratio
        js_ratio_db = jammer_power_dbw - signal_power_dbw

        return JammingResult(
            range_m=range_m,
            off_boresight_deg=off_boresight_deg,
            jammer_gain_dbi=jammer_gain,
            eirp_dbm=eirp_dbm,
            jammer_power_at_target_dbw=jammer_power_dbw,
            signal_power_at_target_dbw=signal_power_dbw,
            js_ratio_db=js_ratio_db,
            path_loss_one_way_db=path_loss_one_way,
            path_loss_two_way_db=path_loss_two_way
        )

    def analyze_vs_range(self,
                         range_min_km: float = 10.0,
                         range_max_km: float = 200.0,
                         num_points: int = 100,
                         off_boresight_deg: float = 0.0) -> JammingResult:
        """
        Analyze J/S ratio vs range at fixed off-boresight angle.

        Args:
            range_min_km: Minimum range (km)
            range_max_km: Maximum range (km)
            num_points: Number of range points
            off_boresight_deg: Fixed off-boresight angle (degrees)

        Returns:
            JammingResult with arrays of values vs range
        """
        ranges_m = np.linspace(range_min_km * 1000, range_max_km * 1000, num_points)
        angles = np.full_like(ranges_m, off_boresight_deg)

        return self.analyze(ranges_m, angles)

    def analyze_vs_angle(self,
                         range_km: float = 50.0,
                         angle_min_deg: float = -90.0,
                         angle_max_deg: float = 90.0,
                         num_points: int = 181) -> JammingResult:
        """
        Analyze J/S ratio vs off-boresight angle at fixed range.

        Args:
            range_km: Fixed range (km)
            angle_min_deg: Minimum angle (degrees)
            angle_max_deg: Maximum angle (degrees)
            num_points: Number of angle points

        Returns:
            JammingResult with arrays of values vs angle
        """
        range_m = range_km * 1000
        angles = np.linspace(angle_min_deg, angle_max_deg, num_points)
        ranges = np.full_like(angles, range_m)

        return self.analyze(ranges, angles)

    def calculate_burn_through_range(self,
                                      js_threshold_db: float = 0.0,
                                      off_boresight_deg: float = 0.0) -> float:
        """
        Calculate the burn-through range where J/S equals threshold.

        At burn-through, the radar can "burn through" the jamming.
        This occurs at CLOSER ranges where the radar return is strong.

        J/S increases with range (jammer: R^-2, radar: R^-4), so
        burn-through happens at the minimum range where jamming is effective.

        Args:
            js_threshold_db: J/S threshold for burn-through (typically 0 dB)
            off_boresight_deg: Off-boresight angle

        Returns:
            Burn-through range in km (range where J/S = threshold)
        """
        # Binary search for range where J/S = threshold
        # At close range, J/S is negative (radar wins)
        # At far range, J/S is positive (jammer wins)
        r_min, r_max = 1000, 500000  # 1 km to 500 km

        for _ in range(50):  # Bisection iterations
            r_mid = (r_min + r_max) / 2
            result = self.analyze(r_mid, off_boresight_deg)

            if result.js_ratio_db < js_threshold_db:
                r_min = r_mid  # J/S too low, increase range
            else:
                r_max = r_mid  # J/S above threshold, decrease range

        return r_mid / 1000  # Return in km


def load_jammer_from_system_config() -> JammerConfig:
    """Load jammer configuration from system_config.yaml TX paths."""
    from pathlib import Path
    import yaml

    config_path = Path(__file__).parent.parent / "system_config" / "system_config.yaml"

    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    # Get the primary TX path (tx_2_18ghz)
    tx_paths = data.get('rf_chains', {}).get('tx_paths', {})

    # Look for primary TX or first TX path
    tx_config = tx_paths.get('tx_2_18ghz', tx_paths.get('tx_low_band', {}))

    # Extract antenna beamwidth from components
    beamwidth = 30.0  # Default
    for component in tx_config.get('components', []):
        if 'beamwidth_deg' in component:
            beamwidth = float(component['beamwidth_deg'])
            break

    # Find antenna gain from components
    antenna_gain = 0.0
    for component in tx_config.get('components', []):
        if component.get('type') in ['horn', 'omni', 'antenna']:
            antenna_gain = float(component.get('gain_db', 0))
            break

    # Get frequency from system config
    freq_config = data.get('frequency', {})
    freq_ghz = float(freq_config.get('reference_ghz', 10.0))

    return JammerConfig(
        input_power_dbm=tx_config.get('source_power_dbm', 0) + tx_config.get('total_gain_db', 45) - antenna_gain,
        antenna_gain_dbi=antenna_gain,
        beamwidth_deg=beamwidth,
        pattern_type='gaussian',
        frequency_ghz=freq_ghz
    )


def analyze_jamming_standalone(range_km: float = 50.0,
                                off_boresight_deg: float = 0.0,
                                jammer: Optional[JammerConfig] = None,
                                emitter: Optional[EmitterConfig] = None) -> JammingResult:
    """
    Convenience function for quick jamming analysis.

    Args:
        range_km: Range to target in km
        off_boresight_deg: Off-boresight angle in degrees
        jammer: Jammer configuration (uses defaults if None)
        emitter: Emitter configuration (uses defaults if None)

    Returns:
        JammingResult with analysis
    """
    if jammer is None:
        try:
            jammer = load_jammer_from_system_config()
        except Exception:
            jammer = JammerConfig()

    if emitter is None:
        emitter = EmitterConfig()

    analyzer = JammingAnalyzer(jammer, emitter)
    return analyzer.analyze(range_km * 1000, off_boresight_deg)


if __name__ == "__main__":
    # Demo analysis
    print("Jamming Analysis Demo")
    print("=" * 60)
    print()

    # Create configurations matching MATLAB reference
    jammer = JammerConfig(
        input_power_dbm=50,  # 100W
        antenna_gain_dbi=20,
        beamwidth_deg=30,
        pattern_type='gaussian',
        frequency_ghz=6.0
    )

    emitter = EmitterConfig(
        power_dbw=60,  # 1 MW
        antenna_gain_dbi=35,
        frequency_ghz=6.0,
        target_rcs_m2=2.0
    )

    print("Jammer Configuration:")
    print(f"  Input power: {jammer.input_power_dbm} dBm ({jammer.input_power_watts:.0f} W)")
    print(f"  Peak antenna gain: {jammer.antenna_gain_dbi} dBi")
    print(f"  Beamwidth: {jammer.beamwidth_deg}°")
    print(f"  Peak EIRP: {jammer.eirp_peak_dbm:.1f} dBm ({jammer.eirp_peak_watts:.0f} W)")
    print()

    print("Emitter Configuration:")
    print(f"  Power: {emitter.power_dbw} dBW ({emitter.power_watts/1e6:.1f} MW)")
    print(f"  Antenna gain: {emitter.antenna_gain_dbi} dBi")
    print(f"  Target RCS: {emitter.target_rcs_m2} m² ({emitter.target_rcs_dbsm:.1f} dBsm)")
    print()

    analyzer = JammingAnalyzer(jammer, emitter)

    # Single point analysis
    print("Single Point Analysis (50 km, on-boresight):")
    result = analyzer.analyze(50000, 0)
    result.print_summary()
    print()

    # Burn-through range
    bt_range = analyzer.calculate_burn_through_range(js_threshold_db=0)
    print(f"Burn-through range (J/S = 0 dB): {bt_range:.1f} km")
