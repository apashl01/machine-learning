"""
System Configuration Package

Provides shared configuration across all EW analysis packages.
Changes to system_config.yaml propagate to:
- ESM Analysis
- Direction Finding Analysis
- EKF Geolocation
- RF Chain Analysis
- ADC Analysis

Key features:
- Single source of truth for system parameters
- Noise floor calculation from ADC + RF chain specs
- Interferometer configuration shared across DF and EKF
- Frequency-dependent parameter lookup
"""

__version__ = "1.0.0"

from .loader import (
    load_system_config,
    SystemConfig,
    ADCConfig,
    RFChainConfig,
    InterferometerConfig,
    AntennaConfig
)
from .noise import (
    calculate_system_noise_floor,
    calculate_sensitivity,
    calculate_multiband_noise_floor,
    NoiseFloorResult,
    MultiBandNoiseResult
)
from .compliance import (
    check_compliance,
    load_requirements,
    generate_compliance_report,
    ComplianceResult,
    RequirementCheck
)

__all__ = [
    'load_system_config',
    'SystemConfig',
    'ADCConfig',
    'RFChainConfig',
    'InterferometerConfig',
    'AntennaConfig',
    'calculate_system_noise_floor',
    'calculate_sensitivity',
    'calculate_multiband_noise_floor',
    'NoiseFloorResult',
    'MultiBandNoiseResult',
    'check_compliance',
    'load_requirements',
    'generate_compliance_report',
    'ComplianceResult',
    'RequirementCheck'
]
