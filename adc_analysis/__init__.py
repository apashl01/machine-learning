"""
ADC Analysis Package

Comprehensive RF ADC performance analysis including:
- Noise floor and dynamic range calculation
- Sensitivity analysis
- SFDR and distortion characterization
- Per-band specifications support

Matches MATLAB analyze_rf_adc.m functionality.
"""

__version__ = "2.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import (
    load_adc_specs,
    load_model1_specs,
    load_model2_specs,
    ADCSpecs,
    AnalysisConfig
)
from .core import (
    analyze_rf_adc,
    ADCResults,
    print_results_summary,
    compare_adcs,
    print_comparison_table
)

__all__ = [
    # Config
    'load_adc_specs',
    'load_model1_specs',
    'load_model2_specs',
    'ADCSpecs',
    'AnalysisConfig',
    # Analysis
    'analyze_rf_adc',
    'ADCResults',
    'print_results_summary',
    'compare_adcs',
    'print_comparison_table',
]
