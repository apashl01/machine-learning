"""
RF Chain Analysis Package

Cascaded RF chain performance analysis including:
- Gain and noise figure cascading (Friis formula)
- TX mode: Power tracking with saturation detection
- RX mode: Damage threshold analysis

Matches MATLAB rf_chain analysis functionality.
"""

__version__ = "2.0.0"
__author__ = "Andrew's Analysis Tools"

from .config import (
    load_chain_config,
    load_rf_chain_config,
    ChainConfig,
    Component,
    CableComponent,
    AmplifierComponent,
    AttenuatorComponent,
    AntennaComponent,
    ChainType,
    ComponentType
)
from .core.analyzer import (
    analyze_rf_chain,
    RFChainAnalyzer,
    ChainAnalysisResults,
    MidFreqSummary,
    ComponentContribution,
    print_results_summary,
    print_gain_breakdown_table
)

__all__ = [
    # Config
    'load_chain_config',
    'load_rf_chain_config',
    'ChainConfig',
    'Component',
    'CableComponent',
    'AmplifierComponent',
    'AttenuatorComponent',
    'AntennaComponent',
    'ChainType',
    'ComponentType',
    # Analysis
    'analyze_rf_chain',
    'RFChainAnalyzer',
    'ChainAnalysisResults',
    'MidFreqSummary',
    'ComponentContribution',
    'print_results_summary',
    'print_gain_breakdown_table',
]
