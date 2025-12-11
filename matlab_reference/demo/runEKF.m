function [x_history, P_history, innovation_history] = runEKF(config, measurements, trajectory, interferometer_data)
%RUNEKF Execute Extended Kalman Filter for geolocation
%
% Inputs:
%   config - configuration struct from config_setup()
%   measurements - array of angle measurements (radians)
%   trajectory - trajectory struct from generate_trajectory()
%   interferometer_data - interferometer performance data (for measurement noise)
%
% Outputs:
%   x_history - estimated emitter position over time (N_steps x 3) [ECEF]
%   P_history - covariance diagonal over time (N_steps x 3)
%   innovation_history - measurement innovations over time (N_steps x 1)

    N_steps = config.sim.N_steps;
    
    % Initialize state estimate
    x_est = config.ekf.initial_guess_ecef';
    P = diag([config.ekf.best_P0^2, config.ekf.best_P0^2, (config.ekf.best_P0/2)^2]);
    
    % Process noise
    Q = diag([config.ekf.best_Q, config.ekf.best_Q, config.ekf.best_Q]);
    
    % History storage
    x_history = zeros(N_steps, 3);
    P_history = zeros(N_steps, 3);
    innovation_history = zeros(N_steps, 1);
    
    % Initial state
    x_history(1,:) = x_est';
    P_history(1,:) = diag(P)';
    
    % EKF Loop
    for k = 2:N_steps
        % Predict (stationary emitter - no motion model)
        x_pred = x_est;
        F = eye(3);
        P_pred = F * P * F' + Q;
        
        % Check if measurement is valid (within incident angle threshold)
        if ~interferometer_data.measurement_valid(k)
            % Skip update step - just use prediction
            x_est = x_pred;
            P = P_pred;
            innovation_history(k) = 0;  % No innovation for skipped measurements
        else
            % Measurement update (normal EKF)
            z = measurements(k);
            
            % Measurement noise (time-varying based on interferometer performance)
            % R_scale allows tuning the trust in measurements during parameter sweep
            R = (interferometer_data.angle_error_1sigma_rad(k) * config.ekf.best_R_scale)^2;
            
            % Measurement model with interferometer offset
            [h, H] = measurementModelWithOffset(...
                x_pred, ...
                trajectory.interferometer_ecef(k,:)', ...
                trajectory.platform_lat(k), ...
                trajectory.platform_lon(k), ...
                trajectory.platform_pitch(k), ...
                trajectory.platform_roll(k), ...
                trajectory.platform_yaw(k), ...
                config.interferometer.offset_body, ...
                config.interferometer.orientation);
            
            % Update
            innovation = z - h;
            S = H * P_pred * H' + R;
            K = P_pred * H' / S;
            
            x_est = x_pred + K * innovation;
            P = (eye(3) - K * H) * P_pred;
            
            innovation_history(k) = innovation;
        end
        
        % Store
        x_history(k,:) = x_est';
        P_history(k,:) = diag(P)';
    end
end

function [h, H] = measurementModelWithOffset(x_emitter_ecef, interferometer_ecef, ...
                                   platform_lat, platform_lon, ...
                                   pitch, roll, yaw, ...
                                   interfero_offset_body, interfero_orientation)
%MEASUREMENTMODELWITHOFFSET Compute predicted measurement and Jacobian
%
% Inputs:
%   x_emitter_ecef - estimated emitter position in ECEF (3x1)
%   interferometer_ecef - interferometer position in ECEF (3x1)
%   platform_lat, platform_lon - platform position (degrees)
%   pitch, roll, yaw - platform attitude (degrees)
%   interfero_offset_body - interferometer offset from CG (3x1, meters)
%   interfero_orientation - interferometer orientation offset (3x1, degrees)
%
% Outputs:
%   h - predicted measurement (radians)
%   H - measurement Jacobian (1x3)

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
    
    % Predicted measurement (angle in X-Z plane)
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

function R = ecef2nedRotation(lat, lon)
%ECEF2NEDROTATION Rotation matrix from ECEF to NED frame
%
% Inputs:
%   lat - latitude (degrees)
%   lon - longitude (degrees)
%
% Output:
%   R - 3x3 rotation matrix

    lat_rad = lat * pi/180;
    lon_rad = lon * pi/180;
    
    R = [-sin(lat_rad)*cos(lon_rad), -sin(lat_rad)*sin(lon_rad), cos(lat_rad);
         -sin(lon_rad),               cos(lon_rad),              0;
         -cos(lat_rad)*cos(lon_rad), -cos(lat_rad)*sin(lon_rad), -sin(lat_rad)];
end

function R = ned2bodyRotation(pitch, roll, yaw)
%NED2BODYROTATION Rotation matrix from NED to body frame
%
% Inputs:
%   pitch - pitch angle (degrees)
%   roll - roll angle (degrees)
%   yaw - yaw angle (degrees)
%
% Output:
%   R - 3x3 rotation matrix

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
%INTERFEROMETERORIENTATIONROTATION Rotation for interferometer orientation offset
%
% Input:
%   orientation_deg - [roll, pitch, yaw] in degrees (3x1)
%
% Output:
%   R - 3x3 rotation matrix

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
