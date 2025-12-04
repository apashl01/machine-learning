"""
ESM Detection Analysis Package

This package provides tools for Electronic Support Measures (ESM)
detection analysis, including:

- ESM detection range calculations (one-way R^2 propagation)
- Comparison with radar detection ranges (two-way R^4)
- Scan position dwell scheduling optimization
- Monte Carlo sensitivity analysis
- Visualization tools

Ported from MATLAB radar_range_analysis.m with additional
dwell scheduling capabilities.

Example usage:
    from esm_analysis import (
        RadarParameters, ReceiverParameters, ESMDetector,
        DwellScheduler, EmitterModel
    )

    # Define receiver
    receiver = ReceiverParameters(
        noise_figure_dB=5.0,
        bandwidth_MHz=20.0,
        antenna_gain_dB=0.0
    )

    # Define threat radar
    radar = RadarParameters(
        eirp_dBW=60.0,
        freq_GHz=10.0
    )

    # Calculate detection range
    detector = ESMDetector(receiver)
    detection_range_km = detector.calculate_detection_range(radar)
    print(f"Detection range: {detection_range_km:.1f} km")
"""

from .esm_detection import (
    RadarParameters,
    ReceiverParameters,
    DetectionResult,
    ESMDetector,
    compare_to_radar_range,
    sensitivity_analysis,
    monte_carlo_analysis,
    C, KB, T0,
)

from .dwell_scheduler import (
    ScanStrategy,
    ScanPosition,
    EmitterModel,
    DwellSchedule,
    DwellScheduler,
    generate_threat_set,
)

from .visualization import (
    plot_detection_range_comparison,
    plot_sensitivity_sweep,
    plot_monte_carlo_results,
    plot_dwell_schedule,
    plot_schedule_evaluation,
    plot_range_vs_frequency,
)

__version__ = "1.0.0"
__author__ = "Ported from MATLAB"
