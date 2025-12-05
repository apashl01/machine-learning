"""
Unit Conversion Utilities

Common unit conversions for RF and ESM analysis.
"""

import math


# =============================================================================
# POWER CONVERSIONS
# =============================================================================

def dbw_to_dbm(power_dbw: float) -> float:
    """Convert dBW to dBm."""
    return power_dbw + 30


def dbm_to_dbw(power_dbm: float) -> float:
    """Convert dBm to dBW."""
    return power_dbm - 30


def watts_to_dbw(power_w: float) -> float:
    """Convert Watts to dBW."""
    if power_w <= 0:
        return -200.0  # Floor value
    return 10 * math.log10(power_w)


def dbw_to_watts(power_dbw: float) -> float:
    """Convert dBW to Watts."""
    return 10 ** (power_dbw / 10)


def watts_to_dbm(power_w: float) -> float:
    """Convert Watts to dBm."""
    return watts_to_dbw(power_w) + 30


def dbm_to_watts(power_dbm: float) -> float:
    """Convert dBm to Watts."""
    return dbw_to_watts(power_dbm - 30)


def mw_to_dbm(power_mw: float) -> float:
    """Convert milliWatts to dBm."""
    if power_mw <= 0:
        return -200.0
    return 10 * math.log10(power_mw)


def dbm_to_mw(power_dbm: float) -> float:
    """Convert dBm to milliWatts."""
    return 10 ** (power_dbm / 10)


# =============================================================================
# FREQUENCY CONVERSIONS
# =============================================================================

def hz_to_ghz(freq_hz: float) -> float:
    """Convert Hz to GHz."""
    return freq_hz / 1e9


def ghz_to_hz(freq_ghz: float) -> float:
    """Convert GHz to Hz."""
    return freq_ghz * 1e9


def hz_to_mhz(freq_hz: float) -> float:
    """Convert Hz to MHz."""
    return freq_hz / 1e6


def mhz_to_hz(freq_mhz: float) -> float:
    """Convert MHz to Hz."""
    return freq_mhz * 1e6


def ghz_to_mhz(freq_ghz: float) -> float:
    """Convert GHz to MHz."""
    return freq_ghz * 1000


def mhz_to_ghz(freq_mhz: float) -> float:
    """Convert MHz to GHz."""
    return freq_mhz / 1000


# =============================================================================
# DISTANCE CONVERSIONS
# =============================================================================

def meters_to_km(dist_m: float) -> float:
    """Convert meters to kilometers."""
    return dist_m / 1000


def km_to_meters(dist_km: float) -> float:
    """Convert kilometers to meters."""
    return dist_km * 1000


def meters_to_nm(dist_m: float) -> float:
    """Convert meters to nautical miles."""
    return dist_m / 1852


def nm_to_meters(dist_nm: float) -> float:
    """Convert nautical miles to meters."""
    return dist_nm * 1852


def meters_to_miles(dist_m: float) -> float:
    """Convert meters to statute miles."""
    return dist_m / 1609.34


def miles_to_meters(dist_miles: float) -> float:
    """Convert statute miles to meters."""
    return dist_miles * 1609.34


def km_to_nm(dist_km: float) -> float:
    """Convert kilometers to nautical miles."""
    return dist_km / 1.852


def nm_to_km(dist_nm: float) -> float:
    """Convert nautical miles to kilometers."""
    return dist_nm * 1.852


# =============================================================================
# TIME CONVERSIONS
# =============================================================================

def us_to_s(time_us: float) -> float:
    """Convert microseconds to seconds."""
    return time_us * 1e-6


def s_to_us(time_s: float) -> float:
    """Convert seconds to microseconds."""
    return time_s * 1e6


def ms_to_s(time_ms: float) -> float:
    """Convert milliseconds to seconds."""
    return time_ms * 1e-3


def s_to_ms(time_s: float) -> float:
    """Convert seconds to milliseconds."""
    return time_s * 1e3


def us_to_ms(time_us: float) -> float:
    """Convert microseconds to milliseconds."""
    return time_us * 1e-3


def ms_to_us(time_ms: float) -> float:
    """Convert milliseconds to microseconds."""
    return time_ms * 1e3


# =============================================================================
# ANGLE CONVERSIONS
# =============================================================================

def deg_to_rad(angle_deg: float) -> float:
    """Convert degrees to radians."""
    return angle_deg * math.pi / 180


def rad_to_deg(angle_rad: float) -> float:
    """Convert radians to degrees."""
    return angle_rad * 180 / math.pi


# =============================================================================
# RF-SPECIFIC UTILITIES
# =============================================================================

def wavelength_to_freq(wavelength_m: float) -> float:
    """Convert wavelength (meters) to frequency (Hz)."""
    c = 299792458  # Speed of light m/s
    return c / wavelength_m


def freq_to_wavelength(freq_hz: float) -> float:
    """Convert frequency (Hz) to wavelength (meters)."""
    c = 299792458
    return c / freq_hz


def linear_to_db(value: float) -> float:
    """Convert linear power ratio to dB."""
    if value <= 0:
        return -200.0
    return 10 * math.log10(value)


def db_to_linear(value_db: float) -> float:
    """Convert dB to linear power ratio."""
    return 10 ** (value_db / 10)


def linear_to_db_voltage(value: float) -> float:
    """Convert linear voltage ratio to dB."""
    if value <= 0:
        return -200.0
    return 20 * math.log10(value)


def db_to_linear_voltage(value_db: float) -> float:
    """Convert dB to linear voltage ratio."""
    return 10 ** (value_db / 20)


# =============================================================================
# TEMPERATURE CONVERSIONS
# =============================================================================

def celsius_to_kelvin(temp_c: float) -> float:
    """Convert Celsius to Kelvin."""
    return temp_c + 273.15


def kelvin_to_celsius(temp_k: float) -> float:
    """Convert Kelvin to Celsius."""
    return temp_k - 273.15


def fahrenheit_to_celsius(temp_f: float) -> float:
    """Convert Fahrenheit to Celsius."""
    return (temp_f - 32) * 5 / 9


def celsius_to_fahrenheit(temp_c: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return temp_c * 9 / 5 + 32
