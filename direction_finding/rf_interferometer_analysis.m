% 1D RF Interferometer Analysis
% 4-element array for 2-18 GHz operation
% Analysis of angle accuracy and ambiguity regions

clear all; close all; clc;

%% System Parameters
n_elements = 4;
freq_range = [2e9, 18e9]; % Hz
c_light_in_per_ns = 11.8028; % Speed of light in inches/nanosecond
phase_error_deg = 12; % Phase error in degrees at high SNR (baseline system noise)

% Signal and Noise Parameters
signal_strength_dbm = -60; % Input signal strength (dBm)
noise_floor_dbm = -100; % System noise floor (dBm)

% Antenna Pattern CSV file
antenna_pattern_file = 'antenna_pattern.csv'; % Replace with your CSV filename
antenna_pattern_freq_ghz = 9; % Frequency at which pattern was measured (GHz)

% Define baseline spacing (distance between any two elements)
% Total aperture (longest baseline) = 10 inches for accuracy
% Non-uniform (Vernier) spacing to resolve ambiguities
% Shortest spacing based on lambda/2 at 18 GHz for unambiguous coverage

lambda_min = c_light_in_per_ns / (freq_range(2)/1e9); % inches at 18 GHz
d_short = lambda_min / 2; % Shortest spacing for ambiguity resolution

% Non-uniform element positions - optimized for 2-18 GHz
% Configuration: short baseline for ambiguity, long baseline for accuracy
element_positions = [0, d_short, 3.5, 10.0]; % inches

% Calculate all possible baselines between elements
baselines_adjacent = diff(element_positions); % Adjacent spacings
baselines_all = [];
for i = 1:n_elements
    for j = i+1:n_elements
        baselines_all = [baselines_all, element_positions(j) - element_positions(i)];
    end
end
baselines_all = unique(baselines_all); % All unique baselines

fprintf('Interferometer Configuration:\n');
fprintf('Number of elements: %d\n', n_elements);
fprintf('Total aperture (longest baseline): %.2f inches (%.1f mm)\n', max(baselines_all), max(baselines_all)*25.4);
fprintf('Shortest baseline: %.3f inches (%.2f mm)\n', min(baselines_all), min(baselines_all)*25.4);
fprintf('Element positions: [%.2f, %.2f, %.2f, %.2f] inches\n', element_positions);
fprintf('All unique baselines: '); fprintf('%.2f  ', baselines_all); fprintf('inches\n');
fprintf('Phase error at high SNR: %.1f degrees\n', phase_error_deg);
fprintf('Signal strength: %.1f dBm\n', signal_strength_dbm);
fprintf('Noise floor: %.1f dBm\n\n', noise_floor_dbm);

%% Load and Process Antenna Pattern
fprintf('Loading antenna pattern from: %s\n', antenna_pattern_file);
fprintf('Pattern measured at %.0f GHz, applied across 2-18 GHz band\n', antenna_pattern_freq_ghz);

% Check if file exists
if ~isfile(antenna_pattern_file)
    fprintf('Warning: Antenna pattern file not found. Using ideal isotropic pattern (0 dB gain).\n');
    % Create ideal isotropic pattern
    antenna_angles = 0:1:90;
    antenna_gain_db = zeros(size(antenna_angles));
else
    % Load CSV file
    antenna_data = readmatrix(antenna_pattern_file);
    
    % Extract columns: I_hat (angle) and R (gain in dB)
    all_angles = antenna_data(:, 1);
    all_gains = antenna_data(:, 2);
    
    % Extract 0:90 degrees
    idx_0_90 = (all_angles >= 0) & (all_angles <= 90);
    angles_0_90 = all_angles(idx_0_90);
    gains_0_90 = all_gains(idx_0_90);
    
    % Extract 270:360 degrees and convert to 90:0 (mirror)
    idx_270_360 = (all_angles >= 270) & (all_angles <= 360);
    angles_270_360 = 360 - all_angles(idx_270_360); % Convert to equivalent 90:0
    gains_270_360 = all_gains(idx_270_360);
    
    % Combine and sort
    antenna_angles = [angles_0_90; angles_270_360];
    antenna_gain_db = [gains_0_90; gains_270_360];
    [antenna_angles, sort_idx] = sort(antenna_angles);
    antenna_gain_db = antenna_gain_db(sort_idx);
    
    fprintf('Antenna pattern loaded: %d data points from 0 to %.1f degrees\n', ...
        length(antenna_angles), max(antenna_angles));
    fprintf('Gain at boresight: %.1f dB, at 45°: %.1f dB, at 70°: %.1f dB\n', ...
        interp1(antenna_angles, antenna_gain_db, 0, 'linear'), ...
        interp1(antenna_angles, antenna_gain_db, 45, 'linear'), ...
        interp1(antenna_angles, antenna_gain_db, 70, 'linear'));
end

% Create interpolation function for antenna gain
% Pattern assumed to be similar across frequency band
antenna_gain_interp = @(angle) interp1(antenna_angles, antenna_gain_db, ...
    abs(angle), 'linear', 'extrap');

%% Analysis Parameters
incident_angles = -80:0.5:80; % Degrees off boresight
test_frequencies = [2, 5, 10, 15, 18] * 1e9; % Test frequencies in Hz
n_freq = length(test_frequencies);

%% Compute Angle Accuracy with SNR-dependent Phase Error
angle_error_ideal = zeros(n_freq, length(incident_angles));
angle_error_realistic = zeros(n_freq, length(incident_angles));
snr_db = zeros(n_freq, length(incident_angles));
phase_error_realistic = zeros(n_freq, length(incident_angles));

for f_idx = 1:n_freq
    f = test_frequencies(f_idx);
    
    for ang_idx = 1:length(incident_angles)
        theta = incident_angles(ang_idx);
        
        % Use longest baseline (10 inches) for best accuracy
        D = max(baselines_all);
        
        % Get antenna gain at this angle
        gain_db = antenna_gain_interp(abs(theta));
        
        % Calculate SNR at this angle
        % SNR = Signal + Gain - Noise
        snr_db(f_idx, ang_idx) = signal_strength_dbm + gain_db - noise_floor_dbm;
        snr_linear = 10^(snr_db(f_idx, ang_idx)/10);
        
        % Phase error increases with decreasing SNR
        % At high SNR: phase_error = phase_error_deg
        % Phase error scales as 1/sqrt(SNR) for low SNR
        % Use a model: σ_phase = σ_baseline / sqrt(SNR_linear) for SNR < some threshold
        % For high SNR, phase error is constant at baseline value
        if snr_linear > 100 % High SNR threshold (20 dB)
            phase_error_at_angle = phase_error_deg;
        else
            % Phase error degrades as SNR drops
            phase_error_at_angle = phase_error_deg * sqrt(100 / max(snr_linear, 1));
        end
        phase_error_realistic(f_idx, ang_idx) = phase_error_at_angle;
        
        % Convert phase error from degrees to radians
        phase_error_rad_ideal = phase_error_deg * pi / 180;
        phase_error_rad_realistic = phase_error_at_angle * pi / 180;
        
        % Angle error formula: 11.8028 * phase_error / (2*pi*D*f*cos(incident_angle))
        % Result is in radians, convert to degrees
        
        % Ideal case (constant phase error)
        angle_error_rad = abs(c_light_in_per_ns * phase_error_rad_ideal / ...
            (2*pi * D * (f/1e9) * cosd(theta)));
        angle_error_ideal(f_idx, ang_idx) = angle_error_rad * 180 / pi;
        
        % Realistic case (SNR-dependent phase error)
        angle_error_rad = abs(c_light_in_per_ns * phase_error_rad_realistic / ...
            (2*pi * D * (f/1e9) * cosd(theta)));
        angle_error_realistic(f_idx, ang_idx) = angle_error_rad * 180 / pi;
    end
end

%% Compute Ambiguity Regions
% Unambiguous angle range for each baseline
ambiguity_angle = zeros(length(baselines_all), n_freq);

for f_idx = 1:n_freq
    f = test_frequencies(f_idx);
    lambda = c_light_in_per_ns / (f/1e9); % wavelength in inches
    
    for b_idx = 1:length(baselines_all)
        D = baselines_all(b_idx);
        % Unambiguous angle when phase difference = 2π
        % 2π*D*sin(θ)/λ = 2π → sin(θ) = λ/D
        if lambda/D <= 1
            ambiguity_angle(b_idx, f_idx) = asind(lambda/D);
        else
            ambiguity_angle(b_idx, f_idx) = 90; % No ambiguity
        end
    end
end

%% Plotting
figure('Position', [100, 100, 1400, 900]);

% Plot 1: Angle Accuracy vs Incident Angle (Ideal vs Realistic)
subplot(2,2,1);
hold on; grid on;
colors = lines(n_freq);
for f_idx = 1:n_freq
    % Plot ideal (dashed)
    plot(incident_angles, angle_error_ideal(f_idx, :), '--', 'LineWidth', 1.5, ...
        'Color', colors(f_idx,:), 'HandleVisibility', 'off');
    % Plot realistic (solid)
    plot(incident_angles, angle_error_realistic(f_idx, :), '-', 'LineWidth', 2, ...
        'Color', colors(f_idx,:), 'DisplayName', ...
        sprintf('%.0f GHz', test_frequencies(f_idx)/1e9));
end
xlabel('Incident Angle off Boresight (degrees)');
ylabel('Angle Error (degrees)');
title(sprintf('Angle Accuracy vs Incident Angle\n(Solid: w/ SNR effects, Dashed: Ideal, D_{max} = %.1f in)', ...
    max(baselines_all)));
legend('Location', 'northwest');
set(gca, 'YScale', 'log');
xlim([-80, 80]);
ylim([0.1, 100]);

% Plot 2: Antenna Gain and SNR vs Angle
subplot(2,2,2);
yyaxis left
plot(incident_angles, antenna_gain_interp(abs(incident_angles)), 'b-', 'LineWidth', 2);
ylabel('Antenna Gain (dB)');
ylim([-40, 10]);
grid on;

yyaxis right
hold on;
for f_idx = 1:n_freq
    plot(incident_angles, snr_db(f_idx, :), 'LineWidth', 1.5, ...
        'DisplayName', sprintf('%.0f GHz', test_frequencies(f_idx)/1e9));
end
ylabel('SNR (dB)');
xlabel('Incident Angle off Boresight (degrees)');
title(sprintf('Antenna Gain (%.0f GHz pattern) and SNR', antenna_pattern_freq_ghz));
legend('Location', 'southwest');
xlim([-80, 80]);

% Plot 3: Ambiguity Analysis (Shortest Baseline Only)
subplot(2,2,3);
shortest_baseline_idx = 1; % First baseline is shortest
plot(test_frequencies/1e9, ambiguity_angle(shortest_baseline_idx, :), 'o-', ...
    'LineWidth', 2, 'MarkerSize', 10, 'Color', [0.2, 0.6, 0.2], ...
    'MarkerFaceColor', [0.2, 0.6, 0.2]);
hold on;
yline(90, 'r--', 'Full Coverage', 'LineWidth', 1.5);
grid on;
xlabel('Frequency (GHz)');
ylabel('Unambiguous Half-Angle (degrees)');
title(sprintf('Ambiguity-Free Region (Shortest Baseline: %.2f in)', baselines_all(shortest_baseline_idx)));
ylim([0, 95]);
text(mean(test_frequencies/1e9), ambiguity_angle(shortest_baseline_idx, 3) + 5, ...
    'Shortest baseline resolves ambiguity', 'HorizontalAlignment', 'center');

% Plot 4: Array Geometry
subplot(2,2,4);
plot(element_positions, zeros(size(element_positions)), 'ro', ...
    'MarkerSize', 15, 'MarkerFaceColor', 'r', 'LineWidth', 2);
hold on;
for i = 1:length(element_positions)-1
    plot([element_positions(i), element_positions(i+1)], [0, 0], 'b--', 'LineWidth', 1.5);
    text(mean([element_positions(i), element_positions(i+1)]), -0.15, ...
        sprintf('%.2f"', baselines_adjacent(i)), 'HorizontalAlignment', 'center');
end
% Show total aperture
plot([element_positions(1), element_positions(end)], [0.3, 0.3], 'g-', 'LineWidth', 2);
text(mean([element_positions(1), element_positions(end)]), 0.35, ...
    sprintf('Total: %.1f"', max(baselines_all)), 'HorizontalAlignment', 'center', 'Color', 'g');
xlabel('Position (inches)');
title('Interferometer Array Geometry');
ylim([-0.5, 0.6]);
xlim([-0.5, max(element_positions)+0.5]);
grid on;
set(gca, 'YTick', []);

%% Summary Report
fprintf('\n========== PERFORMANCE SUMMARY ==========\n\n');

fprintf('Angle Accuracy at Boresight (0°):\n');
boresight_idx = find(incident_angles == 0);
for f_idx = 1:n_freq
    fprintf('  %.0f GHz: %.4f° (ideal) / %.4f° (realistic)\n', ...
        test_frequencies(f_idx)/1e9, ...
        angle_error_ideal(f_idx, boresight_idx), ...
        angle_error_realistic(f_idx, boresight_idx));
end

fprintf('\nSNR at Boresight:\n');
for f_idx = 1:n_freq
    fprintf('  %.0f GHz: %.1f dB\n', ...
        test_frequencies(f_idx)/1e9, snr_db(f_idx, boresight_idx));
end

fprintf('\nAmbiguity-Free Angular Range (Shortest Baseline: %.2f in):\n', baselines_all(1));
for f_idx = 1:n_freq
    fprintf('  %.0f GHz: ±%.1f degrees\n', ...
        test_frequencies(f_idx)/1e9, ambiguity_angle(1, f_idx));
end

fprintf('\nAngle Error at ±45° Incident Angle:\n');
idx_45 = find(abs(incident_angles - 45) < 0.6, 1);
if ~isempty(idx_45)
    for f_idx = 1:n_freq
        fprintf('  %.0f GHz: %.4f° (ideal) / %.4f° (realistic), SNR: %.1f dB\n', ...
            test_frequencies(f_idx)/1e9, ...
            angle_error_ideal(f_idx, idx_45), ...
            angle_error_realistic(f_idx, idx_45), ...
            snr_db(f_idx, idx_45));
    end
end

fprintf('\nAngle Error at ±70° Incident Angle:\n');
idx_70 = find(abs(incident_angles - 70) < 0.6, 1);
if ~isempty(idx_70)
    for f_idx = 1:n_freq
        fprintf('  %.0f GHz: %.4f° (ideal) / %.4f° (realistic), SNR: %.1f dB\n', ...
            test_frequencies(f_idx)/1e9, ...
            angle_error_ideal(f_idx, idx_70), ...
            angle_error_realistic(f_idx, idx_70), ...
            snr_db(f_idx, idx_70));
    end
end

fprintf('\n========================================\n');

%% Additional Analysis: Phase Error and System Performance
figure('Position', [150, 150, 1400, 900]);

% Plot 1: Phase Error vs Angle (showing SNR degradation effect)
subplot(2,2,1);
hold on; grid on;
colors = lines(n_freq);
for f_idx = 1:n_freq
    plot(incident_angles, phase_error_realistic(f_idx, :), 'LineWidth', 2, ...
        'Color', colors(f_idx,:), 'DisplayName', ...
        sprintf('%.0f GHz', test_frequencies(f_idx)/1e9));
end
yline(phase_error_deg, 'k--', 'Baseline Phase Error', 'LineWidth', 1.5, ...
    'LabelHorizontalAlignment', 'left');
xlabel('Incident Angle (degrees)');
ylabel('Phase Measurement Error (degrees)');
title('Phase Error vs Angle (SNR-dependent)');
legend('Location', 'northwest');
xlim([-80, 80]);
set(gca, 'YScale', 'log');
ylim([phase_error_deg*0.5, 100]);

% Plot 2: Comparison of Ideal vs Realistic at one frequency
subplot(2,2,2);
f_compare = 3; % Use 10 GHz for comparison
semilogy(incident_angles, angle_error_ideal(f_compare, :), 'b--', ...
    'LineWidth', 2, 'DisplayName', 'Ideal (const phase error)');
hold on;
semilogy(incident_angles, angle_error_realistic(f_compare, :), 'r-', ...
    'LineWidth', 2, 'DisplayName', 'Realistic (w/ SNR)');
grid on;
xlabel('Incident Angle (degrees)');
ylabel('Angle Error (degrees)');
title(sprintf('Ideal vs Realistic Performance at %.0f GHz', test_frequencies(f_compare)/1e9));
legend('Location', 'northwest');
xlim([-80, 80]);

% Plot 3: Usable Field of View (FOV) based on error threshold
subplot(2,2,3);
error_thresholds = [1, 2, 5, 10]; % degrees
fov_limits = zeros(length(error_thresholds), n_freq);
hold on;
colors_thresh = lines(length(error_thresholds));

for thresh_idx = 1:length(error_thresholds)
    thresh = error_thresholds(thresh_idx);
    for f_idx = 1:n_freq
        % Find maximum angle where error is below threshold
        valid_angles = incident_angles(angle_error_realistic(f_idx, :) <= thresh);
        if ~isempty(valid_angles)
            fov_limits(thresh_idx, f_idx) = max(valid_angles);
        else
            fov_limits(thresh_idx, f_idx) = 0;
        end
    end
    plot(test_frequencies/1e9, fov_limits(thresh_idx, :), 'o-', ...
        'LineWidth', 2, 'MarkerSize', 8, 'Color', colors_thresh(thresh_idx,:), ...
        'DisplayName', sprintf('±%.0f° error limit', thresh));
end
grid on;
xlabel('Frequency (GHz)');
ylabel('Usable Half-FOV (degrees)');
title('Usable Field of View vs Frequency');
legend('Location', 'best');
ylim([0, 90]);

% Plot 4: SNR contour plot
subplot(2,2,4);
[X, Y] = meshgrid(test_frequencies/1e9, incident_angles);
contourf(X, Y, snr_db', 20, 'LineStyle', 'none');
colorbar;
xlabel('Frequency (GHz)');
ylabel('Incident Angle (degrees)');
title('SNR (dB) across Frequency and Angle');
hold on;
% Mark 10 dB SNR contour (useful threshold)
contour(X, Y, snr_db', [10, 10], 'r-', 'LineWidth', 2);
text(mean(test_frequencies/1e9), 60, '10 dB SNR', 'Color', 'r', ...
    'FontWeight', 'bold', 'BackgroundColor', 'white');

sgtitle('SNR and Performance Analysis with Antenna Pattern');
