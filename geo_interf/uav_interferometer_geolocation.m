%% UAV Interferometer Geolocation Simulation
% Simulates a UAV with longitudinal (nose-to-tail) 1D interferometer
% measuring ground emitters for geolocation

clear all;
close all;
clc;

%% Configuration Parameters
config = struct();

% Interferometer parameters
config.baseline_inches = 10;          % Baseline length in inches
config.frequency_ghz = 6;             % Operating frequency in GHz
config.phase_error_deg = 12;          % Phase measurement error in degrees

% UAV parameters
config.altitude = 1000;               % UAV altitude in meters
config.speed = 50;                    % UAV ground speed in m/s
config.dt = 1.0;                      % Time step in seconds
config.measurement_interval = 10;     % Measurements every N time steps

% Emitter location (ground, 2D)
config.emitter_pos = [0, 0];         % [x, y] in meters

% Flight pattern selection
% Options: 'single_offset', 'curved', 'multiple_offsets'
config.flight_pattern = 'curved';

% Pattern-specific parameters
config.lateral_offset = 800;          % For single offset approach (meters)
config.lateral_offsets = [-1000, -500, 0, 500, 1000]; % For multiple passes
config.start_range = 3000;            % Starting distance from emitter (meters)
config.end_range = 500;               % Ending distance from emitter (meters)
config.curvature = 0.8;               % For curved approach (0=straight, 1=aggressive)

%% Run Simulation
fprintf('Starting simulation...\n');
fprintf('Config: altitude=%.1f, speed=%.1f, start_range=%.1f, end_range=%.1f\n', ...
    config.altitude, config.speed, config.start_range, config.end_range);
[measurements, trajectory, estimated_pos, results] = simulate_geolocation(config);

%% Display Results
fprintf('\n=== Geolocation Results ===\n');
fprintf('True Emitter Position: [%.1f, %.1f] m\n', config.emitter_pos(1), config.emitter_pos(2));
fprintf('Estimated Position: [%.1f, %.1f] m\n', estimated_pos(1), estimated_pos(2));
fprintf('Position Error: %.2f m\n', results.position_error);
fprintf('Number of Measurements: %d\n', length(measurements));
fprintf('Mean Boresight Angle: %.2f°\n', results.mean_boresight);
fprintf('Mean Angular Error: %.3f°\n', results.mean_angle_error);
fprintf('\n');

%% Visualize Results
visualize_geolocation(config, measurements, trajectory, estimated_pos, results);


%% ===================================================================
%% MAIN SIMULATION FUNCTION
%% ===================================================================
function [measurements, trajectory, estimated_pos, results] = simulate_geolocation(config)
    % Generate flight trajectory
    [trajectory, headings] = generate_flight_pattern(config);
    
    % Initialize measurements storage
    measurements = struct('uav_pos', {}, 'heading', {}, 'depression', {}, ...
                         'true_depression', {}, 'boresight', {}, 'error', {});
    
    % Simulate measurements along trajectory
    meas_idx = 1;
    num_trajectory_points = size(trajectory, 1);
    
    if num_trajectory_points < 2
        error('Trajectory generation failed - not enough points');
    end
    
    for i = 1:config.measurement_interval:num_trajectory_points
        uav_pos = trajectory(i, :);
        uav_heading = headings(i);
        
        % Get interferometer measurement
        [meas_dep, true_dep, boresight, angle_err] = measure_depression_angle(...
            uav_pos, uav_heading, config.emitter_pos, config);
        
        % Store measurement
        measurements(meas_idx).uav_pos = uav_pos;
        measurements(meas_idx).heading = uav_heading;
        measurements(meas_idx).depression = meas_dep;
        measurements(meas_idx).true_depression = true_dep;
        measurements(meas_idx).boresight = boresight;
        measurements(meas_idx).error = angle_err;
        
        meas_idx = meas_idx + 1;
    end
    
    % Estimate emitter position from measurements
    estimated_pos = estimate_emitter_position(measurements);
    
    % Calculate results statistics
    results = struct();
    results.position_error = norm(estimated_pos - config.emitter_pos);
    results.mean_boresight = mean([measurements.boresight]);
    results.mean_angle_error = mean([measurements.error]);
    results.max_angle_error = max([measurements.error]);
    results.min_angle_error = min([measurements.error]);
end


%% ===================================================================
%% FLIGHT PATTERN GENERATION
%% ===================================================================
function [positions, headings] = generate_flight_pattern(config)
    switch config.flight_pattern
        case 'single_offset'
            [positions, headings] = generate_offset_approach(config, config.lateral_offset);
            
        case 'curved'
            [positions, headings] = generate_curved_approach(config);
            
        case 'multiple_offsets'
            positions = [];
            headings = [];
            for offset = config.lateral_offsets
                [pos, head] = generate_offset_approach(config, offset);
                positions = [positions; pos];
                headings = [headings; head];
            end
            
        otherwise
            error('Unknown flight pattern: %s', config.flight_pattern);
    end
end

function [positions, headings] = generate_offset_approach(config, lateral_offset)
    % Generate straight-line approach with lateral offset
    
    % Start position: behind emitter with lateral offset
    start_x = config.emitter_pos(1) - config.start_range;
    start_y = config.emitter_pos(2) + lateral_offset;
    
    % End position: closer to emitter with same lateral offset
    end_x = config.emitter_pos(1) - config.end_range;
    end_y = config.emitter_pos(2) + lateral_offset;
    
    % Generate waypoints
    distance = sqrt((end_x - start_x)^2 + (end_y - start_y)^2);
    num_points = max(50, round(distance / (config.speed * config.dt)));
    
    positions = zeros(num_points, 3);
    headings = zeros(num_points, 1);
    
    for i = 1:num_points
        t = (i-1) / (num_points-1);
        x = start_x + t * (end_x - start_x);
        y = start_y + t * (end_y - start_y);
        
        % Update heading to point toward emitter
        dx = config.emitter_pos(1) - x;
        dy = config.emitter_pos(2) - y;
        heading = atan2d(dy, dx);
        
        positions(i, :) = [x, y, config.altitude];
        headings(i) = heading;
    end
end

function [positions, headings] = generate_curved_approach(config)
    % Generate curved approach starting with offset and curving toward emitter
    
    initial_offset = config.lateral_offset;
    if ~isfield(config, 'curvature')
        curvature = 0.8;
    else
        curvature = config.curvature;
    end
    
    % Generate parametric curve
    total_distance = config.start_range - config.end_range;
    num_points = max(50, round(total_distance / (config.speed * config.dt)));
    
    positions = zeros(num_points, 3);
    headings = zeros(num_points, 1);
    
    for i = 1:num_points
        t = (i-1) / (num_points-1);
        
        % Distance along x-axis (toward emitter)
        x_progress = config.start_range - t * total_distance;
        
        % Lateral offset decreases with curve
        lateral = initial_offset * (1 - t)^curvature;
        
        x = config.emitter_pos(1) - x_progress;
        y = config.emitter_pos(2) + lateral;
        
        % Calculate heading to point toward emitter
        dx = config.emitter_pos(1) - x;
        dy = config.emitter_pos(2) - y;
        heading = atan2d(dy, dx);
        
        positions(i, :) = [x, y, config.altitude];
        headings(i) = heading;
    end
end


%% ===================================================================
%% INTERFEROMETER MODEL
%% ===================================================================
function angle_error = calculate_angle_error(boresight_angle_deg, config)
    % Calculate angular measurement error based on boresight angle
    % Error formula: σ_θ = (c × σ_φ) / (2π × D × f × cos(boresight))
    
    c = 11.8028;  % Speed of light in inches/nanosecond
    sigma_phase = deg2rad(config.phase_error_deg);
    
    boresight_rad = deg2rad(boresight_angle_deg);
    cos_boresight = cos(boresight_rad);
    
    % Prevent division by zero for measurements along baseline
    if abs(cos_boresight) < 0.01
        cos_boresight = 0.01;
    end
    
    sigma_theta_rad = (c * sigma_phase) / ...
        (2 * pi * config.baseline_inches * config.frequency_ghz * cos_boresight);
    
    angle_error = rad2deg(sigma_theta_rad);
end

function [measured_dep, true_dep, boresight, angle_err] = measure_depression_angle(...
    uav_pos, uav_heading_deg, emitter_pos, config)
    % Simulate interferometer measurement of depression angle
    
    % Vector from UAV to emitter (signal arrival direction)
    dx = emitter_pos(1) - uav_pos(1);
    dy = emitter_pos(2) - uav_pos(2);
    dz = -uav_pos(3);  % Negative because emitter is below UAV
    
    slant_range = sqrt(dx^2 + dy^2 + dz^2);
    horizontal_range = sqrt(dx^2 + dy^2);
    
    % True depression angle (below horizontal)
    true_dep = atan2d(-dz, horizontal_range);
    
    % For BOTTOM-MOUNTED interferometer with VERTICAL baseline:
    % - Baseline points straight down (when UAV is level)
    % - Best measurement (boresight = 0°) = emitter directly below
    % - Worst measurement (boresight = 90°) = emitter at horizon
    %
    % Boresight angle = angle from vertical = 90° - depression_angle
    boresight = 90 - true_dep;
    
    % Calculate measurement error
    angle_err = calculate_angle_error(boresight, config);
    
    % Add noise to measurement
    measured_dep = true_dep + angle_err * randn();
end


%% ===================================================================
%% GEOLOCATION ESTIMATOR
%% ===================================================================
function estimated_pos = estimate_emitter_position(measurements)
    % Estimate emitter position using least squares
    
    if length(measurements) < 2
        error('Need at least 2 measurements for geolocation');
    end
    
    % Initial guess: average of UAV ground positions
    % Extract x,y positions from all measurements
    all_positions = zeros(length(measurements), 2);
    for i = 1:length(measurements)
        all_positions(i, :) = measurements(i).uav_pos(1:2);
    end
    initial_guess = mean(all_positions, 1);
    
    % Set up optimization
    options = optimoptions('lsqnonlin', 'Display', 'off', 'Algorithm', 'levenberg-marquardt');
    
    % Solve least squares problem
    estimated_pos = lsqnonlin(@(pos) residuals_func(pos, measurements), ...
        initial_guess, [], [], options);
end

function res = residuals_func(emitter_xy, measurements)
    % Calculate residuals for each measurement
    
    res = zeros(length(measurements), 1);
    
    for i = 1:length(measurements)
        uav_pos = measurements(i).uav_pos;
        measured_dep = measurements(i).depression;
        error_std = measurements(i).error;
        
        % Calculate expected depression angle
        dx = emitter_xy(1) - uav_pos(1);
        dy = emitter_xy(2) - uav_pos(2);
        horizontal_range = sqrt(dx^2 + dy^2);
        expected_dep = atan2d(uav_pos(3), horizontal_range);
        
        % Weight by measurement quality
        weight = 1.0 / (error_std + 0.1);
        res(i) = weight * (measured_dep - expected_dep);
    end
end


%% ===================================================================
%% VISUALIZATION
%% ===================================================================
function visualize_geolocation(config, measurements, trajectory, estimated_pos, results)
    figure('Position', [100, 100, 1400, 1000]);
    
    % Extract data for plotting
    num_meas = length(measurements);
    uav_positions = zeros(num_meas, 3);
    boresight_angles = zeros(num_meas, 1);
    angle_errors = zeros(num_meas, 1);
    measured_deps = zeros(num_meas, 1);
    true_deps = zeros(num_meas, 1);
    
    for i = 1:num_meas
        uav_positions(i, :) = measurements(i).uav_pos;
        boresight_angles(i) = measurements(i).boresight;
        angle_errors(i) = measurements(i).error;
        measured_deps(i) = measurements(i).depression;
        true_deps(i) = measurements(i).true_depression;
    end
    
    %% Plot 1: Top-down view
    subplot(2, 2, 1);
    hold on;
    
    % Plot emitter
    plot(config.emitter_pos(1), config.emitter_pos(2), 'r*', 'MarkerSize', 20, ...
        'LineWidth', 2, 'DisplayName', 'True Emitter');
    
    % Plot estimated position
    plot(estimated_pos(1), estimated_pos(2), 'g^', 'MarkerSize', 15, ...
        'LineWidth', 2, 'DisplayName', 'Estimated');
    
    % Plot error line
    plot([config.emitter_pos(1), estimated_pos(1)], ...
         [config.emitter_pos(2), estimated_pos(2)], 'k--', 'LineWidth', 1.5);
    text(estimated_pos(1), estimated_pos(2) + 100, ...
        sprintf('Error: %.1f m', results.position_error), ...
        'HorizontalAlignment', 'center', 'FontSize', 10, 'FontWeight', 'bold');
    
    % Plot trajectory
    plot(trajectory(:, 1), trajectory(:, 2), 'b-', 'LineWidth', 2, ...
        'DisplayName', 'UAV Path');
    
    % Plot measurement positions with color based on quality
    scatter(uav_positions(:, 1), uav_positions(:, 2), 50, boresight_angles, ...
        'filled', 'DisplayName', 'Measurements');
    colorbar;
    caxis([0 90]);
    ylabel(colorbar, 'Boresight Angle (deg)');
    
    % Plot sample bearing lines
    sample_indices = round(linspace(1, length(measurements), min(20, length(measurements))));
    for i = sample_indices
        plot([uav_positions(i, 1), config.emitter_pos(1)], ...
             [uav_positions(i, 2), config.emitter_pos(2)], ...
             'Color', [0.5 0.5 0.5 0.2], 'LineWidth', 0.5);
    end
    
    xlabel('X Position (m)', 'FontSize', 12, 'FontWeight', 'bold');
    ylabel('Y Position (m)', 'FontSize', 12, 'FontWeight', 'bold');
    title('Top-Down View', 'FontSize', 14, 'FontWeight', 'bold');
    legend('Location', 'best');
    grid on;
    axis equal;
    hold off;
    
    %% Plot 2: Boresight angle over time
    subplot(2, 2, 2);
    hold on;
    plot(1:length(measurements), boresight_angles, 'b-', 'LineWidth', 2);
    yline(30, 'Color', [1 0.5 0], 'LineStyle', '--', 'LineWidth', 2, ...
        'DisplayName', '30° Reference');
    yline(60, 'r--', 'LineWidth', 2, 'DisplayName', '60° Reference');
    xlabel('Measurement Number', 'FontSize', 12, 'FontWeight', 'bold');
    ylabel('Boresight Angle (degrees)', 'FontSize', 12, 'FontWeight', 'bold');
    title('Interferometer Boresight Angle', 'FontSize', 14, 'FontWeight', 'bold');
    legend('Location', 'best');
    grid on;
    hold off;
    
    %% Plot 3: Angle measurement error
    subplot(2, 2, 3);
    plot(1:length(measurements), angle_errors, 'r-', 'LineWidth', 2);
    xlabel('Measurement Number', 'FontSize', 12, 'FontWeight', 'bold');
    ylabel('Angular Error (degrees)', 'FontSize', 12, 'FontWeight', 'bold');
    title('Interferometer Measurement Error', 'FontSize', 14, 'FontWeight', 'bold');
    grid on;
    ylim([0 max(angle_errors) * 1.1]);
    
    %% Plot 4: Depression angle measurements
    subplot(2, 2, 4);
    hold on;
    plot(1:length(measurements), measured_deps, 'b.', 'MarkerSize', 8, ...
        'DisplayName', 'Measured');
    plot(1:length(measurements), true_deps, 'r-', 'LineWidth', 2, ...
        'DisplayName', 'True');
    xlabel('Measurement Number', 'FontSize', 12, 'FontWeight', 'bold');
    ylabel('Depression Angle (degrees)', 'FontSize', 12, 'FontWeight', 'bold');
    title('Depression Angle Measurements', 'FontSize', 14, 'FontWeight', 'bold');
    legend('Location', 'best');
    grid on;
    hold off;
    
    % Overall title
    sgtitle(sprintf('UAV Interferometer Geolocation - %s Pattern', ...
        strrep(config.flight_pattern, '_', ' ')), ...
        'FontSize', 16, 'FontWeight', 'bold');
end
