"""
Direction Finding Analysis Package

1D RF interferometer analysis including:
- Angle accuracy vs incident angle and frequency
- SNR-dependent phase error modeling
- Ambiguity-free region calculation
- Multi-baseline Vernier array support

Matches MATLAB rf_interferometer_analysis.m functionality.
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import load_interferometer_config, InterferometerConfig
from .core import (
    analyze_interferometer,
    InterferometerAnalyzer,
    InterferometerResults,
    AngleAccuracyResult,
    AmbiguityResult,
    print_summary
)

__all__ = [
    'load_interferometer_config',
    'InterferometerConfig',
    'analyze_interferometer',
    'InterferometerAnalyzer',
    'InterferometerResults',
    'AngleAccuracyResult',
    'AmbiguityResult',
    'print_summary'
]
