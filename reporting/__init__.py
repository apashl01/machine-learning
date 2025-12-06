"""
Reporting Package

Generate PowerPoint design review presentations from analysis results.

Supports:
- RF Chain Analysis
- ADC Analysis
- Direction Finding Analysis
- Antenna Coverage Analysis
- EKF Geolocation Analysis
"""

__version__ = "1.0.0"

from .core import DesignReviewGenerator
from .generators import (
    add_title_slide,
    add_rf_chain_slides,
    add_adc_slides,
    add_direction_finding_slides,
    add_antenna_coverage_slides,
    add_ekf_geolocation_slides,
    add_summary_slide
)

__all__ = [
    'DesignReviewGenerator',
    'add_title_slide',
    'add_rf_chain_slides',
    'add_adc_slides',
    'add_direction_finding_slides',
    'add_antenna_coverage_slides',
    'add_ekf_geolocation_slides',
    'add_summary_slide'
]
