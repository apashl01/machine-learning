function config = config_setup()
%CONFIG_SETUP Initialize all configuration parameters for EKF geolocation simulation
%
% Returns:
%   config - struct containing all simulation configuration parameters
%
% Author: Generated MATLAB Script
% Date: October 30, 2025

%% =========================
%  EMITTER CONFIGURATION
%% =========================

config.emitter.lat = 35.0;
config.emitter.lon = -120.0;
config.emitter.alt = 100;

%% =========================
%  EMITTER SIGNAL CONFIGURATION
%% =========================

config.emitter.eirp_dbw = 40.0;           % Effective Isotropic Radiated Power (dBW)
config.emitter.frequency_hz = 3e9;        % Carrier frequency (Hz) - 3 GHz default

fprintf('Emitter Configuration:\n');
fprintf('  Position: Lat=%.6f°, Lon=%.6f°, Alt=%.2f m\n', ...
        config.emitter.lat, config.emitter.lon, config.emitter.alt);
fprintf('  EIRP: %.1f dBW\n', config.emitter.eirp_dbw);
fprintf('  Frequency: %.2f GHz\n\n', config.emitter.frequency_hz / 1e9);

%% =========================
%  INTERFEROMETER CONFIGURATION
%% =========================

% INTERFEROMETER MOUNTING POSITION (in platform body frame)
% Origin is at platform center of gravity (CG)
% Body frame: X-forward, Y-right, Z-down (aerospace convention)

% BELLY-MOUNTED / NADIR-FACING CONFIGURATION
config.interferometer.offset_body = [0.0;   % X: meters forward of CG
                                     0.0;   % Y: meters right of CG
                                     1.5];  % Z: meters below CG (positive Z = down)

% INTERFEROMETER ORIENTATION (additional rotation from body frame)
config.interferometer.orientation = [0.0;   % Roll (deg)
                                     0.0;   % Pitch (deg)
                                     0.0];  % Yaw (deg)

% INTERFEROMETER ARRAY CONFIGURATION
% 4-element array for ambiguity resolution and accuracy
config.interferometer.n_elements = 4;
config.interferometer.c_light_in_per_ns = 11.8028;  % Speed of light in inches/nanosecond

% Non-uniform (Vernier) element spacing - optimized for frequency range
% Positions in inches from first element
lambda_min_inches = config.interferometer.c_light_in_per_ns / (config.emitter.frequency_hz/1e9);
d_short = lambda_min_inches / 2;  % Shortest spacing for ambiguity resolution
config.interferometer.element_positions = [0, d_short, 3.5, 10.0];  % inches

% Phase error at high SNR (baseline system noise)
config.interferometer.phase_error_high_snr_deg = 12;  % degrees

% Measurement validity threshold
config.interferometer.max_incident_angle_deg = 70;  % Ignore measurements beyond this angle

% Antenna pattern file
config.interferometer.antenna_pattern_file = 'antenna_pattern.csv';  % REPLACE WITH YOUR FILE
config.interferometer.antenna_pattern_freq_ghz = config.emitter.frequency_hz / 1e9;

% Calculate all unique baselines
baselines_all = [];
for i = 1:config.interferometer.n_elements
    for j = i+1:config.interferometer.n_elements
        baselines_all = [baselines_all, ...
            config.interferometer.element_positions(j) - config.interferometer.element_positions(i)];
    end
end
config.interferometer.baselines = unique(baselines_all);

% Display interferometer configuration
fprintf('Interferometer Configuration:\n');
fprintf('  Type: Belly-mounted, Nadir-facing, Longitudinally-aligned\n');
fprintf('  Mounting Position (body frame):\n');
fprintf('    X (forward): %.2f m\n', config.interferometer.offset_body(1));
fprintf('    Y (right):   %.2f m\n', config.interferometer.offset_body(2));
fprintf('    Z (down):    %.2f m\n', config.interferometer.offset_body(3));
fprintf('  Measurement Plane: X-Z (longitudinal-vertical)\n');
fprintf('  Orientation (relative to body):\n');
fprintf('    Roll:  %.2f deg\n', config.interferometer.orientation(1));
fprintf('    Pitch: %.2f deg\n', config.interferometer.orientation(2));
fprintf('    Yaw:   %.2f deg\n', config.interferometer.orientation(3));
fprintf('  Array Configuration:\n');
fprintf('    Elements: %d\n', config.interferometer.n_elements);
fprintf('    Element positions: [%.2f, %.2f, %.2f, %.2f] inches\n', ...
            config.interferometer.element_positions);
fprintf('    Longest baseline: %.2f inches (%.1f mm)\n', ...
            max(config.interferometer.baselines), max(config.interferometer.baselines)*25.4);
fprintf('    Shortest baseline: %.3f inches (%.2f mm)\n', ...
            min(config.interferometer.baselines), min(config.interferometer.baselines)*25.4);
fprintf('    Phase error (high SNR): %.1f deg\n', config.interferometer.phase_error_high_snr_deg);
fprintf('    Max incident angle: %.1f deg (measurements beyond this are ignored)\n', ...
        config.interferometer.max_incident_angle_deg);
fprintf('    Antenna pattern file: %s\n\n', config.interferometer.antenna_pattern_file);

%% =========================
%  TRAJECTORY CONFIGURATION
%% =========================

config.trajectory.type = 'figure8';  % Options: 'circle', 'figure8', 'racetrack', 
                                     % 'sturn', 'straight_offset', 'curved_approach'
config.trajectory.standoff_distance_km = 10.0;
config.trajectory.size_scale = 1.5;
config.trajectory.altitude_mean = 3000;      % meters
config.trajectory.altitude_variation = 500;  % meters

fprintf('Trajectory Configuration:\n');
fprintf('  Type: %s\n', config.trajectory.type);
fprintf('  Standoff Distance: %.1f km\n', config.trajectory.standoff_distance_km);
fprintf('  Size Scale: %.2f\n', config.trajectory.size_scale);
fprintf('  Altitude: %.0f ± %.0f m\n\n', ...
        config.trajectory.altitude_mean, config.trajectory.altitude_variation);

%% =========================
%  TUNING CONFIGURATION
%% =========================

config.tuning.run_parameter_sweep = true;

if config.tuning.run_parameter_sweep
    config.tuning.Q_values = [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0];
    config.tuning.P0_values = [1000, 5000, 10000, 20000, 50000];
    config.tuning.R_scale_values = [0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0];
    
    fprintf('Running parameter sweep with:\n');
    fprintf('  Q values: %d options\n', length(config.tuning.Q_values));
    fprintf('  P0 values: %d options\n', length(config.tuning.P0_values));
    fprintf('  R scale values: %d options\n', length(config.tuning.R_scale_values));
    fprintf('  Total combinations: %d\n\n', ...
            length(config.tuning.Q_values) * length(config.tuning.P0_values) * ...
            length(config.tuning.R_scale_values));
else
    config.tuning.Q_values = 0.01;
    config.tuning.P0_values = 10000;
    config.tuning.R_scale_values = 1.0;
    fprintf('Single run mode with default parameters\n\n');
end

%% =========================
%  SIMULATION PARAMETERS
%% =========================

config.sim.dt = 1.0;
config.sim.t_total = 300;
config.sim.time = 0:config.sim.dt:config.sim.t_total;
config.sim.N_steps = length(config.sim.time);
config.sim.random_seed = 42;

% Set random seed for reproducibility
rng(config.sim.random_seed);

% Calculate emitter ECEF position
config.emitter.ecef = lla2ecef([config.emitter.lat, config.emitter.lon, config.emitter.alt]);

%% =========================
%  INITIAL GUESS
%% =========================

config.ekf.initial_offset_km = 5.0;
config.ekf.initial_guess_ecef = config.emitter.ecef + ...
    config.ekf.initial_offset_km * 1000 * [1, 1, 0.5] / norm([1, 1, 0.5]);

fprintf('Configuration setup complete!\n\n');

end
