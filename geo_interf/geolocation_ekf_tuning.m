%% EKF Parameter Tuning for Single-Platform 3D Geolocation
% This script runs multiple simulations with different EKF tuning parameters
% to find the optimal configuration for best performance
% Author: Generated MATLAB Script
% Date: October 28, 2025

clear all; close all; clc;

%% =========================
%  TUNING CONFIGURATION
%% =========================

% Set to true to run parameter sweep, false for single run
RUN_PARAMETER_SWEEP = true;

% Define parameter ranges to test
if RUN_PARAMETER_SWEEP
    % Process noise Q (emitter is stationary, but we need some to prevent filter divergence)
    Q_values = [0.001, 0.01, 0.1, 1.0, 10.0];  % Variance in m^2
    
    % Initial covariance P0 (initial uncertainty)
    P0_values = [1000, 5000, 10000, 20000, 50000];  % Std dev in meters
    
    % Measurement noise R scaling factor (multiply true noise)
    R_scale_values = [0.5, 0.8, 1.0, 1.2, 1.5];
    
    fprintf('Running parameter sweep with:\n');
    fprintf('  Q values: %d options\n', length(Q_values));
    fprintf('  P0 values: %d options\n', length(P0_values));
    fprintf('  R scale values: %d options\n', length(R_scale_values));
    fprintf('  Total combinations: %d\n\n', length(Q_values)*length(P0_values)*length(R_scale_values));
else
    % Single run with default parameters
    Q_values = 0.01;
    P0_values = 10000;
    R_scale_values = 1.0;
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

% Design trajectory with significant changes in line of bearing
platform_center_lat = emitter_lat + 0.05;  % ~5.5 km north
platform_center_lon = emitter_lon + 0.05;  % ~5.5 km east
platform_alt_mean = 3000;                   % Mean altitude (meters)

% Circular trajectory parameters
radius_km = 7.0;                % Radius of circular path (km)
omega = 2*pi / t_total;         % Angular velocity (rad/s)
alt_variation = 500;            % Altitude variation (meters)

% Pre-allocate trajectory arrays
platform_lat = zeros(N_steps, 1);
platform_lon = zeros(N_steps, 1);
platform_alt = zeros(N_steps, 1);
platform_pitch = zeros(N_steps, 1);
platform_roll = zeros(N_steps, 1);
platform_yaw = zeros(N_steps, 1);

% Generate trajectory
for i = 1:N_steps
    t = time(i);
    theta = omega * t;
    
    % Circular motion with altitude variation
    delta_lat = (radius_km / 111.0) * cos(theta);
    delta_lon = (radius_km / (111.0 * cosd(platform_center_lat))) * sin(theta);
    
    platform_lat(i) = platform_center_lat + delta_lat;
    platform_lon(i) = platform_center_lon + delta_lon;
    platform_alt(i) = platform_alt_mean + alt_variation * sin(2*theta);
    
    % Attitude: yaw follows tangent to circle, slight pitch and roll
    platform_yaw(i) = rad2deg(theta + pi/2);  % Tangent direction
    platform_pitch(i) = 2.0 * sin(theta);     % Small pitch variation
    platform_roll(i) = 1.5 * cos(1.5*theta);  % Small roll variation
end

% Convert platform trajectory to ECEF
platform_ecef = zeros(N_steps, 3);
for i = 1:N_steps
    platform_ecef(i,:) = lla2ecef([platform_lat(i), platform_lon(i), platform_alt(i)]);
end

%% =========================
%  1D INTERFEROMETER MODEL
%% =========================

% Measurement noise parameters
sigma_angle = 0.5;  % Angle measurement noise std dev (degrees)

% Pre-allocate measurement array
measurements = zeros(N_steps, 1);  % 1D angle measurements (degrees)

% Generate true measurements (same for all parameter combinations)
for i = 1:N_steps
    % Vector from platform to emitter in ECEF
    r_ecef = emitter_ecef - platform_ecef(i,:);
    
    % Convert to platform body frame
    R_ecef_to_ned = ecef2nedRotation(platform_lat(i), platform_lon(i));
    r_ned = R_ecef_to_ned * r_ecef';
    
    R_ned_to_body = ned2bodyRotation(platform_pitch(i), platform_roll(i), platform_yaw(i));
    r_body = R_ned_to_body * r_ned;
    
    % Compute 1D angle in body frame
    angle_true = atan2d(r_body(3), r_body(1));
    
    % Add measurement noise
    measurements(i) = angle_true + sigma_angle * randn();
end

fprintf('Generated %d measurements over %.1f seconds\n\n', N_steps, t_total);

%% =========================
%  PARAMETER SWEEP
%% =========================

% Storage for results
n_combinations = length(Q_values) * length(P0_values) * length(R_scale_values);
results = struct('Q', {}, 'P0', {}, 'R_scale', {}, ...
                 'final_error', {}, 'mean_error', {}, 'convergence_time', {}, ...
                 'final_uncertainty', {}, 'mean_innovation', {});

result_idx = 0;

fprintf('Starting parameter sweep...\n');
fprintf('Progress: ');

% Initial guess (same for all runs)
initial_offset_km = 5.0;
initial_guess_ecef = emitter_ecef + initial_offset_km * 1000 * [1, 1, 0.5] / norm([1, 1, 0.5]);

% Loop through all parameter combinations
for q_idx = 1:length(Q_values)
    for p0_idx = 1:length(P0_values)
        for r_idx = 1:length(R_scale_values)
            result_idx = result_idx + 1;
            
            % Current parameters
            Q_val = Q_values(q_idx);
            P0_val = P0_values(p0_idx);
            R_scale = R_scale_values(r_idx);
            
            % Progress indicator
            if mod(result_idx, 10) == 0
                fprintf('%d/%d ', result_idx, n_combinations);
            end
            
            % Run EKF with these parameters
            [x_hist, P_hist, innov_hist] = runEKF(initial_guess_ecef, ...
                Q_val, P0_val, R_scale, sigma_angle, ...
                measurements, platform_ecef, platform_lat, platform_lon, ...
                platform_pitch, platform_roll, platform_yaw, emitter_ecef);
            
            % Compute performance metrics
            position_errors = zeros(N_steps, 1);
            for k = 1:N_steps
                position_errors(k) = norm(x_hist(k,:)' - emitter_ecef');
            end
            
            % Final error
            final_error = position_errors(end);
            
            % Mean error over last 50% of trajectory
            mean_error = mean(position_errors(ceil(N_steps/2):end));
            
            % Convergence time (when error first drops below 500m)
            convergence_idx = find(position_errors < 500, 1, 'first');
            if ~isempty(convergence_idx)
                convergence_time = time(convergence_idx);
            else
                convergence_time = inf;
            end
            
            % Final uncertainty
            final_uncertainty = sqrt(sum(P_hist(end,:)));
            
            % Mean absolute innovation
            mean_innovation = mean(abs(innov_hist(2:end))) * 180/pi;
            
            % Store results
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

%% =========================
%  ANALYZE RESULTS
%% =========================

% Extract metrics into arrays
final_errors = [results.final_error];
mean_errors = [results.mean_error];
convergence_times = [results.convergence_time];
final_uncertainties = [results.final_uncertainty];
Q_list = [results.Q];
P0_list = [results.P0];
R_scale_list = [results.R_scale];

% Find best configurations
[best_final_error, best_final_idx] = min(final_errors);
[best_mean_error, best_mean_idx] = min(mean_errors);
[best_convergence, best_conv_idx] = min(convergence_times);

% Composite score (weighted combination)
% Lower is better
composite_score = normalize(final_errors, 'range') * 0.4 + ...
                  normalize(mean_errors, 'range') * 0.3 + ...
                  normalize(convergence_times, 'range') * 0.3;
[best_composite_score, best_composite_idx] = min(composite_score);

fprintf('BEST CONFIGURATIONS:\n');
fprintf('==================\n\n');

fprintf('Best Final Error (%.2f m):\n', best_final_error);
fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
        results(best_final_idx).Q, results(best_final_idx).P0, results(best_final_idx).R_scale);
fprintf('  Convergence time: %.1f s\n\n', results(best_final_idx).convergence_time);

fprintf('Best Mean Error (%.2f m):\n', best_mean_error);
fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
        results(best_mean_idx).Q, results(best_mean_idx).P0, results(best_mean_idx).R_scale);
fprintf('  Final error: %.2f m\n\n', results(best_mean_idx).final_error);

fprintf('Best Convergence Time (%.1f s):\n', best_convergence);
fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
        results(best_conv_idx).Q, results(best_conv_idx).P0, results(best_conv_idx).R_scale);
fprintf('  Final error: %.2f m\n\n', results(best_conv_idx).final_error);

fprintf('Best Composite Score (%.4f):\n', best_composite_score);
fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
        results(best_composite_idx).Q, results(best_composite_idx).P0, results(best_composite_idx).R_scale);
fprintf('  Final error: %.2f m, Convergence: %.1f s\n\n', ...
        results(best_composite_idx).final_error, results(best_composite_idx).convergence_time);

%% =========================
%  RUN BEST CONFIGURATION
%% =========================

fprintf('Running detailed simulation with best composite parameters...\n');

best_Q = results(best_composite_idx).Q;
best_P0 = results(best_composite_idx).P0;
best_R_scale = results(best_composite_idx).R_scale;

[x_history, P_history, innovation_history] = runEKF(initial_guess_ecef, ...
    best_Q, best_P0, best_R_scale, sigma_angle, ...
    measurements, platform_ecef, platform_lat, platform_lon, ...
    platform_pitch, platform_roll, platform_yaw, emitter_ecef);

% Compute errors for best configuration
position_errors = zeros(N_steps, 1);
for k = 1:N_steps
    position_errors(k) = norm(x_history(k,:)' - emitter_ecef');
end

% Convert to LLA
estimated_lla = zeros(N_steps, 3);
for k = 1:N_steps
    estimated_lla(k,:) = ecef2lla(x_history(k,:));
end

fprintf('Best configuration simulation complete.\n\n');

%% =========================
%  VISUALIZATION
%% =========================

%% Figure 1: Parameter Sweep Results - 3D Scatter Plots
figure('Position', [50, 50, 1400, 900]);

% Create 3D scatter plots for different parameter combinations
subplot(2,3,1)
scatter3(log10(Q_list), P0_list/1000, final_errors, 50, final_errors, 'filled');
xlabel('log10(Q)');
ylabel('P0 (km)');
zlabel('Final Error (m)');
title('Final Error vs Q and P0');
colorbar;
grid on;
view(-45, 30);

subplot(2,3,2)
scatter3(log10(Q_list), R_scale_list, final_errors, 50, final_errors, 'filled');
xlabel('log10(Q)');
ylabel('R Scale Factor');
zlabel('Final Error (m)');
title('Final Error vs Q and R Scale');
colorbar;
grid on;
view(-45, 30);

subplot(2,3,3)
scatter3(P0_list/1000, R_scale_list, final_errors, 50, final_errors, 'filled');
xlabel('P0 (km)');
ylabel('R Scale Factor');
zlabel('Final Error (m)');
title('Final Error vs P0 and R Scale');
colorbar;
grid on;
view(-45, 30);

subplot(2,3,4)
scatter3(log10(Q_list), P0_list/1000, convergence_times, 50, convergence_times, 'filled');
xlabel('log10(Q)');
ylabel('P0 (km)');
zlabel('Convergence Time (s)');
title('Convergence Time vs Q and P0');
colorbar;
grid on;
view(-45, 30);

subplot(2,3,5)
scatter3(log10(Q_list), R_scale_list, mean_errors, 50, mean_errors, 'filled');
xlabel('log10(Q)');
ylabel('R Scale Factor');
zlabel('Mean Error (m)');
title('Mean Error vs Q and R Scale');
colorbar;
grid on;
view(-45, 30);

subplot(2,3,6)
scatter(composite_score, final_errors, 50, convergence_times, 'filled');
xlabel('Composite Score');
ylabel('Final Error (m)');
title('Final Error vs Composite Score');
colorbar;
ylabel(colorbar, 'Convergence Time (s)');
grid on;

%% Figure 2: Parameter Sensitivity Analysis
figure('Position', [100, 100, 1400, 600]);

subplot(1,3,1)
boxplot(final_errors, Q_list);
xlabel('Process Noise Q (m^2)');
ylabel('Final Error (m)');
title('Effect of Process Noise Q');
grid on;

subplot(1,3,2)
boxplot(final_errors, P0_list);
xlabel('Initial Uncertainty P0 (m)');
ylabel('Final Error (m)');
title('Effect of Initial Uncertainty P0');
grid on;

subplot(1,3,3)
boxplot(final_errors, R_scale_list);
xlabel('Measurement Noise Scale Factor');
ylabel('Final Error (m)');
title('Effect of Measurement Noise R');
grid on;

%% Figure 3: Best Configuration Performance
figure('Position', [150, 150, 1400, 900]);

subplot(2,3,1)
plot3(platform_lon, platform_lat, platform_alt, 'b-', 'LineWidth', 1.5);
hold on;
plot3(emitter_lon, emitter_lat, emitter_alt, 'r*', 'MarkerSize', 15, 'LineWidth', 2);
plot3(estimated_lla(:,2), estimated_lla(:,1), estimated_lla(:,3), 'g.', 'MarkerSize', 4);
plot3(estimated_lla(end,2), estimated_lla(end,1), estimated_lla(end,3), ...
      'go', 'MarkerSize', 10, 'LineWidth', 2);
grid on;
xlabel('Longitude (deg)');
ylabel('Latitude (deg)');
zlabel('Altitude (m)');
title('Platform Trajectory (Best Parameters)');
legend('Platform', 'True Emitter', 'Estimates', 'Final', 'Location', 'best');
view(-45, 30);

subplot(2,3,2)
plot(time, position_errors, 'b-', 'LineWidth', 1.5);
hold on;
uncertainty_bound = sqrt(sum(P_history, 2));
plot(time, uncertainty_bound, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Error (m)');
title('Position Error vs Time');
legend('Actual Error', '1-\sigma Uncertainty', 'Location', 'best');

subplot(2,3,3)
semilogy(time, position_errors, 'b-', 'LineWidth', 1.5);
hold on;
semilogy(time, uncertainty_bound, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Error (m) - Log Scale');
title('Error Convergence (Log Scale)');
legend('Actual Error', '1-\sigma Uncertainty', 'Location', 'best');

subplot(2,3,4)
plot(time, estimated_lla(:,1) - emitter_lat, 'b-', 'LineWidth', 1.5);
hold on;
lat_uncertainty = sqrt(P_history(:,1)) / 111000;
plot(time, lat_uncertainty, 'r--', 'LineWidth', 1);
plot(time, -lat_uncertainty, 'r--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Latitude Error (deg)');
title('Latitude Error');
legend('Error', '1-\sigma', 'Location', 'best');

subplot(2,3,5)
plot(time, estimated_lla(:,2) - emitter_lon, 'b-', 'LineWidth', 1.5);
hold on;
lon_uncertainty = sqrt(P_history(:,2)) / (111000 * cosd(emitter_lat));
plot(time, lon_uncertainty, 'r--', 'LineWidth', 1);
plot(time, -lon_uncertainty, 'r--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Longitude Error (deg)');
title('Longitude Error');
legend('Error', '1-\sigma', 'Location', 'best');

subplot(2,3,6)
plot(time, estimated_lla(:,3) - emitter_alt, 'b-', 'LineWidth', 1.5);
hold on;
alt_uncertainty = sqrt(P_history(:,3));
plot(time, alt_uncertainty, 'r--', 'LineWidth', 1);
plot(time, -alt_uncertainty, 'r--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Altitude Error (m)');
title('Altitude Error');
legend('Error', '1-\sigma', 'Location', 'best');

%% Figure 4: Top 10 Configurations Comparison
figure('Position', [200, 200, 1200, 800]);

% Find top 10 configurations
[sorted_composite, sort_idx] = sort(composite_score);
top_10_idx = sort_idx(1:min(10, length(sort_idx)));

% Run all top 10 and plot
colors = lines(10);
legends_cell = cell(10, 1);

for i = 1:length(top_10_idx)
    idx = top_10_idx(i);
    
    [x_hist, P_hist, ~] = runEKF(initial_guess_ecef, ...
        results(idx).Q, results(idx).P0, results(idx).R_scale, sigma_angle, ...
        measurements, platform_ecef, platform_lat, platform_lon, ...
        platform_pitch, platform_roll, platform_yaw, emitter_ecef);
    
    pos_errors = zeros(N_steps, 1);
    for k = 1:N_steps
        pos_errors(k) = norm(x_hist(k,:)' - emitter_ecef');
    end
    
    subplot(2,1,1)
    hold on;
    plot(time, pos_errors, 'Color', colors(i,:), 'LineWidth', 1.5);
    
    subplot(2,1,2)
    hold on;
    semilogy(time, pos_errors, 'Color', colors(i,:), 'LineWidth', 1.5);
    
    legends_cell{i} = sprintf('Q=%.3f, P0=%d, R=%.2f', ...
        results(idx).Q, results(idx).P0, results(idx).R_scale);
end

subplot(2,1,1)
grid on;
xlabel('Time (s)');
ylabel('Position Error (m)');
title('Top 10 Configurations - Linear Scale');
legend(legends_cell, 'Location', 'best', 'FontSize', 8);

subplot(2,1,2)
grid on;
xlabel('Time (s)');
ylabel('Position Error (m)');
title('Top 10 Configurations - Log Scale');
legend(legends_cell, 'Location', 'best', 'FontSize', 8);

fprintf('\nAll visualizations complete!\n');

%% =========================
%  SUPPORTING FUNCTIONS
%% =========================

function [x_history, P_history, innovation_history] = runEKF(initial_guess_ecef, ...
    Q_val, P0_val, R_scale, sigma_angle, measurements, platform_ecef, ...
    platform_lat, platform_lon, platform_pitch, platform_roll, platform_yaw, emitter_ecef)
    % Run a single EKF simulation with given parameters
    
    N_steps = length(measurements);
    
    % Initialize state and covariance
    x_est = initial_guess_ecef';
    P = diag([P0_val^2, P0_val^2, (P0_val/2)^2]);
    
    % Process and measurement noise
    Q = diag([Q_val, Q_val, Q_val]);
    R = ((sigma_angle * pi/180) * R_scale)^2;
    
    % Storage
    x_history = zeros(N_steps, 3);
    P_history = zeros(N_steps, 3);
    innovation_history = zeros(N_steps, 1);
    
    x_history(1,:) = x_est';
    P_history(1,:) = diag(P)';
    
    % EKF loop
    for k = 2:N_steps
        % Prediction
        x_pred = x_est;
        F = eye(3);
        P_pred = F * P * F' + Q;
        
        % Update
        z = measurements(k) * pi/180;
        
        [h, H] = measurementModel(x_pred, platform_ecef(k,:)', ...
                                  platform_lat(k), platform_lon(k), ...
                                  platform_pitch(k), platform_roll(k), platform_yaw(k));
        
        innovation = z - h;
        S = H * P_pred * H' + R;
        K = P_pred * H' / S;
        
        x_est = x_pred + K * innovation;
        P = (eye(3) - K * H) * P_pred;
        
        % Store
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
    
    % Numerical Jacobian
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
