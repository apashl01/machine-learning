"""
Signal Propagation Module

Calculates received signal strength at each trajectory point using:
- Free space path loss (FSPL)
- Thermal noise calculation
- SNR estimation

Matches MATLAB demo/calculate_signal_propagation.m functionality.
"""

import numpy as np
from dataclasses import dataclass


# Physical constants
C_LIGHT = 299792458.0           # Speed of light (m/s)
K_BOLTZMANN = 1.380649e-23      # Boltzmann constant (J/K)


@dataclass
class SignalData:
    """Container for signal propagation data."""
    received_power_dbw: np.ndarray    # Received power (dBW) [N_steps]
    received_power_watts: np.ndarray  # Received power (Watts) [N_steps]
    path_loss_db: np.ndarray          # Free space path loss (dB) [N_steps]
    snr_db: np.ndarray                # Signal-to-noise ratio (dB) [N_steps]
    noise_floor_dbw: float            # Noise floor (dBW)

    def print_summary(self, distances_km: np.ndarray):
        """Print signal propagation summary."""
        print(f"Signal Propagation Summary:")
        print(f"  Distance range: {np.min(distances_km):.2f} - {np.max(distances_km):.2f} km")
        print(f"  Path loss range: {np.min(self.path_loss_db):.2f} - {np.max(self.path_loss_db):.2f} dB")
        print(f"  Received power range: {np.min(self.received_power_dbw):.2f} - "
              f"{np.max(self.received_power_dbw):.2f} dBW")
        print(f"  SNR range: {np.min(self.snr_db):.2f} - {np.max(self.snr_db):.2f} dB")
        print(f"  Noise floor: {self.noise_floor_dbw:.2f} dBW")


def calculate_signal_propagation(config, trajectory) -> SignalData:
    """
    Calculate received signal strength at each trajectory point.

    Assumptions:
    - Emitter always points toward UAV (max gain in UAV direction)
    - Free space propagation (no multipath, atmospheric losses minimal)
    - Line of sight exists at all times

    Args:
        config: SimulationConfig object
        trajectory: TrajectoryData object

    Returns:
        SignalData object with propagation calculations
    """
    print("Calculating signal propagation...")

    n_steps = config.n_steps
    eirp_dbw = config.emitter.eirp_dbw
    frequency_hz = config.emitter.frequency_hz
    distances_km = trajectory.distances_from_emitter

    # Wavelength
    wavelength = C_LIGHT / frequency_hz
    print(f"  Wavelength: {wavelength:.4f} m ({wavelength * 100:.2f} cm)")

    # Convert distances to meters
    distances_m = distances_km * 1000.0

    # Free space path loss
    # FSPL(dB) = 20*log10(d) + 20*log10(f) + 20*log10(4*pi/c)
    path_loss_db = (20 * np.log10(distances_m) +
                   20 * np.log10(frequency_hz) +
                   20 * np.log10(4 * np.pi / C_LIGHT))

    # Received power
    # P_rx(dBW) = EIRP(dBW) - PathLoss(dB)
    received_power_dbw = eirp_dbw - path_loss_db
    received_power_watts = 10.0 ** (received_power_dbw / 10.0)

    # Calculate SNR
    # Thermal noise: N = k * T * B
    T_kelvin = 290.0              # Room temperature
    bandwidth_hz = 1e6            # Assume 1 MHz bandwidth
    noise_figure_db = 3.0         # Typical receiver noise figure

    # Thermal noise power (dBW)
    thermal_noise_dbw = 10 * np.log10(K_BOLTZMANN * T_kelvin * bandwidth_hz)

    # Noise floor including receiver noise figure
    noise_floor_dbw = thermal_noise_dbw + noise_figure_db

    # SNR at each point
    snr_db = received_power_dbw - noise_floor_dbw

    signal_data = SignalData(
        received_power_dbw=received_power_dbw,
        received_power_watts=received_power_watts,
        path_loss_db=path_loss_db,
        snr_db=snr_db,
        noise_floor_dbw=noise_floor_dbw
    )

    signal_data.print_summary(distances_km)
    print(f"  Noise floor: {noise_floor_dbw:.2f} dBW ({bandwidth_hz/1e6:.1f} MHz BW, "
          f"{noise_figure_db:.1f} dB NF)")

    # Verify line of sight
    emitter_alt = config.emitter.alt
    min_platform_alt = np.min(trajectory.platform_alt)

    if emitter_alt < min_platform_alt:
        print(f"  Line of sight: CLEAR (emitter below all platform altitudes)")
    else:
        print(f"  WARNING: Emitter altitude ({emitter_alt:.0f} m) may not be below "
              f"platform (min: {min_platform_alt:.0f} m)")

    print("Signal propagation calculation complete!\n")

    return signal_data
