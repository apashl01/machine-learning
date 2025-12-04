%% Single-Platform 3D Geolocation using Extended Kalman Filter
% Simulation of a mobile platform with 1D interferometer estimating
% the position of a stationary ground-based emitter
% Author: Generated MATLAB Script
% Date: October 28, 2025

clear all; close all; clc;

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
% Platform flies in a circular pattern around the emitter with varying altitude

% Platform initial position (offset from emitter)
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
    % Convert offset in km to degrees (approximate)
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

% The 1D interferometer measures an angle in a specific plane
% defined in the platform body frame. For this simulation, we assume
% the interferometer measures the angle in the roll-pitch plane
% (azimuth-elevation plane relative to aircraft body axes)

% Measurement noise parameters
sigma_angle = 0.5;  % Angle measurement noise std dev (degrees)

% Pre-allocate measurement array
measurements = zeros(N_steps, 1);  % 1D angle measurements (degrees)

% Generate true measurements
for i = 1:N_steps
    % Vector from platform to emitter in ECEF
    r_ecef = emitter_ecef - platform_ecef(i,:);
    
    % Convert to platform body frame
    % First: ECEF to local NED frame
    R_ecef_to_ned = ecef2nedRotation(platform_lat(i), platform_lon(i));
    r_ned = R_ecef_to_ned * r_ecef';
    
    % Second: NED to body frame using platform attitude
    R_ned_to_body = ned2bodyRotation(platform_pitch(i), platform_roll(i), platform_yaw(i));
    r_body = R_ned_to_body * r_ned;
    
    % Compute 1D angle in body frame (e.g., angle in x-z plane)
    % This represents the angle measured by the interferometer
    angle_true = atan2d(r_body(3), r_body(1));  % Elevation angle in body x-z plane
    
    % Add measurement noise
    measurements(i) = angle_true + sigma_angle * randn();
end

fprintf('Generated %d measurements over %.1f seconds\n\n', N_steps, t_total);

%% =========================
%  EXTENDED KALMAN FILTER INITIALIZATION
%% =========================

% State vector: [x, y, z] in ECEF coordinates
% Initial guess (deliberately offset from true position)
initial_offset_km = 5.0;  % 5 km offset
initial_guess_ecef = emitter_ecef + initial_offset_km * 1000 * [1, 1, 0.5] / norm([1, 1, 0.5]);

% State and covariance
x_est = initial_guess_ecef';  % 3x1 state vector
P = diag([10000^2, 10000^2, 5000^2]);  % Initial covariance (large uncertainty)

% Process noise covariance (emitter is stationary)
Q = diag([0.01, 0.01, 0.01]);  % Very small process noise

% Measurement noise covariance
R = (sigma_angle * pi/180)^2;  % Convert to radians squared

% Storage for filter history
x_history = zeros(N_steps, 3);
P_history = zeros(N_steps, 3);  % Store diagonal elements of P
innovation_history = zeros(N_steps, 1);

% Initial logging
x_history(1,:) = x_est';
P_history(1,:) = diag(P)';

fprintf('EKF Initialized\n');
fprintf('  Initial guess offset: %.2f km\n', norm(x_est - emitter_ecef')/1000);
fprintf('  Initial uncertainty (1-sigma): [%.0f, %.0f, %.0f] m\n\n', sqrt(diag(P)));

%% =========================
%  EKF SIMULATION LOOP
%% =========================

fprintf('Running EKF simulation...\n');

for k = 2:N_steps
    %% Prediction Step
    % State prediction (emitter is stationary)
    x_pred = x_est;  % No dynamics
    
    % Covariance prediction
    F = eye(3);  % State transition matrix (identity for static emitter)
    P_pred = F * P * F' + Q;
    
    %% Update Step
    % Current measurement
    z = measurements(k) * pi/180;  % Convert to radians
    
    % Predicted measurement and Jacobian
    [h, H] = measurementModel(x_pred, platform_ecef(k,:)', ...
                              platform_lat(k), platform_lon(k), ...
                              platform_pitch(k), platform_roll(k), platform_yaw(k));
    
    % Innovation
    innovation = z - h;
    
    % Innovation covariance
    S = H * P_pred * H' + R;
    
    % Kalman gain
    K = P_pred * H' / S;
    
    % State update
    x_est = x_pred + K * innovation;
    
    % Covariance update
    P = (eye(3) - K * H) * P_pred;
    
    % Store history
    x_history(k,:) = x_est';
    P_history(k,:) = diag(P)';
    innovation_history(k) = innovation;
end

fprintf('EKF simulation complete.\n\n');

%% =========================
%  POST-PROCESSING
%% =========================

% Compute estimation errors
position_errors = zeros(N_steps, 1);
for k = 1:N_steps
    position_errors(k) = norm(x_history(k,:)' - emitter_ecef');
end

% Convert estimated positions to LLA for display
estimated_lla = zeros(N_steps, 3);
for k = 1:N_steps
    estimated_lla(k,:) = ecef2lla(x_history(k,:));
end

% Final estimates
final_error = position_errors(end);
final_uncertainty = sqrt(sum(P_history(end,:)));

fprintf('Final Results:\n');
fprintf('  Position error: %.2f m\n', final_error);
fprintf('  Position uncertainty (1-sigma): %.2f m\n', final_uncertainty);
fprintf('  Final estimate: Lat=%.6f deg, Lon=%.6f deg, Alt=%.2f m\n', ...
        estimated_lla(end,1), estimated_lla(end,2), estimated_lla(end,3));

%% =========================
%  VISUALIZATION
%% =========================

%% Figure 1: 3D Trajectory and Emitter Position
figure('Position', [100, 100, 1200, 800]);

subplot(2,2,1)
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
title('Platform Trajectory and Emitter Position Estimation');
legend('Platform Path', 'True Emitter', 'Estimates', 'Final Estimate', ...
       'Location', 'best');
view(-45, 30);

%% Position Error over Time
subplot(2,2,2)
plot(time, position_errors, 'b-', 'LineWidth', 1.5);
hold on;
uncertainty_bound = sqrt(sum(P_history, 2));
plot(time, uncertainty_bound, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Error (m)');
title('Position Estimation Error vs Time');
legend('Actual Error', '1-\sigma Uncertainty', 'Location', 'best');

%% Error Convergence (Log Scale)
subplot(2,2,3)
semilogy(time, position_errors, 'b-', 'LineWidth', 1.5);
hold on;
semilogy(time, uncertainty_bound, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Error (m) - Log Scale');
title('Position Error Convergence');
legend('Actual Error', '1-\sigma Uncertainty', 'Location', 'best');

%% Innovation Sequence
subplot(2,2,4)
plot(time, innovation_history * 180/pi, 'k-', 'LineWidth', 1);
hold on;
plot(time, 2*sigma_angle*ones(size(time)), 'r--', 'LineWidth', 1);
plot(time, -2*sigma_angle*ones(size(time)), 'r--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Innovation (deg)');
title('Measurement Innovation Sequence');
legend('Innovation', '2-\sigma Bounds', 'Location', 'best');

%% Figure 2: Detailed Error Analysis
figure('Position', [150, 150, 1200, 600]);

subplot(1,3,1)
plot(time, estimated_lla(:,1) - emitter_lat, 'b-', 'LineWidth', 1.5);
hold on;
lat_uncertainty = sqrt(P_history(:,1)) / 111000;  % Convert m to degrees (approx)
plot(time, lat_uncertainty, 'r--', 'LineWidth', 1);
plot(time, -lat_uncertainty, 'r--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Latitude Error (deg)');
title('Latitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

subplot(1,3,2)
plot(time, estimated_lla(:,2) - emitter_lon, 'b-', 'LineWidth', 1.5);
hold on;
lon_uncertainty = sqrt(P_history(:,2)) / (111000 * cosd(emitter_lat));
plot(time, lon_uncertainty, 'r--', 'LineWidth', 1);
plot(time, -lon_uncertainty, 'r--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Longitude Error (deg)');
title('Longitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

subplot(1,3,3)
plot(time, estimated_lla(:,3) - emitter_alt, 'b-', 'LineWidth', 1.5);
hold on;
alt_uncertainty = sqrt(P_history(:,3));
plot(time, alt_uncertainty, 'r--', 'LineWidth', 1);
plot(time, -alt_uncertainty, 'r--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Altitude Error (m)');
title('Altitude Estimation Error');
legend('Error', '1-\sigma', 'Location', 'best');

%% Figure 3: Geometry Analysis
figure('Position', [200, 200, 1000, 500]);

% Calculate bearing angles from platform to emitter
bearings = zeros(N_steps, 1);
elevations = zeros(N_steps, 1);

for k = 1:N_steps
    r_ecef = emitter_ecef - platform_ecef(k,:);
    R_ecef_to_ned = ecef2nedRotation(platform_lat(k), platform_lon(k));
    r_ned = R_ecef_to_ned * r_ecef';
    
    bearings(k) = atan2d(r_ned(2), r_ned(1));
    elevations(k) = atan2d(-r_ned(3), sqrt(r_ned(1)^2 + r_ned(2)^2));
end

subplot(1,2,1)
plot(time, bearings, 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Bearing Angle (deg)');
title('Line of Bearing Change Over Time');

subplot(1,2,2)
plot(time, elevations, 'r-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Elevation Angle (deg)');
title('Elevation Angle Over Time');

fprintf('\nVisualization complete. All figures generated.\n');

%% =========================
%  SUPPORTING FUNCTIONS
%% =========================

function R = ecef2nedRotation(lat, lon)
    % Rotation matrix from ECEF to NED frame
    lat_rad = lat * pi/180;
    lon_rad = lon * pi/180;
    
    R = [-sin(lat_rad)*cos(lon_rad), -sin(lat_rad)*sin(lon_rad), cos(lat_rad);
         -sin(lon_rad),               cos(lon_rad),              0;
         -cos(lat_rad)*cos(lon_rad), -cos(lat_rad)*sin(lon_rad), -sin(lat_rad)];
end

function R = ned2bodyRotation(pitch, roll, yaw)
    % Rotation matrix from NED to body frame using Euler angles (3-2-1 sequence)
    % Angles in degrees
    pitch_rad = pitch * pi/180;
    roll_rad = roll * pi/180;
    yaw_rad = yaw * pi/180;
    
    % Individual rotation matrices
    R_yaw = [cos(yaw_rad), sin(yaw_rad), 0;
             -sin(yaw_rad), cos(yaw_rad), 0;
             0,             0,            1];
    
    R_pitch = [cos(pitch_rad), 0, -sin(pitch_rad);
               0,              1,  0;
               sin(pitch_rad), 0,  cos(pitch_rad)];
    
    R_roll = [1, 0,             0;
              0, cos(roll_rad), sin(roll_rad);
              0, -sin(roll_rad), cos(roll_rad)];
    
    % Combined rotation (Yaw-Pitch-Roll sequence)
    R = R_roll * R_pitch * R_yaw;
end

function [h, H] = measurementModel(x_emitter_ecef, platform_ecef, ...
                                   platform_lat, platform_lon, ...
                                   pitch, roll, yaw)
    % Measurement model: predicts 1D angle measurement
    % Inputs:
    %   x_emitter_ecef: Estimated emitter position in ECEF (3x1)
    %   platform_ecef: Platform position in ECEF (3x1)
    %   platform_lat, platform_lon: Platform geodetic coordinates (deg)
    %   pitch, roll, yaw: Platform attitude (deg)
    % Outputs:
    %   h: Predicted measurement (angle in radians)
    %   H: Measurement Jacobian (1x3)
    
    % Vector from platform to emitter in ECEF
    r_ecef = x_emitter_ecef - platform_ecef;
    
    % Rotation from ECEF to NED
    R_ecef_to_ned = ecef2nedRotation(platform_lat, platform_lon);
    r_ned = R_ecef_to_ned * r_ecef;
    
    % Rotation from NED to body
    R_ned_to_body = ned2bodyRotation(pitch, roll, yaw);
    r_body = R_ned_to_body * r_ned;
    
    % Predicted measurement: angle in body x-z plane
    h = atan2(r_body(3), r_body(1));
    
    % Compute Jacobian using numerical differentiation
    epsilon = 1.0;  % Perturbation size (meters)
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
