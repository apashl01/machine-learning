#!/usr/bin/env python3
"""
Example: Generate EW System Design Review PowerPoint

This script demonstrates how to generate a complete design review
presentation using analysis results from the various packages.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from reporting import DesignReviewGenerator
from reporting.generators import (
    add_title_slide,
    add_esm_slides,
    add_rf_chain_slides,
    add_adc_slides,
    add_direction_finding_slides,
    add_antenna_coverage_slides,
    add_ekf_geolocation_slides,
    add_jamming_slides,
    add_summary_slide
)


def main():
    """Generate example design review presentation."""

    print("=" * 60)
    print("EW SYSTEM DESIGN REVIEW GENERATOR")
    print("=" * 60)

    # Create generator
    gen = DesignReviewGenerator(
        title="EW System Design Review",
        author="Analysis Team"
    )

    # Title slide
    add_title_slide(gen, subtitle="Preliminary Design Review")

    # Agenda
    gen.add_content_slide(
        "Agenda",
        bullets=[
            "ESM Analysis - Detection range and sensitivity",
            "RF Chain Analysis - Link budget and component performance",
            "ADC Analysis - Digitizer specifications and performance",
            "Direction Finding - Interferometer accuracy analysis",
            "Antenna Coverage - Pattern and coverage analysis",
            "EKF Geolocation - Emitter localization simulation",
            "Summary & Next Steps"
        ]
    )

    # ESM Analysis section
    esm_config = {
        'frequency_range_ghz': [2, 18],
        'sensitivity_dbm': -65,
        'scan_type': 'Frequency Hopping',
        'revisit_rate_hz': 10
    }
    esm_results = {
        'detection_range_km': 150,
        'poi': 0.95,
        'sensitivity_dbm': -65,
        'max_frequency_ghz': 18
    }
    add_esm_slides(gen, config=esm_config, results=esm_results,
                   output_dir="esm_analysis/output")

    # RF Chain section (with example config)
    rf_config = {
        'chain_type': 'RX',
        'frequency_ghz': 10.0,
        'n_components': 5,
        'input_power_dbm': -60,
        'damage_threshold_dbm': 0,
        'components': [
            {'name': 'Antenna', 'type': 'Horn', 'gain_db': 15.0, 'noise_figure_db': 0},
            {'name': 'Cable 1', 'type': 'Coax', 'gain_db': -2.0, 'noise_figure_db': 2.0},
            {'name': 'LNA', 'type': 'Amplifier', 'gain_db': 25.0, 'noise_figure_db': 1.5},
            {'name': 'Filter', 'type': 'BPF', 'gain_db': -1.5, 'noise_figure_db': 1.5},
            {'name': 'Cable 2', 'type': 'Coax', 'gain_db': -3.0, 'noise_figure_db': 3.0},
        ]
    }
    rf_results = {
        'total_gain_db': 33.5,
        'cascade_nf_db': 3.2,
        'output_power_dbm': -26.5,
        'saturated': False
    }
    add_rf_chain_slides(gen, config=rf_config, results=rf_results,
                        output_dir="rf_chain_analysis/output")

    # ADC section
    adc_config = {
        'model': 'High-Speed ADC Model 1',
        'resolution_bits': 14,
        'sample_rate_msps': 3000,
        'input_range_vpp': 2.0,
        'bands': {
            'Band A': {'freq_min': 0.5, 'freq_max': 1.0, 'sfdr_dbc': 75, 'snr_db': 65, 'enob': 10.5},
            'Band B': {'freq_min': 1.0, 'freq_max': 2.0, 'sfdr_dbc': 72, 'snr_db': 63, 'enob': 10.2},
            'Band C': {'freq_min': 2.0, 'freq_max': 3.0, 'sfdr_dbc': 68, 'snr_db': 60, 'enob': 9.7},
        }
    }
    adc_results = {
        'effective_bits': 10.1,
        'sfdr_db': 71.7,
        'snr_db': 62.7,
        'dynamic_range_db': 85.0
    }
    add_adc_slides(gen, config=adc_config, results=adc_results,
                   output_dir="adc_analysis/output")

    # Direction Finding section
    df_config = {
        'n_elements': 4,
        'freq_min_ghz': 2,
        'freq_max_ghz': 18,
        'phase_error_deg': 12,
        'element_positions': [0, 0.328, 3.5, 10.0],
        'max_baseline': 10.0,
        'baselines': [0.328, 3.172, 3.5, 6.5, 9.672, 10.0]
    }
    df_results = {
        'angle_accuracy_deg': 0.5,
        'ambiguity_free_fov': 80,
        'min_snr_db': 10,
        'max_incident_angle': 70
    }
    add_direction_finding_slides(gen, config=df_config, results=df_results,
                                  output_dir="direction_finding_analysis/output")

    # Antenna Coverage section
    ant_config = {
        'n_antennas': 4,
        'frequency_ghz': 10.0,
        'coverage_requirement': '360 deg azimuth, -60 to +30 deg elevation',
        'antennas': [
            {'name': 'Forward', 'type': 'Spiral', 'position': 'Nose', 'orientation': '0 deg', 'peak_gain_dbi': 5.0},
            {'name': 'Left', 'type': 'Spiral', 'position': 'Port Wing', 'orientation': '-90 deg', 'peak_gain_dbi': 5.0},
            {'name': 'Right', 'type': 'Spiral', 'position': 'Starboard Wing', 'orientation': '+90 deg', 'peak_gain_dbi': 5.0},
            {'name': 'Aft', 'type': 'Spiral', 'position': 'Tail', 'orientation': '180 deg', 'peak_gain_dbi': 5.0},
        ]
    }
    ant_results = {
        'coverage_percentage': 95.2,
        'min_gain_db': -8.5,
        'max_gain_db': 5.0,
        'blind_spots': 2
    }
    add_antenna_coverage_slides(gen, config=ant_config, results=ant_results,
                                 output_dir="antenna_coverage_analysis/output")

    # EKF Geolocation section
    ekf_config = {
        'emitter': {
            'lat': 35.0,
            'lon': -120.0,
            'alt': 100,
            'eirp_dbw': 40,
            'frequency_ghz': 3.0
        },
        'trajectory': {
            'type': 'figure8',
            'standoff_distance_km': 10,
            'altitude_mean': 3000
        },
        'interferometer': {
            'n_elements': 4,
            'max_baseline': 10.0,
            'phase_error_deg': 12,
            'max_incident_angle_deg': 70,
            'element_positions': [0, 1.968, 3.5, 10.0]
        },
        'ekf': {
            'initial_offset_km': 5,
            'Q': 10.0,
            'P0': 1000,
            'R_scale': 2.0
        }
    }
    ekf_results = {
        'final_error_m': 65.0,
        'final_uncertainty_m': 94.0,
        'convergence_time_s': 225,
        'valid_measurements_pct': 29.2,
        'final_estimate': {'lat': 35.000085, 'lon': -119.999774, 'alt': 39.2},
        'true_position': {'lat': 35.0, 'lon': -120.0, 'alt': 100}
    }
    add_ekf_geolocation_slides(gen, config=ekf_config, results=ekf_results,
                                output_dir="ekf_geolocation/output")

    # Jamming Analysis section
    add_jamming_slides(gen)

    # Summary
    add_summary_slide(
        gen,
        key_findings=[
            "ESM achieves 150 km detection range with 95% POI",
            "RF chain provides 33.5 dB gain with 3.2 dB cascade NF",
            "ADC achieves 10.1 ENOB across operating bands",
            "Interferometer provides 0.5 deg angle accuracy at high SNR",
            "Antenna coverage achieves 95% hemispherical coverage",
            "EKF geolocation converges to <100m error within 4 minutes"
        ],
        recommendations=[
            "Consider adding filtering to improve ADC SFDR at higher frequencies",
            "Evaluate additional antenna for nadir coverage gap",
            "Optimize EKF parameters for faster convergence"
        ],
        next_steps=[
            "Complete critical design review analysis",
            "Prototype interferometer array for lab testing",
            "Integrate with STK for full mission simulation"
        ]
    )

    # Save presentation
    output_dir = Path(__file__).parent / "output"
    output_path = output_dir / "design_review.pptx"
    gen.save(str(output_path))

    print("\nDesign review presentation generated successfully!")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
