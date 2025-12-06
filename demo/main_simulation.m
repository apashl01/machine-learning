%% MAIN_SIMULATION - EKF Geolocation with Interferometer
% Main script that orchestrates the entire simulation
%
% This script:
%   1. Loads configuration
%   2. Generates trajectory
%   3. Generates measurements
%   4. Runs parameter sweep (optional)
%   5. Runs EKF with best parameters
%   6. Visualizes results (essential plots only)
%
% Author: Generated MATLAB Script
% Date: October 30, 2025

clear all; close all; clc;

% Add path to ekf_functions if needed
% addpath('path/to/ekf_functions');

%% =========================
%  STEP 1: LOAD CONFIGURATION
%% =========================

config = config_setup();

%% =========================
%  STEP 2: GENERATE TRAJECTORY
%% =========================

trajectory = generate_trajectory(config);

%% =========================
%  STEP 2.5: CALCULATE SIGNAL PROPAGATION
%% =========================

signal_data = calculate_signal_propagation(config, trajectory);

%% =========================
%  STEP 3: GENERATE MEASUREMENTS WITH INTERFEROMETER MODEL
%% =========================

fprintf('Generating measurements with high-fidelity interferometer model...\n');

[measurements, interferometer_data] = interferometer_model(config, trajectory, signal_data);

% Store incident angles for later visualization
incident_angles = interferometer_data.incident_angles * pi/180;  % Convert to radians for consistency

%% =========================
%  STEP 4: PARAMETER SWEEP (OPTIONAL)
%% =========================

N_steps = config.sim.N_steps;  % Used in parameter sweep loop

if config.tuning.run_parameter_sweep
    fprintf('\nRunning parameter sweep...\n');
    
    Q_values = config.tuning.Q_values;
    P0_values = config.tuning.P0_values;
    R_scale_values = config.tuning.R_scale_values;
    
    n_combinations = length(Q_values) * length(P0_values) * length(R_scale_values);
    results = struct('Q', {}, 'P0', {}, 'R_scale', {}, ...
                     'final_error', {}, 'mean_error', {}, 'convergence_time', {});
    
    result_idx = 0;
    fprintf('Progress: ');
    
    for q_idx = 1:length(Q_values)
        for p0_idx = 1:length(P0_values)
            for r_idx = 1:length(R_scale_values)
                result_idx = result_idx + 1;
                
                if mod(result_idx, 10) == 0
                    fprintf('%d/%d ', result_idx, n_combinations);
                end
                
                % Temporarily set parameters
                config.ekf.best_Q = Q_values(q_idx);
                config.ekf.best_P0 = P0_values(p0_idx);
                config.ekf.best_R_scale = R_scale_values(r_idx);
                
                % Run EKF
                [x_hist, ~, ~] = runEKF(config, measurements, trajectory, interferometer_data);
                
                % Calculate errors
                position_errors = zeros(N_steps, 1);
                for k = 1:N_steps
                    position_errors(k) = norm(x_hist(k,:)' - config.emitter.ecef');
                end
                
                final_error = position_errors(end);
                mean_error = mean(position_errors(ceil(N_steps/2):end));
                
                convergence_idx = find(position_errors < 500, 1, 'first');
                if ~isempty(convergence_idx)
                    convergence_time = config.sim.time(convergence_idx);
                else
                    convergence_time = inf;
                end
                
                % Store results
                results(result_idx).Q = Q_values(q_idx);
                results(result_idx).P0 = P0_values(p0_idx);
                results(result_idx).R_scale = R_scale_values(r_idx);
                results(result_idx).final_error = final_error;
                results(result_idx).mean_error = mean_error;
                results(result_idx).convergence_time = convergence_time;
            end
        end
    end
    
    fprintf('\nParameter sweep complete!\n\n');
    
    % Find best parameters
    final_errors = [results.final_error];
    mean_errors = [results.mean_error];
    convergence_times = [results.convergence_time];
    
    composite_score = normalize(final_errors, 'range') * 0.4 + ...
                      normalize(mean_errors, 'range') * 0.3 + ...
                      normalize(convergence_times, 'range') * 0.3;
    [~, best_idx] = min(composite_score);
    
    config.ekf.best_Q = results(best_idx).Q;
    config.ekf.best_P0 = results(best_idx).P0;
    config.ekf.best_R_scale = results(best_idx).R_scale;
    
    fprintf('BEST PARAMETERS (Composite Score):\n');
    fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
            config.ekf.best_Q, config.ekf.best_P0, config.ekf.best_R_scale);
    fprintf('  Final error: %.2f m\n', results(best_idx).final_error);
    fprintf('  Convergence time: %.1f s\n\n', results(best_idx).convergence_time);
else
    % Use default parameters
    config.ekf.best_Q = config.tuning.Q_values;
    config.ekf.best_P0 = config.tuning.P0_values;
    config.ekf.best_R_scale = config.tuning.R_scale_values;
end

%% =========================
%  STEP 5: RUN EKF WITH BEST PARAMETERS
%% =========================

fprintf('Running EKF with best parameters...\n');

[x_history, P_history, innovation_history] = runEKF(config, measurements, trajectory, interferometer_data);

% Calculate errors
position_errors = zeros(N_steps, 1);
estimated_lla = zeros(N_steps, 3);
for k = 1:N_steps
    position_errors(k) = norm(x_history(k,:)' - config.emitter.ecef');
    estimated_lla(k,:) = ecef2lla(x_history(k,:));
end

final_error = position_errors(end);
final_uncertainty = sqrt(sum(P_history(end,:)));

fprintf('Simulation complete!\n\n');
fprintf('Final Results:\n');
fprintf('  Position error: %.2f m\n', final_error);
fprintf('  Position uncertainty (1-sigma): %.2f m\n', final_uncertainty);
fprintf('  Final estimate: Lat=%.6f°, Lon=%.6f°, Alt=%.2f m\n\n', ...
        estimated_lla(end,1), estimated_lla(end,2), estimated_lla(end,3));

%% =========================
%  STEP 6: VISUALIZATION
%% =========================

%% Figure 1: Main Trajectory and Error Plot
figure('Position', [50, 50, 1400, 900]);

% 3D Trajectory
subplot(2,2,1)
% Plot full trajectory
plot3(trajectory.platform_lon, trajectory.platform_lat, trajectory.platform_alt, 'b-', 'LineWidth', 1);
hold on;

% Mark valid measurement points (green)
valid_idx = interferometer_data.measurement_valid;
plot3(trajectory.platform_lon(valid_idx), trajectory.platform_lat(valid_idx), ...
      trajectory.platform_alt(valid_idx), 'g.', 'MarkerSize', 6);

% Mark invalid measurement points (red)
invalid_idx = ~interferometer_data.measurement_valid;
if any(invalid_idx)
    plot3(trajectory.platform_lon(invalid_idx), trajectory.platform_lat(invalid_idx), ...
          trajectory.platform_alt(invalid_idx), 'r.', 'MarkerSize', 6);
end

% Plot emitter and estimates
plot3(config.emitter.lon, config.emitter.lat, config.emitter.alt, 'r*', 'MarkerSize', 20, 'LineWidth', 3);
plot3(estimated_lla(:,2), estimated_lla(:,1), estimated_lla(:,3), 'm.', 'MarkerSize', 2);
plot3(estimated_lla(end,2), estimated_lla(end,1), estimated_lla(end,3), ...
      'mo', 'MarkerSize', 12, 'LineWidth', 3);

% Mark start point
plot3(trajectory.platform_lon(1), trajectory.platform_lat(1), trajectory.platform_alt(1), ...
      'bs', 'MarkerSize', 12, 'LineWidth', 2);

grid on;
xlabel('Longitude (deg)');
ylabel('Latitude (deg)');
zlabel('Altitude (m)');
title(sprintf('%s Trajectory (Green=Used, Red=Rejected)', config.trajectory.type));
if any(invalid_idx)
    legend('Path', 'Valid Meas', 'Rejected Meas', 'True Emitter', 'Estimates', ...
           'Final Est.', 'Start', 'Location', 'best');
else
    legend('Path', 'Valid Meas', 'True Emitter', 'Estimates', 'Final Est.', ...
           'Start', 'Location', 'best');
end
view(-45, 25);

% Top-down view
subplot(2,2,2)
plot(trajectory.platform_lon, trajectory.platform_lat, 'b-', 'LineWidth', 2);
hold on;
plot(config.emitter.lon, config.emitter.lat, 'r*', 'MarkerSize', 20, 'LineWidth', 3);
plot(estimated_lla(:,2), estimated_lla(:,1), 'g.', 'MarkerSize', 3);
plot(estimated_lla(end,2), estimated_lla(end,1), 'go', 'MarkerSize', 12, 'LineWidth', 3);
plot(trajectory.platform_lon(1), trajectory.platform_lat(1), 'bs', 'MarkerSize', 12, 'LineWidth', 2);
grid on;
xlabel('Longitude (deg)');
ylabel('Latitude (deg)');
title('Top-Down View');
legend('Platform', 'Emitter', 'Estimates', 'Final', 'Start', 'Location', 'best');
axis equal;

% Position Error
subplot(2,2,3)
plot(config.sim.time, position_errors, 'b-', 'LineWidth', 2);
hold on;
uncertainty_bound = sqrt(sum(P_history, 2));
plot(config.sim.time, uncertainty_bound, 'r--', 'LineWidth', 2);
grid on;
xlabel('Time (s)');
ylabel('Error (m)');
title('Position Estimation Error');
legend('Actual Error', '1-\sigma Uncertainty', 'Location', 'best');

% Distance from Emitter
subplot(2,2,4)
plot(config.sim.time, trajectory.distances_from_emitter, 'b-', 'LineWidth', 2);
hold on;
yline(config.trajectory.standoff_distance_km, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Distance (km)');
title('Interferometer Distance from Emitter');
legend('Distance', 'Nominal Standoff', 'Location', 'best');

%% Figure 2: Component Errors
figure('Position', [150, 150, 1400, 600]);

subplot(1,3,1)
plot(config.sim.time, estimated_lla(:,1) - config.emitter.lat, 'b-', 'LineWidth', 1.5);
hold on;
lat_uncertainty = sqrt(P_history(:,1)) / 111000;
plot(config.sim.time, lat_uncertainty, 'r--', 'LineWidth', 1.5);
plot(config.sim.time, -lat_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Latitude Error (deg)');
title('Latitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

subplot(1,3,2)
plot(config.sim.time, estimated_lla(:,2) - config.emitter.lon, 'b-', 'LineWidth', 1.5);
hold on;
lon_uncertainty = sqrt(P_history(:,2)) / (111000 * cosd(config.emitter.lat));
plot(config.sim.time, lon_uncertainty, 'r--', 'LineWidth', 1.5);
plot(config.sim.time, -lon_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Longitude Error (deg)');
title('Longitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

subplot(1,3,3)
plot(config.sim.time, estimated_lla(:,3) - config.emitter.alt, 'b-', 'LineWidth', 1.5);
hold on;
alt_uncertainty = sqrt(P_history(:,3));
plot(config.sim.time, alt_uncertainty, 'r--', 'LineWidth', 1.5);
plot(config.sim.time, -alt_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Altitude Error (m)');
title('Altitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

%% Figure 3: Incident Angle and Geometry
figure('Position', [200, 200, 1400, 600]);

% Incident angle over time
subplot(1,2,1)
plot(config.sim.time, incident_angles*180/pi, 'b-', 'LineWidth', 2);
hold on;
yline(0, 'g--', 'LineWidth', 1);
yline(45, 'y--', 'LineWidth', 1);
yline(90, 'r--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Incident Angle (deg)');
title('Incident Angle from Boresight');
legend('Incident Angle', '0° (on-axis)', '45°', '90° (perpendicular)', 'Location', 'best');

% Geometry snapshot at mid-point
subplot(1,2,2)
hold on;

% Select mid-point of trajectory
idx = round(N_steps/2);

% Get vector to emitter in body frame
r_ecef = config.emitter.ecef - trajectory.platform_ecef_cg(idx,:);
R_ecef_to_ned = ecef2nedRotation(trajectory.platform_lat(idx), trajectory.platform_lon(idx));
r_ned = R_ecef_to_ned * r_ecef';
R_ned_to_body = ned2bodyRotation(trajectory.platform_pitch(idx), ...
                                 trajectory.platform_roll(idx), ...
                                 trajectory.platform_yaw(idx));
r_body = R_ned_to_body * r_ned;
r_body_norm = r_body / norm(r_body);

% Draw body frame axes
quiver3(0, 0, 0, 1, 0, 0, 'g-', 'LineWidth', 3, 'MaxHeadSize', 0.4);  % Nose (forward)
quiver3(0, 0, 0, 0, 1, 0, 'm--', 'LineWidth', 2, 'MaxHeadSize', 0.4);  % Wing (right)

% Draw actual boresight from trajectory (includes interferometer orientation)
boresight_body = trajectory.boresight_body(idx,:);
quiver3(0, 0, 0, boresight_body(1), boresight_body(2), boresight_body(3), ...
        'r-', 'LineWidth', 3, 'MaxHeadSize', 0.4);  % Boresight (actual direction)

% Draw emitter direction
quiver3(0, 0, 0, r_body_norm(1), r_body_norm(2), r_body_norm(3), ...
        'c-', 'LineWidth', 2.5, 'MaxHeadSize', 0.4);

% X-Z measurement plane
[xx, zz] = meshgrid([-0.5, 0.5], [-0.5, 0.5]);
yy = zeros(size(xx));
surf(xx, yy, zz, 'FaceAlpha', 0.15, 'EdgeColor', 'k', 'FaceColor', 'yellow');

grid on;
xlabel('X (Forward)');
ylabel('Y (Right)');
zlabel('Z (Down)');
title(sprintf('Geometry at t=%.0fs | Incident Angle=%.1f°', ...
              config.sim.time(idx), incident_angles(idx)*180/pi));
legend('Nose', 'Wing', 'Boresight', 'To Emitter', 'X-Z Plane', 'Location', 'best');
axis equal;
view(-45, 20);
xlim([-1.2, 1.2]);
ylim([-1.2, 1.2]);
zlim([-0.2, 1.2]);

fprintf('All visualizations complete!\n\n');

%% Figure 4: Interferometer Performance Analysis
figure('Position', [250, 250, 1200, 800]);

% SNR over time
subplot(2,2,1)
plot(config.sim.time, interferometer_data.snr_db, 'b-', 'LineWidth', 2);
hold on;
yline(20, 'r--', 'LineWidth', 1.5, 'Label', '20 dB (High SNR threshold)');
yline(10, 'y--', 'LineWidth', 1.5, 'Label', '10 dB');
grid on;
xlabel('Time (s)');
ylabel('SNR (dB)');
title('Signal-to-Noise Ratio');
legend('Location', 'best');

% Phase error over time - REMOVED (constant at 12 degrees in high SNR)

% Angle measurement error over time
subplot(2,2,2)
plot(config.sim.time, interferometer_data.angle_error_deg, 'g-', 'LineWidth', 2);
grid on;
xlabel('Time (s)');
ylabel('Angle Error (degrees)');
title('Angle Measurement Accuracy');
set(gca, 'YScale', 'log');

% Angle error vs incident angle
subplot(2,2,3)
scatter(interferometer_data.incident_angles, interferometer_data.angle_error_deg, 50, ...
        interferometer_data.snr_db, 'filled');
colorbar;
ylabel(colorbar, 'SNR (dB)');
grid on;
xlabel('Incident Angle (degrees)');
ylabel('Angle Error (degrees)');
title('Angle Error vs Incident Angle (colored by SNR)');
set(gca, 'YScale', 'log');

% SNR vs incident angle
subplot(2,2,4)
scatter(interferometer_data.incident_angles, interferometer_data.snr_db, 50, ...
        config.sim.time, 'filled');
colorbar;
ylabel(colorbar, 'Time (s)');
grid on;
xlabel('Incident Angle (degrees)');
ylabel('SNR (dB)');
title('SNR vs Incident Angle (colored by time)');

sgtitle(sprintf('Interferometer Performance Analysis (%.1f GHz, %.1f" aperture)', ...
        config.emitter.frequency_hz/1e9, max(config.interferometer.baselines)));

fprintf('Interferometer analysis plots complete!\n\n');

%% =========================
%  HELPER FUNCTIONS
%% =========================

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
