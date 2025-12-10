%% EW Mission Analysis - Phase 3: Jamming Analysis
% 
% Analyzes jamming effectiveness using mission geometry from Phase 1
% Calculates J/S ratio (Jamming-to-Signal) and displays jammer performance
%
% Prerequisites:
%   - Run Phase 1 first to generate ew_mission_data.mat
%   - Have jammer antenna pattern CSV file available
%
% Key Outputs:
%   - Jammer antenna pattern heatmap with pointing overlay
%   - J/S ratio over mission timeline
%   - Link budget analysis
%   - Jamming effectiveness summary
%
% Author: EW Mission Analysis Team
% Date: 2025-10-21

clear; clc; close all;

%% ========================================================================
%  USER CONFIGURATION
%  ========================================================================

% Jammer Antenna Pattern CSV File
% Format: Column 1 = angle (degrees, -90 to +90)
%         Columns 2-18 = gain (dBi) at frequencies 2-18 GHz
jammer_pattern_csv = 'jammer_antenna_pattern.csv';

% Jammer Parameters
jammer_input_power_dbm = 50;     % Power into antenna (dBm) - e.g., 50 dBm = 100W
jammer_antenna_gain_dbi = 20;    % Antenna gain (dBi)

% Convert for internal calculations
jammer_power_watts = 10^((jammer_input_power_dbm - 30) / 10);
jammer_power_dbw = 10*log10(jammer_power_watts);

% Emitter (Radar) Parameters
emitter_power_dbw = 60;          % Transmit power (dBW) - e.g., 60 dBW = 1 MW  
emitter_antenna_gain_dbi = 35;   % Antenna gain (dBi)
emitter_frequency_ghz = 6;       % Operating frequency (GHz) - used for all analysis

% Convert for internal calculations
emitter_power_watts = 10^(emitter_power_dbw / 10);

% UAV Parameters
uav_rcs_m2 = 2;                  % Radar cross section (m²)
uav_rcs_dbsm = 10*log10(uav_rcs_m2);

% Analysis frequency for jamming calculations
% All J/S and link budget calculations done at this frequency
analysis_frequency_ghz = emitter_frequency_ghz;

% Constants
c = 3e8;  % Speed of light (m/s)

fprintf('=== Phase 3: Jamming Analysis ===\n\n');

%% ========================================================================
%  LOAD MISSION DATA FROM PHASE 1
%  ========================================================================

if ~exist('ew_mission_data.mat', 'file')
    error('Mission data not found! Run Phase 1 first to generate ew_mission_data.mat');
end

load('ew_mission_data.mat', 'mission_data');

fprintf('Loaded mission data from Phase 1\n');
fprintf('Approach pattern: %s\n', mission_data.parameters.approach_pattern);
fprintf('Mission duration: %.1f seconds\n', mission_data.time(end));
fprintf('Analysis frequency: %.1f GHz\n\n', analysis_frequency_ghz);

% Extract key variables
t_total = mission_data.time;
num_steps = length(t_total);
uav_position = mission_data.position;
emitter_pos = mission_data.emitter_position;
distance_to_emitter = mission_data.distance_to_emitter;
jammer_off_boresight = mission_data.jammer_off_boresight;

%% ========================================================================
%  LOAD JAMMER ANTENNA PATTERN
%  ========================================================================

fprintf('=== Loading Jammer Antenna Pattern ===\n');

if ~exist(jammer_pattern_csv, 'file')
    warning('Jammer pattern CSV not found: %s', jammer_pattern_csv);
    fprintf('Creating synthetic antenna pattern for demonstration...\n');
    
    % Create synthetic pattern if CSV not available
    pattern_angles = (-90:1:90)';  % -90 to +90 degrees
    pattern_freqs = 2:1:18;  % 2 to 18 GHz
    
    % Synthetic pattern: Gaussian beam with 30° beamwidth
    beamwidth = 30;  % degrees (3dB beamwidth)
    peak_gain = 20;  % dBi at boresight
    
    pattern_gain = zeros(length(pattern_angles), length(pattern_freqs));
    for f_idx = 1:length(pattern_freqs)
        % Gain decreases as Gaussian from boresight
        pattern_gain(:, f_idx) = peak_gain - 12 * (pattern_angles / (beamwidth/2)).^2;
        pattern_gain(pattern_gain(:, f_idx) < -20, f_idx) = -20;  % Floor at -20 dBi
    end
else
    % Load actual CSV file
    fprintf('Loading: %s\n', jammer_pattern_csv);
    pattern_data = readmatrix(jammer_pattern_csv);
    
    pattern_angles = pattern_data(:, 1);  % First column: angles
    pattern_gain = pattern_data(:, 2:end);  % Remaining columns: gain at each frequency
    
    % Infer frequencies from number of columns
    num_freq_cols = size(pattern_gain, 2);
    if num_freq_cols == 17
        pattern_freqs = 2:1:18;  % Standard 2-18 GHz
    else
        pattern_freqs = linspace(2, 18, num_freq_cols);
    end
end

fprintf('Pattern loaded: %d angles × %d frequencies\n', ...
    length(pattern_angles), length(pattern_freqs));
fprintf('Angle range: %.0f° to %.0f°\n', min(pattern_angles), max(pattern_angles));
fprintf('Frequency range: %.1f to %.1f GHz\n\n', min(pattern_freqs), max(pattern_freqs));

%% ========================================================================
%  CALCULATE JAMMER GAIN AT EACH TIME STEP
%  ========================================================================

fprintf('=== Calculating Jammer Performance ===\n');

% For each time step, find jammer gain at the off-boresight angle
% Interpolate from pattern data at analysis frequency
jammer_gain_dbi = zeros(1, num_steps);

% Find the frequency index closest to analysis frequency
[~, freq_idx] = min(abs(pattern_freqs - analysis_frequency_ghz));

fprintf('Using pattern at %.1f GHz (closest to analysis frequency)\n', pattern_freqs(freq_idx));

for i = 1:num_steps
    % Get off-boresight angle
    angle = jammer_off_boresight(i);
    
    % Clamp to pattern range
    angle = max(min(pattern_angles), min(max(pattern_angles), angle));
    
    % Interpolate gain from pattern
    jammer_gain_dbi(i) = interp1(pattern_angles, pattern_gain(:, freq_idx), angle, 'linear');
end

fprintf('Jammer gain range: %.1f to %.1f dBi\n', min(jammer_gain_dbi), max(jammer_gain_dbi));
fprintf('Mean jammer gain: %.1f dBi\n', mean(jammer_gain_dbi));

% Calculate EIRP statistics
eirp_dbm = jammer_input_power_dbm + jammer_gain_dbi;
eirp_watts = 10.^(eirp_dbm / 10) / 1000;
fprintf('EIRP range: %.1f to %.1f watts (%.1f to %.1f dBm)\n', ...
    min(eirp_watts), max(eirp_watts), min(eirp_dbm), max(eirp_dbm));
fprintf('Mean EIRP: %.1f watts (%.1f dBm)\n', mean(eirp_watts), mean(eirp_dbm));

%% ========================================================================
%  CALCULATE J/S RATIO (JAMMING-TO-SIGNAL)
%  ========================================================================

fprintf('\n=== Calculating J/S Ratio ===\n');

% Wavelength at analysis frequency
lambda = c / (analysis_frequency_ghz * 1e9);

% Path loss (free space, one-way jammer to emitter)
% L = (4*pi*R/lambda)^2
path_loss_jammer_db = 20*log10(distance_to_emitter) + 20*log10(4*pi/lambda);

% Jammer power at emitter (one-way link)
% P_j = P_tx + G_tx - L
jammer_power_at_emitter_dbw = jammer_power_dbw + jammer_gain_dbi - path_loss_jammer_db;

% Signal power at emitter (two-way radar link)
% Radar equation: P_r = P_t * G_t * G_r * lambda^2 * RCS / (4*pi)^3 / R^4
% Since emitter receives its own reflection:
% P_s = P_emitter + G_emitter + G_emitter + RCS_dBsm - L_two_way
% where L_two_way = 40*log10(R) + 20*log10(4*pi/lambda)

path_loss_two_way_db = 40*log10(distance_to_emitter) + 20*log10(4*pi/lambda);
signal_power_at_emitter_dbw = emitter_power_dbw + 2*emitter_antenna_gain_dbi + ...
    uav_rcs_dbsm - path_loss_two_way_db;

% J/S ratio in dB
js_ratio_db = jammer_power_at_emitter_dbw - signal_power_at_emitter_dbw;

fprintf('Average jammer power at emitter: %.1f dBW\n', mean(jammer_power_at_emitter_dbw));
fprintf('Average signal power at emitter: %.1f dBW\n', mean(signal_power_at_emitter_dbw));
fprintf('Average J/S ratio: %.1f dB\n', mean(js_ratio_db));
fprintf('Min J/S: %.1f dB, Max J/S: %.1f dB\n', min(js_ratio_db), max(js_ratio_db));

% Jamming effectiveness thresholds
js_threshold_marginal = 0;   % 0 dB: equal power
js_threshold_good = 10;       % 10 dB: good jamming
js_threshold_excellent = 20;  % 20 dB: excellent jamming

percent_above_0db = 100 * sum(js_ratio_db > js_threshold_marginal) / num_steps;
percent_above_10db = 100 * sum(js_ratio_db > js_threshold_good) / num_steps;
percent_above_20db = 100 * sum(js_ratio_db > js_threshold_excellent) / num_steps;

fprintf('\nJamming Effectiveness:\n');
fprintf('  J/S > 0 dB (marginal):   %.1f%% of mission\n', percent_above_0db);
fprintf('  J/S > 10 dB (good):      %.1f%% of mission\n', percent_above_10db);
fprintf('  J/S > 20 dB (excellent): %.1f%% of mission\n', percent_above_20db);

%% ========================================================================
%  VISUALIZATION
%  ========================================================================

figure('Position', [100, 100, 1400, 900], 'Name', 'Phase 3: Jamming Analysis');

%% Plot 1: Jammer Antenna Pattern Heatmap with Pointing Overlay
subplot(2,3,1);

% Create heatmap: Off-Boresight Angle vs Time, color = Gain from pattern
% This shows the antenna pattern (Y-axis) and where we're pointing (overlay)

time_grid = t_total / 60;  % Convert to minutes
angle_grid = pattern_angles;  % -90 to +90 degrees

% Build 2D gain matrix: rows = angle, cols = time
% For each time step, show the FULL antenna pattern (not just where we're pointing)
% This creates the background showing "what gain is available at each angle"
gain_matrix = repmat(pattern_gain(:, freq_idx), 1, num_steps);

% Plot heatmap
imagesc(time_grid, angle_grid, gain_matrix);
axis xy;  % Normal orientation (low angles at bottom)
colorbar;
colormap(jet);
ylabel('Off-Boresight Angle (deg)', 'Color', 'k');
caxis([min(pattern_gain(:, freq_idx)), max(pattern_gain(:, freq_idx))]);

hold on;

% Overlay: where jammer is actually pointing
plot(time_grid, jammer_off_boresight, 'w-', 'LineWidth', 2.5);
plot(time_grid, jammer_off_boresight, 'k--', 'LineWidth', 1);

xlabel('Time (min)');
title(sprintf('Jammer Pattern & Pointing (%.1f GHz)', pattern_freqs(freq_idx)));
legend('Actual Pointing', 'Location', 'northeast');

% Add text annotation
text(0.02, 0.98, {'Background: Antenna gain pattern', ...
    sprintf('White line: Where jammer points (%.1f GHz)', pattern_freqs(freq_idx))}, ...
    'Units', 'normalized', 'VerticalAlignment', 'top', 'Color', 'white', ...
    'FontSize', 8, 'BackgroundColor', 'black');

%% Plot 2: J/S Ratio Over Time
subplot(2,3,2);

plot(time_grid, js_ratio_db, 'b-', 'LineWidth', 1.5);
hold on;
yline(js_threshold_marginal, 'k--', '0 dB (Equal Power)', 'LineWidth', 1.5, 'LabelHorizontalAlignment', 'left');
yline(js_threshold_good, 'g--', '10 dB (Good)', 'LineWidth', 1.5, 'LabelHorizontalAlignment', 'left');
yline(js_threshold_excellent, 'r--', '20 dB (Excellent)', 'LineWidth', 1.5, 'LabelHorizontalAlignment', 'left');

xlabel('Time (min)');
ylabel('J/S Ratio (dB)');
title('Jamming-to-Signal Ratio');
grid on;
legend('J/S Ratio', 'Location', 'best');

%% Plot 3: Jammer Gain Utilization
subplot(2,3,3);

plot(time_grid, jammer_gain_dbi, 'r-', 'LineWidth', 1.5);
hold on;
yline(max(pattern_gain(:)), 'k--', sprintf('Peak: %.1f dBi', max(pattern_gain(:))), ...
    'LineWidth', 1, 'LabelHorizontalAlignment', 'right');

xlabel('Time (min)');
ylabel('Jammer Gain (dBi)');
title('Jammer Antenna Gain at Pointing Angle');
grid on;

%% Plot 4: EIRP Heatmap (Watts)
subplot(2,3,4);

% Calculate EIRP at each angle in the pattern
% EIRP (dBm) = Input Power (dBm) + Antenna Gain (dBi)
% EIRP (watts) = 10^(EIRP_dBm / 10) / 1000

% Build EIRP matrix for full pattern
eirp_dbm_pattern = jammer_input_power_dbm + pattern_gain(:, freq_idx);
eirp_watts_pattern = 10.^(eirp_dbm_pattern / 10) / 1000;  % Convert dBm to watts

% Create matrix: same pattern repeated for all time steps
eirp_matrix = repmat(eirp_watts_pattern, 1, num_steps);

% Plot heatmap
imagesc(time_grid, angle_grid, eirp_matrix);
axis xy;
colorbar;
colormap(jet);
ylabel('Off-Boresight Angle (deg)', 'Color', 'k');

hold on;

% Overlay: where jammer is actually pointing
plot(time_grid, jammer_off_boresight, 'w-', 'LineWidth', 2.5);
plot(time_grid, jammer_off_boresight, 'k--', 'LineWidth', 1);

xlabel('Time (min)');
title(sprintf('EIRP Pattern & Pointing (%.1f GHz)', pattern_freqs(freq_idx)));
c = colorbar;
c.Label.String = 'EIRP (Watts)';

% Add text annotation
text(0.02, 0.98, {'Background: EIRP in Watts', ...
    sprintf('Input: %.1f dBm (%.1f W)', jammer_input_power_dbm, jammer_power_watts), ...
    'White line: Actual pointing'}, ...
    'Units', 'normalized', 'VerticalAlignment', 'top', 'Color', 'white', ...
    'FontSize', 8, 'BackgroundColor', 'black');

%% Plot 5: Range and Off-Boresight
subplot(2,3,5);

yyaxis left;
plot(time_grid, distance_to_emitter/1000, 'b-', 'LineWidth', 1.5);
ylabel('Range (km)');
xlabel('Time (min)');

yyaxis right;
plot(time_grid, jammer_off_boresight, 'r-', 'LineWidth', 1.5);
ylabel('Off-Boresight Angle (deg)');

title('Range and Jammer Pointing');
grid on;
legend('Range', 'Off-Boresight', 'Location', 'best');

%% Plot 6: Jamming Effectiveness Summary
subplot(2,3,6);

% Pie chart or bar chart of effectiveness
categories_eff = {'J/S > 20 dB', '10-20 dB', '0-10 dB', 'J/S < 0 dB'};
excellent = sum(js_ratio_db > js_threshold_excellent);
good = sum(js_ratio_db > js_threshold_good & js_ratio_db <= js_threshold_excellent);
marginal = sum(js_ratio_db > js_threshold_marginal & js_ratio_db <= js_threshold_good);
poor = sum(js_ratio_db <= js_threshold_marginal);

percentages = [excellent, good, marginal, poor] / num_steps * 100;

bar(percentages);
set(gca, 'XTickLabel', categories_eff);
ylabel('Percentage of Mission (%)');
title('Jamming Effectiveness Distribution');
grid on;

% Color code
colors_eff = [0.2, 0.8, 0.2;  % Excellent: green
              0.8, 0.8, 0.2;  % Good: yellow
              0.8, 0.5, 0.2;  % Marginal: orange
              0.8, 0.2, 0.2]; % Poor: red
              
colormap(gca, colors_eff);

sgtitle('Phase 3: Jamming Analysis', 'FontSize', 14, 'FontWeight', 'bold');

%% ========================================================================
%  SAVE RESULTS
%  ========================================================================

% Add jamming results to mission data
mission_data.jamming.jammer_power_watts = jammer_power_watts;
mission_data.jamming.jammer_gain_dbi = jammer_gain_dbi;
mission_data.jamming.js_ratio_db = js_ratio_db;
mission_data.jamming.jammer_power_at_emitter_dbw = jammer_power_at_emitter_dbw;
mission_data.jamming.signal_power_at_emitter_dbw = signal_power_at_emitter_dbw;
mission_data.jamming.emitter_frequency_ghz = emitter_frequency_ghz;
mission_data.jamming.emitter_power_watts = emitter_power_watts;
mission_data.jamming.emitter_antenna_gain_dbi = emitter_antenna_gain_dbi;
mission_data.jamming.uav_rcs_m2 = uav_rcs_m2;

% Save updated mission data
save('ew_mission_data.mat', 'mission_data');

fprintf('\n=== Phase 3 Complete ===\n');
fprintf('Updated mission data saved to ew_mission_data.mat\n');
fprintf('Summary:\n');
fprintf('  Jammer power: %.0f W (%.1f dBW)\n', jammer_power_watts, jammer_power_dbw);
fprintf('  Mean J/S ratio: %.1f dB\n', mean(js_ratio_db));
fprintf('  Effective jamming (J/S > 10 dB): %.1f%% of mission\n', percent_above_10db);
fprintf('\nAll plots displayed in figure.\n');
