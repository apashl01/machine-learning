function signal_data = calculate_signal_propagation(config, trajectory)
%CALCULATE_SIGNAL_PROPAGATION Compute received signal strength at each trajectory point
%
% Inputs:
%   config - configuration struct from config_setup()
%   trajectory - trajectory struct from generate_trajectory()
%
% Outputs:
%   signal_data - struct containing:
%       .received_power_dbw - received power at interferometer (dBW) [N_steps x 1]
%       .received_power_watts - received power in watts [N_steps x 1]
%       .path_loss_db - free space path loss (dB) [N_steps x 1]
%       .snr_db - signal-to-noise ratio (dB) [N_steps x 1]
%
% Assumptions:
%   - Emitter always points toward UAV (max gain in UAV direction)
%   - Free space propagation (no multipath, atmospheric losses minimal)
%   - Line of sight exists at all times
%
% Author: Generated MATLAB Script
% Date: October 30, 2025

fprintf('Calculating signal propagation...\n');

N_steps = config.sim.N_steps;

%% Extract Parameters
eirp_dbw = config.emitter.eirp_dbw;
frequency_hz = config.emitter.frequency_hz;
distances_km = trajectory.distances_from_emitter;  % Already calculated in trajectory

% Speed of light
c = 299792458;  % m/s

% Wavelength
lambda = c / frequency_hz;  % meters

fprintf('  Wavelength: %.4f m (%.2f cm)\n', lambda, lambda * 100);

%% Calculate Free Space Path Loss
% FSPL(dB) = 20*log10(d) + 20*log10(f) + 20*log10(4*pi/c)
% Or equivalently: FSPL(dB) = 20*log10(d) + 20*log10(f) - 147.55
% Where d is in meters and f is in Hz

distances_m = distances_km * 1000;  % Convert km to meters

% Free space path loss for each point
signal_data.path_loss_db = 20*log10(distances_m) + 20*log10(frequency_hz) + 20*log10(4*pi/c);

% Alternative formula (should give same result):
% signal_data.path_loss_db = 20*log10(distances_m) + 20*log10(frequency_hz) - 147.55;

%% Calculate Received Power
% P_rx(dBW) = EIRP(dBW) - PathLoss(dB)
signal_data.received_power_dbw = eirp_dbw - signal_data.path_loss_db;

% Convert to watts for convenience
signal_data.received_power_watts = 10.^(signal_data.received_power_dbw / 10);

%% Calculate SNR (Placeholder - requires receiver noise figure)
% For now, assume a typical receiver noise floor
% Thermal noise: N = k * T * B
% where k = Boltzmann constant, T = temperature (K), B = bandwidth (Hz)

% Typical assumptions:
T_kelvin = 290;                    % Room temperature
k_boltzmann = 1.380649e-23;       % Boltzmann constant (J/K)
bandwidth_hz = 1e6;                % Assume 1 MHz bandwidth (adjust as needed)
noise_figure_db = 3;               % Typical receiver noise figure (dB)

% Thermal noise power (dBW)
thermal_noise_dbw = 10*log10(k_boltzmann * T_kelvin * bandwidth_hz);

% Noise floor including receiver noise figure
noise_floor_dbw = thermal_noise_dbw + noise_figure_db;

% SNR at each point
signal_data.snr_db = signal_data.received_power_dbw - noise_floor_dbw;

%% Summary Statistics
fprintf('  Distance range: %.2f - %.2f km\n', min(distances_km), max(distances_km));
fprintf('  Path loss range: %.2f - %.2f dB\n', min(signal_data.path_loss_db), max(signal_data.path_loss_db));
fprintf('  Received power range: %.2f - %.2f dBW\n', ...
        min(signal_data.received_power_dbw), max(signal_data.received_power_dbw));
fprintf('  SNR range: %.2f - %.2f dB\n', min(signal_data.snr_db), max(signal_data.snr_db));
fprintf('  Noise floor: %.2f dBW (%.1f MHz BW, %.1f dB NF)\n\n', ...
        noise_floor_dbw, bandwidth_hz/1e6, noise_figure_db);

%% Verify Line of Sight (Optional Check)
% Check if emitter altitude is below all platform altitudes (should be true for our scenario)
emitter_alt = config.emitter.alt;
min_platform_alt = min(trajectory.platform_alt);

if emitter_alt < min_platform_alt
    fprintf('  Line of sight: CLEAR (emitter below all platform altitudes)\n\n');
else
    warning('  Emitter altitude (%.0f m) may not be below platform (min: %.0f m)\n\n', ...
            emitter_alt, min_platform_alt);
end

fprintf('Signal propagation calculation complete!\n\n');

end
