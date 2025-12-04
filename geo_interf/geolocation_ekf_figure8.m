%% EKF Parameter Tuning for Single-Platform 3D Geolocation
% Enhanced with Figure-8 trajectory and configurable standoff distance
% Author: Generated MATLAB Script
% Date: October 28, 2025

clear all; close all; clc;

%% =========================
%  TRAJECTORY CONFIGURATION
%% =========================

% TRAJECTORY CONTROL PARAMETERS
TRAJECTORY_TYPE = 'figure8';  % Options: 'circle', 'figure8', 'racetrack'
STANDOFF_DISTANCE_KM = 10.0;   % Minimum distance from emitter (km)
                               % Larger values keep platform farther from emitter
                               % Recommended range: 5-20 km for good geometry

% Additional trajectory parameters
TRAJECTORY_SIZE_SCALE = 1.5;   % Scale factor for trajectory size (multiplier)
                               % 1.0 = nominal, 1.5 = 50% larger, etc.
ALTITUDE_MEAN = 3000;          % Mean platform altitude (meters)
ALTITUDE_VARIATION = 500;      % Altitude oscillation amplitude (meters)

fprintf('Trajectory Configuration:\n');
fprintf('  Type: %s\n', TRAJECTORY_TYPE);
fprintf('  Standoff Distance: %.1f km\n', STANDOFF_DISTANCE_KM);
fprintf('  Size Scale: %.2f\n', TRAJECTORY_SIZE_SCALE);
fprintf('  Altitude: %.0f ± %.0f m\n\n', ALTITUDE_MEAN, ALTITUDE_VARIATION);

%% =========================
%  TUNING CONFIGURATION
%% =========================

% Set to true to run parameter sweep, false for single run
RUN_PARAMETER_SWEEP = false;  % Set to true for full parameter analysis

% Define parameter ranges to test
if RUN_PARAMETER_SWEEP
    Q_values = [0.001, 0.01, 0.1, 1.0, 10.0];
    P0_values = [1000, 5000, 10000, 20000, 50000];
    R_scale_values = [0.5, 0.8, 1.0, 1.2, 1.5];
    
    fprintf('Running parameter sweep with:\n');
    fprintf('  Q values: %d options\n', length(Q_values));
    fprintf('  P0 values: %d options\n', length(P0_values));
    fprintf('  R scale values: %d options\n', length(R_scale_values));
    fprintf('  Total combinations: %d\n\n', length(Q_values)*length(P0_values)*length(R_scale_values));
else
    % Single run with default/optimized parameters
    Q_values = 0.01;
    P0_values = 10000;
    R_scale_values = 1.0;
    fprintf('Single run mode with default parameters\n\n');
end

%% =========================
%  SIMULATION PARAMETERS
%% =========================

% Time parameters
dt = 1.0;                    % Time step (seconds)
t_total = 300;               % Total simulation time (seconds)
time = 0:dt:t_total;
N_steps = length(time);

% Random seed for reproducibility
rng(42);

%% =========================
%  TRUE EMITTER POSITION
%% =========================

% Ground-based emitter location (Geodetic coordinates)
emitter_lat = 35.0;          % Latitude (degrees)
emitter_lon = -120.0;        % Longitude (degrees)
emitter_alt = 100;           % Altitude (meters above WGS84 ellipsoid)

% Convert emitter to ECEF coordinates
emitter_ecef = lla2ecef([emitter_lat, emitter_lon, emitter_alt]);

fprintf('True Emitter Position:\n');
fprintf('  Lat: %.6f deg, Lon: %.6f deg, Alt: %.2f m\n', ...
        emitter_lat, emitter_lon, emitter_alt);
fprintf('  ECEF: [%.2f, %.2f, %.2f] m\n\n', emitter_ecef);

%% =========================
%  PLATFORM TRAJECTORY
%% =========================

% Pre-allocate trajectory arrays
platform_lat = zeros(N_steps, 1);
platform_lon = zeros(N_steps, 1);
platform_alt = zeros(N_steps, 1);
platform_pitch = zeros(N_steps, 1);
platform_roll = zeros(N_steps, 1);
platform_yaw = zeros(N_steps, 1);

% Generate trajectory based on selected type
switch lower(TRAJECTORY_TYPE)
    case 'figure8'
        fprintf('Generating Figure-8 trajectory...\n');
        
        % Figure-8 parameters (Lemniscate of Gerono)
        % The figure-8 is centered offset from the emitter
        omega = 2*pi / t_total;  % Complete one figure-8 per simulation
        
        % Base size of figure-8 (before scaling)
        a_base = STANDOFF_DISTANCE_KM / 111.0;  % Semi-major axis in degrees lat
        b_base = STANDOFF_DISTANCE_KM / (111.0 * cosd(emitter_lat));  % Semi-minor axis in degrees lon
        
        % Apply size scaling
        a = a_base * TRAJECTORY_SIZE_SCALE;
        b = b_base * TRAJECTORY_SIZE_SCALE;
        
        % Offset center of figure-8 from emitter to maintain standoff
        center_offset_lat = STANDOFF_DISTANCE_KM / 111.0;
        center_offset_lon = 0;
        
        platform_center_lat = emitter_lat + center_offset_lat;
        platform_center_lon = emitter_lon + center_offset_lon;
        
        for i = 1:N_steps
            t = time(i);
            theta = omega * t;
            
            % Parametric equations for figure-8 (Lemniscate)
            % x(t) = a * sin(t)
            % y(t) = b * sin(t) * cos(t) = (b/2) * sin(2t)
            delta_lat = a * sin(theta);
            delta_lon = b * sin(2*theta) / 2;
            
            platform_lat(i) = platform_center_lat + delta_lat;
            platform_lon(i) = platform_center_lon + delta_lon;
            platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(3*theta);
            
            % Attitude: yaw follows velocity direction
            % Velocity derivatives: dx/dt = a*cos(t), dy/dt = b*cos(2t)
            vx = a * cos(theta);
            vy = b * cos(2*theta);
            platform_yaw(i) = atan2d(vy, vx);
            
            % Dynamic pitch and roll based on trajectory curvature
            platform_pitch(i) = 3.0 * sin(theta) * cos(theta);
            platform_roll(i) = 2.0 * sin(2*theta);
        end
        
    case 'circle'
        fprintf('Generating Circular trajectory...\n');
        
        % Circular trajectory parameters
        radius_lat = STANDOFF_DISTANCE_KM / 111.0;
        radius_lon = STANDOFF_DISTANCE_KM / (111.0 * cosd(emitter_lat));
        radius = (radius_lat + radius_lon) / 2 * TRAJECTORY_SIZE_SCALE;
        
        omega = 2*pi / t_total;
        
        % Center circle offset from emitter
        platform_center_lat = emitter_lat + STANDOFF_DISTANCE_KM / 111.0;
        platform_center_lon = emitter_lon + STANDOFF_DISTANCE_KM / (111.0 * cosd(emitter_lat));
        
        for i = 1:N_steps
            t = time(i);
            theta = omega * t;
            
            delta_lat = radius * cos(theta);
            delta_lon = radius * sin(theta);
            
            platform_lat(i) = platform_center_lat + delta_lat;
            platform_lon(i) = platform_center_lon + delta_lon;
            platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(2*theta);
            
            platform_yaw(i) = rad2deg(theta + pi/2);
            platform_pitch(i) = 2.0 * sin(theta);
            platform_roll(i) = 1.5 * cos(1.5*theta);
        end
        
    case 'racetrack'
        fprintf('Generating Racetrack trajectory...\n');
        
        % Racetrack (oval) trajectory
        straight_length = STANDOFF_DISTANCE_KM * TRAJECTORY_SIZE_SCALE / 111.0;
        turn_radius = STANDOFF_DISTANCE_KM / (2 * 111.0);
        
        % Center racetrack offset from emitter
        platform_center_lat = emitter_lat + STANDOFF_DISTANCE_KM / 111.0;
        platform_center_lon = emitter_lon;
        
        % Compute path length for velocity
        turn_length = pi * turn_radius;  % Half circle at each end
        total_length = 2 * straight_length + 2 * turn_length;
        velocity = total_length / t_total;  % degrees per second
        
        for i = 1:N_steps
            t = time(i);
            distance = mod(velocity * t, total_length);
            
            if distance < straight_length
                % First straight section
                platform_lat(i) = platform_center_lat + distance;
                platform_lon(i) = platform_center_lon - turn_radius;
                platform_yaw(i) = 0;
                
            elseif distance < straight_length + turn_length
                % First turn
                theta = (distance - straight_length) / turn_radius;
                platform_lat(i) = platform_center_lat + straight_length + turn_radius * sin(theta);
                platform_lon(i) = platform_center_lon - turn_radius * cos(theta);
                platform_yaw(i) = rad2deg(theta);
                
            elseif distance < 2*straight_length + turn_length
                % Second straight section
                platform_lat(i) = platform_center_lat + straight_length - (distance - straight_length - turn_length);
                platform_lon(i) = platform_center_lon + turn_radius;
                platform_yaw(i) = 180;
                
            else
                % Second turn
                theta = (distance - 2*straight_length - turn_length) / turn_radius;
                platform_lat(i) = platform_center_lat - turn_radius * sin(theta);
                platform_lon(i) = platform_center_lon + turn_radius * cos(theta);
                platform_yaw(i) = 180 + rad2deg(theta);
            end
            
            platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(2*pi*t/t_total);
            platform_pitch(i) = 2.0 * sin(2*pi*t/t_total);
            platform_roll(i) = 1.5 * cos(3*2*pi*t/t_total);
        end
        
    otherwise
        error('Unknown trajectory type: %s', TRAJECTORY_TYPE);
end

% Convert platform trajectory to ECEF
platform_ecef = zeros(N_steps, 3);
for i = 1:N_steps
    platform_ecef(i,:) = lla2ecef([platform_lat(i), platform_lon(i), platform_alt(i)]);
end

% Calculate and display actual distances from emitter
distances_from_emitter = zeros(N_steps, 1);
for i = 1:N_steps
    distances_from_emitter(i) = norm(platform_ecef(i,:) - emitter_ecef) / 1000;  % km
end

min_distance = min(distances_from_emitter);
max_distance = max(distances_from_emitter);
mean_distance = mean(distances_from_emitter);

fprintf('Trajectory generated successfully!\n');
fprintf('  Distance from emitter:\n');
fprintf('    Minimum: %.2f km\n', min_distance);
fprintf('    Maximum: %.2f km\n', max_distance);
fprintf('    Mean: %.2f km\n\n', mean_distance);

%% =========================
%  1D INTERFEROMETER MODEL
%% =========================

% Measurement noise parameters
sigma_angle = 0.5;  % Angle measurement noise std dev (degrees)

% Pre-allocate measurement array
measurements = zeros(N_steps, 1);

% Generate true measurements
for i = 1:N_steps
    r_ecef = emitter_ecef - platform_ecef(i,:);
    
    R_ecef_to_ned = ecef2nedRotation(platform_lat(i), platform_lon(i));
    r_ned = R_ecef_to_ned * r_ecef';
    
    R_ned_to_body = ned2bodyRotation(platform_pitch(i), platform_roll(i), platform_yaw(i));
    r_body = R_ned_to_body * r_ned;
    
    angle_true = atan2d(r_body(3), r_body(1));
    measurements(i) = angle_true + sigma_angle * randn();
end

fprintf('Generated %d measurements over %.1f seconds\n\n', N_steps, t_total);

%% =========================
%  PARAMETER SWEEP OR SINGLE RUN
%% =========================

% Initial guess (offset from true position)
initial_offset_km = 5.0;
initial_guess_ecef = emitter_ecef + initial_offset_km * 1000 * [1, 1, 0.5] / norm([1, 1, 0.5]);

if RUN_PARAMETER_SWEEP
    %% RUN PARAMETER SWEEP
    n_combinations = length(Q_values) * length(P0_values) * length(R_scale_values);
    results = struct('Q', {}, 'P0', {}, 'R_scale', {}, ...
                     'final_error', {}, 'mean_error', {}, 'convergence_time', {}, ...
                     'final_uncertainty', {}, 'mean_innovation', {});
    
    result_idx = 0;
    fprintf('Starting parameter sweep...\n');
    fprintf('Progress: ');
    
    for q_idx = 1:length(Q_values)
        for p0_idx = 1:length(P0_values)
            for r_idx = 1:length(R_scale_values)
                result_idx = result_idx + 1;
                
                Q_val = Q_values(q_idx);
                P0_val = P0_values(p0_idx);
                R_scale = R_scale_values(r_idx);
                
                if mod(result_idx, 10) == 0
                    fprintf('%d/%d ', result_idx, n_combinations);
                end
                
                [x_hist, P_hist, innov_hist] = runEKF(initial_guess_ecef, ...
                    Q_val, P0_val, R_scale, sigma_angle, ...
                    measurements, platform_ecef, platform_lat, platform_lon, ...
                    platform_pitch, platform_roll, platform_yaw, emitter_ecef);
                
                position_errors = zeros(N_steps, 1);
                for k = 1:N_steps
                    position_errors(k) = norm(x_hist(k,:)' - emitter_ecef');
                end
                
                final_error = position_errors(end);
                mean_error = mean(position_errors(ceil(N_steps/2):end));
                
                convergence_idx = find(position_errors < 500, 1, 'first');
                if ~isempty(convergence_idx)
                    convergence_time = time(convergence_idx);
                else
                    convergence_time = inf;
                end
                
                final_uncertainty = sqrt(sum(P_hist(end,:)));
                mean_innovation = mean(abs(innov_hist(2:end))) * 180/pi;
                
                results(result_idx).Q = Q_val;
                results(result_idx).P0 = P0_val;
                results(result_idx).R_scale = R_scale;
                results(result_idx).final_error = final_error;
                results(result_idx).mean_error = mean_error;
                results(result_idx).convergence_time = convergence_time;
                results(result_idx).final_uncertainty = final_uncertainty;
                results(result_idx).mean_innovation = mean_innovation;
            end
        end
    end
    
    fprintf('\nParameter sweep complete!\n\n');
    
    %% ANALYZE RESULTS
    final_errors = [results.final_error];
    mean_errors = [results.mean_error];
    convergence_times = [results.convergence_time];
    
    composite_score = normalize(final_errors, 'range') * 0.4 + ...
                      normalize(mean_errors, 'range') * 0.3 + ...
                      normalize(convergence_times, 'range') * 0.3;
    [~, best_composite_idx] = min(composite_score);
    
    fprintf('BEST CONFIGURATION (Composite Score):\n');
    fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
            results(best_composite_idx).Q, results(best_composite_idx).P0, ...
            results(best_composite_idx).R_scale);
    fprintf('  Final error: %.2f m, Convergence: %.1f s\n\n', ...
            results(best_composite_idx).final_error, ...
            results(best_composite_idx).convergence_time);
    
    best_Q = results(best_composite_idx).Q;
    best_P0 = results(best_composite_idx).P0;
    best_R_scale = results(best_composite_idx).R_scale;
    
else
    %% SINGLE RUN
    best_Q = Q_values;
    best_P0 = P0_values;
    best_R_scale = R_scale_values;
end

%% =========================
%  RUN WITH BEST/DEFAULT PARAMETERS
%% =========================

fprintf('Running EKF simulation...\n');

[x_history, P_history, innovation_history] = runEKF(initial_guess_ecef, ...
    best_Q, best_P0, best_R_scale, sigma_angle, ...
    measurements, platform_ecef, platform_lat, platform_lon, ...
    platform_pitch, platform_roll, platform_yaw, emitter_ecef);

% Compute errors
position_errors = zeros(N_steps, 1);
for k = 1:N_steps
    position_errors(k) = norm(x_history(k,:)' - emitter_ecef');
end

% Convert to LLA
estimated_lla = zeros(N_steps, 3);
for k = 1:N_steps
    estimated_lla(k,:) = ecef2lla(x_history(k,:));
end

final_error = position_errors(end);
final_uncertainty = sqrt(sum(P_history(end,:)));

fprintf('Simulation complete!\n\n');
fprintf('Final Results:\n');
fprintf('  Position error: %.2f m\n', final_error);
fprintf('  Position uncertainty (1-sigma): %.2f m\n', final_uncertainty);
fprintf('  Final estimate: Lat=%.6f deg, Lon=%.6f deg, Alt=%.2f m\n\n', ...
        estimated_lla(end,1), estimated_lla(end,2), estimated_lla(end,3));

%% =========================
%  VISUALIZATION
%% =========================

%% Figure 1: 3D Trajectory and Geometry
figure('Position', [50, 50, 1400, 900]);

% 3D Trajectory
subplot(2,2,1)
plot3(platform_lon, platform_lat, platform_alt, 'b-', 'LineWidth', 2);
hold on;
plot3(emitter_lon, emitter_lat, emitter_alt, 'r*', 'MarkerSize', 20, 'LineWidth', 3);
plot3(estimated_lla(:,2), estimated_lla(:,1), estimated_lla(:,3), 'g.', 'MarkerSize', 3);
plot3(estimated_lla(end,2), estimated_lla(end,1), estimated_lla(end,3), ...
      'go', 'MarkerSize', 12, 'LineWidth', 3);

% Mark start point
plot3(platform_lon(1), platform_lat(1), platform_alt(1), ...
      'bs', 'MarkerSize', 12, 'LineWidth', 2);

grid on;
xlabel('Longitude (deg)');
ylabel('Latitude (deg)');
zlabel('Altitude (m)');
title(sprintf('%s Trajectory and Emitter Position', TRAJECTORY_TYPE));
legend('Platform Path', 'True Emitter', 'Estimates', 'Final Estimate', 'Start', ...
       'Location', 'best');
view(-45, 25);

% Top-down view
subplot(2,2,2)
plot(platform_lon, platform_lat, 'b-', 'LineWidth', 2);
hold on;
plot(emitter_lon, emitter_lat, 'r*', 'MarkerSize', 20, 'LineWidth', 3);
plot(estimated_lla(:,2), estimated_lla(:,1), 'g.', 'MarkerSize', 3);
plot(estimated_lla(end,2), estimated_lla(end,1), 'go', 'MarkerSize', 12, 'LineWidth', 3);
plot(platform_lon(1), platform_lat(1), 'bs', 'MarkerSize', 12, 'LineWidth', 2);

% Draw standoff circle for reference
theta_circle = linspace(0, 2*pi, 100);
standoff_lat = emitter_lat + (STANDOFF_DISTANCE_KM/111.0) * sin(theta_circle);
standoff_lon = emitter_lon + (STANDOFF_DISTANCE_KM/(111.0*cosd(emitter_lat))) * cos(theta_circle);
plot(standoff_lon, standoff_lat, 'k--', 'LineWidth', 1);

grid on;
xlabel('Longitude (deg)');
ylabel('Latitude (deg)');
title('Top-Down View');
legend('Platform', 'Emitter', 'Estimates', 'Final', 'Start', ...
       sprintf('%.1f km Standoff', STANDOFF_DISTANCE_KM), 'Location', 'best');
axis equal;

% Position Error over Time
subplot(2,2,3)
plot(time, position_errors, 'b-', 'LineWidth', 2);
hold on;
uncertainty_bound = sqrt(sum(P_history, 2));
plot(time, uncertainty_bound, 'r--', 'LineWidth', 2);
grid on;
xlabel('Time (s)');
ylabel('Error (m)');
title('Position Estimation Error');
legend('Actual Error', '1-\sigma Uncertainty', 'Location', 'best');

% Distance from Emitter
subplot(2,2,4)
plot(time, distances_from_emitter, 'b-', 'LineWidth', 2);
hold on;
yline(STANDOFF_DISTANCE_KM, 'r--', 'LineWidth', 1.5, 'Label', 'Nominal Standoff');
yline(min_distance, 'g:', 'LineWidth', 1, 'Label', sprintf('Min: %.1f km', min_distance));
yline(max_distance, 'm:', 'LineWidth', 1, 'Label', sprintf('Max: %.1f km', max_distance));
grid on;
xlabel('Time (s)');
ylabel('Distance (km)');
title('Platform Distance from Emitter');
legend('Location', 'best');

%% Figure 2: Error Analysis
figure('Position', [100, 100, 1400, 600]);

subplot(1,3,1)
plot(time, estimated_lla(:,1) - emitter_lat, 'b-', 'LineWidth', 1.5);
hold on;
lat_uncertainty = sqrt(P_history(:,1)) / 111000;
plot(time, lat_uncertainty, 'r--', 'LineWidth', 1.5);
plot(time, -lat_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Latitude Error (deg)');
title('Latitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

subplot(1,3,2)
plot(time, estimated_lla(:,2) - emitter_lon, 'b-', 'LineWidth', 1.5);
hold on;
lon_uncertainty = sqrt(P_history(:,2)) / (111000 * cosd(emitter_lat));
plot(time, lon_uncertainty, 'r--', 'LineWidth', 1.5);
plot(time, -lon_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Longitude Error (deg)');
title('Longitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

subplot(1,3,3)
plot(time, estimated_lla(:,3) - emitter_alt, 'b-', 'LineWidth', 1.5);
hold on;
alt_uncertainty = sqrt(P_history(:,3));
plot(time, alt_uncertainty, 'r--', 'LineWidth', 1.5);
plot(time, -alt_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Altitude Error (m)');
title('Altitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

%% Figure 3: Geometry Analysis
figure('Position', [150, 150, 1200, 800]);

% Calculate bearing and elevation angles
bearings = zeros(N_steps, 1);
elevations = zeros(N_steps, 1);

for k = 1:N_steps
    r_ecef = emitter_ecef - platform_ecef(k,:);
    R_ecef_to_ned = ecef2nedRotation(platform_lat(k), platform_lon(k));
    r_ned = R_ecef_to_ned * r_ecef';
    
    bearings(k) = atan2d(r_ned(2), r_ned(1));
    elevations(k) = atan2d(-r_ned(3), sqrt(r_ned(1)^2 + r_ned(2)^2));
end

subplot(2,2,1)
plot(time, bearings, 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Bearing (deg)');
title('Line of Bearing Over Time');

subplot(2,2,2)
plot(time, elevations, 'r-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Elevation (deg)');
title('Elevation Angle Over Time');

subplot(2,2,3)
% Bearing rate of change
bearing_rate = [0; diff(unwrap(bearings*pi/180))*180/pi / dt];
plot(time, abs(bearing_rate), 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('|Bearing Rate| (deg/s)');
title('Bearing Change Rate (Geometry Diversity)');

subplot(2,2,4)
plot(time, innovation_history * 180/pi, 'k-', 'LineWidth', 1);
hold on;
plot(time, 2*sigma_angle*ones(size(time)), 'r--', 'LineWidth', 1.5);
plot(time, -2*sigma_angle*ones(size(time)), 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Innovation (deg)');
title('Measurement Innovation');
legend('Innovation', '2-\sigma Bounds', 'Location', 'best');

fprintf('All visualizations complete!\n');

%% =========================
%  SUPPORTING FUNCTIONS
%% =========================

function [x_history, P_history, innovation_history] = runEKF(initial_guess_ecef, ...
    Q_val, P0_val, R_scale, sigma_angle, measurements, platform_ecef, ...
    platform_lat, platform_lon, platform_pitch, platform_roll, platform_yaw, emitter_ecef)
    
    N_steps = length(measurements);
    
    x_est = initial_guess_ecef';
    P = diag([P0_val^2, P0_val^2, (P0_val/2)^2]);
    
    Q = diag([Q_val, Q_val, Q_val]);
    R = ((sigma_angle * pi/180) * R_scale)^2;
    
    x_history = zeros(N_steps, 3);
    P_history = zeros(N_steps, 3);
    innovation_history = zeros(N_steps, 1);
    
    x_history(1,:) = x_est';
    P_history(1,:) = diag(P)';
    
    for k = 2:N_steps
        x_pred = x_est;
        F = eye(3);
        P_pred = F * P * F' + Q;
        
        z = measurements(k) * pi/180;
        
        [h, H] = measurementModel(x_pred, platform_ecef(k,:)', ...
                                  platform_lat(k), platform_lon(k), ...
                                  platform_pitch(k), platform_roll(k), platform_yaw(k));
        
        innovation = z - h;
        S = H * P_pred * H' + R;
        K = P_pred * H' / S;
        
        x_est = x_pred + K * innovation;
        P = (eye(3) - K * H) * P_pred;
        
        x_history(k,:) = x_est';
        P_history(k,:) = diag(P)';
        innovation_history(k) = innovation;
    end
end

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
    
    R_yaw = [cos(yaw_rad), sin(yaw_rad), 0;
             -sin(yaw_rad), cos(yaw_rad), 0;
             0,             0,            1];
    
    R_pitch = [cos(pitch_rad), 0, -sin(pitch_rad);
               0,              1,  0;
               sin(pitch_rad), 0,  cos(pitch_rad)];
    
    R_roll = [1, 0,             0;
              0, cos(roll_rad), sin(roll_rad);
              0, -sin(roll_rad), cos(roll_rad)];
    
    R = R_roll * R_pitch * R_yaw;
end

function [h, H] = measurementModel(x_emitter_ecef, platform_ecef, ...
                                   platform_lat, platform_lon, ...
                                   pitch, roll, yaw)
    r_ecef = x_emitter_ecef - platform_ecef;
    
    R_ecef_to_ned = ecef2nedRotation(platform_lat, platform_lon);
    r_ned = R_ecef_to_ned * r_ecef;
    
    R_ned_to_body = ned2bodyRotation(pitch, roll, yaw);
    r_body = R_ned_to_body * r_ned;
    
    h = atan2(r_body(3), r_body(1));
    
    epsilon = 1.0;
    H = zeros(1, 3);
    
    for i = 1:3
        x_pert = x_emitter_ecef;
        x_pert(i) = x_pert(i) + epsilon;
        
        r_ecef_pert = x_pert - platform_ecef;
        r_ned_pert = R_ecef_to_ned * r_ecef_pert;
        r_body_pert = R_ned_to_body * r_ned_pert;
        
        h_pert = atan2(r_body_pert(3), r_body_pert(1));
        
        H(i) = (h_pert - h) / epsilon;
    end
end
