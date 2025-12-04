%% UAV Interferometer - Lateral Offset Sweep Analysis
% Analyzes how lateral offset affects geolocation performance in curved approach
% Includes explicit GDOP calculation and geometry analysis

clear all;
close all;
clc;

%% Fixed Configuration Parameters
config = struct();

% Fixed interferometer parameters
config.baseline_inches = 10;
config.frequency_ghz = 6;
config.phase_error_deg = 12;

% Fixed operational parameters
config.altitude = 1524;              % 5000 ft in meters
config.speed = 50;                   % m/s
config.dt = 1.0;                     % seconds
config.measurement_interval = 10;    % Take measurement every N timesteps
config.start_range = 20000;          % 20 km
config.end_range = 500;              % meters
config.curvature = 0.8;              % Curve aggressiveness (for curved pattern)
config.s_frequency = 2;              % Number of S-curves (for s-curve pattern)

% Emitter location
config.emitter_pos = [0, 0];

% Flight pattern selection
% Options: 'curved' or 's_curve'
config.flight_pattern = 's_curve';   % Change to 'curved' for original curved approach

%% Lateral Offset/Amplitude Sweep Definition
if strcmp(config.flight_pattern, 'curved')
    sweep_values = 200:200:3000;  % Lateral offsets for curved approach
    sweep_name = 'Lateral Offset';
else  % s_curve
    sweep_values = 200:200:3000;  % Weaving amplitudes for S-curve approach
    sweep_name = 'S-Curve Amplitude';
end

num_trials = 10;                  % Monte Carlo trials per configuration

fprintf('\n=== %s Sweep Analysis ===\n', sweep_name);
fprintf('Flight Pattern: %s\n', config.flight_pattern);
fprintf('Fixed Parameters:\n');
fprintf('  Altitude: %.0f m (%.0f ft)\n', config.altitude, config.altitude * 3.28084);
fprintf('  Start Range: %.0f km\n', config.start_range / 1000);
fprintf('  End Range: %.0f m\n', config.end_range);
fprintf('\nRunning sweep from %.0f m to %.0f m %s...\n\n', ...
    sweep_values(1), sweep_values(end), lower(sweep_name));

%% Run Sweep
results = run_lateral_sweep(sweep_values, config, num_trials);

%% Generate Comprehensive Plots
generate_comprehensive_plots(results, sweep_values, config, sweep_name);

fprintf('\n=== Analysis Complete ===\n\n');


%% ===================================================================
%% SWEEP EXECUTION
%% ===================================================================

function results = run_lateral_sweep(sweep_values, base_config, num_trials)
    num_points = length(sweep_values);
    
    % Initialize storage arrays
    results = struct();
    results.sweep_values = sweep_values;
    
    % Performance metrics
    results.geoloc_error_mean = zeros(num_points, 1);
    results.geoloc_error_std = zeros(num_points, 1);
    results.geoloc_error_all = cell(num_points, 1);
    
    % Interferometer metrics
    results.mean_boresight = zeros(num_points, 1);
    results.min_boresight = zeros(num_points, 1);
    results.max_boresight = zeros(num_points, 1);
    results.mean_interf_error = zeros(num_points, 1);
    results.max_interf_error = zeros(num_points, 1);
    
    % Pointing angle metrics
    results.mean_pointing_angle = zeros(num_points, 1);
    results.max_pointing_angle = zeros(num_points, 1);
    results.percent_within_30deg = zeros(num_points, 1);
    
    % Geometry metrics
    results.gdop = zeros(num_points, 1);
    results.gdop_x = zeros(num_points, 1);
    results.gdop_y = zeros(num_points, 1);
    results.condition_number = zeros(num_points, 1);
    results.num_measurements = zeros(num_points, 1);
    
    % Trajectory and measurement details (save one example per offset)
    results.example_trajectories = cell(num_points, 1);
    results.example_measurements = cell(num_points, 1);
    results.example_pointing_angles = cell(num_points, 1);
    
    for i = 1:num_points
        config = base_config;
        
        % Set appropriate parameter based on flight pattern
        if strcmp(config.flight_pattern, 'curved')
            config.lateral_offset = sweep_values(i);
        else  % s_curve
            config.s_amplitude = sweep_values(i);
        end
        
        trial_errors = zeros(num_trials, 1);
        
        fprintf('Sweep value: %.0f m... ', sweep_values(i));
        
        for trial = 1:num_trials
            [measurements, trajectory, estimated_pos, res, pointing_angles] = simulate_geolocation(config);
            trial_errors(trial) = res.position_error;
            
            % Store first trial details
            if trial == 1
                results.mean_boresight(i) = res.mean_boresight;
                results.min_boresight(i) = min([measurements.boresight]);
                results.max_boresight(i) = max([measurements.boresight]);
                results.mean_interf_error(i) = res.mean_angle_error;
                results.max_interf_error(i) = res.max_angle_error;
                results.num_measurements(i) = length(measurements);
                
                % Pointing angle statistics
                results.mean_pointing_angle(i) = mean(abs(pointing_angles));
                results.max_pointing_angle(i) = max(abs(pointing_angles));
                results.percent_within_30deg(i) = 100 * sum(abs(pointing_angles) <= 30) / length(pointing_angles);
                
                % Calculate GDOP
                gdop_metrics = calculate_gdop(measurements, config.emitter_pos, config.altitude);
                results.gdop(i) = gdop_metrics.gdop;
                results.gdop_x(i) = gdop_metrics.gdop_x;
                results.gdop_y(i) = gdop_metrics.gdop_y;
                results.condition_number(i) = gdop_metrics.condition_number;
                
                % Save example trajectory and measurements
                results.example_trajectories{i} = trajectory;
                results.example_measurements{i} = measurements;
                results.example_pointing_angles{i} = pointing_angles;
            end
        end
        
        % Statistics over trials
        results.geoloc_error_mean(i) = mean(trial_errors);
        results.geoloc_error_std(i) = std(trial_errors);
        results.geoloc_error_all{i} = trial_errors;
        
        fprintf('Geoloc: %.1f ± %.1f m, GDOP: %.2f, Mean Point: %.1f°\n', ...
            results.geoloc_error_mean(i), results.geoloc_error_std(i), ...
            results.gdop(i), results.mean_pointing_angle(i));
    end
end


%% ===================================================================
%% GDOP CALCULATION
%% ===================================================================

function gdop_metrics = calculate_gdop(measurements, true_emitter_pos, altitude)
    % Calculate Geometric Dilution of Precision
    % GDOP quantifies how measurement geometry amplifies sensor errors
    % Returns unitless GDOP where Position_Error ≈ GDOP × (Angular_Error × Range)
    
    num_meas = length(measurements);
    
    % Build Jacobian matrix (measurement sensitivity to position)
    % H(i,j) = ∂(depression_angle_i)/∂(position_j) in radians/meter
    H = zeros(num_meas, 2);  % 2D position (x, y)
    
    for i = 1:num_meas
        uav_pos = measurements(i).uav_pos;
        
        % Position differences
        dx = true_emitter_pos(1) - uav_pos(1);
        dy = true_emitter_pos(2) - uav_pos(2);
        h_range = sqrt(dx^2 + dy^2);
        
        % Partial derivatives of depression angle w.r.t. emitter position
        % depression = atan2(altitude, h_range)
        % ∂depression/∂x and ∂depression/∂y
        
        % Common term
        denom = altitude^2 + h_range^2;
        
        % Chain rule: ∂depression/∂x = (∂depression/∂h_range) * (∂h_range/∂x)
        ddep_dhrange = -altitude / denom;  % Derivative of atan2(altitude, h_range) w.r.t. h_range
        
        H(i, 1) = ddep_dhrange * (dx / h_range);  % ∂depression/∂x in radians/meter
        H(i, 2) = ddep_dhrange * (dy / h_range);  % ∂depression/∂y in radians/meter
    end
    
    % Measurement error covariance matrix (diagonal, uncorrelated measurements)
    % Convert angular errors to radians
    measurement_variances = zeros(num_meas, 1);
    for i = 1:num_meas
        measurement_variances(i) = (measurements(i).error * pi/180)^2;  % rad^2
    end
    
    R = diag(measurement_variances);  % Measurement noise covariance
    
    % Try to compute covariance via standard formula
    % Position covariance = (H^T * R^-1 * H)^-1
    
    try
        % Fisher Information Matrix: H^T * R^-1 * H
        FIM = H' * (R \ H);
        
        % Position covariance matrix (meters^2)
        if rcond(FIM) > 1e-12
            Cov = inv(FIM);  % meters^2
            
            % GDOP is sqrt of trace of normalized covariance
            % Standard GDOP definition: sqrt(trace(Cov)) / σ_measurement
            % But we want unitless, so we normalize differently
            
            % Calculate mean measurement error in radians
            mean_angular_error = mean(sqrt(measurement_variances));  % radians
            
            % Position uncertainty (meters)
            position_uncertainty = sqrt(trace(Cov));  % meters
            
            % Typical range for normalization (geometric mean of all ranges)
            ranges = zeros(num_meas, 1);
            for i = 1:num_meas
                uav_pos = measurements(i).uav_pos;
                dx = true_emitter_pos(1) - uav_pos(1);
                dy = true_emitter_pos(2) - uav_pos(2);
                ranges(i) = sqrt(dx^2 + dy^2);
            end
            mean_range = geomean(ranges);
            
            % GDOP = Position_Uncertainty / (Angular_Error × Range)
            % This gives unitless amplification factor
            gdop_metrics.gdop = position_uncertainty / (mean_angular_error * mean_range);
            
            % Component GDOPs
            gdop_metrics.gdop_x = sqrt(Cov(1,1)) / (mean_angular_error * mean_range);
            gdop_metrics.gdop_y = sqrt(Cov(2,2)) / (mean_angular_error * mean_range);
            
            gdop_metrics.covariance = Cov;  % meters^2
            gdop_metrics.position_uncertainty = position_uncertainty;  % meters
            gdop_metrics.condition_number = cond(H);
        else
            % Singular or near-singular - poor geometry
            gdop_metrics.gdop = Inf;
            gdop_metrics.gdop_x = Inf;
            gdop_metrics.gdop_y = Inf;
            gdop_metrics.covariance = Inf(2,2);
            gdop_metrics.position_uncertainty = Inf;
            gdop_metrics.condition_number = Inf;
        end
    catch
        % Matrix inversion failed
        gdop_metrics.gdop = Inf;
        gdop_metrics.gdop_x = Inf;
        gdop_metrics.gdop_y = Inf;
        gdop_metrics.covariance = Inf(2,2);
        gdop_metrics.position_uncertainty = Inf;
        gdop_metrics.condition_number = Inf;
    end
    
    gdop_metrics.jacobian = H;
end


%% ===================================================================
%% PLOTTING
%% ===================================================================

function generate_comprehensive_plots(results, sweep_values, config, sweep_name)
    
    %% Figure 1: Main Performance Metrics
    figure('Position', [50, 50, 1600, 1200]);
    
    % Plot 1: Geolocation Error
    subplot(3, 3, 1);
    hold on;
    errorbar(sweep_values, results.geoloc_error_mean, results.geoloc_error_std, ...
        'ko-', 'LineWidth', 2, 'MarkerSize', 8, 'MarkerFaceColor', 'k', 'CapSize', 10);
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('Geolocation Error (m)', 'FontWeight', 'bold', 'FontSize', 12);
    title('Geolocation Performance', 'FontWeight', 'bold', 'FontSize', 14);
    grid on;
    hold off;
    
    % Plot 2: GDOP
    subplot(3, 3, 2);
    hold on;
    plot(sweep_values, results.gdop, 'b-o', 'LineWidth', 2, 'MarkerSize', 8, 'MarkerFaceColor', 'b');
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('GDOP', 'FontWeight', 'bold', 'FontSize', 12);
    title('Geometric Dilution of Precision', 'FontWeight', 'bold', 'FontSize', 14);
    grid on;
    hold off;
    
    % Plot 3: Boresight Angles
    subplot(3, 3, 3);
    hold on;
    plot(sweep_values, results.mean_boresight, 'r-o', 'LineWidth', 2, ...
        'MarkerSize', 8, 'DisplayName', 'Mean');
    plot(sweep_values, results.min_boresight, 'g--s', 'LineWidth', 1.5, ...
        'MarkerSize', 6, 'DisplayName', 'Min (Best)');
    plot(sweep_values, results.max_boresight, 'm--^', 'LineWidth', 1.5, ...
        'MarkerSize', 6, 'DisplayName', 'Max (Worst)');
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('Boresight Angle (deg)', 'FontWeight', 'bold', 'FontSize', 12);
    title('Interferometer Boresight Angles', 'FontWeight', 'bold', 'FontSize', 14);
    legend('Location', 'best');
    grid on;
    hold off;
    
    % Plot 4: Interferometer Error
    subplot(3, 3, 4);
    hold on;
    plot(sweep_values, results.mean_interf_error, 'r-o', 'LineWidth', 2, ...
        'MarkerSize', 8, 'DisplayName', 'Mean');
    plot(sweep_values, results.max_interf_error, 'm--^', 'LineWidth', 1.5, ...
        'MarkerSize', 6, 'DisplayName', 'Max');
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('Angular Error (deg)', 'FontWeight', 'bold', 'FontSize', 12);
    title('Interferometer Measurement Error', 'FontWeight', 'bold', 'FontSize', 14);
    legend('Location', 'best');
    grid on;
    hold off;
    
    % Plot 5: UAV Pointing Angle
    subplot(3, 3, 5);
    hold on;
    plot(sweep_values, results.mean_pointing_angle, 'b-o', 'LineWidth', 2, ...
        'MarkerSize', 8, 'DisplayName', 'Mean');
    plot(sweep_values, results.max_pointing_angle, 'r--s', 'LineWidth', 1.5, ...
        'MarkerSize', 6, 'DisplayName', 'Max');
    yline(30, 'k--', 'LineWidth', 2, 'DisplayName', '30° Goal');
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('Pointing Angle (deg)', 'FontWeight', 'bold', 'FontSize', 12);
    title('UAV Pointing Angle from Emitter', 'FontWeight', 'bold', 'FontSize', 14);
    legend('Location', 'best');
    grid on;
    hold off;
    
    % Plot 6: Percent Within 30° Goal
    subplot(3, 3, 6);
    bar(sweep_values, results.percent_within_30deg, 'FaceColor', [0.2 0.7 0.3]);
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('% of Flight Within 30°', 'FontWeight', 'bold', 'FontSize', 12);
    title('Compliance with 30° Pointing Goal', 'FontWeight', 'bold', 'FontSize', 14);
    grid on;
    ylim([0 100]);
    
    % Plot 7: Error Breakdown
    subplot(3, 3, 7);
    hold on;
    % Normalize to show relative contributions
    interf_contribution = results.mean_interf_error * 111000;  % Convert deg to meters (rough)
    geom_amplification = results.geoloc_error_mean ./ interf_contribution;
    
    yyaxis left;
    plot(sweep_values, results.mean_interf_error * 111000, 'r-o', ...
        'LineWidth', 2, 'MarkerSize', 8);
    ylabel('Sensor Error (m)', 'FontWeight', 'bold', 'FontSize', 12, 'Color', 'r');
    
    yyaxis right;
    plot(sweep_values, geom_amplification, 'b-s', ...
        'LineWidth', 2, 'MarkerSize', 8);
    ylabel('Geometric Amplification', 'FontWeight', 'bold', 'FontSize', 12, 'Color', 'b');
    
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    title('Error Breakdown: Sensor vs Geometry', 'FontWeight', 'bold', 'FontSize', 14);
    grid on;
    hold off;
    
    % Plot 8: GDOP Components (X vs Y)
    subplot(3, 3, 8);
    hold on;
    plot(sweep_values, results.gdop_x, 'r-o', 'LineWidth', 2, ...
        'MarkerSize', 8, 'DisplayName', 'GDOP X');
    plot(sweep_values, results.gdop_y, 'b-s', 'LineWidth', 2, ...
        'MarkerSize', 8, 'DisplayName', 'GDOP Y');
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('GDOP Component', 'FontWeight', 'bold', 'FontSize', 12);
    title('GDOP by Axis', 'FontWeight', 'bold', 'FontSize', 14);
    legend('Location', 'best');
    grid on;
    hold off;
    
    % Plot 9: Number of Measurements
    subplot(3, 3, 9);
    bar(sweep_values, results.num_measurements, 'FaceColor', [0.5 0.5 0.8]);
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('Number of Measurements', 'FontWeight', 'bold', 'FontSize', 12);
    title('Measurements Per Flight', 'FontWeight', 'bold', 'FontSize', 14);
    grid on;
    
    sgtitle(sprintf('%s Sweep - %s Pattern (Alt: %.0fm, Range: %.0fkm)', ...
        sweep_name, strrep(config.flight_pattern, '_', '-'), config.altitude, config.start_range/1000), ...
        'FontSize', 16, 'FontWeight', 'bold');
    
    
    %% Figure 2: Example Trajectories at Different Values
    figure('Position', [100, 100, 1400, 1000]);
    
    % Select 4 representative values to display
    num_examples = min(4, length(sweep_values));
    example_indices = round(linspace(1, length(sweep_values), num_examples));
    
    for idx = 1:num_examples
        i = example_indices(idx);
        
        subplot(2, 2, idx);
        hold on;
        
        trajectory = results.example_trajectories{i};
        measurements = results.example_measurements{i};
        pointing_angles = results.example_pointing_angles{i};
        
        % Extract measurement positions and boresight angles
        meas_pos = zeros(length(measurements), 2);
        boresight_vals = zeros(length(measurements), 1);
        for j = 1:length(measurements)
            meas_pos(j, :) = measurements(j).uav_pos(1:2);
            boresight_vals(j) = measurements(j).boresight;
        end
        
        % Plot emitter
        plot(config.emitter_pos(1), config.emitter_pos(2), 'r*', ...
            'MarkerSize', 25, 'LineWidth', 3);
        
        % Plot full trajectory, color by pointing angle compliance
        compliant = abs(pointing_angles) <= 30;
        plot(trajectory(compliant, 1), trajectory(compliant, 2), 'g-', 'LineWidth', 2);
        plot(trajectory(~compliant, 1), trajectory(~compliant, 2), 'Color', [1 0.5 0], 'LineWidth', 2);
        
        % Plot measurement points color-coded by boresight
        scatter(meas_pos(:,1), meas_pos(:,2), 80, boresight_vals, 'filled');
        colorbar;
        caxis([0 90]);
        
        % Plot sample bearing lines
        sample_idx = round(linspace(1, length(measurements), min(10, length(measurements))));
        for j = sample_idx
            plot([meas_pos(j,1), config.emitter_pos(1)], ...
                 [meas_pos(j,2), config.emitter_pos(2)], ...
                 'Color', [0.5 0.5 0.5 0.3], 'LineWidth', 0.5);
        end
        
        xlabel('X Position (m)', 'FontWeight', 'bold');
        ylabel('Y Position (m)', 'FontWeight', 'bold');
        title(sprintf('%s: %.0f m\nGDOP: %.2f, Error: %.1f m, %.0f%% within 30°', ...
            sweep_name, sweep_values(i), results.gdop(i), results.geoloc_error_mean(i), ...
            results.percent_within_30deg(i)), 'FontWeight', 'bold');
        grid on;
        axis equal;
        hold off;
    end
    
    sgtitle('Example Flight Geometries (Green=Within 30°, Orange=>30°, Color=Boresight)', ...
        'FontSize', 16, 'FontWeight', 'bold');
    
    
    %% Figure 3: Trade-off Analysis
    figure('Position', [150, 150, 1200, 500]);
    
    % Normalize all metrics to [0, 1] for comparison
    norm_geoloc_error = (results.geoloc_error_mean - min(results.geoloc_error_mean)) / ...
        (max(results.geoloc_error_mean) - min(results.geoloc_error_mean));
    norm_gdop = (results.gdop - min(results.gdop)) / (max(results.gdop) - min(results.gdop));
    norm_interf_error = (results.mean_interf_error - min(results.mean_interf_error)) / ...
        (max(results.mean_interf_error) - min(results.mean_interf_error));
    
    subplot(1, 2, 1);
    hold on;
    plot(sweep_values, norm_geoloc_error, 'k-o', 'LineWidth', 2.5, ...
        'MarkerSize', 10, 'MarkerFaceColor', 'k', 'DisplayName', 'Geolocation Error');
    plot(sweep_values, norm_gdop, 'b--s', 'LineWidth', 2, ...
        'MarkerSize', 8, 'MarkerFaceColor', 'b', 'DisplayName', 'GDOP (Geometry)');
    plot(sweep_values, norm_interf_error, 'r--^', 'LineWidth', 2, ...
        'MarkerSize', 8, 'MarkerFaceColor', 'r', 'DisplayName', 'Interferometer Error');
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('Normalized Value', 'FontWeight', 'bold', 'FontSize', 12);
    title('Trade-off: Sensor Quality vs Geometry', 'FontWeight', 'bold', 'FontSize', 14);
    legend('Location', 'best', 'FontSize', 11);
    grid on;
    ylim([0 1.1]);
    hold off;
    
    % Find optimal value (minimum geolocation error)
    [min_error, min_idx] = min(results.geoloc_error_mean);
    optimal_value = sweep_values(min_idx);
    
    subplot(1, 2, 2);
    bar(sweep_values, results.geoloc_error_mean, 'FaceColor', [0.3 0.6 0.9]);
    hold on;
    plot(optimal_value, min_error, 'r*', 'MarkerSize', 20, 'LineWidth', 3);
    text(optimal_value, min_error + 50, sprintf('Optimal: %.0fm\nError: %.1fm', ...
        optimal_value, min_error), 'HorizontalAlignment', 'center', ...
        'FontWeight', 'bold', 'FontSize', 11, 'BackgroundColor', 'w');
    xlabel(sprintf('%s (m)', sweep_name), 'FontWeight', 'bold', 'FontSize', 12);
    ylabel('Geolocation Error (m)', 'FontWeight', 'bold', 'FontSize', 12);
    title(sprintf('Optimal %s', sweep_name), 'FontWeight', 'bold', 'FontSize', 14);
    grid on;
    hold off;
    
    sgtitle('Performance Trade-off Analysis', 'FontSize', 16, 'FontWeight', 'bold');
    
    % Print summary
    fprintf('\n=== OPTIMAL CONFIGURATION ===\n');
    fprintf('Optimal %s: %.0f m\n', sweep_name, optimal_value);
    fprintf('Geolocation Error: %.1f ± %.1f m\n', min_error, results.geoloc_error_std(min_idx));
    fprintf('GDOP: %.2f\n', results.gdop(min_idx));
    fprintf('Mean Boresight: %.1f°\n', results.mean_boresight(min_idx));
    fprintf('Mean Pointing Angle: %.1f°\n', results.mean_pointing_angle(min_idx));
    fprintf('Percent Within 30°: %.1f%%\n', results.percent_within_30deg(min_idx));
    fprintf('Mean Interferometer Error: %.3f°\n', results.mean_interf_error(min_idx));
    fprintf('Number of Measurements: %d\n', results.num_measurements(min_idx));
end


%% ===================================================================
%% SIMULATION FUNCTIONS (from main script)
%% ===================================================================

function [measurements, trajectory, estimated_pos, results, pointing_angles] = simulate_geolocation(config)
    % Generate flight trajectory based on pattern
    if strcmp(config.flight_pattern, 'curved')
        [trajectory, headings] = generate_curved_approach(config);
    elseif strcmp(config.flight_pattern, 's_curve')
        [trajectory, headings] = generate_s_curve_approach(config);
    else
        error('Unknown flight pattern: %s', config.flight_pattern);
    end
    
    measurements = struct('uav_pos', {}, 'heading', {}, 'depression', {}, ...
                         'true_depression', {}, 'boresight', {}, 'error', {});
    
    % Calculate pointing angles for all trajectory points
    pointing_angles = zeros(size(trajectory, 1), 1);
    for i = 1:size(trajectory, 1)
        uav_pos = trajectory(i, :);
        uav_heading = headings(i);
        
        % Calculate bearing to emitter
        dx = config.emitter_pos(1) - uav_pos(1);
        dy = config.emitter_pos(2) - uav_pos(2);
        bearing_to_emitter = atan2d(dy, dx);
        
        % Pointing angle = difference between heading and bearing to emitter
        pointing_angles(i) = bearing_to_emitter - uav_heading;
        
        % Normalize to [-180, 180]
        while pointing_angles(i) > 180
            pointing_angles(i) = pointing_angles(i) - 360;
        end
        while pointing_angles(i) < -180
            pointing_angles(i) = pointing_angles(i) + 360;
        end
    end
    
    % Take measurements
    meas_idx = 1;
    for i = 1:config.measurement_interval:size(trajectory, 1)
        uav_pos = trajectory(i, :);
        uav_heading = headings(i);
        
        [meas_dep, true_dep, boresight, angle_err] = measure_depression_angle(...
            uav_pos, uav_heading, config.emitter_pos, config);
        
        measurements(meas_idx).uav_pos = uav_pos;
        measurements(meas_idx).heading = uav_heading;
        measurements(meas_idx).depression = meas_dep;
        measurements(meas_idx).true_depression = true_dep;
        measurements(meas_idx).boresight = boresight;
        measurements(meas_idx).error = angle_err;
        
        meas_idx = meas_idx + 1;
    end
    
    estimated_pos = estimate_emitter_position(measurements);
    
    results = struct();
    results.position_error = norm(estimated_pos - config.emitter_pos);
    results.mean_boresight = mean([measurements.boresight]);
    results.mean_angle_error = mean([measurements.error]);
    results.max_angle_error = max([measurements.error]);
    results.min_angle_error = min([measurements.error]);
end

function [positions, headings] = generate_curved_approach(config)
    initial_offset = config.lateral_offset;
    curvature = config.curvature;
    
    total_distance = config.start_range - config.end_range;
    num_points = max(100, round(total_distance / (config.speed * config.dt)));
    
    positions = zeros(num_points, 3);
    headings = zeros(num_points, 1);
    
    for i = 1:num_points
        t = (i-1) / (num_points-1);
        x_progress = config.start_range - t * total_distance;
        lateral = initial_offset * (1 - t)^curvature;
        
        x = config.emitter_pos(1) - x_progress;
        y = config.emitter_pos(2) + lateral;
        
        positions(i, :) = [x, y, config.altitude];
    end
    
    % Calculate headings based on flight path tangent (direction of motion)
    for i = 1:num_points
        if i < num_points
            % Use forward difference (direction to next point)
            dx_path = positions(i+1, 1) - positions(i, 1);
            dy_path = positions(i+1, 2) - positions(i, 2);
        else
            % Use backward difference for last point
            dx_path = positions(i, 1) - positions(i-1, 1);
            dy_path = positions(i, 2) - positions(i-1, 2);
        end
        
        % Heading follows direction of motion
        headings(i) = atan2d(dy_path, dx_path);
    end
end

function [positions, headings] = generate_s_curve_approach(config)
    % S-curve (sinusoidal weaving) approach
    % Weaves back and forth while approaching emitter
    % Amplitude determines how wide the weaving is
    
    amplitude = config.s_amplitude;  % Lateral weaving amplitude (meters)
    
    if ~isfield(config, 's_frequency')
        % Number of complete S-curves over the approach
        num_cycles = 2;  % Default: 2 complete sine waves
    else
        num_cycles = config.s_frequency;
    end
    
    total_distance = config.start_range - config.end_range;
    num_points = max(100, round(total_distance / (config.speed * config.dt)));
    
    positions = zeros(num_points, 3);
    headings = zeros(num_points, 1);
    
    for i = 1:num_points
        t = (i-1) / (num_points-1);
        
        % Progress toward emitter (x-axis)
        x_progress = config.start_range - t * total_distance;
        
        % Sinusoidal lateral offset
        % sin(2*pi*cycles*t) gives the weaving pattern
        lateral = amplitude * sin(2 * pi * num_cycles * t);
        
        x = config.emitter_pos(1) - x_progress;
        y = config.emitter_pos(2) + lateral;
        
        positions(i, :) = [x, y, config.altitude];
    end
    
    % Calculate headings based on flight path tangent (direction of motion)
    for i = 1:num_points
        if i < num_points
            % Use forward difference (direction to next point)
            dx_path = positions(i+1, 1) - positions(i, 1);
            dy_path = positions(i+1, 2) - positions(i, 2);
        else
            % Use backward difference for last point
            dx_path = positions(i, 1) - positions(i-1, 1);
            dy_path = positions(i, 2) - positions(i-1, 2);
        end
        
        % Heading follows direction of motion
        headings(i) = atan2d(dy_path, dx_path);
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
    
    % Vector from UAV to emitter (signal arrival direction)
    dx = emitter_pos(1) - uav_pos(1);
    dy = emitter_pos(2) - uav_pos(2);
    dz = -uav_pos(3);  % Negative because emitter is below UAV
    
    horizontal_range = sqrt(dx^2 + dy^2);
    slant_range = sqrt(dx^2 + dy^2 + dz^2);
    
    % True depression angle (below horizontal)
    true_dep = atan2d(-dz, horizontal_range);
    
    % Normalize signal direction vector
    signal_unit = [dx, dy, dz] / slant_range;
    
    % Baseline vector (belly-mounted, nose-to-tail orientation)
    % When UAV is level: baseline points straight down but is oriented along fuselage
    % The baseline is vertical (points in -Z), but rotates in azimuth with UAV heading
    
    % For a vertical baseline with nose-to-tail orientation:
    % The baseline vector is [0, 0, -1] in UAV body frame
    % But we need it in the world frame, accounting for UAV heading
    
    % Actually, since the interferometer is mounted pointing DOWN and the baseline
    % runs nose-to-tail, the baseline vector is simply vertical: [0, 0, -1]
    % The heading affects which plane we measure in, but the baseline is still vertical
    
    baseline_unit = [0, 0, -1];  % Vertical, pointing down
    
    % Boresight angle = angle between signal and baseline vectors
    % cos(boresight) = dot product of unit vectors
    cos_boresight = dot(signal_unit, baseline_unit);
    
    % Boresight angle in degrees
    % 0° = signal along baseline (from directly below) - BEST
    % 90° = signal perpendicular to baseline (horizontal) - WORST
    boresight = acosd(abs(cos_boresight));
    
    % For a vertical baseline and ground emitter:
    % boresight = 90° - depression_angle
    % This should match our previous calculation, but now it's derived from first principles
    
    % HOWEVER - the key insight is that the measurement is taken in the plane
    % defined by the baseline and the UAV heading direction
    % The measurement itself is the depression angle in that specific azimuthal plane
    
    % The depression angle measured by the interferometer is in the plane
    % containing the nose-to-tail axis (rotated by heading)
    heading_rad = deg2rad(uav_heading_deg);
    
    % Project signal onto the vertical plane containing the UAV heading
    % Heading direction (in horizontal plane)
    heading_vec = [cos(heading_rad), sin(heading_rad), 0];
    
    % Component of horizontal signal direction along heading
    horiz_signal = [dx, dy, 0] / horizontal_range;
    along_heading = dot(horiz_signal, heading_vec);
    
    % Range in the plane of measurement (along heading direction)
    range_in_plane = along_heading * horizontal_range;
    
    % Depression angle in the measurement plane
    % This is what the interferometer actually measures
    measured_dep_true = atan2d(-dz, abs(range_in_plane));
    
    % Use this as the true measured value (before noise)
    true_dep = measured_dep_true;
    
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
        
        % CHANGED: Use equal weighting instead of error-based weighting
        % This allows geometric diversity to contribute properly
        % Previously: weight = 1.0 / (error_std + 0.1);
        weight = 1.0;  % Equal weight for all measurements
        
        res(i) = weight * (measured_dep - expected_dep);
    end
end
