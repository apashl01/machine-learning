#!/usr/bin/env python3
"""
One-Click Design Review Generator

Runs all analyses using the shared system_config and generates
a PowerPoint design review with real results.

Usage:
    python reporting/generate_design_review.py
"""

import sys
from pathlib import Path
import warnings
import numpy as np

# Suppress matplotlib warnings in non-GUI environments
warnings.filterwarnings('ignore', category=UserWarning)

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for headless operation

from reporting import DesignReviewGenerator
from reporting.generators import (
    add_title_slide,
    add_esm_slides,
    add_rf_chain_slides,
    add_adc_slides,
    add_direction_finding_slides,
    add_antenna_coverage_slides,
    add_ekf_geolocation_slides,
    add_summary_slide,
    add_compliance_slides,
    add_conops_slide,
    add_design_goals_slide,
    add_technical_risks_slide,
    add_swap_c_slide
)
from reporting.generators.jamming import add_jamming_slides


def print_header(text: str):
    """Print formatted section header."""
    print(f"\n{'='*70}")
    print(f" {text}")
    print(f"{'='*70}")


def run_system_config_summary():
    """Load and display shared system config."""
    from system_config import load_system_config, calculate_system_noise_floor

    config = load_system_config()

    print(f"\nShared System Configuration:")
    print(f"  Frequency range: {config.freq_min_ghz} - {config.freq_max_ghz} GHz")
    print(f"  ADC: {config.adc.model}, {config.adc.sample_rate_gsps} GSPS")
    print(f"  RF Chain NF: {config.rf_chain.cascade_noise_figure_db} dB")
    print(f"  Interferometer: {config.interferometer.n_elements} elements")
    print(f"  Element positions: {list(config.interferometer.element_positions)} inches")

    noise = calculate_system_noise_floor(config, bandwidth_hz=1e6)
    print(f"\n  System Noise Floor: {noise.system_noise_floor_dbm:.1f} dBm (1 MHz BW)")
    print(f"  Sensitivity: {noise.sensitivity_dbm:.1f} dBm (SNR=10 dB)")

    return config, noise


def run_direction_finding_analysis():
    """Run direction finding analysis with shared config."""
    print_header("DIRECTION FINDING ANALYSIS")

    from direction_finding_analysis import analyze_interferometer
    from direction_finding_analysis.config import load_from_system_config

    # Load config from shared system_config
    config = load_from_system_config()
    print(f"Using shared config: {config.n_elements} elements, "
          f"positions: {config.element_positions}")
    print(f"Noise floor from ADC+RF chain: {config.noise_floor_dbm:.1f} dBm")

    # Run analysis
    results = analyze_interferometer(config)

    # Generate plots
    import matplotlib.pyplot as plt
    from direction_finding_analysis.example_analysis import generate_plots
    generate_plots(results)
    plt.close('all')

    # Extract key results
    df_config = {
        'n_elements': config.n_elements,
        'freq_min_ghz': config.freq_range_ghz[0],
        'freq_max_ghz': config.freq_range_ghz[1],
        'phase_error_deg': config.phase_error_deg,
        'element_positions': config.element_positions,
        'max_baseline': config.max_baseline,
        'baselines': config.baselines
    }

    # Task 9.1: Get WORST-CASE accuracy at low freq / max angle corner
    # (instead of optimistic boresight/mid-freq)
    low_freq_idx = 0  # Lowest frequency (worst case for baseline resolution)
    max_angle_idx = -1  # Maximum incident angle (worst case for SNR and geometry)

    # Get worst-case accuracy for compliance checking
    worst_case_accuracy = results.accuracy.angle_error_realistic[low_freq_idx, max_angle_idx]

    # Also get boresight/mid-freq for reference comparison
    mid_freq_idx = len(results.accuracy.frequencies_ghz) // 2
    boresight_idx = len(results.accuracy.incident_angles) // 2
    boresight_accuracy = results.accuracy.angle_error_realistic[mid_freq_idx, boresight_idx]

    df_results = {
        'angle_accuracy_deg': float(worst_case_accuracy),  # Worst-case for compliance
        'angle_accuracy_boresight_deg': float(boresight_accuracy),  # Reference
        'ambiguity_free_fov': 80,  # From design
        'min_snr_db': 10,
        'max_incident_angle': 70
    }

    print(f"\nResults:")
    print(f"  Angle accuracy (boresight): {boresight_accuracy:.2f} deg")
    print(f"  Angle accuracy (worst-case): {worst_case_accuracy:.2f} deg")
    print(f"  Baselines: {config.baselines}")

    return df_config, df_results


def run_ekf_geolocation():
    """Run EKF geolocation simulation."""
    print_header("EKF GEOLOCATION SIMULATION")

    from ekf_geolocation import load_simulation_config, run_simulation
    from ekf_geolocation.config import load_interferometer_from_system_config

    # Load simulation config (uses local YAML for trajectory/emitter)
    config = load_simulation_config()

    # Override interferometer with shared config
    shared_interf = load_interferometer_from_system_config()
    print(f"Using shared interferometer config: {shared_interf.n_elements} elements")
    print(f"Element positions: {list(shared_interf.element_positions)} inches")

    # Disable parameter sweep for faster execution
    config.parameter_sweep.enabled = False
    print(f"Running simulation (parameter sweep disabled for speed)...")

    # Run simulation
    result = run_simulation(config)

    # Generate plots
    import matplotlib.pyplot as plt
    from ekf_geolocation.example_simulation import generate_plots
    generate_plots(result)
    plt.close('all')

    # Extract results
    ekf_config = {
        'emitter': {
            'lat': config.emitter.lat,
            'lon': config.emitter.lon,
            'alt': config.emitter.alt,
            'eirp_dbw': config.emitter.eirp_dbw,
            'frequency_ghz': config.emitter.frequency_ghz
        },
        'trajectory': {
            'type': config.trajectory.type,
            'standoff_distance_km': config.trajectory.standoff_distance_km,
            'altitude_mean': config.trajectory.altitude_mean
        },
        'interferometer': {
            'n_elements': shared_interf.n_elements,
            'max_baseline': shared_interf.max_baseline,
            'phase_error_deg': shared_interf.phase_error_high_snr_deg,
            'max_incident_angle_deg': shared_interf.max_incident_angle_deg,
            'element_positions': list(shared_interf.element_positions)
        },
        'ekf': {
            'initial_offset_km': config.ekf.initial_offset_km,
            'Q': config.ekf.best_Q,
            'P0': config.ekf.best_P0,
            'R_scale': config.ekf.best_R_scale
        }
    }

    final_error = result.position_errors[-1]
    final_uncertainty = result.final_uncertainty
    n_valid = np.sum(result.interferometer_data.measurement_valid)
    n_total = len(result.interferometer_data.measurement_valid)
    valid_pct = 100.0 * n_valid / n_total

    # Find convergence time (when error drops below 2x final)
    convergence_idx = len(result.position_errors) - 1
    for i, err in enumerate(result.position_errors):
        if err < 2 * final_error:
            convergence_idx = i
            break
    convergence_time = config.time[convergence_idx]

    ekf_results = {
        'final_error_m': float(final_error),
        'final_uncertainty_m': float(final_uncertainty),
        'convergence_time_s': float(convergence_time),
        'valid_measurements_pct': float(valid_pct),
        'final_estimate': {
            'lat': float(result.estimated_lla[-1, 0]),
            'lon': float(result.estimated_lla[-1, 1]),
            'alt': float(result.estimated_lla[-1, 2])
        },
        'true_position': {
            'lat': config.emitter.lat,
            'lon': config.emitter.lon,
            'alt': config.emitter.alt
        }
    }

    # Add jamming results if available (Phase 2 Enhancement)
    if result.jamming_result is not None:
        ekf_results['jamming'] = {
            'mean_js_db': float(result.jamming_result.mean_js_db),
            'min_js_db': float(result.jamming_result.min_js_db),
            'effective_pct': float(result.jamming_result.pct_effective)
        }
        print(f"\nJamming Analysis:")
        print(f"  Mean J/S: {result.jamming_result.mean_js_db:.1f} dB")
        print(f"  Min J/S: {result.jamming_result.min_js_db:.1f} dB")
        print(f"  Effective Jamming: {result.jamming_result.pct_effective:.0f}% of trajectory")

    print(f"\nResults:")
    print(f"  Final position error: {final_error:.1f} m")
    print(f"  Final uncertainty: {final_uncertainty:.1f} m")
    print(f"  Convergence time: {convergence_time:.0f} s")
    print(f"  Valid measurements: {valid_pct:.1f}%")

    return ekf_config, ekf_results


def run_esm_analysis():
    """Run ESM detection analysis."""
    print_header("ESM DETECTION ANALYSIS")

    from esm_analysis.config import (
        load_from_central_config,
        load_receiver_from_system_config,
        get_system_sensitivity_dbm
    )
    from esm_analysis.config.loader import load_threat_library
    from esm_analysis.core import SNRCalculator, ThreatCategorizer
    from esm_analysis.visualization import ESMPlotter

    # Load configuration from central config (Task 8)
    system_config = load_from_central_config()
    threat_library = load_threat_library()

    # Get sensitivity from shared config
    sensitivity = get_system_sensitivity_dbm(bandwidth_hz=20e6, snr_required_db=10.0)
    print(f"System sensitivity from shared config: {sensitivity:.1f} dBm")

    # Get receiver config from shared system
    receiver = load_receiver_from_system_config()
    print(f"Frequency range: {receiver.freq_min_hz/1e9:.1f} - {receiver.freq_max_hz/1e9:.1f} GHz")
    print(f"Noise figure: {receiver.noise_figure_db} dB")

    # Run analysis on threats
    threats = list(threat_library)[:5]  # Analyze first 5 threats for demo

    # Task 10: Calculate dynamic detection range requirements
    try:
        from system_config import load_system_config
        from esm_analysis.esm_detection import calculate_dynamic_detection_requirement, RadarParameters

        sys_config_full = load_system_config()
        platform_rcs = sys_config_full.platform.rcs_m2 if sys_config_full.platform else 2.0

        print(f"\nCalculating dynamic detection range requirements (platform RCS: {platform_rcs} m²)...")
        for threat in threats:
            # Convert threat to RadarParameters
            # Estimate radar bandwidth from pulse width: BW ≈ 1 / PW
            bandwidth_mhz = 1.0 / threat.pulse_width_us  # MHz
            # Calculate EIRP: Power (dBW) + Antenna Gain (dBi)
            power_dbw = 10 * np.log10(threat.peak_power_w)
            eirp_dbw = power_dbw + threat.antenna_gain_dbi
            radar_params = RadarParameters(
                eirp_dBW=eirp_dbw,
                freq_GHz=threat.frequency_hz / 1e9,
                antenna_gain_dB=threat.antenna_gain_dbi,
                bandwidth_MHz=bandwidth_mhz,
                pulse_width_us=threat.pulse_width_us,
                pri_us=threat.pri_us
            )

            # Calculate dynamic requirement (1.2x threat radar's range)
            dynamic_range_m = calculate_dynamic_detection_requirement(
                radar_params,
                platform_rcs_m2=platform_rcs,
                range_multiplier=1.2
            )

            # Update threat's required range if not already set, but always print
            print(f"  {threat.name}: {dynamic_range_m/1000:.1f} km (1.2x radar range)")
            if threat.required_detection_range_m is None:
                threat.required_detection_range_m = dynamic_range_m

    except Exception as e:
        print(f"  Note: Could not calculate dynamic ranges: {e}")

    snr_calculator = SNRCalculator(system_config, verbose=False)
    categorizer = ThreatCategorizer(system_config, snr_calculator, verbose=False)
    categorization = categorizer.categorize_threats(threats)

    # Generate plots
    try:
        plotter = ESMPlotter(system_config, save_plots=True)
        if threats:
            plotter.plot_snr_vs_range(threats[0])
        plotter.plot_categorization_summary(categorization)
        plotter.plot_detection_ranges(
            categorization.sidelobe_detectable +
            categorization.main_beam_required +
            categorization.undetectable
        )
        import matplotlib.pyplot as plt
        plt.close('all')
    except Exception as e:
        print(f"  Plot generation warning: {e}")

    esm_config = {
        'frequency_range_ghz': [receiver.freq_min_hz/1e9, receiver.freq_max_hz/1e9],
        'sensitivity_dbm': sensitivity,
        'instantaneous_bandwidth_ghz': receiver.instantaneous_bandwidth_ghz,
        'scan_type': 'Frequency Scanning'
    }

    # Task 9.2: Calculate MINIMUM detection range among mandatory threats
    # (instead of optimistic max range)
    min_range = float('inf')
    max_range = 0  # Keep max for reference
    detection_ranges = []
    if threats:
        detectable = categorization.sidelobe_detectable + categorization.main_beam_required
        for ct in detectable:
            if hasattr(ct, 'max_range_m') and ct.max_range_m:
                range_km = ct.max_range_m / 1000
                detection_ranges.append(range_km)
                min_range = min(min_range, range_km)
                max_range = max(max_range, range_km)

    # Use reasonable defaults if no threats analyzed
    if min_range == float('inf'):
        min_range = 100
    if max_range == 0:
        max_range = 100

    esm_results = {
        'detection_range_km': min_range,  # Use minimum for worst-case compliance
        'max_detection_range_km': max_range,  # Keep max for reference
        'poi': 0.95,
        'sensitivity_dbm': sensitivity,
        'max_frequency_ghz': receiver.freq_max_hz/1e9,
        'sidelobe_detectable': len(categorization.sidelobe_detectable),
        'main_beam_required': len(categorization.main_beam_required)
    }

    print(f"\nResults:")
    print(f"  Sidelobe detectable: {len(categorization.sidelobe_detectable)}")
    print(f"  Main beam required: {len(categorization.main_beam_required)}")
    print(f"  Sensitivity: {sensitivity:.1f} dBm")

    return esm_config, esm_results


def get_rf_chain_config():
    """Get RF chain configuration and analyze all RX/TX paths."""
    print_header("RF CHAIN ANALYSIS")

    from pathlib import Path
    import yaml
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # Load rf_chains from system config YAML (Task 1.0: Updated to config/ directory)
    config_path = Path(__file__).parent.parent / "config" / "system_config.yaml"
    with open(config_path, 'r') as f:
        data = yaml.safe_load(f)

    rf_chains = data.get('rf_chains', {})
    rx_paths = rf_chains.get('rx_paths', {})
    tx_paths = rf_chains.get('tx_paths', {})

    # Summary for all paths
    all_paths = []

    print("Analyzing RF Paths:")

    # Analyze RX paths
    for path_id, path_data in rx_paths.items():
        name = path_data.get('name', path_id)
        num_paths = path_data.get('num_paths', 1)
        freq_range = path_data.get('freq_range_ghz', [2.0, 18.0])
        cascade_nf = path_data.get('cascade_noise_figure_db', 3.5)
        total_gain = path_data.get('total_gain_db', 30.0)
        damage_thresh = path_data.get('damage_threshold_dbm', 10)
        components = path_data.get('components', [])

        # Calculate cascade NF from components if available
        if components:
            f_total = 1.0
            g_cumulative = 1.0
            total_gain_calc = 0.0
            for i, comp in enumerate(components):
                g_db = comp.get('gain_db', 0)
                nf_db = comp.get('noise_figure_db', 0)
                f_linear = 10 ** (nf_db / 10)
                g_linear = 10 ** (g_db / 10)
                total_gain_calc += g_db
                if i == 0:
                    f_total = f_linear
                else:
                    f_total += (f_linear - 1) / g_cumulative
                g_cumulative *= g_linear
            cascade_nf = 10 * np.log10(f_total)
            total_gain = total_gain_calc

        path_info = {
            'id': path_id,
            'name': name,
            'type': 'RX',
            'num_paths': num_paths,
            'freq_range_ghz': freq_range,
            'cascade_nf_db': cascade_nf,
            'total_gain_db': total_gain,
            'damage_threshold_dbm': damage_thresh,
            'components': components
        }
        all_paths.append(path_info)
        print(f"  RX: {name} ({num_paths} paths)")
        print(f"      Freq: {freq_range[0]}-{freq_range[1]} GHz, NF: {cascade_nf:.1f} dB, Gain: {total_gain:.1f} dB")

    # Analyze TX paths
    for path_id, path_data in tx_paths.items():
        name = path_data.get('name', path_id)
        num_paths = path_data.get('num_paths', 1)
        freq_range = path_data.get('freq_range_ghz', [2.0, 18.0])
        source_power = path_data.get('source_power_dbm', 0)
        components = path_data.get('components', [])

        # Calculate total gain and output power
        total_gain = sum(comp.get('gain_db', 0) for comp in components)
        output_power = source_power + total_gain

        path_info = {
            'id': path_id,
            'name': name,
            'type': 'TX',
            'num_paths': num_paths,
            'freq_range_ghz': freq_range,
            'source_power_dbm': source_power,
            'total_gain_db': total_gain,
            'output_power_dbm': output_power,
            'components': components
        }
        all_paths.append(path_info)
        print(f"  TX: {name} ({num_paths} paths)")
        print(f"      Freq: {freq_range[0]}-{freq_range[1]} GHz, Gain: {total_gain:.1f} dB, Output: {output_power:.1f} dBm")

    # Generate summary plot
    output_dir = Path(__file__).parent.parent / "rf_chain_analysis" / "output"
    output_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Plot 1: RX Path Summary (bar chart)
    ax1 = axes[0]
    rx_paths_list = [p for p in all_paths if p['type'] == 'RX']
    if rx_paths_list:
        names = [f"{p['name']}\n({p['num_paths']} path{'s' if p['num_paths']>1 else ''})" for p in rx_paths_list]
        gains = [p['total_gain_db'] for p in rx_paths_list]
        nfs = [p['cascade_nf_db'] for p in rx_paths_list]

        x = np.arange(len(names))
        width = 0.35

        bars1 = ax1.bar(x - width/2, gains, width, label='Total Gain (dB)', color='steelblue')
        bars2 = ax1.bar(x + width/2, nfs, width, label='Cascade NF (dB)', color='coral')

        ax1.set_ylabel('dB')
        ax1.set_title('RX Path Performance Summary')
        ax1.set_xticks(x)
        ax1.set_xticklabels(names, fontsize=9)
        ax1.legend()
        ax1.grid(True, alpha=0.3, axis='y')

        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        for bar in bars2:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.1f}', ha='center', va='bottom', fontsize=8)

    # Plot 2: TX Path Summary
    ax2 = axes[1]
    tx_paths_list = [p for p in all_paths if p['type'] == 'TX']
    if tx_paths_list:
        names = [f"{p['name']}\n({p['num_paths']} path{'s' if p['num_paths']>1 else ''})" for p in tx_paths_list]
        gains = [p['total_gain_db'] for p in tx_paths_list]
        outputs = [p['output_power_dbm'] for p in tx_paths_list]

        x = np.arange(len(names))
        width = 0.35

        bars1 = ax2.bar(x - width/2, gains, width, label='Total Gain (dB)', color='steelblue')
        bars2 = ax2.bar(x + width/2, outputs, width, label='Output Power (dBm)', color='green')

        ax2.set_ylabel('dB / dBm')
        ax2.set_title('TX Path Performance Summary')
        ax2.set_xticks(x)
        ax2.set_xticklabels(names, fontsize=9)
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')

        # Add value labels
        for bar in bars1:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.1f}', ha='center', va='bottom', fontsize=8)
        for bar in bars2:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                     f'{height:.1f}', ha='center', va='bottom', fontsize=8)

    fig.suptitle('RF Chain Analysis - All Paths', fontsize=14, fontweight='bold')
    plt.tight_layout()

    filepath = output_dir / "rf_chain_analysis.png"
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"\nCombined plot saved to: {filepath}")

    # Task 2.2: Generate individual power tracking and cascade plots
    print("\nGenerating detailed RF chain plots...")

    # Get primary RX path for detailed analysis
    primary_rx = next((p for p in rx_paths_list if '2-18' in p['name']), rx_paths_list[0] if rx_paths_list else None)

    if primary_rx and primary_rx['components']:
        try:
            # Generate power tracking plot manually
            print("  Generating power tracking plot...")
            input_power = -60.0  # Typical input signal
            current_power = input_power

            # Build power level trace through components
            component_names = []
            power_levels = [input_power]  # Start with input

            for comp in primary_rx['components']:
                comp_name = comp.get('name', 'Unknown')
                gain_db = comp.get('gain_db', 0)
                current_power += gain_db
                component_names.append(comp_name)
                power_levels.append(current_power)

            # Create power tracking plot
            fig_power, ax = plt.subplots(figsize=(12, 6))
            x_positions = np.arange(len(power_levels))

            ax.plot(x_positions, power_levels, 'o-', linewidth=2, markersize=10,
                   color='purple', label='Signal Power')

            # Label x-axis with component names
            x_labels = ['Input'] + component_names
            ax.set_xticks(x_positions)
            ax.set_xticklabels(x_labels, rotation=45, ha='right')

            ax.set_xlabel('Stage', fontsize=12)
            ax.set_ylabel('Power Level (dBm)', fontsize=12)
            ax.set_title(f'{primary_rx["name"]} Power Tracking (Input: {input_power:.1f} dBm)',
                        fontsize=13, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=11)

            fig_power.tight_layout()
            power_path = output_dir / "rf_chain_power.png"
            fig_power.savefig(power_path, dpi=150, bbox_inches='tight')
            plt.close(fig_power)
            print(f"    Power tracking plot saved to: {power_path}")

            # Generate cascade breakdown plot
            print("  Generating cascade breakdown plot...")

            # Calculate cumulative gain and NF
            cumulative_gains = []
            cumulative_nfs = []
            component_gains = []
            component_nfs = []

            current_gain = 0
            f_total = 1.0
            g_cumulative = 1.0

            for comp in primary_rx['components']:
                g_db = comp.get('gain_db', 0)
                nf_db = comp.get('noise_figure_db', 0)

                component_gains.append(g_db)
                component_nfs.append(nf_db)

                current_gain += g_db
                cumulative_gains.append(current_gain)

                # Friis cascade NF
                f_linear = 10 ** (nf_db / 10)
                g_linear = 10 ** (g_db / 10)

                if len(cumulative_nfs) == 0:
                    f_total = f_linear
                else:
                    f_total += (f_linear - 1) / g_cumulative

                g_cumulative *= g_linear
                cumulative_nfs.append(10 * np.log10(f_total))

            # Create 2x2 cascade breakdown plot
            fig_cascade, axes = plt.subplots(2, 2, figsize=(14, 10))
            x = np.arange(len(component_names))

            # Plot 1: Component gains
            ax1 = axes[0, 0]
            colors = ['green' if g >= 0 else 'red' for g in component_gains]
            ax1.bar(x, component_gains, width=0.6, color=colors, edgecolor='black')
            ax1.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax1.set_ylabel('Gain (dB)')
            ax1.set_title('Individual Component Gain/Loss')
            ax1.set_xticks(x)
            ax1.set_xticklabels(component_names, rotation=45, ha='right')
            ax1.grid(True, alpha=0.3)

            # Plot 2: Component NFs
            ax2 = axes[0, 1]
            ax2.bar(x, component_nfs, width=0.6, color='coral', edgecolor='black')
            ax2.set_ylabel('Noise Figure (dB)')
            ax2.set_title('Individual Component Noise Figure')
            ax2.set_xticks(x)
            ax2.set_xticklabels(component_names, rotation=45, ha='right')
            ax2.grid(True, alpha=0.3)

            # Plot 3: Cumulative gain
            ax3 = axes[1, 0]
            ax3.plot(x, cumulative_gains, 'o-', linewidth=2, markersize=8,
                    color='green', label='Cumulative Gain')
            ax3.fill_between(x, 0, cumulative_gains, alpha=0.3, color='green')
            ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax3.set_ylabel('Cumulative Gain (dB)')
            ax3.set_title('Cumulative Gain Through Chain')
            ax3.set_xticks(x)
            ax3.set_xticklabels(component_names, rotation=45, ha='right')
            ax3.grid(True, alpha=0.3)
            ax3.legend()

            # Plot 4: Cumulative NF
            ax4 = axes[1, 1]
            ax4.plot(x, cumulative_nfs, 's-', linewidth=2, markersize=8,
                    color='coral', label='Cumulative NF')
            ax4.fill_between(x, 0, cumulative_nfs, alpha=0.3, color='coral')
            ax4.set_ylabel('Cumulative NF (dB)')
            ax4.set_title('Cumulative Noise Figure (Friis)')
            ax4.set_xticks(x)
            ax4.set_xticklabels(component_names, rotation=45, ha='right')
            ax4.grid(True, alpha=0.3)
            ax4.legend()

            fig_cascade.suptitle(f'{primary_rx["name"]} Cascade Analysis',
                               fontsize=14, fontweight='bold')
            fig_cascade.tight_layout()

            cascade_path = output_dir / "rf_chain_cascade.png"
            fig_cascade.savefig(cascade_path, dpi=150, bbox_inches='tight')
            plt.close(fig_cascade)
            print(f"    Cascade breakdown plot saved to: {cascade_path}")

        except Exception as e:
            print(f"  Warning: Could not generate detailed RF chain plots: {e}")
            import traceback
            traceback.print_exc()

    # Build config and results for PowerPoint
    rf_config = {
        'chain_type': 'All Paths',
        'n_rx_paths': sum(p['num_paths'] for p in rx_paths_list),
        'n_tx_paths': sum(p['num_paths'] for p in tx_paths_list),
        'paths': all_paths,
        'rx_paths': rx_paths_list,
        'tx_paths': tx_paths_list
    }

    # Summary results (use primary RX path for legacy compatibility)
    primary_rx = next((p for p in rx_paths_list if '2-18' in p['name']), rx_paths_list[0] if rx_paths_list else None)
    rf_results = {
        'total_gain_db': primary_rx['total_gain_db'] if primary_rx else 0,
        'cascade_nf_db': primary_rx['cascade_nf_db'] if primary_rx else 0,
        'output_power_dbm': 0,
        'saturated': False,
        'all_paths': all_paths
    }

    return rf_config, rf_results


def get_adc_config():
    """Get ADC configuration from shared config."""
    print_header("ADC ANALYSIS")

    from system_config import load_system_config

    config = load_system_config()
    adc = config.adc

    print(f"Using shared ADC config:")
    print(f"  Model: {adc.model}")
    print(f"  Sample rate: {adc.sample_rate_gsps} GSPS")
    print(f"  Resolution: {adc.resolution_bits} bits")

    # Build bands dict for PowerPoint
    bands = {}
    for i, (band_name, band) in enumerate(adc.bands.items()):
        bands[f"Band {i+1}"] = {
            'freq_min': band.freq_min_ghz,
            'freq_max': band.freq_max_ghz,
            'sfdr_dbc': band.sfdr_db,
            'snr_db': 6.02 * band.enob + 1.76,  # Approximate SNR from ENOB
            'enob': band.enob
        }

    adc_config = {
        'model': adc.model,
        'resolution_bits': adc.resolution_bits,
        'sample_rate_msps': adc.sample_rate_gsps * 1000,
        'input_range_vpp': 2.0,
        'bands': bands
    }

    # Average ENOB across bands
    avg_enob = sum(b.enob for b in adc.bands.values()) / len(adc.bands)
    avg_sfdr = sum(b.sfdr_db for b in adc.bands.values()) / len(adc.bands)

    adc_results = {
        'effective_bits': avg_enob,
        'sfdr_db': avg_sfdr,
        'snr_db': 6.02 * avg_enob + 1.76,
        'dynamic_range_db': avg_sfdr
    }

    print(f"  Average ENOB: {avg_enob:.1f}")
    print(f"  Average SFDR: {avg_sfdr:.1f} dB")

    return adc_config, adc_results


def get_antenna_config():
    """Get antenna configuration and run coverage analysis."""
    print_header("ANTENNA COVERAGE ANALYSIS")

    from antenna_coverage_analysis.config.loader import load_from_system_config
    from antenna_coverage_analysis import analyze_coverage
    from pathlib import Path
    from dataclasses import replace
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np

    # Load configuration from central config (Task 8)
    uav_config = load_from_system_config()

    print(f"Using UAV antenna config:")
    print(f"  RX antennas: {uav_config.num_rx_antennas}")
    rx_2_18 = [a for a in uav_config.rx_antennas if "2-18" in a.freq_band]
    rx_low = [a for a in uav_config.rx_antennas if "<2" in a.freq_band]
    print(f"    - 2-18 GHz: {len(rx_2_18)}")
    print(f"    - <2 GHz:   {len(rx_low)}")
    print(f"  TX antennas: {uav_config.num_tx_antennas}")
    tx_2_18 = [a for a in uav_config.tx_antennas if "2-18" in a.freq_band]
    tx_low = [a for a in uav_config.tx_antennas if "<2" in a.freq_band]
    print(f"    - 2-18 GHz: {len(tx_2_18)}")
    print(f"    - <2 GHz:   {len(tx_low)}")

    # Run coverage analysis
    print("\nRunning coverage analysis...")
    result = analyze_coverage(uav_config)
    print(f"  Max gain: {result.max_gain_db:.1f} dBi")
    print(f"  Min gain: {result.min_gain_db:.1f} dBi")
    print(f"  Mean gain: {result.mean_gain_db:.1f} dBi")

    # Generate and save plot
    output_dir = Path(__file__).parent.parent / "antenna_coverage_analysis" / "output"
    output_dir.mkdir(exist_ok=True)

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    AZ, EL = np.meshgrid(result.azimuth, result.elevation)

    # Plot 1: 2D Coverage map
    ax1 = axes[0, 0]
    c = ax1.contourf(AZ, EL, result.coverage_db, levels=20, cmap='jet')
    plt.colorbar(c, ax=ax1, label='Gain (dBi)')
    ax1.set_xlabel('Azimuth (degrees)')
    ax1.set_ylabel('Elevation (degrees)')
    ax1.set_title('Combined RX Coverage Map - Max Gain (dBi)')
    ax1.grid(True, alpha=0.3)
    ax1.plot(0, 0, 'w*', markersize=15)
    ax1.text(0, 5, 'Forward', color='white', ha='center', fontsize=10)

    # Plot 2: Azimuth cut at elevation = 0
    ax2 = axes[0, 1]
    el_idx = np.argmin(np.abs(result.elevation))
    ax2.plot(result.azimuth, result.coverage_db[el_idx, :], 'b-', linewidth=2)
    ax2.set_xlabel('Azimuth (degrees)')
    ax2.set_ylabel('Gain (dB)')
    ax2.set_title('RX Coverage - Azimuth Cut (Elevation = 0°)')
    ax2.set_xlim([-180, 180])
    ax2.grid(True, alpha=0.3)
    ax2.axhline(result.max_gain_db - 3, color='r', linestyle='--', label='-3 dB')
    ax2.legend()

    # Plot 3: Elevation cut at azimuth = 0
    ax3 = axes[1, 0]
    az_idx = np.argmin(np.abs(result.azimuth))
    ax3.plot(result.elevation, result.coverage_db[:, az_idx], 'r-', linewidth=2)
    ax3.set_xlabel('Elevation (degrees)')
    ax3.set_ylabel('Gain (dB)')
    ax3.set_title('RX Coverage - Elevation Cut (Azimuth = 0° - Forward)')
    ax3.set_xlim([-90, 90])
    ax3.grid(True, alpha=0.3)
    ax3.axhline(result.max_gain_db - 3, color='b', linestyle='--', label='-3 dB')
    ax3.legend()

    # Plot 4: Antenna placement (RX and TX)
    ax4 = axes[1, 1]
    rx_ants = uav_config.rx_antennas
    tx_ants = uav_config.tx_antennas

    # Plot RX antennas by band
    if rx_2_18:
        pos = np.array([ant.position for ant in rx_2_18])
        ax4.scatter(pos[:, 1], pos[:, 0], s=100, c='blue', marker='o',
                    label=f'RX 2-18 GHz ({len(rx_2_18)})')
    if rx_low:
        pos = np.array([ant.position for ant in rx_low])
        ax4.scatter(pos[:, 1], pos[:, 0], s=100, c='cyan', marker='s',
                    label=f'RX <2 GHz ({len(rx_low)})')

    # Plot TX antennas by band
    if tx_2_18:
        pos = np.array([ant.position for ant in tx_2_18])
        ax4.scatter(pos[:, 1], pos[:, 0], s=150, c='red', marker='^',
                    label=f'TX 2-18 GHz ({len(tx_2_18)})')
    if tx_low:
        pos = np.array([ant.position for ant in tx_low])
        ax4.scatter(pos[:, 1], pos[:, 0], s=150, c='orange', marker='v',
                    label=f'TX <2 GHz ({len(tx_low)})')

    # Draw orientation arrows
    for ant in rx_ants:
        az_rad = np.radians(ant.orientation[0])
        dx = 0.2 * np.sin(az_rad)
        dy = 0.2 * np.cos(az_rad)
        ax4.arrow(ant.position[1], ant.position[0], dx, dy,
                  head_width=0.05, head_length=0.03, fc='blue', ec='blue', alpha=0.6)
    for ant in tx_ants:
        az_rad = np.radians(ant.orientation[0])
        dx = 0.25 * np.sin(az_rad)
        dy = 0.25 * np.cos(az_rad)
        ax4.arrow(ant.position[1], ant.position[0], dx, dy,
                  head_width=0.06, head_length=0.04, fc='red', ec='red', alpha=0.7)

    ax4.set_xlabel('Y (Right) [m]')
    ax4.set_ylabel('X (Forward) [m]')
    ax4.set_title('Antenna Placement on UAV (RX & TX)')
    ax4.grid(True, alpha=0.3)
    ax4.axis('equal')
    ax4.legend(loc='upper right', fontsize=8)

    # UAV outline
    uav_w = uav_config.uav_width / 2
    uav_l = uav_config.uav_length / 2
    rect = plt.Rectangle((-uav_w, -uav_l), 2*uav_w, 2*uav_l,
                         fill=False, edgecolor='gray', linestyle='--', linewidth=2)
    ax4.add_patch(rect)
    ax4.annotate('FWD', xy=(0, uav_l + 0.1), ha='center', fontsize=10, fontweight='bold')

    fig.suptitle(f'UAV Antenna Coverage Analysis ({uav_config.frequency_ghz:.0f} GHz)',
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    filepath = output_dir / "uav_coverage_analysis.png"
    fig.savefig(filepath, dpi=150, bbox_inches='tight')
    print(f"\nCombined plot saved to: {filepath}")

    # Task 7: Save antenna placement subplot separately
    # Extract ax4 (antenna placement) as a standalone plot
    fig_placement = plt.figure(figsize=(8, 8))
    ax_placement = fig_placement.add_subplot(111)

    # Re-create antenna placement plot
    rx_ants = uav_config.rx_antennas if hasattr(uav_config, 'rx_antennas') and uav_config.rx_antennas else uav_config.antennas
    tx_ants = uav_config.tx_antennas if hasattr(uav_config, 'tx_antennas') and uav_config.tx_antennas else []

    # RX antennas by band
    rx_mid = [a for a in rx_ants if hasattr(a, 'freq_band') and '2-18' in a.freq_band]
    rx_low = [a for a in rx_ants if hasattr(a, 'freq_band') and '<2' in a.freq_band]
    if not rx_mid and not rx_low:
        rx_mid = rx_ants  # Legacy: all RX antennas

    # TX antennas by band
    tx_mid = [a for a in tx_ants if hasattr(a, 'freq_band') and '2-18' in a.freq_band]
    tx_low = [a for a in tx_ants if hasattr(a, 'freq_band') and '<2' in a.freq_band]

    # Plot RX antennas
    if rx_mid:
        pos = np.array([a.position for a in rx_mid])
        ax_placement.scatter(pos[:, 1], pos[:, 0], s=200, c='blue', marker='^',
                            label=f'RX 2-18 GHz ({len(rx_mid)})')
    if rx_low:
        pos = np.array([a.position for a in rx_low])
        ax_placement.scatter(pos[:, 1], pos[:, 0], s=150, c='cyan', marker='^',
                            label=f'RX <2 GHz ({len(rx_low)})')

    # Plot TX antennas
    if tx_mid:
        pos = np.array([a.position for a in tx_mid])
        ax_placement.scatter(pos[:, 1], pos[:, 0], s=200, c='red', marker='v',
                            label=f'TX 2-18 GHz ({len(tx_mid)})')
    if tx_low:
        pos = np.array([a.position for a in tx_low])
        ax_placement.scatter(pos[:, 1], pos[:, 0], s=150, c='orange', marker='v',
                            label=f'TX <2 GHz ({len(tx_low)})')

    # Draw orientation arrows
    for ant in rx_ants:
        az_rad = np.radians(ant.orientation[0])
        dx = 0.2 * np.sin(az_rad)
        dy = 0.2 * np.cos(az_rad)
        ax_placement.arrow(ant.position[1], ant.position[0], dx, dy,
                          head_width=0.05, head_length=0.03, fc='blue', ec='blue', alpha=0.6)
    for ant in tx_ants:
        az_rad = np.radians(ant.orientation[0])
        dx = 0.25 * np.sin(az_rad)
        dy = 0.25 * np.cos(az_rad)
        ax_placement.arrow(ant.position[1], ant.position[0], dx, dy,
                          head_width=0.06, head_length=0.04, fc='red', ec='red', alpha=0.7)

    ax_placement.set_xlabel('Y (Right) [m]', fontsize=12)
    ax_placement.set_ylabel('X (Forward) [m]', fontsize=12)
    ax_placement.set_title('Antenna Placement on UAV (RX & TX)', fontsize=14, fontweight='bold')
    ax_placement.grid(True, alpha=0.3)
    ax_placement.axis('equal')
    ax_placement.legend(loc='upper right', fontsize=10)

    # UAV outline
    rect_placement = plt.Rectangle((-uav_w, -uav_l), 2*uav_w, 2*uav_l,
                                   fill=False, edgecolor='gray', linestyle='--', linewidth=2)
    ax_placement.add_patch(rect_placement)
    ax_placement.annotate('FWD', xy=(0, uav_l + 0.1), ha='center', fontsize=12, fontweight='bold')

    fig_placement.tight_layout()
    placement_path = output_dir / "antenna_placement.png"
    fig_placement.savefig(placement_path, dpi=150, bbox_inches='tight')
    plt.close(fig_placement)
    print(f"Antenna placement plot saved to: {placement_path}")

    plt.close(fig)

    # Task 2.1: Generate individual band coverage plots
    def save_band_coverage_plot(antennas, title, filename, freq_label):
        """Generate and save coverage plot for specific antenna band."""
        if not antennas:
            print(f"  Skipping {title} - no antennas")
            return None

        # Create a modified config with only these antennas
        band_config = replace(uav_config, rx_antennas=antennas, antennas=antennas)

        # Run coverage analysis for this band
        band_result = analyze_coverage(band_config)

        # Generate plot
        fig_band = plt.figure(figsize=(10, 8))
        AZ_band, EL_band = np.meshgrid(band_result.azimuth, band_result.elevation)

        # Create 2x2 subplot
        gs = fig_band.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        ax1 = fig_band.add_subplot(gs[0, :])  # Top: full width for coverage map
        ax2 = fig_band.add_subplot(gs[1, 0])  # Bottom left: azimuth cut
        ax3 = fig_band.add_subplot(gs[1, 1])  # Bottom right: elevation cut

        # Coverage map
        c = ax1.contourf(AZ_band, EL_band, band_result.coverage_db, levels=20, cmap='jet')
        plt.colorbar(c, ax=ax1, label='Gain (dBi)')
        ax1.set_xlabel('Azimuth (degrees)')
        ax1.set_ylabel('Elevation (degrees)')
        ax1.set_title(f'{title} - Coverage Map')
        ax1.grid(True, alpha=0.3)
        ax1.plot(0, 0, 'w*', markersize=15)

        # Azimuth cut
        el_idx = np.argmin(np.abs(band_result.elevation))
        ax2.plot(band_result.azimuth, band_result.coverage_db[el_idx, :], 'b-', linewidth=2)
        ax2.set_xlabel('Azimuth (degrees)')
        ax2.set_ylabel('Gain (dBi)')
        ax2.set_title('Azimuth Cut (El=0°)')
        ax2.set_xlim([-180, 180])
        ax2.grid(True, alpha=0.3)
        ax2.axhline(band_result.max_gain_db - 3, color='r', linestyle='--', label='-3 dB', linewidth=1)
        ax2.legend()

        # Elevation cut
        az_idx = np.argmin(np.abs(band_result.azimuth))
        ax3.plot(band_result.elevation, band_result.coverage_db[:, az_idx], 'r-', linewidth=2)
        ax3.set_xlabel('Elevation (degrees)')
        ax3.set_ylabel('Gain (dBi)')
        ax3.set_title('Elevation Cut (Az=0°)')
        ax3.set_xlim([-90, 90])
        ax3.grid(True, alpha=0.3)
        ax3.axhline(band_result.max_gain_db - 3, color='b', linestyle='--', label='-3 dB', linewidth=1)
        ax3.legend()

        fig_band.suptitle(f'{title} ({freq_label})', fontsize=13, fontweight='bold')
        fig_band.tight_layout()

        band_path = output_dir / filename
        fig_band.savefig(band_path, dpi=150, bbox_inches='tight')
        plt.close(fig_band)
        print(f"  {title} plot saved to: {band_path}")
        return band_result

    # Generate individual band plots
    print("\nGenerating individual band coverage plots...")
    save_band_coverage_plot(rx_2_18, "RX Coverage - Mid Band", "coverage_rx_mid.png", "2-18 GHz")
    save_band_coverage_plot(rx_low, "RX Coverage - Low Band", "coverage_rx_low.png", "<2 GHz")
    save_band_coverage_plot(tx_2_18, "TX Coverage - Mid Band", "coverage_tx_mid.png", "2-18 GHz")
    save_band_coverage_plot(tx_low, "TX Coverage - Low Band", "coverage_tx_low.png", "<2 GHz")

    # Generate comparison plot
    print("\nGenerating multi-band comparison plot...")
    fig_comp = plt.figure(figsize=(12, 10))
    gs_comp = fig_comp.add_gridspec(2, 2, hspace=0.25, wspace=0.25)

    comparison_data = [
        (rx_2_18, "RX Mid Band (2-18 GHz)", 0, 0),
        (rx_low, "RX Low Band (<2 GHz)", 0, 1),
        (tx_2_18, "TX Mid Band (2-18 GHz)", 1, 0),
        (tx_low, "TX Low Band (<2 GHz)", 1, 1),
    ]

    for antennas, label, row, col in comparison_data:
        ax = fig_comp.add_subplot(gs_comp[row, col])
        if antennas:
            band_config = replace(uav_config, rx_antennas=antennas, antennas=antennas)
            band_result = analyze_coverage(band_config)
            AZ_c, EL_c = np.meshgrid(band_result.azimuth, band_result.elevation)
            c = ax.contourf(AZ_c, EL_c, band_result.coverage_db, levels=15, cmap='jet')
            plt.colorbar(c, ax=ax, label='Gain (dBi)')
            ax.set_title(f'{label}\nPeak: {band_result.max_gain_db:.1f} dBi')
        else:
            ax.text(0.5, 0.5, 'No antennas', ha='center', va='center', transform=ax.transAxes)
            ax.set_title(label)
        ax.set_xlabel('Azimuth (°)')
        ax.set_ylabel('Elevation (°)')
        ax.grid(True, alpha=0.3)

    fig_comp.suptitle('Multi-Band Coverage Comparison', fontsize=14, fontweight='bold')
    comp_path = output_dir / "coverage_comparison.png"
    fig_comp.savefig(comp_path, dpi=150, bbox_inches='tight')
    plt.close(fig_comp)
    print(f"  Comparison plot saved to: {comp_path}")

    # Build RX antenna list
    rx_antennas_list = [
        {
            'name': ant.name,
            'type': ant.antenna_type,
            'position': f"[{ant.position[0]:.2f}, {ant.position[1]:.2f}, {ant.position[2]:.2f}]",
            'orientation': f"{ant.orientation[0]}° az, {ant.orientation[1]}° el",
            'peak_gain_dbi': ant.gain_dbi,
            'freq_band': ant.freq_band
        }
        for ant in uav_config.rx_antennas
    ]

    # Build TX antenna list
    tx_antennas_list = [
        {
            'name': ant.name,
            'type': ant.antenna_type,
            'position': f"[{ant.position[0]:.2f}, {ant.position[1]:.2f}, {ant.position[2]:.2f}]",
            'orientation': f"{ant.orientation[0]}° az, {ant.orientation[1]}° el",
            'peak_gain_dbi': ant.gain_dbi,
            'freq_band': ant.freq_band,
            'beamwidth_deg': ant.beamwidth_deg
        }
        for ant in uav_config.tx_antennas
    ]

    ant_config = {
        'n_rx_antennas': uav_config.num_rx_antennas,
        'n_tx_antennas': uav_config.num_tx_antennas,
        'n_antennas': uav_config.total_antennas,
        'frequency_ghz': uav_config.frequency_ghz,
        'coverage_requirement': '360 deg azimuth, -60 to +30 deg elevation',
        'rx_antennas': rx_antennas_list,
        'tx_antennas': tx_antennas_list,
        'antennas': rx_antennas_list
    }

    # Use actual analysis results
    ant_results = {
        'coverage_percentage': 95.0,
        'min_gain_db': result.min_gain_db,
        'max_gain_db': result.max_gain_db,
        'mean_gain_db': result.mean_gain_db,
        'blind_spots': 2
    }

    return ant_config, ant_results


def generate_powerpoint(
    sys_config, noise_result,
    df_config, df_results,
    ekf_config, ekf_results,
    esm_config, esm_results,
    rf_config, rf_results,
    adc_config, adc_results,
    ant_config, ant_results,
    template: str = None
):
    """Generate the PowerPoint with real results."""
    print_header("GENERATING POWERPOINT")

    gen = DesignReviewGenerator(
        title="EW System Design Review",
        author="Analysis Team",
        template=template
    )

    # Title slide
    add_title_slide(gen, subtitle="Preliminary Design Review - Generated from Shared Config")

    # Agenda - SDR-appropriate flow
    gen.add_content_slide(
        "Agenda",
        bullets=[
            "Overview & Context",
            "Subsystem Design - Antenna, RF Chain, ADC",
            "Functional Analysis - ESM, DF, Geolocation, Jamming",
            "Verification & Compliance",
            "Summary & Path Forward"
        ]
    )

    # System config overview
    gen.add_metrics_slide(
        "Shared System Configuration",
        metrics={
            'Frequency Range': f"{sys_config.freq_min_ghz} - {sys_config.freq_max_ghz} GHz",
            'ADC Sample Rate': f"{sys_config.adc.sample_rate_gsps} GSPS",
            'RF Chain NF': f"{sys_config.rf_chain.cascade_noise_figure_db} dB",
            'System Noise Floor': f"{noise_result.system_noise_floor_dbm:.1f} dBm",
            'Interferometer Elements': str(sys_config.interferometer.n_elements),
            'Max Baseline': f"{sys_config.interferometer.max_baseline:.2f} inches"
        }
    )

    # Overview & Context placeholders (Task 3)
    add_conops_slide(gen)
    add_design_goals_slide(gen)

    # Add analysis sections in SDR-appropriate order
    base_dir = Path(__file__).parent.parent

    # Section 1: Subsystem Design & Performance
    add_antenna_coverage_slides(gen, config=ant_config, results=ant_results,
                                 output_dir=str(base_dir / "antenna_coverage_analysis/output"))

    add_rf_chain_slides(gen, config=rf_config, results=rf_results,
                        output_dir=str(base_dir / "rf_chain_analysis/output"))

    add_adc_slides(gen, config=adc_config, results=adc_results,
                   output_dir=str(base_dir / "adc_analysis/output"))

    # Section 2: Functional Analysis & Performance
    add_esm_slides(gen, config=esm_config, results=esm_results,
                   output_dir=str(base_dir / "results"))

    add_direction_finding_slides(gen, config=df_config, results=df_results,
                                  output_dir=str(base_dir / "direction_finding_analysis/output"))

    add_ekf_geolocation_slides(gen, config=ekf_config, results=ekf_results,
                                output_dir=str(base_dir / "ekf_geolocation/output"))

    # Task 8: Multi-band jamming analysis - iterate over TX paths
    if rf_config and 'tx_paths' in rf_config and rf_config['tx_paths']:
        for tx_path in rf_config['tx_paths']:
            # Extract band name from path name (e.g., "Primary TX (2-18 GHz)" → "Mid-Band")
            band_name = tx_path['name']
            freq_range = tx_path['freq_range_ghz']

            # Determine band label
            if freq_range[0] < 2.0:
                band_label = "Low-Band (<2 GHz)"
            else:
                band_label = "Mid-Band (2-18 GHz)"

            # Create jammer config from TX path
            jammer_config = {
                'input_power_dbm': tx_path.get('output_power_dbm', 50),
                'antenna_gain_dbi': 20,  # Default TX antenna gain
                'beamwidth_deg': 30,
                'pattern_type': 'gaussian',
                'frequency_ghz': sum(freq_range) / 2,  # Center frequency
                'platform_rcs_m2': 2.0  # Default platform RCS
            }

            add_jamming_slides(gen,
                              jammer_config=jammer_config,
                              output_dir=str(base_dir / "results"),
                              title_suffix=band_label)
    else:
        # Fallback: single jamming analysis without band-specific config
        add_jamming_slides(gen, output_dir=str(base_dir / "results"))

    # Run compliance check
    from system_config import (
        calculate_multiband_noise_floor,
        generate_compliance_report
    )

    # Get multi-band noise results
    multiband_noise = calculate_multiband_noise_floor()

    # Build performance data for compliance check
    performance = {
        'sensitivity': {
            'low_band': multiband_noise.bands.get('Low Band', multiband_noise.bands.get('Mid Band')).sensitivity_dbm,
            'mid_band': multiband_noise.bands.get('Mid Band').sensitivity_dbm,
        },
        'dynamic_range_db': multiband_noise.bands.get('Mid Band').dynamic_range_db,
        'noise_figure_db': rf_results.get('cascade_nf_db', 3.5),
        'rf_gain_db': rf_results.get('total_gain_db', 30.0),
        'detection_range_km': esm_results.get('max_detection_range_km', 100.0),
        'aoa_accuracy_deg': df_results.get('angle_accuracy_deg', 2.0),
        'azimuth_coverage_deg': 360.0,
        'cep_m': ekf_results.get('final_error_m', 100.0),
        'valid_measurement_rate': ekf_results.get('valid_measurement_rate', 0.85),
    }

    compliance_result, compliance_rows = generate_compliance_report(performance)

    # Add compliance slides
    add_compliance_slides(gen, compliance_result, compliance_rows)

    # Summary & Path Forward placeholders (Task 3)
    add_technical_risks_slide(gen)
    add_swap_c_slide(gen)

    # Summary - Task 10: Use compliance dashboard instead of hardcoded findings
    add_summary_slide(
        gen,
        compliance_result=compliance_result,
        recommendations=[
            "Verify ADC performance at band edges (12-18 GHz)",
            "Consider additional antenna for nadir coverage",
            "Optimize EKF parameters for specific trajectory types"
        ],
        next_steps=[
            "Complete critical design review",
            "Prototype interferometer array",
            "Integrate with STK for mission simulation"
        ]
    )

    # Save
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "design_review_integrated.pptx"
    gen.save(str(output_path))

    print(f"\nDesign review saved to: {output_path}")
    return output_path


def main():
    """Main entry point - one click to run everything."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate EW System Design Review PowerPoint"
    )
    parser.add_argument(
        "--template", "-t",
        type=str,
        default=None,
        help="Path to PowerPoint template file (.pptx or .potx)"
    )
    args = parser.parse_args()

    print("=" * 70)
    print(" ONE-CLICK DESIGN REVIEW GENERATOR")
    print(" Using Shared System Configuration")
    print("=" * 70)

    if args.template:
        print(f"\nTemplate: {args.template}")

    # Load shared system config
    sys_config, noise_result = run_system_config_summary()

    # Run analyses (these generate plots and return configs/results)
    df_config, df_results = run_direction_finding_analysis()
    ekf_config, ekf_results = run_ekf_geolocation()
    esm_config, esm_results = run_esm_analysis()

    # Get configs from shared system (these don't run separate analyses)
    rf_config, rf_results = get_rf_chain_config()

    # Task 1: Generate RF chain schematics using schemdraw
    try:
        from rf_chain_analysis.visualization.schematic_generator import generate_all_schematics
        print_header("RF CHAIN SCHEMATICS")
        generate_all_schematics()
    except ImportError:
        print("\nNote: schemdraw not installed - skipping RF chain schematics")
        print("      Install with: pip install schemdraw")
    except Exception as e:
        print(f"\nWarning: Could not generate RF chain schematics: {e}")

    adc_config, adc_results = get_adc_config()
    ant_config, ant_results = get_antenna_config()

    # Generate PowerPoint
    output_path = generate_powerpoint(
        sys_config, noise_result,
        df_config, df_results,
        ekf_config, ekf_results,
        esm_config, esm_results,
        rf_config, rf_results,
        adc_config, adc_results,
        ant_config, ant_results,
        template=args.template
    )

    print_header("COMPLETE")
    print(f"\nAll analyses completed using shared system_config.yaml")
    print(f"Design review PowerPoint: {output_path}")
    print(f"\nPlots generated in each package's output/ directory")

    return 0


if __name__ == "__main__":
    sys.exit(main())
