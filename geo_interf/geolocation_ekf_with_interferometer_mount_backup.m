%% EKF Geolocation with Interferometer Mounting Position
% Enhanced with configurable interferometer mounting offset from platform CG
% Author: Generated MATLAB Script
% Date: October 28, 2025

clear all; close all; clc;

%% =========================
%  INTERFEROMETER CONFIGURATION
%% =========================

% INTERFEROMETER MOUNTING POSITION (in platform body frame)
% Origin is at platform center of gravity (CG)
% Body frame: X-forward, Y-right, Z-down (aerospace convention)

% BELLY-MOUNTED / NADIR-FACING CONFIGURATION
% Positioned on centerline, below CG, facing downward
INTERFEROMETER_OFFSET_BODY = [0.0;   % X: meters forward of CG (0 = on centerline)
                               0.0;   % Y: meters right of CG (0 = on centerline)
                               1.5];  % Z: meters below CG (positive Z = down)

% INTERFEROMETER ORIENTATION (additional rotation from body frame)
% For nadir-facing, longitudinally-aligned interferometer:
% - Roll = 0 (aligned with fuselage centerline)
% - Pitch = 0 (longitudinal axis aligned with flight direction)
% - Yaw = 0 (no azimuth offset)
% The 1D measurement is in the X-Z plane (longitudinal-vertical)
INTERFEROMETER_ORIENTATION = [0.0;   % Roll (deg) - centerline aligned
                               0.0;   % Pitch (deg) - longitudinal aligned
                               0.0];  % Yaw (deg) - no azimuth offset

% Display interferometer configuration
fprintf('Interferometer Configuration:\n');
fprintf('  Type: Belly-mounted, Nadir-facing, Longitudinally-aligned\n');
fprintf('  Mounting Position (body frame):\n');
fprintf('    X (forward): %.2f m\n', INTERFEROMETER_OFFSET_BODY(1));
fprintf('    Y (right):   %.2f m\n', INTERFEROMETER_OFFSET_BODY(2));
fprintf('    Z (down):    %.2f m\n', INTERFEROMETER_OFFSET_BODY(3));
fprintf('  Measurement Plane: X-Z (longitudinal-vertical)\n');
fprintf('  Orientation (relative to body):\n');
fprintf('    Roll:  %.2f deg\n', INTERFEROMETER_ORIENTATION(1));
fprintf('    Pitch: %.2f deg\n', INTERFEROMETER_ORIENTATION(2));
fprintf('    Yaw:   %.2f deg\n\n', INTERFEROMETER_ORIENTATION(3));

%% =========================
%  TRAJECTORY CONFIGURATION
%% =========================

TRAJECTORY_TYPE = 'figure8';       % Options: 'circle', 'figure8', 'racetrack', 'sturn', 'straight_offset', 'curved_approach'
STANDOFF_DISTANCE_KM = 10.0;       % Minimum distance from emitter (km)
TRAJECTORY_SIZE_SCALE = 1.5;       % Scale factor for trajectory size
ALTITUDE_MEAN = 3000;              % Mean platform altitude (meters)
ALTITUDE_VARIATION = 500;          % Altitude oscillation amplitude (meters)

fprintf('Trajectory Configuration:\n');
fprintf('  Type: %s\n', TRAJECTORY_TYPE);
fprintf('  Standoff Distance: %.1f km\n', STANDOFF_DISTANCE_KM);
fprintf('  Size Scale: %.2f\n', TRAJECTORY_SIZE_SCALE);
fprintf('  Altitude: %.0f ± %.0f m\n\n', ALTITUDE_MEAN, ALTITUDE_VARIATION);

%% =========================
%  TUNING CONFIGURATION
%% =========================

RUN_PARAMETER_SWEEP = true;  % Set to true for full parameter analysis

if RUN_PARAMETER_SWEEP
    Q_values = [0.0001, 0.001, 0.01, 0.1, 1.0, 10.0];  % Expanded range
    P0_values = [1000, 5000, 10000, 20000, 50000];
    R_scale_values = [0.3, 0.5, 0.8, 1.0, 1.2, 1.5, 2.0];  % Expanded range
    
    fprintf('Running parameter sweep with:\n');
    fprintf('  Q values: %d options\n', length(Q_values));
    fprintf('  P0 values: %d options\n', length(P0_values));
    fprintf('  R scale values: %d options\n', length(R_scale_values));
    fprintf('  Total combinations: %d\n\n', length(Q_values)*length(P0_values)*length(R_scale_values));
else
    Q_values = 0.01;
    P0_values = 10000;
    R_scale_values = 1.0;
    fprintf('Single run mode with default parameters\n\n');
end

%% =========================
%  SIMULATION PARAMETERS
%% =========================

dt = 1.0;
t_total = 300;
time = 0:dt:t_total;
N_steps = length(time);
rng(42);

%% =========================
%  TRUE EMITTER POSITION
%% =========================

emitter_lat = 35.0;
emitter_lon = -120.0;
emitter_alt = 100;

emitter_ecef = lla2ecef([emitter_lat, emitter_lon, emitter_alt]);

fprintf('True Emitter Position:\n');
fprintf('  Lat: %.6f deg, Lon: %.6f deg, Alt: %.2f m\n', ...
        emitter_lat, emitter_lon, emitter_alt);
fprintf('  ECEF: [%.2f, %.2f, %.2f] m\n\n', emitter_ecef);

%% =========================
%  PLATFORM TRAJECTORY
%% =========================

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
        
        omega = 2*pi / t_total;
        
        a_base = STANDOFF_DISTANCE_KM / 111.0;
        b_base = STANDOFF_DISTANCE_KM / (111.0 * cosd(emitter_lat));
        
        a = a_base * TRAJECTORY_SIZE_SCALE;
        b = b_base * TRAJECTORY_SIZE_SCALE;
        
        center_offset_lat = STANDOFF_DISTANCE_KM / 111.0;
        center_offset_lon = 0;
        
        platform_center_lat = emitter_lat + center_offset_lat;
        platform_center_lon = emitter_lon + center_offset_lon;
        
        for i = 1:N_steps
            t = time(i);
            theta = omega * t;
            
            delta_lat = a * sin(theta);
            delta_lon = b * sin(2*theta) / 2;
            
            platform_lat(i) = platform_center_lat + delta_lat;
            platform_lon(i) = platform_center_lon + delta_lon;
            platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(3*theta);
            
            vx = a * cos(theta);
            vy = b * cos(2*theta);
            platform_yaw(i) = atan2d(vy, vx);
            
            platform_pitch(i) = 3.0 * sin(theta) * cos(theta);
            platform_roll(i) = 2.0 * sin(2*theta);
        end
        
    case 'circle'
        fprintf('Generating Circular trajectory...\n');
        
        radius_lat = STANDOFF_DISTANCE_KM / 111.0;
        radius_lon = STANDOFF_DISTANCE_KM / (111.0 * cosd(emitter_lat));
        radius = (radius_lat + radius_lon) / 2 * TRAJECTORY_SIZE_SCALE;
        
        omega = 2*pi / t_total;
        
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
        
        straight_length = STANDOFF_DISTANCE_KM * TRAJECTORY_SIZE_SCALE / 111.0;
        turn_radius = STANDOFF_DISTANCE_KM / (2 * 111.0);
        
        platform_center_lat = emitter_lat + STANDOFF_DISTANCE_KM / 111.0;
        platform_center_lon = emitter_lon;
        
        turn_length = pi * turn_radius;
        total_length = 2 * straight_length + 2 * turn_length;
        velocity = total_length / t_total;
        
        for i = 1:N_steps
            t = time(i);
            distance = mod(velocity * t, total_length);
            
            if distance < straight_length
                platform_lat(i) = platform_center_lat + distance;
                platform_lon(i) = platform_center_lon - turn_radius;
                platform_yaw(i) = 0;
                
            elseif distance < straight_length + turn_length
                theta = (distance - straight_length) / turn_radius;
                platform_lat(i) = platform_center_lat + straight_length + turn_radius * sin(theta);
                platform_lon(i) = platform_center_lon - turn_radius * cos(theta);
                platform_yaw(i) = rad2deg(theta);
                
            elseif distance < 2*straight_length + turn_length
                platform_lat(i) = platform_center_lat + straight_length - (distance - straight_length - turn_length);
                platform_lon(i) = platform_center_lon + turn_radius;
                platform_yaw(i) = 180;
                
            else
                theta = (distance - 2*straight_length - turn_length) / turn_radius;
                platform_lat(i) = platform_center_lat - turn_radius * sin(theta);
                platform_lon(i) = platform_center_lon + turn_radius * cos(theta);
                platform_yaw(i) = 180 + rad2deg(theta);
            end
            
            platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(2*pi*t/t_total);
            platform_pitch(i) = 2.0 * sin(2*pi*t/t_total);
            platform_roll(i) = 1.5 * cos(3*2*pi*t/t_total);
        end
        
    case 'sturn'
        fprintf('Generating S-Turn trajectory (maximizing azimuth changes)...\n');
        
        % S-turn: Weaving approach toward emitter with maximum azimuth diversity
        % Start at standoff distance, approach emitter while making S-turns
        
        % Starting position (behind and to the side of emitter)
        start_distance_km = STANDOFF_DISTANCE_KM * TRAJECTORY_SIZE_SCALE * 1.5;
        start_lat_offset = start_distance_km / 111.0;  % Start behind emitter
        
        % S-turn parameters
        n_turns = 3;  % Number of complete S-turns during approach
        lateral_amplitude_km = STANDOFF_DISTANCE_KM * 0.6;  % Width of weave
        lateral_amplitude_lat = lateral_amplitude_km / 111.0;
        lateral_amplitude_lon = lateral_amplitude_km / (111.0 * cosd(emitter_lat));
        
        % Approach velocity (distance covered per second)
        approach_distance_km = start_distance_km - STANDOFF_DISTANCE_KM * 0.3;  % End closer
        approach_distance_deg = approach_distance_km / 111.0;
        approach_velocity = approach_distance_deg / t_total;
        
        for i = 1:N_steps
            t = time(i);
            
            % Progress along approach path (0 to 1)
            progress = t / t_total;
            
            % Longitudinal position (approaching emitter)
            lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress);
            
            % Lateral S-turn oscillation (sinusoidal weave)
            % Use sin(2π * n_turns * progress) for n complete S-turns
            lon_offset = lateral_amplitude_lon * sin(2 * pi * n_turns * progress);
            
            platform_lat(i) = lat_approach;
            platform_lon(i) = emitter_lon + lon_offset;
            
            % Altitude profile: gradually descending during approach
            alt_descent = ALTITUDE_VARIATION * progress;
            platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(4*pi*progress) - alt_descent;
            
            % Yaw: follow the velocity direction (tangent to S-curve)
            % Velocity components
            v_lat = -approach_velocity;  % Approaching (negative = southward)
            v_lon = lateral_amplitude_lon * 2 * pi * n_turns * cos(2 * pi * n_turns * progress) / t_total;
            
            platform_yaw(i) = atan2d(v_lon, v_lat);
            
            % Pitch and roll based on turn rate
            turn_phase = 2 * pi * n_turns * progress;
            platform_pitch(i) = -2.0 * progress;  % Slight nose-down during descent
            platform_roll(i) = 15.0 * sin(turn_phase);  % Bank into turns (larger for S-turns)
        end
        
        fprintf('  S-turn configuration:\n');
        fprintf('    Number of turns: %d\n', n_turns);
        fprintf('    Lateral amplitude: %.2f km\n', lateral_amplitude_km);
        fprintf('    Approach distance: %.2f km\n', approach_distance_km);
        fprintf('    Starting position: %.2f km behind emitter\n', start_distance_km);
        
    case 'straight_offset'
        fprintf('Generating Straight Approach with Lateral Offset trajectory...\n');
        
        % Straight line approach with constant lateral offset
        % Maintains lateral separation while approaching emitter
        
        % Starting position (behind emitter with lateral offset)
        start_distance_km = STANDOFF_DISTANCE_KM * TRAJECTORY_SIZE_SCALE * 1.5;
        start_lat_offset = start_distance_km / 111.0;  % Start behind
        
        % Lateral offset (constant throughout approach)
        lateral_offset_km = STANDOFF_DISTANCE_KM * 0.6;
        lateral_offset_lon = lateral_offset_km / (111.0 * cosd(emitter_lat));
        
        % Approach distance
        approach_distance_km = start_distance_km - STANDOFF_DISTANCE_KM * 0.3;
        approach_distance_deg = approach_distance_km / 111.0;
        
        for i = 1:N_steps
            t = time(i);
            progress = t / t_total;  % 0 to 1
            
            % Longitudinal: straight approach
            lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress);
            
            % Lateral: constant offset (parallel to emitter path)
            platform_lat(i) = lat_approach;
            platform_lon(i) = emitter_lon + lateral_offset_lon;  % Constant offset
            
            % Altitude: gradual descent
            platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(2*pi*progress) - ...
                             ALTITUDE_VARIATION * 0.5 * progress;
            
            % Yaw: point toward approach direction
            platform_yaw(i) = 0;  % Flying straight north
            
            % Pitch: slight nose-down during descent
            platform_pitch(i) = -1.5 * progress;
            
            % Roll: wings level (straight flight)
            platform_roll(i) = 1.0 * sin(4*pi*progress);  % Minor oscillations
        end
        
        fprintf('  Straight approach configuration:\n');
        fprintf('    Lateral offset: %.2f km (constant)\n', lateral_offset_km);
        fprintf('    Approach distance: %.2f km\n', approach_distance_km);
        fprintf('    Starting position: %.2f km behind, %.2f km offset\n', ...
                start_distance_km, lateral_offset_km);
        
    case 'curved_approach'
        fprintf('Generating Curved Approach trajectory...\n');
        
        % Starts with lateral offset, curves toward emitter over time
        % Creates arc-like path that ends near emitter
        
        % Starting position (behind and to the side)
        start_distance_km = STANDOFF_DISTANCE_KM * TRAJECTORY_SIZE_SCALE * 1.5;
        start_lat_offset = start_distance_km / 111.0;
        
        % Initial lateral offset
        initial_lateral_offset_km = STANDOFF_DISTANCE_KM * 0.8;
        initial_lateral_offset_lon = initial_lateral_offset_km / (111.0 * cosd(emitter_lat));
        
        % Approach distance
        approach_distance_km = start_distance_km - STANDOFF_DISTANCE_KM * 0.3;
        approach_distance_deg = approach_distance_km / 111.0;
        
        for i = 1:N_steps
            t = time(i);
            progress = t / t_total;  % 0 to 1
            
            % Longitudinal: approach emitter
            lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress);
            
            % Lateral: smooth curve from offset to centerline
            % Use smoothstep function for nice curve: 3*t^2 - 2*t^3
            curve_factor = 3 * progress^2 - 2 * progress^3;  % Smooth S-curve from 0 to 1
            lon_offset = initial_lateral_offset_lon * (1 - curve_factor);
            
            platform_lat(i) = lat_approach;
            platform_lon(i) = emitter_lon + lon_offset;
            
            % Altitude: gradual descent during approach
            platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(3*pi*progress) - ...
                             ALTITUDE_VARIATION * 0.6 * progress;
            
            % Yaw: follow the curve (banking into turn)
            % Compute yaw based on lateral velocity
            if i < N_steps
                lon_rate = (platform_lon(min(i+1,N_steps)) - platform_lon(i)) / dt;
                lat_rate = (platform_lat(min(i+1,N_steps)) - platform_lat(i)) / dt;
            else
                lon_rate = (platform_lon(i) - platform_lon(i-1)) / dt;
                lat_rate = (platform_lat(i) - platform_lat(i-1)) / dt;
            end
            platform_yaw(i) = atan2d(lon_rate, lat_rate);
            
            % Pitch: nose-down during descent
            platform_pitch(i) = -2.0 * progress;
            
            % Roll: bank into the curve
            % Higher roll early when turning more aggressively
            turn_rate = initial_lateral_offset_lon * 6 * (progress - progress^2) / t_total;
            platform_roll(i) = -atan2d(turn_rate, 1.0) * 2.0;  % Bank angle proportional to turn rate
        end
        
        fprintf('  Curved approach configuration:\n');
        fprintf('    Initial lateral offset: %.2f km\n', initial_lateral_offset_km);
        fprintf('    Final lateral offset: ~0 km (over emitter)\n');
        fprintf('    Approach distance: %.2f km\n', approach_distance_km);
        fprintf('    Path: Smooth arc from offset to centerline\n');
        
    otherwise
        error('Unknown trajectory type: %s', TRAJECTORY_TYPE);
end

% Convert platform CG trajectory to ECEF
platform_ecef_cg = zeros(N_steps, 3);
for i = 1:N_steps
    platform_ecef_cg(i,:) = lla2ecef([platform_lat(i), platform_lon(i), platform_alt(i)]);
end

%% =========================
%  BORESIGHT VECTOR CALCULATION
%% =========================

% Calculate interferometer boresight vectors at each time step
% The boresight is the direction the 1D interferometer "looks" in 3D space
% For NADIR-FACING: boresight points DOWNWARD in body frame (+Z direction)
% The 1D interferometer measures angle in X-Z plane around this downward axis

boresight_body = zeros(N_steps, 3);    % Boresight in body frame
boresight_ned = zeros(N_steps, 3);     % Boresight in NED frame
boresight_ecef = zeros(N_steps, 3);    % Boresight in ECEF frame

% For nadir-facing interferometer: boresight points DOWN (+Z in body frame)
% Body frame: X-forward, Y-right, Z-down
boresight_body_ref = [0; 0; 1];  % Boresight: DOWNWARD in body frame (nadir)

fprintf('Calculating boresight vectors for nadir-facing interferometer...\n');

for i = 1:N_steps
    % Apply interferometer orientation offset (usually zero for nadir-facing)
    R_interfero_offset = interferometerOrientationRotation(INTERFEROMETER_ORIENTATION);
    boresight_body(i,:) = (R_interfero_offset * boresight_body_ref)';
    
    % Transform to NED frame
    R_ned_to_body = ned2bodyRotation(platform_pitch(i), platform_roll(i), platform_yaw(i));
    boresight_ned(i,:) = (R_ned_to_body' * boresight_body(i,:)')';
    
    % Transform to ECEF frame
    R_ecef_to_ned = ecef2nedRotation(platform_lat(i), platform_lon(i));
    boresight_ecef(i,:) = (R_ecef_to_ned' * boresight_ned(i,:)')';
end

fprintf('Boresight vectors calculated.\n\n');

% Calculate interferometer position in ECEF at each time step
interferometer_ecef = zeros(N_steps, 3);
for i = 1:N_steps
    % Rotation from ECEF to NED at platform location
    R_ecef_to_ned = ecef2nedRotation(platform_lat(i), platform_lon(i));
    
    % Rotation from NED to body frame
    R_ned_to_body = ned2bodyRotation(platform_pitch(i), platform_roll(i), platform_yaw(i));
    
    % Combined rotation from ECEF to body
    R_ecef_to_body = R_ned_to_body * R_ecef_to_ned;
    
    % Interferometer offset in ECEF frame
    offset_ecef = R_ecef_to_body' * INTERFEROMETER_OFFSET_BODY;
    
    % Interferometer position in ECEF
    interferometer_ecef(i,:) = platform_ecef_cg(i,:) + offset_ecef';
end

% Calculate distances from emitter (using interferometer position)
distances_from_emitter = zeros(N_steps, 1);
for i = 1:N_steps
    distances_from_emitter(i) = norm(interferometer_ecef(i,:) - emitter_ecef) / 1000;
end

min_distance = min(distances_from_emitter);
max_distance = max(distances_from_emitter);
mean_distance = mean(distances_from_emitter);

% Calculate offset effect
offset_magnitude = norm(INTERFEROMETER_OFFSET_BODY);

fprintf('Trajectory generated successfully!\n');
fprintf('  Distance from emitter (interferometer position):\n');
fprintf('    Minimum: %.2f km\n', min_distance);
fprintf('    Maximum: %.2f km\n', max_distance);
fprintf('    Mean: %.2f km\n', mean_distance);
fprintf('  Interferometer offset magnitude: %.2f m\n\n', offset_magnitude);

%% =========================
%  1D INTERFEROMETER MODEL
%% =========================

sigma_angle = 0.5;  % Angle measurement noise std dev (degrees)

measurements = zeros(N_steps, 1);

% Generate measurements using interferometer position (not platform CG)
% For belly-mounted, nadir-facing, longitudinally-aligned configuration:
%   - BORESIGHT: Points downward (+Z in body frame) - where sensor "looks"
%   - MEASUREMENT PLANE: X-Z plane (longitudinal-vertical)
%   - The interferometer measures angle in the X-Z plane around the boresight
%   - In level flight with emitter below, angle ≈ 0° (directly below)
%   - Positive angles = emitter ahead, Negative angles = emitter behind
%   - Nadir-facing geometry provides good elevation sensitivity
for i = 1:N_steps
    % Vector from interferometer to emitter in ECEF
    r_ecef = emitter_ecef - interferometer_ecef(i,:);
    
    % Convert to platform body frame at CG (for attitude reference)
    R_ecef_to_ned = ecef2nedRotation(platform_lat(i), platform_lon(i));
    r_ned = R_ecef_to_ned * r_ecef';
    
    R_ned_to_body = ned2bodyRotation(platform_pitch(i), platform_roll(i), platform_yaw(i));
    r_body = R_ned_to_body * r_ned;
    
    % Apply interferometer orientation offset
    R_interfero_offset = interferometerOrientationRotation(INTERFEROMETER_ORIENTATION);
    r_interfero = R_interfero_offset * r_body;
    
    % Compute 1D angle in interferometer measurement frame
    angle_true = atan2d(r_interfero(3), r_interfero(1));
    
    % Add measurement noise
    measurements(i) = angle_true + sigma_angle * randn();
end

% Calculate incident angle (angle from boresight)
incident_angles = zeros(N_steps, 1);
for i = 1:N_steps
    % Vector from interferometer to emitter in body frame
    r_ecef = emitter_ecef - interferometer_ecef(i,:);
    R_ecef_to_ned = ecef2nedRotation(platform_lat(i), platform_lon(i));
    r_ned = R_ecef_to_ned * r_ecef';
    R_ned_to_body = ned2bodyRotation(platform_pitch(i), platform_roll(i), platform_yaw(i));
    r_body = R_ned_to_body * r_ned;
    
    % Apply interferometer orientation offset
    R_interfero_offset = interferometerOrientationRotation(INTERFEROMETER_ORIENTATION);
    r_interfero = R_interfero_offset * r_body;
    
    % Boresight is [0, 0, 1] (down)
    boresight = [0; 0; 1];
    
    % Incident angle = angle between emitter direction and boresight
    cos_incident = dot(r_interfero, boresight) / norm(r_interfero);
    incident_angles(i) = acosd(cos_incident);
end

fprintf('Generated %d measurements over %.1f seconds\n', N_steps, t_total);
fprintf('Incident angle range: %.1f° to %.1f°\n', min(incident_angles), max(incident_angles));
fprintf('Mean incident angle: %.1f°\n', mean(incident_angles));

% Verify nadir-facing geometry at a sample point
sample_time_idx = round(N_steps/4);  % Check at 25% through trajectory
fprintf('\nNadir-Facing Geometry Verification (t=%.1f s):\n', time(sample_time_idx));

% Calculate vector to emitter in body frame
r_ecef_sample = emitter_ecef - interferometer_ecef(sample_time_idx,:);
R_ecef_to_ned_sample = ecef2nedRotation(platform_lat(sample_time_idx), platform_lon(sample_time_idx));
r_ned_sample = R_ecef_to_ned_sample * r_ecef_sample';
R_ned_to_body_sample = ned2bodyRotation(platform_pitch(sample_time_idx), ...
                                         platform_roll(sample_time_idx), ...
                                         platform_yaw(sample_time_idx));
r_body_sample = R_ned_to_body_sample * r_ned_sample;

% Calculate angles
angle_xz = atan2d(r_body_sample(3), r_body_sample(1));  % Longitudinal angle
angle_yz = atan2d(r_body_sample(3), r_body_sample(2));  % Lateral angle
elevation_angle = asind(-r_body_sample(3) / norm(r_body_sample));  % Elevation (negative Z = up)

fprintf('  Emitter vector in body frame: [%.1f, %.1f, %.1f] m\n', r_body_sample);
fprintf('  Measurement (X-Z plane angle): %.2f deg\n', angle_xz);
fprintf('  Lateral angle (Y-Z plane): %.2f deg\n', angle_yz);
fprintf('  Elevation from horizontal: %.2f deg\n', elevation_angle);
fprintf('  Distance to emitter: %.2f km\n\n', norm(r_body_sample)/1000);

%% =========================
%  PARAMETER SWEEP OR SINGLE RUN
%% =========================

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
                    measurements, interferometer_ecef, platform_lat, platform_lon, ...
                    platform_pitch, platform_roll, platform_yaw, ...
                    INTERFEROMETER_OFFSET_BODY, INTERFEROMETER_ORIENTATION, emitter_ecef);
                
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
    [~, best_final_idx] = min(final_errors);
    [~, best_conv_idx] = min(convergence_times);
    
    fprintf('===============================================\n');
    fprintf('PARAMETER SWEEP RESULTS FOR %s TRAJECTORY\n', upper(TRAJECTORY_TYPE));
    fprintf('===============================================\n\n');
    
    fprintf('BEST FINAL ERROR CONFIGURATION:\n');
    fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
            results(best_final_idx).Q, results(best_final_idx).P0, ...
            results(best_final_idx).R_scale);
    fprintf('  Final error: %.2f m\n', results(best_final_idx).final_error);
    fprintf('  Convergence time: %.1f s\n\n', results(best_final_idx).convergence_time);
    
    fprintf('BEST CONVERGENCE TIME CONFIGURATION:\n');
    fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
            results(best_conv_idx).Q, results(best_conv_idx).P0, ...
            results(best_conv_idx).R_scale);
    fprintf('  Final error: %.2f m\n', results(best_conv_idx).final_error);
    fprintf('  Convergence time: %.1f s\n\n', results(best_conv_idx).convergence_time);
    
    fprintf('BEST COMPOSITE SCORE (RECOMMENDED):\n');
    fprintf('  Q = %.4f, P0 = %.0f, R_scale = %.2f\n', ...
            results(best_composite_idx).Q, results(best_composite_idx).P0, ...
            results(best_composite_idx).R_scale);
    fprintf('  Final error: %.2f m\n', results(best_composite_idx).final_error);
    fprintf('  Mean error: %.2f m\n', results(best_composite_idx).mean_error);
    fprintf('  Convergence: %.1f s\n', results(best_composite_idx).convergence_time);
    fprintf('  Composite score: %.4f\n\n', composite_score(best_composite_idx));
    
    % Statistics across all parameter combinations
    fprintf('PARAMETER SWEEP STATISTICS:\n');
    fprintf('  Final Error Range: %.2f - %.2f m\n', min(final_errors), max(final_errors));
    fprintf('  Mean Final Error: %.2f m\n', mean(final_errors));
    fprintf('  Convergence Time Range: %.1f - %.1f s\n', ...
            min(convergence_times(isfinite(convergence_times))), ...
            max(convergence_times(isfinite(convergence_times))));
    fprintf('  Configurations that converged: %d / %d\n\n', ...
            sum(isfinite(convergence_times)), length(convergence_times));
    
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
    measurements, interferometer_ecef, platform_lat, platform_lon, ...
    platform_pitch, platform_roll, platform_yaw, ...
    INTERFEROMETER_OFFSET_BODY, INTERFEROMETER_ORIENTATION, emitter_ecef);

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

% Global subplot counter for easy reference across all figures
global_subplot_num = 0;

%% Figure 1: 3D Trajectory with Interferometer Position
figure('Position', [50, 50, 1400, 900]);

% 3D Trajectory
subplot(2,2,1)
global_subplot_num = global_subplot_num + 1;
plot3(platform_lon, platform_lat, platform_alt, 'b-', 'LineWidth', 2);
hold on;

% Plot emitter and estimates
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
add_subplot_number(global_subplot_num, sprintf('%s Trajectory and Emitter Position', TRAJECTORY_TYPE));
legend('Platform Path', 'True Emitter', 'Estimates', 'Final Est.', 'Start', ...
       'Location', 'best');
view(-45, 25);

% Top-down view
subplot(2,2,2)
global_subplot_num = global_subplot_num + 1;
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
;
legend('Platform', 'Emitter', 'Estimates', 'Final', 'Start', ...
       sprintf('%.1f km Standoff', STANDOFF_DISTANCE_KM), 'Location', 'best');
axis equal;

% Position Error over Time
subplot(2,2,3)
global_subplot_num = global_subplot_num + 1;
plot(time, position_errors, 'b-', 'LineWidth', 2);
hold on;
uncertainty_bound = sqrt(sum(P_history, 2));
plot(time, uncertainty_bound, 'r--', 'LineWidth', 2);
grid on;
xlabel('Time (s)');
ylabel('Error (m)');
;
legend('Actual Error', '1-\sigma Uncertainty', 'Location', 'best');

% Distance from Emitter (Interferometer)
subplot(2,2,4)
global_subplot_num = global_subplot_num + 1;
plot(time, distances_from_emitter, 'b-', 'LineWidth', 2);
hold on;
yline(STANDOFF_DISTANCE_KM, 'r--', 'LineWidth', 1.5, 'Label', 'Nominal Standoff');
yline(min_distance, 'g:', 'LineWidth', 1, 'Label', sprintf('Min: %.1f km', min_distance));
yline(max_distance, 'm:', 'LineWidth', 1, 'Label', sprintf('Max: %.1f km', max_distance));
grid on;
xlabel('Time (s)');
ylabel('Distance (km)');
;
legend('Location', 'best');

%% Figure 2: Error Analysis
figure('Position', [150, 150, 1400, 600]);

subplot(1,3,1)
global_subplot_num = global_subplot_num + 1;
plot(time, estimated_lla(:,1) - emitter_lat, 'b-', 'LineWidth', 1.5);
hold on;
lat_uncertainty = sqrt(P_history(:,1)) / 111000;
plot(time, lat_uncertainty, 'r--', 'LineWidth', 1.5);
plot(time, -lat_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Latitude Error (deg)');
;
legend('Error', '1-\sigma', 'Location', 'best');

subplot(1,3,2)
global_subplot_num = global_subplot_num + 1;
plot(time, estimated_lla(:,2) - emitter_lon, 'b-', 'LineWidth', 1.5);
hold on;
lon_uncertainty = sqrt(P_history(:,2)) / (111000 * cosd(emitter_lat));
plot(time, lon_uncertainty, 'r--', 'LineWidth', 1.5);
plot(time, -lon_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Longitude Error (deg)');
;
legend('Error', '1-\sigma', 'Location', 'best');

subplot(1,3,3)
global_subplot_num = global_subplot_num + 1;
plot(time, estimated_lla(:,3) - emitter_alt, 'b-', 'LineWidth', 1.5);
hold on;
alt_uncertainty = sqrt(P_history(:,3));
plot(time, alt_uncertainty, 'r--', 'LineWidth', 1.5);
plot(time, -alt_uncertainty, 'r--', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Altitude Error (m)');
;
legend('Error', '1-\sigma', 'Location', 'best');

%% Figure 3: Geometry and Azimuth Analysis
figure('Position', [100, 100, 1400, 800]);

% Calculate bearing angles and azimuth diversity metrics
bearings = zeros(N_steps, 1);
elevations_geom = zeros(N_steps, 1);

for k = 1:N_steps
    r_ecef = emitter_ecef - platform_ecef_cg(k,:);
    R_ecef_to_ned = ecef2nedRotation(platform_lat(k), platform_lon(k));
    r_ned = R_ecef_to_ned * r_ecef';
    
    bearings(k) = atan2d(r_ned(2), r_ned(1));  % Azimuth angle
    elevations_geom(k) = atan2d(-r_ned(3), sqrt(r_ned(1)^2 + r_ned(2)^2));
end

subplot(2,3,1)
global_subplot_num = global_subplot_num + 1;
plot(time, bearings, 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Azimuth/Bearing (deg)');
;

subplot(2,3,2)
global_subplot_num = global_subplot_num + 1;
plot(time, elevations_geom, 'r-', 'LineWidth', 1.5);
hold on;
yline(0, 'k--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Elevation (deg)');
;

% Azimuth rate of change (key metric for geolocation geometry)
subplot(2,3,3)
global_subplot_num = global_subplot_num + 1;
bearing_unwrapped = unwrap(bearings*pi/180)*180/pi;
bearing_rate = [0; diff(bearing_unwrapped) / dt];
plot(time, abs(bearing_rate), 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('|Azimuth Rate| (deg/s)');
;
text(0.05, 0.95, 'Higher = Better Geometry', 'Units', 'normalized', ...
     'VerticalAlignment', 'top', 'FontSize', 9, 'BackgroundColor', 'w');

% Cumulative azimuth change
subplot(2,3,4)
global_subplot_num = global_subplot_num + 1;
cumulative_azimuth_change = cumsum(abs(bearing_rate)) * dt;
plot(time, cumulative_azimuth_change, 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Cumulative Azimuth Change (deg)');
add_subplot_number(global_subplot_num, sprintf('Total Azimuth Diversity (%s)', TRAJECTORY_TYPE));
text(0.05, 0.95, sprintf('Total: %.1f deg', cumulative_azimuth_change(end)), ...
     'Units', 'normalized', 'VerticalAlignment', 'top', 'FontSize', 10, ...
     'BackgroundColor', 'w', 'FontWeight', 'bold');

% Polar plot of bearing diversity
subplot(2,3,5)
global_subplot_num = global_subplot_num + 1;
polarplot(bearings*pi/180, distances_from_emitter, 'b-', 'LineWidth', 1.5);
hold on;
polarplot(bearings(1)*pi/180, distances_from_emitter(1), 'gs', ...
          'MarkerSize', 12, 'LineWidth', 2);
polarplot(bearings(end)*pi/180, distances_from_emitter(end), 'ro', ...
          'MarkerSize', 12, 'LineWidth', 2);
add_subplot_number(global_subplot_num, 'Bearing Diversity (Polar View)');;
legend('Trajectory', 'Start', 'End', 'Location', 'best');

% 2D trajectory with azimuth vectors
subplot(2,3,6)
global_subplot_num = global_subplot_num + 1;
plot(platform_lon, platform_lat, 'b-', 'LineWidth', 2);
hold on;
plot(emitter_lon, emitter_lat, 'r*', 'MarkerSize', 20, 'LineWidth', 3);

% Draw azimuth vectors at sample points
n_vectors = 10;
vector_indices = round(linspace(1, N_steps, n_vectors));
vector_scale = 0.01;  % Scale for visibility
for idx = vector_indices
    % Vector pointing from platform to emitter
    dx = (emitter_lon - platform_lon(idx)) * vector_scale;
    dy = (emitter_lat - platform_lat(idx)) * vector_scale;
    quiver(platform_lon(idx), platform_lat(idx), dx, dy, 0, ...
           'k-', 'LineWidth', 1.5, 'MaxHeadSize', 0.5);
end

grid on;
xlabel('Longitude (deg)');
ylabel('Latitude (deg)');
;
axis equal;
legend('Platform', 'Emitter', 'Azimuth Vectors', 'Location', 'best');

fprintf('All visualizations complete!\n');

%% Figure 4: Nadir-Facing Measurement Geometry
figure('Position', [200, 200, 1200, 800]);

% Measured angle over time (X-Z plane)
subplot(2,3,1)
global_subplot_num = global_subplot_num + 1;
plot(time, measurements, 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Measured Angle (deg)');
add_subplot_number(global_subplot_num, 'Interferometer Measurements (X-Z Plane Angle)');;
text(0.05, 0.95, 'Positive = Emitter ahead', 'Units', 'normalized', ...
     'VerticalAlignment', 'top', 'FontSize', 9, 'BackgroundColor', 'w');
text(0.05, 0.88, 'Negative = Emitter behind', 'Units', 'normalized', ...
     'VerticalAlignment', 'top', 'FontSize', 9, 'BackgroundColor', 'w');

% Incident angle over time (NEW - angle from boresight)
subplot(2,3,2)
global_subplot_num = global_subplot_num + 1;
plot(time, incident_angles, 'r-', 'LineWidth', 1.5);
hold on;
yline(0, 'g--', 'LineWidth', 1, 'Label', '0° (on-axis)');
yline(45, 'y--', 'LineWidth', 1, 'Label', '45°');
yline(90, 'r--', 'LineWidth', 1, 'Label', '90° (perpendicular)');
grid on;
xlabel('Time (s)');
ylabel('Incident Angle (deg)');
;
ylim([0, 100]);
text(0.05, 0.95, sprintf('Min: %.1f°  Max: %.1f°', min(incident_angles), max(incident_angles)), ...
     'Units', 'normalized', 'VerticalAlignment', 'top', 'FontSize', 9, 'BackgroundColor', 'w');

% Calculate elevation angles over time for reference
elevation_angles = zeros(N_steps, 1);
for k = 1:N_steps
    r_ecef_k = emitter_ecef - interferometer_ecef(k,:);
    R_ecef_to_ned_k = ecef2nedRotation(platform_lat(k), platform_lon(k));
    r_ned_k = R_ecef_to_ned_k * r_ecef_k';
    elevation_angles(k) = asind(-r_ned_k(3) / norm(r_ned_k));
end

subplot(2,3,3)
global_subplot_num = global_subplot_num + 1;
plot(time, elevation_angles, 'r-', 'LineWidth', 1.5);
hold on;
yline(0, 'k--', 'LineWidth', 1);
grid on;
xlabel('Time (s)');
ylabel('Elevation Angle (deg)');
add_subplot_number(global_subplot_num, 'True Elevation Angle (NED frame)');;
text(0.05, 0.95, 'Negative = Emitter below horizon', 'Units', 'normalized', ...
     'VerticalAlignment', 'top', 'FontSize', 9, 'BackgroundColor', 'w');

% Body frame vector components
subplot(2,3,4)
global_subplot_num = global_subplot_num + 1;
body_x = zeros(N_steps, 1);
body_y = zeros(N_steps, 1);
body_z = zeros(N_steps, 1);
for k = 1:N_steps
    r_ecef_k = emitter_ecef - interferometer_ecef(k,:);
    R_ecef_to_ned_k = ecef2nedRotation(platform_lat(k), platform_lon(k));
    r_ned_k = R_ecef_to_ned_k * r_ecef_k';
    R_ned_to_body_k = ned2bodyRotation(platform_pitch(k), platform_roll(k), platform_yaw(k));
    r_body_k = R_ned_to_body_k * r_ned_k;
    body_x(k) = r_body_k(1);
    body_y(k) = r_body_k(2);
    body_z(k) = r_body_k(3);
end

plot(time, body_x/1000, 'r-', 'LineWidth', 1.5);
hold on;
plot(time, body_y/1000, 'g-', 'LineWidth', 1.5);
plot(time, body_z/1000, 'b-', 'LineWidth', 1.5);
grid on;
xlabel('Time (s)');
ylabel('Distance (km)');
;
legend('X (forward)', 'Y (right)', 'Z (down)', 'Location', 'best');

% Measurement geometry diagram at sample times
subplot(2,3,[5,6])  % Use last two subplot positions
global_subplot_num = global_subplot_num + 1;
hold on;

% Select several sample times to show geometry
n_samples = 6;
sample_times_idx = round(linspace(1, N_steps, n_samples));
colors_geom = lines(n_samples);

for i = 1:n_samples
    idx = sample_times_idx(i);
    
    % Get body frame vector
    r_ecef_k = emitter_ecef - interferometer_ecef(idx,:);
    R_ecef_to_ned_k = ecef2nedRotation(platform_lat(idx), platform_lon(idx));
    r_ned_k = R_ecef_to_ned_k * r_ecef_k';
    R_ned_to_body_k = ned2bodyRotation(platform_pitch(idx), platform_roll(idx), platform_yaw(idx));
    r_body_k = R_ned_to_body_k * r_ned_k;
    
    % Normalize for visualization
    r_norm = r_body_k / norm(r_body_k);
    
    % Draw vector from origin
    quiver3(0, 0, 0, r_norm(1), r_norm(2), r_norm(3), ...
            'Color', colors_geom(i,:), 'LineWidth', 2, 'MaxHeadSize', 0.5);
    
    % Label with angle
    text(r_norm(1)*1.1, r_norm(2)*1.1, r_norm(3)*1.1, ...
         sprintf('t=%.0fs\n%.1f°', time(idx), measurements(idx)), ...
         'FontSize', 8, 'Color', colors_geom(i,:));
end

% Draw coordinate axes
quiver3(0, 0, 0, 1, 0, 0, 'k-', 'LineWidth', 2);
quiver3(0, 0, 0, 0, 1, 0, 'k-', 'LineWidth', 2);
quiver3(0, 0, 0, 0, 0, 1, 'k-', 'LineWidth', 2);
text(1.1, 0, 0, '+X (fwd)', 'FontSize', 10, 'FontWeight', 'bold');
text(0, 1.1, 0, '+Y (right)', 'FontSize', 10, 'FontWeight', 'bold');
text(0, 0, 1.1, '+Z (down)', 'FontSize', 10, 'FontWeight', 'bold');

% Draw X-Z measurement plane
[xx, zz] = meshgrid([-1, 1], [-1, 1]);
yy = zeros(size(xx));
surf(xx, yy, zz, 'FaceAlpha', 0.1, 'EdgeColor', 'none', 'FaceColor', 'cyan');

grid on;
xlabel('X (forward)');
ylabel('Y (right)');
zlabel('Z (down)');
add_subplot_number(global_subplot_num, 'Measurement Geometry in Body Frame');
axis equal;
view(-45, 20);
xlim([-1.2, 1.2]);
ylim([-1.2, 1.2]);
zlim([-1.2, 1.2]);

fprintf('\nNadir-facing geometry visualizations complete!\n');

%% Figure 5: Detailed Geometry Snapshot with Reference Vectors
figure('Position', [250, 50, 1400, 900]);

% Select 6 sample times spanning the trajectory
n_samples = 6;
sample_idx = round(linspace(round(N_steps*0.1), round(N_steps*0.9), n_samples));

for i = 1:n_samples
    idx = sample_idx(i);
    
    subplot(2, 3, i)
global_subplot_num = global_subplot_num + 1;
    hold on;
    
    % Current state
    current_lat = platform_lat(idx);
    current_lon = platform_lon(idx);
    current_alt = platform_alt(idx);
    current_pitch = platform_pitch(idx);
    current_roll = platform_roll(idx);
    current_yaw = platform_yaw(idx);
    
    % Origin at platform position
    origin = [0, 0, 0];
    
    % === VECTOR 1: VELOCITY / FLIGHT DIRECTION ===
    % Compute velocity direction from trajectory
    if idx < N_steps
        vel_lat = (platform_lat(idx+1) - platform_lat(idx)) / dt;
        vel_lon = (platform_lon(idx+1) - platform_lon(idx)) / dt;
        vel_alt = (platform_alt(idx+1) - platform_alt(idx)) / dt;
    else
        vel_lat = (platform_lat(idx) - platform_lat(idx-1)) / dt;
        vel_lon = (platform_lon(idx) - platform_lon(idx-1)) / dt;
        vel_alt = (platform_alt(idx) - platform_alt(idx-1)) / dt;
    end
    
    % Convert to NED (approximate)
    vel_ned = [vel_lat * 111000; vel_lon * 111000 * cosd(current_lat); -vel_alt];
    vel_ned = vel_ned / norm(vel_ned);  % Normalize
    
    % Convert to body frame
    R_ned_to_body = ned2bodyRotation(current_pitch, current_roll, current_yaw);
    vel_body = R_ned_to_body * vel_ned;
    
    % Draw velocity vector (BLUE)
    quiver3(origin(1), origin(2), origin(3), ...
            vel_body(1), vel_body(2), vel_body(3), ...
            0, 'b-', 'LineWidth', 3, 'MaxHeadSize', 0.4);
    
    % === VECTOR 2: BORESIGHT (INTERFEROMETER POINTING) ===
    % Nadir-facing: should point down in body frame
    boresight_body_vec = [0; 0; 1];  % Down in body frame
    
    % Draw boresight vector (RED)
    quiver3(origin(1), origin(2), origin(3), ...
            boresight_body_vec(1), boresight_body_vec(2), boresight_body_vec(3), ...
            0, 'r-', 'LineWidth', 3, 'MaxHeadSize', 0.4);
    
    % === VECTOR 3: BODY X-AXIS (FORWARD) ===
    % Shows where the nose points
    body_x = [1; 0; 0];
    quiver3(origin(1), origin(2), origin(3), ...
            body_x(1), body_x(2), body_x(3), ...
            0, 'g-', 'LineWidth', 2, 'MaxHeadSize', 0.4);
    
    % === VECTOR 4: BODY Y-AXIS (RIGHT WING) ===
    % Shows wing orientation (perpendicular to nose)
    body_y = [0; 1; 0];
    quiver3(origin(1), origin(2), origin(3), ...
            body_y(1), body_y(2), body_y(3), ...
            0, 'm--', 'LineWidth', 1.5, 'MaxHeadSize', 0.4);
    
    % === VECTOR 5: EMITTER DIRECTION (IN BODY FRAME) ===
    % Where the emitter actually is relative to platform
    r_ecef = emitter_ecef - platform_ecef_cg(idx,:);
    R_ecef_to_ned = ecef2nedRotation(current_lat, current_lon);
    r_ned = R_ecef_to_ned * r_ecef';
    r_body = R_ned_to_body * r_ned;
    r_body_norm = r_body / norm(r_body);  % Normalize for display
    
    % Draw emitter direction (CYAN)
    quiver3(origin(1), origin(2), origin(3), ...
            r_body_norm(1), r_body_norm(2), r_body_norm(3), ...
            0, 'c-', 'LineWidth', 2.5, 'MaxHeadSize', 0.4);
    
    % === REFERENCE PLANE: X-Z (MEASUREMENT PLANE) ===
    % Show the plane where interferometer measures angle
    [xx, zz] = meshgrid([-0.5, 0.5], [-0.5, 0.5]);
    yy = zeros(size(xx));
    surf(xx, yy, zz, 'FaceAlpha', 0.15, 'EdgeColor', 'k', ...
         'FaceColor', 'yellow', 'LineStyle', ':');
    
    % Formatting
    grid on;
    xlabel('X (Forward)');
    ylabel('Y (Right)');
    zlabel('Z (Down)');
    axis equal;
    xlim([-1.2, 1.2]);
    ylim([-1.2, 1.2]);
    zlim([-0.2, 1.2]);
    view(-45, 20);
    
    % Title with detailed info
    add_subplot_number(global_subplot_num, ...
        sprintf('Geometry Snapshot t=%.0fs | P=%.1f° R=%.1f° Y=%.1f° | Dist=%.1fkm | Meas=%.1f°', ...
                  time(idx), current_pitch, current_roll, current_yaw, ...
                  distances_from_emitter(idx), measurements(idx)));
    
    % Legend (only on first subplot)
    if i == 1
        legend('Velocity', 'Boresight (↓)', 'Nose (→)', 'Wing (→)', 'To Emitter', ...
               'X-Z Plane', 'Location', 'northoutside', 'Orientation', 'horizontal');
    end
end

% Add overall title
sgadd_subplot_number(global_subplot_num, sprintf('%s Trajectory: Body Frame Geometry Snapshots', upper(TRAJECTORY_TYPE)), ...
        'FontSize', 14, 'FontWeight', 'bold');

% Add interpretation guide as text
annotation('textbox', [0.02, 0.02, 0.96, 0.05], ...
           'String', ['INTERPRETATION: Red (boresight) should point DOWN (+Z). ' ...
                      'Green (nose) shows forward. Blue (velocity) may differ from green during turns. ' ...
                      'Cyan (to emitter) shows target direction. Magenta (wing) shows right.'], ...
           'EdgeColor', 'none', 'FontSize', 9, 'HorizontalAlignment', 'center');

fprintf('Geometry snapshot visualization complete!\n\n');

%% Figure 6: Coordinate Transformation Verification
figure('Position', [300, 100, 1400, 900]);

% Select a few sample times for detailed transformation verification
n_verify_samples = 4;
verify_sample_idx = round(linspace(round(N_steps*0.1), round(N_steps*0.9), n_verify_samples));

for plot_idx = 1:n_verify_samples
    idx = verify_sample_idx(plot_idx);
    
    % Get current state
    current_lat = platform_lat(idx);
    current_lon = platform_lon(idx);
    current_pitch = platform_pitch(idx);
    current_roll = platform_roll(idx);
    current_yaw = platform_yaw(idx);
    
    % Vector from interferometer to emitter in ECEF
    r_ecef = emitter_ecef - interferometer_ecef(idx,:);
    
    % Transform to NED
    R_ecef_to_ned = ecef2nedRotation(current_lat, current_lon);
    r_ned = R_ecef_to_ned * r_ecef';
    
    % Transform to body
    R_ned_to_body = ned2bodyRotation(current_pitch, current_roll, current_yaw);
    r_body = R_ned_to_body * r_ned;
    
    % Subplot for this sample
    subplot(2, n_verify_samples, plot_idx)
global_subplot_num = global_subplot_num + 1;
    
    % 3D visualization of transformations
    hold on;
    
    % Origin
    plot3(0, 0, 0, 'ko', 'MarkerSize', 10, 'LineWidth', 2);
    
    % Vector in NED frame (normalized)
    r_ned_norm = r_ned / norm(r_ned) * 2;
    quiver3(0, 0, 0, r_ned_norm(1), r_ned_norm(2), r_ned_norm(3), ...
            0, 'r-', 'LineWidth', 2);
    
    % Vector in body frame (normalized)
    r_body_norm = r_body / norm(r_body) * 2;
    quiver3(0, 0, 0, r_body_norm(1), r_body_norm(2), r_body_norm(3), ...
            0, 'b-', 'LineWidth', 2);
    
    % NED frame axes
    quiver3(0, 0, 0, 1, 0, 0, 0, 'r--', 'LineWidth', 1);
    quiver3(0, 0, 0, 0, 1, 0, 0, 'g--', 'LineWidth', 1);
    quiver3(0, 0, 0, 0, 0, 1, 0, 'b--', 'LineWidth', 1);
    text(1.1, 0, 0, 'N', 'Color', 'r');
    text(0, 1.1, 0, 'E', 'Color', 'g');
    text(0, 0, 1.1, 'D', 'Color', 'b');
    
    grid on;
    xlabel('X');
    ylabel('Y');
    zlabel('Z');
    add_subplot_number(global_subplot_num, sprintf('t=%.0fs\nPRY=[%.1f,%.1f,%.1f]', ...
                  time(idx), current_pitch, current_roll, current_yaw));
    legend('Origin', 'NED vec', 'Body vec', 'Location', 'best');
    view(45, 30);
    axis equal;
    xlim([-2.5, 2.5]);
    ylim([-2.5, 2.5]);
    zlim([-2.5, 2.5]);
    
    % Subplot for measurement verification
    subplot(2, n_verify_samples, n_verify_samples + plot_idx)
global_subplot_num = global_subplot_num + 1;
    
    % Show vector components and computed angle
    bar_data = [r_body(1)/1000, r_body(2)/1000, r_body(3)/1000];
    bar(bar_data);
    
    % Computed measurement angle
    computed_angle = atan2d(r_body(3), r_body(1));
    actual_measurement = measurements(idx);
    
    grid on;
    ylabel('Distance (km)');
    add_subplot_number(global_subplot_num, sprintf('Body Frame Components\nAngle: %.2f° (Meas: %.2f°)', ...
                  computed_angle, actual_measurement));
    set(gca, 'XTickLabel', {'X (fwd)', 'Y (right)', 'Z (down)'});
    
    % Add angle annotation
    text(2, max(abs(bar_data))*0.8, ...
         sprintf('Error: %.3f°', computed_angle - actual_measurement), ...
         'FontSize', 9, 'BackgroundColor', 'w');
end

% Additional verification: rotation matrix properties
subplot(2, n_verify_samples, [n_verify_samples*2-1, n_verify_samples*2])
global_subplot_num = global_subplot_num + 1;

% Check orthogonality and determinant of rotation matrices at all times
orthogonality_errors = zeros(N_steps, 1);
determinants = zeros(N_steps, 1);

for k = 1:N_steps
    R_ecef_to_ned = ecef2nedRotation(platform_lat(k), platform_lon(k));
    R_ned_to_body = ned2bodyRotation(platform_pitch(k), platform_roll(k), platform_yaw(k));
    
    % Combined rotation
    R_combined = R_ned_to_body * R_ecef_to_ned;
    
    % Check orthogonality: R' * R should equal I
    orthogonality_check = R_combined' * R_combined;
    orthogonality_errors(k) = norm(orthogonality_check - eye(3), 'fro');
    
    % Check determinant: should be 1 for proper rotation
    determinants(k) = det(R_combined);
end

yyaxis left
plot(time, orthogonality_errors, 'b-', 'LineWidth', 1.5);
ylabel('Orthogonality Error');
ylim([0, max(orthogonality_errors)*1.5]);

yyaxis right
plot(time, determinants, 'r-', 'LineWidth', 1.5);
ylabel('Determinant');
yline(1, 'k--', 'LineWidth', 1);
ylim([0.95, 1.05]);

grid on;
xlabel('Time (s)');
;
legend('||R^T*R - I||_{Fro}', 'det(R)', 'Expected det', 'Location', 'best');

fprintf('Coordinate transformation verification complete!\n\n');

%% Figure 7: Parameter Sweep Results (if sweep was run)
if RUN_PARAMETER_SWEEP && exist('results', 'var')
    figure('Position', [350, 150, 1400, 800]);
    
    % Extract all parameters
    Q_list = [results.Q];
    P0_list = [results.P0];
    R_scale_list = [results.R_scale];
    final_errors = [results.final_error];
    convergence_times = [results.convergence_time];
    
    % 3D scatter: Q vs R_scale vs Final Error
    subplot(2,3,1)
global_subplot_num = global_subplot_num + 1;
    scatter3(log10(Q_list), R_scale_list, final_errors, 50, final_errors, 'filled');
    xlabel('log10(Q)');
    ylabel('R Scale');
    zlabel('Final Error (m)');
    add_subplot_number(global_subplot_num, sprintf('%s: Q vs R Impact', upper(TRAJECTORY_TYPE)));
    colorbar;
    grid on;
    view(-45, 30);
    
    % Box plot: Effect of Q
    subplot(2,3,2)
global_subplot_num = global_subplot_num + 1;
    boxplot(final_errors, Q_list);
    xlabel('Process Noise Q');
    ylabel('Final Error (m)');
    add_subplot_number(global_subplot_num, 'Effect of Q Parameter');
    grid on;
    set(gca, 'XTickLabelRotation', 45);
    
    % Box plot: Effect of R_scale
    subplot(2,3,3)
global_subplot_num = global_subplot_num + 1;
    boxplot(final_errors, R_scale_list);
    xlabel('Measurement Noise R Scale');
    ylabel('Final Error (m)');
    add_subplot_number(global_subplot_num, 'Effect of R Parameter');
    grid on;
    
    % Convergence time analysis
    subplot(2,3,4)
global_subplot_num = global_subplot_num + 1;
    finite_conv_idx = isfinite(convergence_times);
    scatter(Q_list(finite_conv_idx), convergence_times(finite_conv_idx), ...
            50, R_scale_list(finite_conv_idx), 'filled');
    set(gca, 'XScale', 'log');
    xlabel('Process Noise Q (log scale)');
    ylabel('Convergence Time (s)');
    add_subplot_number(global_subplot_num, 'Convergence Speed vs Q');
    colorbar;
    ylabel(colorbar, 'R Scale');
    grid on;
    
    % Final error vs convergence time tradeoff
    subplot(2,3,5)
global_subplot_num = global_subplot_num + 1;
    scatter(convergence_times(finite_conv_idx), final_errors(finite_conv_idx), ...
            50, log10(Q_list(finite_conv_idx)), 'filled');
    xlabel('Convergence Time (s)');
    ylabel('Final Error (m)');
    add_subplot_number(global_subplot_num, 'Accuracy vs Speed Tradeoff');
    colorbar;
    ylabel(colorbar, 'log10(Q)');
    grid on;
    
    % Histogram of final errors
    subplot(2,3,6)
global_subplot_num = global_subplot_num + 1;
    histogram(final_errors, 30, 'FaceColor', 'b', 'EdgeColor', 'k');
    hold on;
    xline(final_errors(best_composite_idx), 'r-', 'LineWidth', 3, ...
          'Label', sprintf('Best: %.1fm', final_errors(best_composite_idx)));
    xline(median(final_errors), 'g--', 'LineWidth', 2, ...
          'Label', sprintf('Median: %.1fm', median(final_errors)));
    xlabel('Final Error (m)');
    ylabel('Count');
    add_subplot_number(global_subplot_num, sprintf('Error Distribution (%s)', TRAJECTORY_TYPE));
    legend('Location', 'best');
    grid on;
    
    fprintf('Parameter sweep visualization complete!\n\n');
end

%% =========================
%  SUPPORTING FUNCTIONS
%% =========================

function [x_history, P_history, innovation_history] = runEKF(initial_guess_ecef, ...
    Q_val, P0_val, R_scale, sigma_angle, measurements, interferometer_ecef, ...
    platform_lat, platform_lon, platform_pitch, platform_roll, platform_yaw, ...
    interfero_offset_body, interfero_orientation, emitter_ecef)
    
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
        
        [h, H] = measurementModelWithOffset(x_pred, interferometer_ecef(k,:)', ...
                                  platform_lat(k), platform_lon(k), ...
                                  platform_pitch(k), platform_roll(k), platform_yaw(k), ...
                                  interfero_offset_body, interfero_orientation);
        
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

function R = interferometerOrientationRotation(orientation_deg)
    % Create rotation matrix for interferometer orientation offset
    % Input: [roll, pitch, yaw] in degrees
    roll_rad = orientation_deg(1) * pi/180;
    pitch_rad = orientation_deg(2) * pi/180;
    yaw_rad = orientation_deg(3) * pi/180;
    
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

function [h, H] = measurementModelWithOffset(x_emitter_ecef, interferometer_ecef, ...
                                   platform_lat, platform_lon, ...
                                   pitch, roll, yaw, ...
                                   interfero_offset_body, interfero_orientation)
    
    % Vector from interferometer to emitter in ECEF
    r_ecef = x_emitter_ecef - interferometer_ecef;
    
    % Convert to platform body frame
    R_ecef_to_ned = ecef2nedRotation(platform_lat, platform_lon);
    r_ned = R_ecef_to_ned * r_ecef;
    
    R_ned_to_body = ned2bodyRotation(pitch, roll, yaw);
    r_body = R_ned_to_body * r_ned;
    
    % Apply interferometer orientation offset
    R_interfero = interferometerOrientationRotation(interfero_orientation);
    r_interfero = R_interfero * r_body;
    
    % Predicted measurement
    h = atan2(r_interfero(3), r_interfero(1));
    
    % Numerical Jacobian
    epsilon = 1.0;
    H = zeros(1, 3);
    
    for i = 1:3
        x_pert = x_emitter_ecef;
        x_pert(i) = x_pert(i) + epsilon;
        
        r_ecef_pert = x_pert - interferometer_ecef;
        r_ned_pert = R_ecef_to_ned * r_ecef_pert;
        r_body_pert = R_ned_to_body * r_ned_pert;
        r_interfero_pert = R_interfero * r_body_pert;
        
        h_pert = atan2(r_interfero_pert(3), r_interfero_pert(1));
        
        H(i) = (h_pert - h) / epsilon;
    end
end

function add_subplot_number(num, base_title)
    % Add numbered label to subplot title for easy reference
    % num: global subplot number
    % base_title: original title text
    add_subplot_number(global_subplot_num, sprintf('[%d] %s', num, base_title), 'FontWeight', 'bold');
end
