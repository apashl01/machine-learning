"""
Jamming Analysis Package

Provides analysis of:
1. Standalone TX chain performance (EIRP, J/S vs range)
2. Trajectory-based jamming effectiveness simulation
3. Antenna pattern effects (Gaussian, cosine-squared)

Based on legacy MATLAB implementation: ew_mission_phase3_jamming.m
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .core import (
    JammerConfig,
    EmitterConfig,
    JammingResult,
    JammingAnalyzer,
    analyze_jamming_standalone,
)

__all__ = [
    'JammerConfig',
    'EmitterConfig',
    'JammingResult',
    'JammingAnalyzer',
    'analyze_jamming_standalone',
]
