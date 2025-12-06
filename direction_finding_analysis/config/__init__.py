"""Direction Finding Configuration Module"""

from .loader import (
    load_interferometer_config,
    load_from_system_config,
    InterferometerConfig
)

__all__ = [
    'load_interferometer_config',
    'load_from_system_config',
    'InterferometerConfig'
]
