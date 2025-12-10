"""
EKF Geolocation Analysis slide generator.
"""

from typing import Dict, Optional
from pathlib import Path
from ..core import DesignReviewGenerator


def add_ekf_geolocation_slides(gen: DesignReviewGenerator,
                                config: Optional[Dict] = None,
                                results: Optional[Dict] = None,
                                output_dir: Optional[str] = None):
    """
    Add EKF Geolocation Analysis slides.

    Args:
        gen: DesignReviewGenerator instance
        config: Simulation configuration dict
        results: Simulation results dict
        output_dir: Directory containing output plots
    """
    gen.add_section_slide("EKF Geolocation Analysis",
                          "Emitter Localization Performance")

    # Scenario overview
    if config:
        scenario_bullets = []

        # Emitter
        if 'emitter' in config:
            em = config['emitter']
            scenario_bullets.append(
                f"Emitter: {em.get('lat', 'N/A')} deg N, {em.get('lon', 'N/A')} deg E, "
                f"{em.get('alt', 'N/A')} m alt"
            )
            if 'eirp_dbw' in em:
                scenario_bullets.append(f"Emitter EIRP: {em['eirp_dbw']} dBW")
            if 'frequency_ghz' in em:
                scenario_bullets.append(f"Frequency: {em['frequency_ghz']} GHz")

        # Trajectory
        if 'trajectory' in config:
            traj = config['trajectory']
            scenario_bullets.append(f"Trajectory Type: {traj.get('type', 'N/A')}")
            if 'standoff_distance_km' in traj:
                scenario_bullets.append(f"Standoff Distance: {traj['standoff_distance_km']} km")
            if 'altitude_mean' in traj:
                scenario_bullets.append(f"Altitude: {traj['altitude_mean']} m")

        if scenario_bullets:
            gen.add_content_slide(
                "Scenario Configuration",
                bullets=scenario_bullets
            )

    # Interferometer config
    if config and 'interferometer' in config:
        interf = config['interferometer']
        interf_bullets = [
            f"Elements: {interf.get('n_elements', 4)}",
            f"Max Baseline: {interf.get('max_baseline', 'N/A')} inches",
            f"Phase Error (high SNR): {interf.get('phase_error_deg', 12)} deg",
            f"Max Incident Angle: {interf.get('max_incident_angle_deg', 70)} deg",
        ]
        if 'element_positions' in interf:
            positions = interf['element_positions']
            interf_bullets.append(
                f"Positions: [{', '.join(f'{p:.2f}' for p in positions)}] in"
            )

        gen.add_content_slide(
            "Interferometer Configuration",
            bullets=interf_bullets
        )

    # EKF parameters
    if config and 'ekf' in config:
        ekf = config['ekf']
        ekf_bullets = [
            f"Initial Offset: {ekf.get('initial_offset_km', 5)} km",
            f"Process Noise (Q): {ekf.get('Q', 0.01)}",
            f"Initial Covariance (P0): {ekf.get('P0', 10000)}",
            f"Measurement Scale (R): {ekf.get('R_scale', 1.0)}",
        ]
        gen.add_content_slide(
            "EKF Tuning Parameters",
            bullets=ekf_bullets
        )

    # Results metrics
    if results:
        metrics = {}
        if 'final_error_m' in results:
            metrics['Final Error'] = f"{results['final_error_m']:.1f} m"
        if 'final_uncertainty_m' in results:
            metrics['1-sigma Uncertainty'] = f"{results['final_uncertainty_m']:.1f} m"
        if 'convergence_time_s' in results:
            metrics['Convergence Time'] = f"{results['convergence_time_s']:.0f} s"
        if 'valid_measurements_pct' in results:
            metrics['Valid Measurements'] = f"{results['valid_measurements_pct']:.1f}%"

        if metrics:
            gen.add_metrics_slide("Geolocation Performance", metrics)

    # Final position
    if results and 'final_estimate' in results:
        est = results['final_estimate']
        true = results.get('true_position', {})

        headers = ["Parameter", "True Value", "Estimated", "Error"]
        rows = [
            ["Latitude (deg)", f"{true.get('lat', 'N/A'):.6f}",
             f"{est.get('lat', 'N/A'):.6f}",
             f"{(est.get('lat', 0) - true.get('lat', 0)) * 111000:.1f} m"],
            ["Longitude (deg)", f"{true.get('lon', 'N/A'):.6f}",
             f"{est.get('lon', 'N/A'):.6f}",
             f"{(est.get('lon', 0) - true.get('lon', 0)) * 111000:.1f} m"],
            ["Altitude (m)", f"{true.get('alt', 'N/A'):.1f}",
             f"{est.get('alt', 'N/A'):.1f}",
             f"{est.get('alt', 0) - true.get('alt', 0):.1f} m"],
        ]
        gen.add_table_slide("Position Estimate Comparison", headers, rows)

    # Plots
    if output_dir:
        output_path = Path(output_dir)

        # Trajectory and error
        traj_plot = output_path / "ekf_trajectory_error.png"
        if traj_plot.exists():
            gen.add_content_slide(
                "Trajectory & Estimation Error",
                image_path=str(traj_plot),
                image_width=11.0
            )

        # Component errors
        comp_plot = output_path / "ekf_component_errors.png"
        if comp_plot.exists():
            gen.add_content_slide(
                "Position Component Errors",
                image_path=str(comp_plot),
                image_width=11.0
            )

        # Interferometer performance
        interf_plot = output_path / "ekf_interferometer_performance.png"
        if interf_plot.exists():
            gen.add_content_slide(
                "Interferometer Performance",
                image_path=str(interf_plot),
                image_width=11.0
            )

        # Jamming analysis (Phase 2 Enhancement)
        jamming_plot = output_path / "ekf_jamming_analysis.png"
        if jamming_plot.exists():
            gen.add_content_slide(
                "Self-Protect Jamming Analysis",
                image_path=str(jamming_plot),
                image_width=11.0
            )

    # Jamming metrics (Phase 2 Enhancement)
    if results and 'jamming' in results:
        jam = results['jamming']
        jam_metrics = {}
        if 'mean_js_db' in jam:
            jam_metrics['Mean J/S Ratio'] = f"{jam['mean_js_db']:.1f} dB"
        if 'min_js_db' in jam:
            jam_metrics['Minimum J/S'] = f"{jam['min_js_db']:.1f} dB"
        if 'effective_pct' in jam:
            jam_metrics['Effective Jamming'] = f"{jam['effective_pct']:.0f}% of trajectory"

        if jam_metrics:
            gen.add_metrics_slide("Trajectory Jamming Performance", jam_metrics)
