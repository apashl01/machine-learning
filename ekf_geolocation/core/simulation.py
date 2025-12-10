"""
Main Simulation Module

Orchestrates the complete EKF geolocation simulation including:
- Configuration loading
- Trajectory generation
- Signal propagation calculation
- Interferometer measurement generation
- Optional parameter sweep
- EKF execution

Matches MATLAB demo/main_simulation.m functionality.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Tuple
import itertools

from ..utils.coordinates import lla_to_ecef, ecef_to_lla
from .trajectory import generate_trajectory, TrajectoryData
from .signal_propagation import calculate_signal_propagation, SignalData
from .interferometer import interferometer_model, InterferometerData
from .ekf import run_ekf, EKFResult


@dataclass
class JammingAnalysisResult:
    """Container for trajectory jamming analysis results."""
    js_ratio_db: np.ndarray           # J/S ratio at each time step (dB)
    jammer_power_dbw: np.ndarray      # Jammer power at radar (dBW)
    signal_power_dbw: np.ndarray      # Signal power at radar (dBW)
    off_boresight_deg: np.ndarray     # Off-boresight angle at each step (degrees)
    burn_through_mask: np.ndarray     # Boolean mask where J/S < 0 (radar burns through)

    @property
    def mean_js_db(self) -> float:
        """Mean J/S ratio."""
        return float(np.mean(self.js_ratio_db))

    @property
    def min_js_db(self) -> float:
        """Minimum J/S ratio (worst case)."""
        return float(np.min(self.js_ratio_db))

    @property
    def pct_effective(self) -> float:
        """Percentage of time with effective jamming (J/S > 0 dB)."""
        return 100.0 * np.sum(self.js_ratio_db > 0) / len(self.js_ratio_db)


@dataclass
class SimulationResult:
    """Container for complete simulation results."""
    config: object                    # SimulationConfig
    trajectory: TrajectoryData        # Trajectory data
    signal_data: SignalData           # Signal propagation data
    interferometer_data: InterferometerData  # Interferometer measurements
    ekf_result: EKFResult             # EKF estimation results
    position_errors: np.ndarray       # Position errors (meters) [N_steps]
    estimated_lla: np.ndarray         # Estimated position in LLA [N_steps x 3]

    # Phase 2: Jamming analysis (optional)
    jamming_result: Optional[JammingAnalysisResult] = None

    @property
    def final_error(self) -> float:
        """Final position error in meters."""
        return float(self.position_errors[-1])

    @property
    def final_uncertainty(self) -> float:
        """Final 1-sigma uncertainty in meters."""
        return float(np.sqrt(np.sum(self.ekf_result.P_history[-1])))

    def print_summary(self):
        """Print simulation results summary."""
        final_lla = self.estimated_lla[-1]
        print("\n" + "=" * 60)
        print("SIMULATION RESULTS")
        print("=" * 60)
        print(f"\nFinal Results:")
        print(f"  Position error: {self.final_error:.2f} m")
        print(f"  Position uncertainty (1-sigma): {self.final_uncertainty:.2f} m")
        print(f"  Final estimate: Lat={final_lla[0]:.6f} deg, "
              f"Lon={final_lla[1]:.6f} deg, Alt={final_lla[2]:.2f} m")
        print(f"\nTrue emitter position:")
        print(f"  Lat={self.config.emitter.lat:.6f} deg, "
              f"Lon={self.config.emitter.lon:.6f} deg, "
              f"Alt={self.config.emitter.alt:.2f} m")

        # Jamming analysis summary (if available)
        if self.jamming_result is not None:
            print(f"\nSelf-Protect Jamming Analysis:")
            print(f"  Mean J/S: {self.jamming_result.mean_js_db:.1f} dB")
            print(f"  Min J/S: {self.jamming_result.min_js_db:.1f} dB")
            print(f"  Effective jamming: {self.jamming_result.pct_effective:.1f}% of trajectory")


@dataclass
class SweepResult:
    """Container for parameter sweep result."""
    Q: float
    P0: float
    R_scale: float
    final_error: float
    mean_error: float
    convergence_time: float


def calculate_trajectory_jamming(
    config,
    trajectory: TrajectoryData,
    print_progress: bool = True
) -> Optional[JammingAnalysisResult]:
    """
    Calculate self-protect jamming effectiveness over trajectory.

    Computes J/S ratio at each time step based on:
    - Range from platform to emitter (treated as radar)
    - Off-boresight angle of jammer antenna relative to emitter

    Args:
        config: SimulationConfig object
        trajectory: TrajectoryData with platform positions
        print_progress: Whether to print progress messages

    Returns:
        JammingAnalysisResult or None if jamming module unavailable
    """
    try:
        from jamming_analysis import JammerConfig, RadarConfig, JammingAnalyzer
    except ImportError:
        if print_progress:
            print("  Jamming analysis skipped (module not available)")
        return None

    if print_progress:
        print("Calculating trajectory jamming effectiveness...")

    # Get ranges to emitter (km -> m)
    ranges_m = trajectory.distances_from_emitter * 1000.0

    # Calculate off-boresight angles
    # The jammer antenna points forward (along platform boresight)
    # Off-boresight = angle between platform boresight and direction to emitter

    # Get emitter position in ECEF
    emitter_ecef = lla_to_ecef(config.emitter.lat, config.emitter.lon, config.emitter.alt)

    n_steps = len(ranges_m)
    off_boresight_deg = np.zeros(n_steps)

    for k in range(n_steps):
        # Vector from platform to emitter
        platform_pos = trajectory.platform_ecef_cg[k]
        to_emitter = emitter_ecef - platform_pos
        to_emitter_norm = to_emitter / (np.linalg.norm(to_emitter) + 1e-10)

        # Platform boresight (forward direction)
        boresight = trajectory.boresight_ecef[k]
        boresight_norm = boresight / (np.linalg.norm(boresight) + 1e-10)

        # Angle between boresight and direction to emitter
        cos_angle = np.clip(np.dot(boresight_norm, to_emitter_norm), -1.0, 1.0)
        off_boresight_deg[k] = np.degrees(np.arccos(cos_angle))

    # Load jammer config from system_config or use defaults
    try:
        from jamming_analysis.core import load_jammer_from_system_config
        jammer = load_jammer_from_system_config()
        if print_progress:
            print("  Loaded jammer config from system_config")
    except Exception:
        jammer = JammerConfig(
            input_power_dbm=50.0,
            antenna_gain_dbi=12.0,
            beamwidth_deg=30.0,
            frequency_ghz=config.emitter.frequency_ghz,
            platform_rcs_m2=2.0
        )
        if print_progress:
            print("  Using default jammer config")

    # Create radar config from emitter
    radar = RadarConfig(
        power_dbw=60.0,  # 1 MW default radar
        antenna_gain_dbi=35.0,
        frequency_ghz=config.emitter.frequency_ghz
    )

    # Run analysis
    analyzer = JammingAnalyzer(jammer, radar)
    result = analyzer.analyze(ranges_m, off_boresight_deg)

    jamming_result = JammingAnalysisResult(
        js_ratio_db=result.js_ratio_db,
        jammer_power_dbw=result.jammer_power_at_radar_dbw,
        signal_power_dbw=result.signal_power_at_radar_dbw,
        off_boresight_deg=off_boresight_deg,
        burn_through_mask=result.js_ratio_db < 0
    )

    if print_progress:
        print(f"  J/S range: {jamming_result.min_js_db:.1f} to "
              f"{np.max(jamming_result.js_ratio_db):.1f} dB")
        print(f"  Effective jamming: {jamming_result.pct_effective:.1f}% of trajectory")

    return jamming_result


def run_simulation(config, print_progress: bool = True,
                   include_jamming: bool = True) -> SimulationResult:
    """
    Run complete EKF geolocation simulation.

    Args:
        config: SimulationConfig object
        print_progress: Whether to print progress messages
        include_jamming: Whether to include jamming analysis (Phase 2)

    Returns:
        SimulationResult object with all data
    """
    if print_progress:
        config.print_summary()

    # Step 1: Generate trajectory
    trajectory = generate_trajectory(config)

    # Step 2: Calculate signal propagation
    signal_data = calculate_signal_propagation(config, trajectory)

    # Step 3: Generate interferometer measurements
    interferometer_data = interferometer_model(config, trajectory, signal_data)

    # Step 4: Run parameter sweep if enabled
    if config.parameter_sweep.enabled:
        if print_progress:
            print("\nRunning parameter sweep...")
        best_params = run_parameter_sweep(
            config, interferometer_data.measurements,
            trajectory, interferometer_data,
            print_progress=print_progress
        )
        config.ekf.best_Q = best_params[0]
        config.ekf.best_P0 = best_params[1]
        config.ekf.best_R_scale = best_params[2]

    # Step 5: Run EKF with best parameters
    if print_progress:
        print(f"\nRunning EKF with parameters: Q={config.ekf.best_Q}, "
              f"P0={config.ekf.best_P0}, R_scale={config.ekf.best_R_scale}")

    ekf_result = run_ekf(config, interferometer_data.measurements,
                         trajectory, interferometer_data)

    # Calculate errors
    emitter_ecef = lla_to_ecef(config.emitter.lat, config.emitter.lon,
                               config.emitter.alt)
    position_errors = np.zeros(config.n_steps)
    estimated_lla = np.zeros((config.n_steps, 3))

    for k in range(config.n_steps):
        position_errors[k] = np.linalg.norm(ekf_result.x_history[k] - emitter_ecef)
        estimated_lla[k] = ecef_to_lla(ekf_result.x_history[k])

    # Step 6: Calculate jamming effectiveness over trajectory (Phase 2)
    jamming_result = None
    if include_jamming:
        jamming_result = calculate_trajectory_jamming(config, trajectory, print_progress)

    result = SimulationResult(
        config=config,
        trajectory=trajectory,
        signal_data=signal_data,
        interferometer_data=interferometer_data,
        ekf_result=ekf_result,
        position_errors=position_errors,
        estimated_lla=estimated_lla,
        jamming_result=jamming_result
    )

    if print_progress:
        result.print_summary()

    return result


def run_parameter_sweep(config, measurements: np.ndarray,
                       trajectory: TrajectoryData,
                       interferometer_data: InterferometerData,
                       print_progress: bool = True) -> Tuple[float, float, float]:
    """
    Run parameter sweep to find optimal EKF parameters.

    Args:
        config: SimulationConfig object
        measurements: Angle measurements (radians)
        trajectory: TrajectoryData object
        interferometer_data: InterferometerData object
        print_progress: Whether to print progress

    Returns:
        Tuple of (best_Q, best_P0, best_R_scale)
    """
    Q_values = config.parameter_sweep.Q_values
    P0_values = config.parameter_sweep.P0_values
    R_scale_values = config.parameter_sweep.R_scale_values

    n_combinations = len(Q_values) * len(P0_values) * len(R_scale_values)
    results: List[SweepResult] = []

    emitter_ecef = lla_to_ecef(config.emitter.lat, config.emitter.lon,
                               config.emitter.alt)

    if print_progress:
        print(f"  Total combinations: {n_combinations}")
        print("  Progress: ", end="", flush=True)

    result_idx = 0
    for Q, P0, R_scale in itertools.product(Q_values, P0_values, R_scale_values):
        result_idx += 1

        if print_progress and result_idx % 10 == 0:
            print(f"{result_idx}/{n_combinations} ", end="", flush=True)

        # Temporarily set parameters
        config.ekf.best_Q = Q
        config.ekf.best_P0 = P0
        config.ekf.best_R_scale = R_scale

        # Run EKF
        ekf_result = run_ekf(config, measurements, trajectory, interferometer_data)

        # Calculate errors
        position_errors = np.linalg.norm(
            ekf_result.x_history - emitter_ecef, axis=1
        )

        final_error = position_errors[-1]
        mean_error = np.mean(position_errors[len(position_errors)//2:])

        # Find convergence time (when error first drops below 500m)
        convergence_idx = np.where(position_errors < 500)[0]
        if len(convergence_idx) > 0:
            convergence_time = config.time[convergence_idx[0]]
        else:
            convergence_time = np.inf

        results.append(SweepResult(
            Q=Q,
            P0=P0,
            R_scale=R_scale,
            final_error=final_error,
            mean_error=mean_error,
            convergence_time=convergence_time
        ))

    if print_progress:
        print("\n  Parameter sweep complete!")

    # Find best parameters using composite score
    final_errors = np.array([r.final_error for r in results])
    mean_errors = np.array([r.mean_error for r in results])
    convergence_times = np.array([r.convergence_time for r in results])

    # Handle inf values in convergence times
    finite_conv = convergence_times[np.isfinite(convergence_times)]
    if len(finite_conv) > 0:
        max_conv = np.max(finite_conv) * 2
        convergence_times = np.where(np.isinf(convergence_times),
                                    max_conv, convergence_times)

    # Normalize to [0, 1] range
    def normalize(arr):
        arr_min, arr_max = np.min(arr), np.max(arr)
        if arr_max > arr_min:
            return (arr - arr_min) / (arr_max - arr_min)
        return np.zeros_like(arr)

    composite_score = (normalize(final_errors) * 0.4 +
                      normalize(mean_errors) * 0.3 +
                      normalize(convergence_times) * 0.3)

    best_idx = np.argmin(composite_score)
    best = results[best_idx]

    if print_progress:
        print(f"\n  BEST PARAMETERS (Composite Score):")
        print(f"    Q = {best.Q:.4f}, P0 = {best.P0:.0f}, R_scale = {best.R_scale:.2f}")
        print(f"    Final error: {best.final_error:.2f} m")
        print(f"    Convergence time: {best.convergence_time:.1f} s")

    return best.Q, best.P0, best.R_scale
