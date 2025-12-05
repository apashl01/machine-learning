"""
ADC Analysis Package

Comprehensive ADC performance analysis including:
- Measurement accuracy (amplitude, timing, frequency, phase)
- Receiver sensitivity with LNA optimization
- Saturation and damage threshold analysis
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import load_adc_config, ADCConfig, ADCSpec, LNASpec
from .core import (
    MeasurementAnalyzer,
    SensitivityAnalyzer,
    SaturationAnalyzer,
    MeasurementResult,
    SensitivityResult,
    SaturationResult
)

__all__ = [
    'load_adc_config',
    'ADCConfig',
    'ADCSpec',
    'LNASpec',
    'MeasurementAnalyzer',
    'SensitivityAnalyzer',
    'SaturationAnalyzer',
    'MeasurementResult',
    'SensitivityResult',
    'SaturationResult',
]
