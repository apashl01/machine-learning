function [measurements, interferometer_data] = interferometer_model(config, trajectory, signal_data)
%INTERFEROMETER_MODEL Calculate angle measurements with realistic errors
%
% This function implements a high-fidelity interferometer model including:
%   - Incident angle calculation at each time step
%   - Antenna pattern gain (angle-dependent)
%   - SNR-dependent phase error
%   - Geometry-dependent angle accuracy
%
% Based on 4-element RF interferometer analysis with Vernier spacing
%
% Inputs:
%   config - configuration struct from config_setup()
%   trajectory - trajectory struct from generate_trajectory()
%   signal_data - signal propagation data from calculate_signal_propagation()
%
% Outputs:
%   measurements - angle measurements in radians [N_steps x 1]
%   interferometer_data - struct containing detailed analysis:
%       .incident_angles - incident angle from boresight (degrees) [N_steps x 1]
%       .antenna_gain_db - antenna gain at each angle (dB) [N_steps x 1]
%       .snr_db - signal-to-noise ratio (dB) [N_steps x 1]
%       .phase_error_deg - phase measurement error (degrees) [N_steps x 1]
%       .angle_error_deg - angle measurement error (degrees) [N_steps x 1]
%       .angle_error_1sigma_rad - 1-sigma angle error (radians) [N_steps x 1]
%       .measurements_true - true angles without noise (radians) [N_steps x 1]
%
% Author: Generated MATLAB Script
% Date: October 30, 2025

fprintf('Computing interferometer measurements with high-fidelity model...\n');

N_steps = config.sim.N_steps;

%% Load Antenna Pattern
antenna_pattern_file = config.interferometer.antenna_pattern_file;

fprintf('  Loading antenna pattern from: %s\n', antenna_pattern_file);

if ~isfile(antenna_pattern_file)
    warning('Antenna pattern file not found. Using idealized cos-squared pattern.');
    % Idealized antenna pattern: cos^2 approximation
    antenna_angles = 0:1:90;
    antenna_gain_db = 10*log10(cosd(antenna_angles).^2);  % cos-squared pattern
    antenna_gain_db(antenna_gain_db < -40) = -40;  % Limit to -40 dB
else
    % Load CSV file
    antenna_data = readmatrix(antenna_pattern_file);
    
    % Extract columns: angle and gain in dB
    all_angles = antenna_data(:, 1);
    all_gains = antenna_data(:, 2);
    
    % Extract 0:90 degrees
    idx_0_90 = (all_angles >= 0) & (all_angles <= 90);
    angles_0_90 = all_angles(idx_0_90);
    gains_0_90 = all_gains(idx_0_90);
    
    % Extract 270:360 degrees and convert to 90:0 (mirror)
    idx_270_360 = (all_angles >= 270) & (all_angles <= 360);
    angles_270_360 = 360 - all_angles(idx_270_360);
    gains_270_360 = all_gains(idx_270_360);
    
    % Combine and sort
    antenna_angles = [angles_0_90; angles_270_360];
    antenna_gain_db = [gains_0_90; gains_270_360];
    [antenna_angles, sort_idx] = sort(antenna_angles);
    antenna_gain_db = antenna_gain_db(sort_idx);
    
    fprintf('  Antenna pattern loaded: %d points from 0° to %.1f°\n', ...
        length(antenna_angles), max(antenna_angles));
end

% Create interpolation function with proper handling of >90 degree angles
% For angles beyond the pattern range, use a very low gain value
antenna_gain_interp = @(angle) interp1(antenna_angles, antenna_gain_db, ...
    min(abs(angle), 90), 'linear', -40);  % Cap at 90° and use -40 dB for out-of-range

% Store antenna pattern for plotting
interferometer_data.antenna_pattern_angles = antenna_angles;
interferometer_data.antenna_pattern_gain = antenna_gain_db;

%% Extract Parameters
c_light_in_per_ns = config.interferometer.c_light_in_per_ns;
phase_error_baseline = config.interferometer.phase_error_high_snr_deg;
D_max = max(config.interferometer.baselines);  % Longest baseline for accuracy
frequency_hz = config.emitter.frequency_hz;

fprintf('  Frequency: %.2f GHz\n', frequency_hz/1e9);
fprintf('  Longest baseline: %.2f inches (%.1f mm)\n', D_max, D_max*25.4);
fprintf('  Baseline phase error: %.1f deg\n', phase_error_baseline);

%% Initialize Output Arrays
interferometer_data.incident_angles = zeros(N_steps, 1);
interferometer_data.antenna_gain_db = zeros(N_steps, 1);
interferometer_data.snr_db = zeros(N_steps, 1);
interferometer_data.phase_error_deg = zeros(N_steps, 1);
interferometer_data.angle_error_deg = zeros(N_steps, 1);
interferometer_data.angle_error_1sigma_rad = zeros(N_steps, 1);
interferometer_data.measurements_true = zeros(N_steps, 1);
interferometer_data.measurement_valid = false(N_steps, 1);  % Validity flag
measurements = zeros(N_steps, 1);

%% Calculate Measurements for Each Time Step
for i = 1:N_steps
    % Get vector from interferometer to emitter in body frame
    r_ecef = config.emitter.ecef - trajectory.interferometer_ecef(i,:);
    
    R_ecef_to_ned = ecef2nedRotation(trajectory.platform_lat(i), trajectory.platform_lon(i));
    r_ned = R_ecef_to_ned * r_ecef';
    
    R_ned_to_body = ned2bodyRotation(trajectory.platform_pitch(i), ...
                                     trajectory.platform_roll(i), ...
                                     trajectory.platform_yaw(i));
    r_body = R_ned_to_body * r_ned;
    
    % Apply interferometer orientation
    R_interfero = interferometerOrientationRotation(config.interferometer.orientation);
    r_interfero = R_interfero * r_body;
    
    % True angle measurement in interferometer frame (X-Z plane)
    angle_true_rad = atan2(r_interfero(3), r_interfero(1));
    interferometer_data.measurements_true(i) = angle_true_rad;
    
    % Calculate incident angle from boresight
    % Boresight is [0, 0, 1] (down) in interferometer frame
    boresight = [0; 0; 1];
    cos_incident = dot(r_interfero, boresight) / norm(r_interfero);
    incident_angle_deg = acosd(cos_incident);
    interferometer_data.incident_angles(i) = incident_angle_deg;
    
    % Check if measurement is valid (within acceptable incident angle range)
    if incident_angle_deg <= config.interferometer.max_incident_angle_deg
        interferometer_data.measurement_valid(i) = true;
    end
    
    % Get antenna gain at this incident angle
    gain_db = antenna_gain_interp(incident_angle_deg);
    interferometer_data.antenna_gain_db(i) = gain_db;
    
    % Calculate SNR at this time step
    % SNR = Received Power + Antenna Gain - Noise Floor (all in dB)
    % Convert signal_data from dBW to dBm for consistency
    received_power_dbm = signal_data.received_power_dbw(i) + 30;  % dBW to dBm
    noise_floor_dbm = 10*log10(1.380649e-23 * 290 * 1e6) + 30 + 3;  % Thermal + NF, in dBm
    
    snr_db = received_power_dbm + gain_db - noise_floor_dbm;
    interferometer_data.snr_db(i) = snr_db;
    snr_linear = 10^(snr_db/10);
    
    % Calculate phase error (SNR-dependent)
    % At high SNR (>20 dB): phase error = baseline value
    % At low SNR: phase error increases as 1/sqrt(SNR)
    if snr_linear > 100  % 20 dB threshold
        phase_error_deg = phase_error_baseline;
    else
        phase_error_deg = phase_error_baseline * sqrt(100 / max(snr_linear, 1));
    end
    interferometer_data.phase_error_deg(i) = phase_error_deg;
    
    % Calculate angle measurement error
    % Formula from reference: angle_error = c * phase_error / (2π * D * f * cos(incident_angle))
    % where c is in inches/ns, D is baseline in inches, f is in GHz
    phase_error_rad = phase_error_deg * pi / 180;
    
    % Denominator includes cos(incident_angle) - error grows at large incident angles
    angle_error_rad = abs(c_light_in_per_ns * phase_error_rad / ...
        (2*pi * D_max * (frequency_hz/1e9) * cosd(incident_angle_deg)));
    
    interferometer_data.angle_error_deg(i) = angle_error_rad * 180 / pi;
    interferometer_data.angle_error_1sigma_rad(i) = angle_error_rad;
    
    % Add noise to measurement
    % This is the 1D angle measurement in the X-Z plane
    measurements(i) = angle_true_rad + angle_error_rad * randn();
end

%% Summary Statistics
n_valid = sum(interferometer_data.measurement_valid);
n_invalid = N_steps - n_valid;

fprintf('\nInterferometer Performance Summary:\n');
fprintf('  Incident angle range: %.1f° to %.1f°\n', ...
        min(interferometer_data.incident_angles), max(interferometer_data.incident_angles));
fprintf('  Valid measurements: %d / %d (%.1f%%)\n', ...
        n_valid, N_steps, 100*n_valid/N_steps);
fprintf('  Rejected (>%.1f°): %d (%.1f%%)\n', ...
        config.interferometer.max_incident_angle_deg, n_invalid, 100*n_invalid/N_steps);
fprintf('  SNR range: %.1f to %.1f dB\n', ...
        min(interferometer_data.snr_db), max(interferometer_data.snr_db));
fprintf('  Phase error range: %.2f° to %.2f°\n', ...
        min(interferometer_data.phase_error_deg), max(interferometer_data.phase_error_deg));
fprintf('  Angle error range: %.4f° to %.4f°\n', ...
        min(interferometer_data.angle_error_deg), max(interferometer_data.angle_error_deg));

% Find best and worst accuracy points
[min_error, min_idx] = min(interferometer_data.angle_error_deg);
[max_error, max_idx] = max(interferometer_data.angle_error_deg);

fprintf('\n  Best accuracy: %.4f° at t=%.0fs (incident=%.1f°, SNR=%.1f dB)\n', ...
        min_error, config.sim.time(min_idx), ...
        interferometer_data.incident_angles(min_idx), interferometer_data.snr_db(min_idx));
fprintf('  Worst accuracy: %.4f° at t=%.0fs (incident=%.1f°, SNR=%.1f dB)\n\n', ...
        max_error, config.sim.time(max_idx), ...
        interferometer_data.incident_angles(max_idx), interferometer_data.snr_db(max_idx));

fprintf('Interferometer model complete!\n\n');

end

%% Helper Functions
function R = ecef2nedRotation(lat, lon)
    lat_rad = lat * pi/180;
    lon_rad = lon * pi/180;
    R = [-sin(lat_rad)*cos(lon_rad), -sin(lat_rad)*sin(lon_rad), cos(lat_rad);
         -sin(lon_rad),               cos(lon_rad),              0;
         -cos(lat_rad)*cos(lon_rad), -cos(lat_rad)*sin(lon_rad), -sin(lat_rad)];
end

function R = ned2bodyRotation(pitch, roll, yaw)
    pitch_rad = pitch * pi/180;
    roll_rad = roll * pi/180;
    yaw_rad = yaw * pi/180;
    R_yaw = [cos(yaw_rad), sin(yaw_rad), 0; -sin(yaw_rad), cos(yaw_rad), 0; 0, 0, 1];
    R_pitch = [cos(pitch_rad), 0, -sin(pitch_rad); 0, 1, 0; sin(pitch_rad), 0, cos(pitch_rad)];
    R_roll = [1, 0, 0; 0, cos(roll_rad), sin(roll_rad); 0, -sin(roll_rad), cos(roll_rad)];
    R = R_roll * R_pitch * R_yaw;
end

function R = interferometerOrientationRotation(orientation_deg)
    roll_rad = orientation_deg(1) * pi/180;
    pitch_rad = orientation_deg(2) * pi/180;
    yaw_rad = orientation_deg(3) * pi/180;
    R_yaw = [cos(yaw_rad), sin(yaw_rad), 0; -sin(yaw_rad), cos(yaw_rad), 0; 0, 0, 1];
    R_pitch = [cos(pitch_rad), 0, -sin(pitch_rad); 0, 1, 0; sin(pitch_rad), 0, cos(pitch_rad)];
    R_roll = [1, 0, 0; 0, cos(roll_rad), sin(roll_rad); 0, -sin(roll_rad), cos(roll_rad)];
    R = R_roll * R_pitch * R_yaw;
end
