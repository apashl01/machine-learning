"""
RF Chain Analysis Package

Cascaded RF chain performance analysis including gain, noise figure,
sensitivity, and power tracking through receiver and transmitter chains.
"""

__version__ = "1.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import (
    load_rf_chain_config,
    RFChainConfig,
    ComponentLibrary,
    Component,
    RFChain,
    ChainType,
    AnalysisSettings
)
from .core import RFChainAnalyzer, CascadeResult, PowerPoint

__all__ = [
    'load_rf_chain_config',
    'RFChainConfig',
    'ComponentLibrary',
    'Component',
    'RFChain',
    'ChainType',
    'AnalysisSettings',
    'RFChainAnalyzer',
    'CascadeResult',
    'PowerPoint',
]
