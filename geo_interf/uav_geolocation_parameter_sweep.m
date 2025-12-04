%% UAV Interferometer Geolocation - Parameter Sweep Analysis
% Analyzes how different parameters affect geolocation performance

clear all;
close all;
clc;

%% Base Configuration (Fixed Parameters)
base_config = struct();

% Fixed interferometer parameters
base_config.baseline_inches = 10;
base_config.frequency_ghz = 6;
base_config.phase_error_deg = 12;

% Fixed emitter location
base_config.emitter_pos = [0, 0];

% Default operational parameters (will be varied in sweeps)
base_config.altitude = 1000;
base_config.speed = 50;
base_config.dt = 1.0;
base_config.measurement_interval = 10;
base_config.lateral_offset = 800;
base_config.start_range = 3000;
base_config.end_range = 500;
base_config.flight_pattern = 'single_offset';

%% Define Sweeps
sweeps = struct();

% Altitude sweep
sweeps.altitude.name = 'Altitude';
sweeps.altitude.param = 'altitude';
sweeps.altitude.values = 500:100:2000;
sweeps.altitude.units = 'm';
sweeps.altitude.pattern = 'single_offset';

% Lateral offset sweep
sweeps.lateral.name = 'Lateral Offset';
sweeps.lateral.param = 'lateral_offset';
sweeps.lateral.values = 100:100:2000;
sweeps.lateral.units = 'm';
sweeps.lateral.pattern = 'single_offset';

% Start range sweep (standoff distance)
sweeps.standoff.name = 'Start Range';
sweeps.standoff.param = 'start_range';
sweeps.standoff.values = 1500:250:5000;
sweeps.standoff.units = 'm';
sweeps.standoff.pattern = 'single_offset';

% Measurement interval sweep
sweeps.meas_interval.name = 'Measurement Interval';
sweeps.meas_interval.param = 'measurement_interval';
sweeps.meas_interval.values = 5:5:50;
sweeps.meas_interval.units = 'timesteps';
sweeps.meas_interval.pattern = 'single_offset';

%% Run All Sweeps
fprintf('\n=== Running Parameter Sweeps ===\n');

sweep_names = fieldnames(sweeps);
results = struct();

for s = 1:length(sweep_names)
    sweep_name = sweep_names{s};
    sweep = sweeps.(sweep_name);
    
    fprintf('\nRunning %s sweep...\n', sweep.name);
    results.(sweep_name) = run_single_sweep(sweep, base_config);
end

%% Flight Pattern Comparison
fprintf('\nRunning flight pattern comparison...\n');
results.patterns = compare_flight_patterns(base_config);

%% Generate Comprehensive Plots
generate_sweep_plots(results, sweeps, base_config);

fprintf('\n=== Analysis Complete ===\n\n');


%% ===================================================================
%% SWEEP EXECUTION FUNCTIONS
%% ===================================================================

function sweep_results = run_single_sweep(sweep_def, base_config)
    % Run a parameter sweep with multiple trials for statistical confidence
    
    num_points = length(sweep_def.values);
    num_trials = 5;  % Number of Monte Carlo trials per point
    
    % Initialize storage
    sweep_results = struct();
    sweep_results.param_values = sweep_def.values;
    sweep_results.mean_boresight = zeros(num_points, 1);
    sweep_results.min_boresight = zeros(num_points, 1);
    sweep_results.mean_interferometer_error = zeros(num_points, 1);
    sweep_results.geolocation_error = zeros(num_points, 1);
    sweep_results.geolocation_error_std = zeros(num_points, 1);
    sweep_results.num_measurements = zeros(num_points, 1);
    sweep_results.error_multiplication = zeros(num_points, 1);
    
    for i = 1:num_points
        % Create config for this parameter value
        config = base_config;
        config.(sweep_def.param) = sweep_def.values(i);
        config.flight_pattern = sweep_def.pattern;
        
        % Run multiple trials
        trial_geoloc_errors = zeros(num_trials, 1);
        trial_results = cell(num_trials, 1);
        
        for trial = 1:num_trials
            try
                [measurements, ~, estimated_pos, res] = simulate_geolocation(config);
                trial_geoloc_errors(trial) = res.position_error;
                trial_results{trial} = res;
                
                % Store measurement statistics (from first trial)
                if trial == 1
                    sweep_results.mean_boresight(i) = res.mean_boresight;
                    sweep_results.min_boresight(i) = min([measurements.boresight]);
                    sweep_results.mean_interferometer_error(i) = res.mean_angle_error;
                    sweep_results.num_measurements(i) = length(measurements);
                end
            catch ME
                warning('Trial %d failed for %s = %.1f: %s', trial, sweep_def.param, sweep_def.values(i), ME.message);
                trial_geoloc_errors(trial) = NaN;
            end
        end
        
        % Average over trials
        valid_trials = ~isnan(trial_geoloc_errors);
        if any(valid_trials)
            sweep_results.geolocation_error(i) = mean(trial_geoloc_errors(valid_trials));
            sweep_results.geolocation_error_std(i) = std(trial_geoloc_errors(valid_trials));
            
            % Calculate error multiplication factor
            if sweep_results.mean_interferometer_error(i) > 0
                sweep_results.error_multiplication(i) = ...
                    sweep_results.geolocation_error(i) / ...
                    (sweep_results.mean_interferometer_error(i) * 111000);  % Convert deg to meters (rough)
            end
        else
            sweep_results.geolocation_error(i) = NaN;
            sweep_results.geolocation_error_std(i) = NaN;
            sweep_results.error_multiplication(i) = NaN;
        end
        
        fprintf('  %s = %.1f %s: Geoloc Error = %.1f ± %.1f m\n', ...
            sweep_def.param, sweep_def.values(i), sweep_def.units, ...
            sweep_results.geolocation_error(i), sweep_results.geolocation_error_std(i));
    end
end

function pattern_results = compare_flight_patterns(base_config)
    % Compare different flight patterns
    
    patterns = {'single_offset', 'curved', 'multiple_offsets'};
    pattern_names = {'Single Offset', 'Curved Approach', 'Multiple Offsets'};
    
    num_trials = 10;
    
    pattern_results = struct();
    pattern_results.names = pattern_names;
    pattern_results.geoloc_error_mean = zeros(length(patterns), 1);
    pattern_results.geoloc_error_std = zeros(length(patterns), 1);
    pattern_results.mean_boresight = zeros(length(patterns), 1);
    pattern_results.mean_interf_error = zeros(length(patterns), 1);
    
    for p = 1:length(patterns)
        config = base_config;
        config.flight_pattern = patterns{p};
        
        % For multiple offsets, define the offset array
        if strcmp(patterns{p}, 'multiple_offsets')
            config.lateral_offsets = [-1000, -500, 0, 500, 1000];
        end
        
        trial_errors = zeros(num_trials, 1);
        
        for trial = 1:num_trials
            try
                [measurements, ~, ~, res] = simulate_geolocation(config);
                trial_errors(trial) = res.position_error;
                
                if trial == 1
                    pattern_results.mean_boresight(p) = res.mean_boresight;
                    pattern_results.mean_interf_error(p) = res.mean_angle_error;
                end
            catch ME
                warning('Pattern %s trial %d failed: %s', patterns{p}, trial, ME.message);
                trial_errors(trial) = NaN;
            end
        end
        
        valid = ~isnan(trial_errors);
        pattern_results.geoloc_error_mean(p) = mean(trial_errors(valid));
        pattern_results.geoloc_error_std(p) = std(trial_errors(valid));
        
        fprintf('  %s: %.1f ± %.1f m\n', pattern_names{p}, ...
            pattern_results.geoloc_error_mean(p), pattern_results.geoloc_error_std(p));
    end
end


%% ===================================================================
%% PLOTTING FUNCTIONS
%% ===================================================================

function generate_sweep_plots(results, sweeps, base_config)
    % Generate comprehensive visualization of all sweeps
    
    figure('Position', [50, 50, 1600, 1200]);
    
    sweep_names = fieldnames(sweeps);
    num_sweeps = length(sweep_names);
    
    % Plot each sweep in a row with 3 subplots
    for s = 1:num_sweeps
        sweep_name = sweep_names{s};
        sweep = sweeps.(sweep_name);
        res = results.(sweep_name);
        
        % Plot 1: Boresight Angle
        subplot(num_sweeps, 3, (s-1)*3 + 1);
        hold on;
        plot(res.param_values, res.mean_boresight, 'b-o', 'LineWidth', 2, 'MarkerSize', 6);
        plot(res.param_values, res.min_boresight, 'r--s', 'LineWidth', 1.5, 'MarkerSize', 5);
        xlabel(sprintf('%s (%s)', sweep.name, sweep.units), 'FontWeight', 'bold');
        ylabel('Boresight Angle (deg)', 'FontWeight', 'bold');
        title(sprintf('%s vs Boresight', sweep.name), 'FontWeight', 'bold');
        legend('Mean', 'Min (Best)', 'Location', 'best');
        grid on;
        hold off;
        
        % Plot 2: Interferometer Error
        subplot(num_sweeps, 3, (s-1)*3 + 2);
        plot(res.param_values, res.mean_interferometer_error, 'g-o', 'LineWidth', 2, 'MarkerSize', 6);
        xlabel(sprintf('%s (%s)', sweep.name, sweep.units), 'FontWeight', 'bold');
        ylabel('Interferometer Error (deg)', 'FontWeight', 'bold');
        title('Mean Interferometer Error', 'FontWeight', 'bold');
        grid on;
        
        % Plot 3: Geolocation Error
        subplot(num_sweeps, 3, (s-1)*3 + 3);
        hold on;
        errorbar(res.param_values, res.geolocation_error, res.geolocation_error_std, ...
            'ko-', 'LineWidth', 2, 'MarkerSize', 6, 'MarkerFaceColor', 'k', 'CapSize', 8);
        xlabel(sprintf('%s (%s)', sweep.name, sweep.units), 'FontWeight', 'bold');
        ylabel('Geolocation Error (m)', 'FontWeight', 'bold');
        title('Geolocation Error (±1σ)', 'FontWeight', 'bold');
        grid on;
        hold off;
    end
    
    sgtitle('Parameter Sweep Analysis', 'FontSize', 16, 'FontWeight', 'bold');
    
    % Create separate figure for flight pattern comparison
    figure('Position', [100, 100, 1200, 500]);
    
    % Bar chart of geolocation errors by pattern
    subplot(1, 2, 1);
    bar_data = results.patterns.geoloc_error_mean;
    bar_handle = bar(bar_data, 'FaceColor', [0.2 0.6 0.8]);
    hold on;
    errorbar(1:length(bar_data), bar_data, results.patterns.geoloc_error_std, ...
        'k.', 'LineWidth', 1.5, 'CapSize', 10);
    set(gca, 'XTickLabel', results.patterns.names);
    ylabel('Geolocation Error (m)', 'FontWeight', 'bold', 'FontSize', 12);
    title('Flight Pattern Comparison', 'FontWeight', 'bold', 'FontSize', 14);
    grid on;
    hold off;
    
    % Table of performance metrics
    subplot(1, 2, 2);
    axis off;
    
    % Create table data
    table_data = cell(length(results.patterns.names) + 1, 4);
    table_data{1, 1} = 'Pattern';
    table_data{1, 2} = 'Geoloc Error (m)';
    table_data{1, 3} = 'Mean Boresight (°)';
    table_data{1, 4} = 'Interf Error (°)';
    
    for i = 1:length(results.patterns.names)
        table_data{i+1, 1} = results.patterns.names{i};
        table_data{i+1, 2} = sprintf('%.1f ± %.1f', ...
            results.patterns.geoloc_error_mean(i), results.patterns.geoloc_error_std(i));
        table_data{i+1, 3} = sprintf('%.1f', results.patterns.mean_boresight(i));
        table_data{i+1, 4} = sprintf('%.3f', results.patterns.mean_interf_error(i));
    end
    
    % Display table
    t = uitable('Data', table_data, 'Units', 'normalized', 'Position', [0.1 0.2 0.8 0.6]);
    t.ColumnWidth = {150, 120, 120, 120};
    t.FontSize = 11;
    
    title_pos = axes('Position', [0 0 1 1], 'Visible', 'off');
    text(0.5, 0.9, 'Performance Summary', 'FontSize', 14, 'FontWeight', 'bold', ...
        'HorizontalAlignment', 'center', 'Parent', title_pos);
end


%% ===================================================================
%% SIMULATION FUNCTION (from main script)
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
    start_x = config.emitter_pos(1) - config.start_range;
    start_y = config.emitter_pos(2) + lateral_offset;
    end_x = config.emitter_pos(1) - config.end_range;
    end_y = config.emitter_pos(2) + lateral_offset;
    
    distance = sqrt((end_x - start_x)^2 + (end_y - start_y)^2);
    num_points = max(50, round(distance / (config.speed * config.dt)));
    
    positions = zeros(num_points, 3);
    headings = zeros(num_points, 1);
    
    for i = 1:num_points
        t = (i-1) / (num_points-1);
        x = start_x + t * (end_x - start_x);
        y = start_y + t * (end_y - start_y);
        
        dx = config.emitter_pos(1) - x;
        dy = config.emitter_pos(2) - y;
        heading = atan2d(dy, dx);
        
        positions(i, :) = [x, y, config.altitude];
        headings(i) = heading;
    end
end

function [positions, headings] = generate_curved_approach(config)
    initial_offset = config.lateral_offset;
    curvature = 0.8;
    if isfield(config, 'curvature')
        curvature = config.curvature;
    end
    
    total_distance = config.start_range - config.end_range;
    num_points = max(50, round(total_distance / (config.speed * config.dt)));
    
    positions = zeros(num_points, 3);
    headings = zeros(num_points, 1);
    
    for i = 1:num_points
        t = (i-1) / (num_points-1);
        x_progress = config.start_range - t * total_distance;
        lateral = initial_offset * (1 - t)^curvature;
        
        x = config.emitter_pos(1) - x_progress;
        y = config.emitter_pos(2) + lateral;
        
        dx = config.emitter_pos(1) - x;
        dy = config.emitter_pos(2) - y;
        heading = atan2d(dy, dx);
        
        positions(i, :) = [x, y, config.altitude];
        headings(i) = heading;
    end
end

function angle_error = calculate_angle_error(boresight_angle_deg, config)
    c = 11.8028;
    sigma_phase = deg2rad(config.phase_error_deg);
    boresight_rad = deg2rad(boresight_angle_deg);
    cos_boresight = cos(boresight_rad);
    
    if abs(cos_boresight) < 0.01
        cos_boresight = 0.01;
    end
    
    sigma_theta_rad = (c * sigma_phase) / ...
        (2 * pi * config.baseline_inches * config.frequency_ghz * cos_boresight);
    
    angle_error = rad2deg(sigma_theta_rad);
end

function [measured_dep, true_dep, boresight, angle_err] = measure_depression_angle(...
    uav_pos, uav_heading_deg, emitter_pos, config)
    
    dx = emitter_pos(1) - uav_pos(1);
    dy = emitter_pos(2) - uav_pos(2);
    dz = -uav_pos(3);
    
    horizontal_range = sqrt(dx^2 + dy^2);
    true_dep = atan2d(-dz, horizontal_range);
    
    % For bottom-mounted vertical interferometer:
    % Boresight = 90° - depression_angle
    boresight = 90 - true_dep;
    
    angle_err = calculate_angle_error(boresight, config);
    measured_dep = true_dep + angle_err * randn();
end

function estimated_pos = estimate_emitter_position(measurements)
    if length(measurements) < 2
        error('Need at least 2 measurements for geolocation');
    end
    
    all_positions = zeros(length(measurements), 2);
    for i = 1:length(measurements)
        all_positions(i, :) = measurements(i).uav_pos(1:2);
    end
    initial_guess = mean(all_positions, 1);
    
    options = optimoptions('lsqnonlin', 'Display', 'off', 'Algorithm', 'levenberg-marquardt');
    estimated_pos = lsqnonlin(@(pos) residuals_func(pos, measurements), ...
        initial_guess, [], [], options);
end

function res = residuals_func(emitter_xy, measurements)
    res = zeros(length(measurements), 1);
    
    for i = 1:length(measurements)
        uav_pos = measurements(i).uav_pos;
        measured_dep = measurements(i).depression;
        error_std = measurements(i).error;
        
        dx = emitter_xy(1) - uav_pos(1);
        dy = emitter_xy(2) - uav_pos(2);
        horizontal_range = sqrt(dx^2 + dy^2);
        expected_dep = atan2d(uav_pos(3), horizontal_range);
        
        weight = 1.0 / (error_std + 0.1);
        res(i) = weight * (measured_dep - expected_dep);
    end
end
