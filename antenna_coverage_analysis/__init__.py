"""
UAV Antenna Coverage Analysis Package

Multi-antenna coverage analysis for UAV platforms including:
- Spiral antenna pattern generation
- Horn antenna pattern generation
- Combined coverage calculation (max gain selection)
- Coverage statistics

Matches MATLAB uav_antenna_coverage.m functionality.
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import (
    load_uav_config,
    UAVCoverageConfig,
    AntennaSpec,
    SpiralAntennaSpec,
    HornAntennaSpec
)
from .core import (
    analyze_coverage,
    CoverageAnalyzer,
    CoverageResult,
    AntennaPattern,
    print_statistics
)

__all__ = [
    'load_uav_config',
    'UAVCoverageConfig',
    'AntennaSpec',
    'SpiralAntennaSpec',
    'HornAntennaSpec',
    'analyze_coverage',
    'CoverageAnalyzer',
    'CoverageResult',
    'AntennaPattern',
    'print_statistics'
]
