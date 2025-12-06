function trajectory = generate_trajectory(config)
%GENERATE_TRAJECTORY Create platform trajectory and calculate interferometer geometry
%
% Input:
%   config - configuration struct from config_setup()
%
% Output:
%   trajectory - struct containing:
%       .platform_lat, .platform_lon, .platform_alt - platform CG position
%       .platform_pitch, .platform_roll, .platform_yaw - platform attitude
%       .platform_ecef_cg - platform CG in ECEF (N_steps x 3)
%       .interferometer_ecef - interferometer position in ECEF (N_steps x 3)
%       .boresight_body, .boresight_ned, .boresight_ecef - boresight vectors
%       .distances_from_emitter - distances to emitter (km)
%
% Author: Generated MATLAB Script
% Date: October 30, 2025

    N_steps = config.sim.N_steps;
    time = config.sim.time;
    dt = config.sim.dt;
    t_total = config.sim.t_total;
    
    % Extract configuration
    TRAJECTORY_TYPE = config.trajectory.type;
    STANDOFF_DISTANCE_KM = config.trajectory.standoff_distance_km;
    TRAJECTORY_SIZE_SCALE = config.trajectory.size_scale;
    ALTITUDE_MEAN = config.trajectory.altitude_mean;
    ALTITUDE_VARIATION = config.trajectory.altitude_variation;
    
    emitter_lat = config.emitter.lat;
    emitter_lon = config.emitter.lon;
    emitter_ecef = config.emitter.ecef;
    
    % Initialize arrays
    trajectory.platform_lat = zeros(N_steps, 1);
    trajectory.platform_lon = zeros(N_steps, 1);
    trajectory.platform_alt = zeros(N_steps, 1);
    trajectory.platform_pitch = zeros(N_steps, 1);
    trajectory.platform_roll = zeros(N_steps, 1);
    trajectory.platform_yaw = zeros(N_steps, 1);
    
    %% Generate trajectory based on selected type
    switch lower(TRAJECTORY_TYPE)
        case 'figure8'
            fprintf('Generating Figure-8 trajectory...\n');
            
            omega = 2*pi / t_total;
            a_base = STANDOFF_DISTANCE_KM / 111.0;
            b_base = STANDOFF_DISTANCE_KM / (111.0 * cosd(emitter_lat));
            a = a_base * TRAJECTORY_SIZE_SCALE;
            b = b_base * TRAJECTORY_SIZE_SCALE;
            
            center_offset_lat = STANDOFF_DISTANCE_KM / 111.0;
            platform_center_lat = emitter_lat + center_offset_lat;
            platform_center_lon = emitter_lon;
            
            for i = 1:N_steps
                t = time(i);
                theta = omega * t;
                
                delta_lat = a * sin(theta);
                delta_lon = b * sin(2*theta) / 2;
                
                trajectory.platform_lat(i) = platform_center_lat + delta_lat;
                trajectory.platform_lon(i) = platform_center_lon + delta_lon;
                trajectory.platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(3*theta);
                
                vx = a * cos(theta);
                vy = b * cos(2*theta);
                trajectory.platform_yaw(i) = atan2d(vy, vx);
                
                trajectory.platform_pitch(i) = 3.0 * sin(theta) * cos(theta);
                trajectory.platform_roll(i) = 2.0 * sin(2*theta);
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
                
                trajectory.platform_lat(i) = platform_center_lat + radius * cos(theta);
                trajectory.platform_lon(i) = platform_center_lon + radius * sin(theta);
                trajectory.platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(2*theta);
                
                trajectory.platform_yaw(i) = rad2deg(theta + pi/2);
                trajectory.platform_pitch(i) = 2.0 * sin(theta);
                trajectory.platform_roll(i) = 1.5 * cos(1.5*theta);
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
                    trajectory.platform_lat(i) = platform_center_lat + distance;
                    trajectory.platform_lon(i) = platform_center_lon - turn_radius;
                    trajectory.platform_yaw(i) = 0;
                elseif distance < straight_length + turn_length
                    theta = (distance - straight_length) / turn_radius;
                    trajectory.platform_lat(i) = platform_center_lat + straight_length + turn_radius * sin(theta);
                    trajectory.platform_lon(i) = platform_center_lon - turn_radius * cos(theta);
                    trajectory.platform_yaw(i) = rad2deg(theta);
                elseif distance < 2*straight_length + turn_length
                    trajectory.platform_lat(i) = platform_center_lat + straight_length - (distance - straight_length - turn_length);
                    trajectory.platform_lon(i) = platform_center_lon + turn_radius;
                    trajectory.platform_yaw(i) = 180;
                else
                    theta = (distance - 2*straight_length - turn_length) / turn_radius;
                    trajectory.platform_lat(i) = platform_center_lat - turn_radius * sin(theta);
                    trajectory.platform_lon(i) = platform_center_lon + turn_radius * cos(theta);
                    trajectory.platform_yaw(i) = 180 + rad2deg(theta);
                end
                
                trajectory.platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(2*pi*t/t_total);
                trajectory.platform_pitch(i) = 2.0 * sin(2*pi*t/t_total);
                trajectory.platform_roll(i) = 1.5 * cos(3*2*pi*t/t_total);
            end
            
        case 'sturn'
            fprintf('Generating S-Turn trajectory...\n');
            
            start_distance_km = STANDOFF_DISTANCE_KM * TRAJECTORY_SIZE_SCALE * 1.5;
            start_lat_offset = start_distance_km / 111.0;
            
            n_turns = 3;
            lateral_amplitude_km = STANDOFF_DISTANCE_KM * 0.6;
            lateral_amplitude_lon = lateral_amplitude_km / (111.0 * cosd(emitter_lat));
            
            approach_distance_km = start_distance_km - STANDOFF_DISTANCE_KM * 0.3;
            approach_distance_deg = approach_distance_km / 111.0;
            approach_velocity = approach_distance_deg / t_total;
            
            for i = 1:N_steps
                t = time(i);
                progress = t / t_total;
                
                lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress);
                lon_offset = lateral_amplitude_lon * sin(2 * pi * n_turns * progress);
                
                trajectory.platform_lat(i) = lat_approach;
                trajectory.platform_lon(i) = emitter_lon + lon_offset;
                
                alt_descent = ALTITUDE_VARIATION * progress;
                trajectory.platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(4*pi*progress) - alt_descent;
                
                v_lat = -approach_velocity;
                v_lon = lateral_amplitude_lon * 2 * pi * n_turns * cos(2 * pi * n_turns * progress) / t_total;
                trajectory.platform_yaw(i) = atan2d(v_lon, v_lat);
                
                turn_phase = 2 * pi * n_turns * progress;
                trajectory.platform_pitch(i) = -2.0 * progress;
                trajectory.platform_roll(i) = 15.0 * sin(turn_phase);
            end
            
        case 'straight_offset'
            fprintf('Generating Straight Approach with Lateral Offset...\n');
            
            start_distance_km = STANDOFF_DISTANCE_KM * TRAJECTORY_SIZE_SCALE * 1.5;
            start_lat_offset = start_distance_km / 111.0;
            lateral_offset_km = STANDOFF_DISTANCE_KM * 0.6;
            lateral_offset_lon = lateral_offset_km / (111.0 * cosd(emitter_lat));
            approach_distance_km = start_distance_km - STANDOFF_DISTANCE_KM * 0.3;
            approach_distance_deg = approach_distance_km / 111.0;
            
            for i = 1:N_steps
                t = time(i);
                progress = t / t_total;
                
                lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress);
                trajectory.platform_lat(i) = lat_approach;
                trajectory.platform_lon(i) = emitter_lon + lateral_offset_lon;
                trajectory.platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(2*pi*progress) - ...
                                            ALTITUDE_VARIATION * 0.5 * progress;
                trajectory.platform_yaw(i) = 0;
                trajectory.platform_pitch(i) = -1.5 * progress;
                trajectory.platform_roll(i) = 1.0 * sin(4*pi*progress);
            end
            
        case 'curved_approach'
            fprintf('Generating Curved Approach trajectory...\n');
            
            start_distance_km = STANDOFF_DISTANCE_KM * TRAJECTORY_SIZE_SCALE * 1.5;
            start_lat_offset = start_distance_km / 111.0;
            initial_lateral_offset_km = STANDOFF_DISTANCE_KM * 0.8;
            initial_lateral_offset_lon = initial_lateral_offset_km / (111.0 * cosd(emitter_lat));
            approach_distance_km = start_distance_km - STANDOFF_DISTANCE_KM * 0.3;
            approach_distance_deg = approach_distance_km / 111.0;
            
            for i = 1:N_steps
                t = time(i);
                progress = t / t_total;
                
                lat_approach = emitter_lat + start_lat_offset - (approach_distance_deg * progress);
                curve_factor = 3 * progress^2 - 2 * progress^3;
                lon_offset = initial_lateral_offset_lon * (1 - curve_factor);
                
                trajectory.platform_lat(i) = lat_approach;
                trajectory.platform_lon(i) = emitter_lon + lon_offset;
                trajectory.platform_alt(i) = ALTITUDE_MEAN + ALTITUDE_VARIATION * sin(3*pi*progress) - ...
                                            ALTITUDE_VARIATION * 0.6 * progress;
                
                if i < N_steps
                    lon_rate = (trajectory.platform_lon(min(i+1,N_steps)) - trajectory.platform_lon(i)) / dt;
                    lat_rate = (trajectory.platform_lat(min(i+1,N_steps)) - trajectory.platform_lat(i)) / dt;
                else
                    lon_rate = (trajectory.platform_lon(i) - trajectory.platform_lon(i-1)) / dt;
                    lat_rate = (trajectory.platform_lat(i) - trajectory.platform_lat(i-1)) / dt;
                end
                trajectory.platform_yaw(i) = atan2d(lon_rate, lat_rate);
                trajectory.platform_pitch(i) = -2.0 * progress;
                
                turn_rate = initial_lateral_offset_lon * 6 * (progress - progress^2) / t_total;
                trajectory.platform_roll(i) = -atan2d(turn_rate, 1.0) * 2.0;
            end
            
        otherwise
            error('Unknown trajectory type: %s', TRAJECTORY_TYPE);
    end
    
    %% Convert platform CG to ECEF
    trajectory.platform_ecef_cg = zeros(N_steps, 3);
    for i = 1:N_steps
        trajectory.platform_ecef_cg(i,:) = lla2ecef([trajectory.platform_lat(i), ...
                                                      trajectory.platform_lon(i), ...
                                                      trajectory.platform_alt(i)]);
    end
    
    %% Calculate Boresight Vectors
    trajectory.boresight_body = zeros(N_steps, 3);
    trajectory.boresight_ned = zeros(N_steps, 3);
    trajectory.boresight_ecef = zeros(N_steps, 3);
    
    boresight_body_ref = [0; 0; 1];  % Downward in body frame (nadir)
    
    fprintf('Calculating boresight vectors...\n');
    
    for i = 1:N_steps
        R_interfero_offset = interferometerOrientationRotation(config.interferometer.orientation);
        trajectory.boresight_body(i,:) = (R_interfero_offset * boresight_body_ref)';
        
        R_ned_to_body = ned2bodyRotation(trajectory.platform_pitch(i), ...
                                         trajectory.platform_roll(i), ...
                                         trajectory.platform_yaw(i));
        trajectory.boresight_ned(i,:) = (R_ned_to_body' * trajectory.boresight_body(i,:)')';
        
        R_ecef_to_ned = ecef2nedRotation(trajectory.platform_lat(i), trajectory.platform_lon(i));
        trajectory.boresight_ecef(i,:) = (R_ecef_to_ned' * trajectory.boresight_ned(i,:)')';
    end
    
    %% Calculate Interferometer Position in ECEF
    trajectory.interferometer_ecef = zeros(N_steps, 3);
    
    for i = 1:N_steps
        R_ecef_to_ned = ecef2nedRotation(trajectory.platform_lat(i), trajectory.platform_lon(i));
        R_ned_to_body = ned2bodyRotation(trajectory.platform_pitch(i), ...
                                         trajectory.platform_roll(i), ...
                                         trajectory.platform_yaw(i));
        R_ecef_to_body = R_ned_to_body * R_ecef_to_ned;
        
        offset_ecef = R_ecef_to_body' * config.interferometer.offset_body;
        trajectory.interferometer_ecef(i,:) = trajectory.platform_ecef_cg(i,:) + offset_ecef';
    end
    
    %% Calculate Distances from Emitter
    trajectory.distances_from_emitter = zeros(N_steps, 1);
    for i = 1:N_steps
        trajectory.distances_from_emitter(i) = norm(trajectory.interferometer_ecef(i,:) - emitter_ecef) / 1000;
    end
    
    min_distance = min(trajectory.distances_from_emitter);
    max_distance = max(trajectory.distances_from_emitter);
    mean_distance = mean(trajectory.distances_from_emitter);
    
    fprintf('Trajectory generated successfully!\n');
    fprintf('  Distance from emitter (interferometer position):\n');
    fprintf('    Minimum: %.2f km\n', min_distance);
    fprintf('    Maximum: %.2f km\n', max_distance);
    fprintf('    Mean: %.2f km\n\n', mean_distance);
end

% Helper functions (must be included in same file for function calls)
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
