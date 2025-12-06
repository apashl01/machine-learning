"""
Slide generators for each analysis type.
"""

from .title import add_title_slide, add_summary_slide
from .rf_chain import add_rf_chain_slides
from .adc import add_adc_slides
from .direction_finding import add_direction_finding_slides
from .antenna_coverage import add_antenna_coverage_slides
from .ekf_geolocation import add_ekf_geolocation_slides
from .esm import add_esm_slides

__all__ = [
    'add_title_slide',
    'add_summary_slide',
    'add_rf_chain_slides',
    'add_adc_slides',
    'add_direction_finding_slides',
    'add_antenna_coverage_slides',
    'add_ekf_geolocation_slides',
    'add_esm_slides'
]
