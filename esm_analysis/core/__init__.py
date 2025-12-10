"""
Core analysis modules for ESM Detection.

Provides SNR calculation, threat categorization, and detection modeling.
"""

from .snr_calculator import SNRCalculator, SNRResult
from .threat_categorizer import ThreatCategorizer, ThreatCategory, CategorizedThreat
from .detection_model import (
    DetectionModel,
    DetectionResult,
    DetectionMode,
    DetectionStatus,
    calculate_albersheim_pd,
)

__all__ = [
    'SNRCalculator',
    'SNRResult',
    'ThreatCategorizer',
    'ThreatCategory',
    'CategorizedThreat',
    'DetectionModel',
    'DetectionResult',
    'DetectionMode',
    'DetectionStatus',
    'calculate_albersheim_pd',
]
