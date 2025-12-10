"""
Jamming Analysis Package

Provides Self-Protect Jamming (SPJ) analysis:
1. J/S ratio calculations (jammer R^-2 vs radar R^-4)
2. Platform RCS effects on jamming effectiveness
3. Antenna pattern effects (Gaussian, cosine-squared)
4. Burn-through range calculation

Key insight: J/S ∝ R² / σ
- Larger range = better J/S (jammer more effective)
- Smaller platform RCS = better J/S

Based on legacy MATLAB implementation: ew_mission_phase3_jamming.m
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .core import (
    JammerConfig,
    RadarConfig,
    EmitterConfig,  # Backwards compatibility alias
    JammingResult,
    JammingAnalyzer,
    analyze_jamming_standalone,
)

__all__ = [
    'JammerConfig',
    'RadarConfig',
    'EmitterConfig',
    'JammingResult',
    'JammingAnalyzer',
    'analyze_jamming_standalone',
]
