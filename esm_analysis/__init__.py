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
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import load_config, SystemConfig, ThreatLibrary
from .core import SNRCalculator, ThreatCategorizer, DetectionModel
from .scheduling import DwellScheduler
from .visualization import ESMPlotter

__all__ = [
    'load_config',
    'SystemConfig',
    'ThreatLibrary',
    'SNRCalculator',
    'ThreatCategorizer',
    'DetectionModel',
    'DwellScheduler',
    'ESMPlotter',
]
