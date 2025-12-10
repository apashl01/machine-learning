"""
ESM Detection Analysis Package

A comprehensive Electronic Support Measures (ESM) analysis suite for
radar threat detection, categorization, and receiver scheduling optimization.

Modules:
    config: Configuration loading and validation
    core: SNR calculation, threat categorization, detection models
    scheduling: Dwell scheduling algorithms
    visualization: Plotting and reporting functions
    utils: Unit conversions and helper functions
    measurement_accuracy: Pulse parameter measurement accuracy analysis (DLFM, TOA, PW)
    spurious_analysis: ADC spurious and false alarm analysis
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import load_config, SystemConfig, ThreatLibrary
from .core import (
    SNRCalculator,
    ThreatCategorizer,
    DetectionModel,
    DetectionMode,
    DetectionStatus,
    calculate_albersheim_pd,
)
from .scheduling import DwellScheduler
from .visualization import ESMPlotter
from .measurement_accuracy import (
    MeasurementConfig,
    MeasurementResult,
    MeasurementAccuracyAnalyzer,
    analyze_measurement_accuracy
)
from .spurious_analysis import (
    SpuriousConfig,
    FalseAlarmResult,
    DeterministicSpuriousResult,
    SpuriousAnalyzer,
    analyze_spurious
)

__all__ = [
    'load_config',
    'SystemConfig',
    'ThreatLibrary',
    'SNRCalculator',
    'ThreatCategorizer',
    'DetectionModel',
    'DetectionMode',
    'DetectionStatus',
    'calculate_albersheim_pd',
    'DwellScheduler',
    'ESMPlotter',
    'MeasurementConfig',
    'MeasurementResult',
    'MeasurementAccuracyAnalyzer',
    'analyze_measurement_accuracy',
    'SpuriousConfig',
    'FalseAlarmResult',
    'DeterministicSpuriousResult',
    'SpuriousAnalyzer',
    'analyze_spurious',
]
