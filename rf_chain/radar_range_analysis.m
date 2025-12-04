%% Radar Detection Range Analysis
% Calculates maximum detection range using the Radar Range Equation
% MATLAB R2024a

clear; close all; clc;

%% Physical Constants
c = 3e8;                    % Speed of light (m/s)
kB = 1.380649e-23;          % Boltzmann constant (J/K)
T0 = 290;                   % Reference temperature (K)

%% Radar Parameters
fprintf('=== Radar Detection Range Analysis ===\n\n');

% Transmitter Parameters
% NOTE: Choose ONE of the following two approaches:
% Option 1: Specify EIRP directly (Pt + Gt combined)
% Option 2: Specify Pt and Gt separately

use_eirp = true;  % Set to true if working with EIRP, false for separate Pt and Gt

if use_eirp
    EIRP_dBW = 50;              % Effective Isotropic Radiated Power (dBW)
    Gt_dB = 35;                 % Transmit antenna gain (dB) - for reference only
    Pt_dBW = EIRP_dBW - Gt_dB;  % Back-calculate transmit power
    fprintf('Using EIRP mode:\n');
    fprintf('  EIRP: %.1f dBW\n', EIRP_dBW);
    fprintf('  Antenna Gain (reference): %.1f dB\n', Gt_dB);
    fprintf('  Implied Transmit Power: %.1f dBW\n\n', Pt_dBW);
else
    Pt_dBW = 50;                % Peak transmit power (dBW)
    Gt_dB = 35;                 % Transmit antenna gain (dB)
    EIRP_dBW = Pt_dBW + Gt_dB;  % Calculate EIRP
    fprintf('Using separate Pt and Gt mode:\n');
    fprintf('  Transmit Power: %.1f dBW\n', Pt_dBW);
    fprintf('  Antenna Gain: %.1f dB\n', Gt_dB);
    fprintf('  EIRP: %.1f dBW\n\n', EIRP_dBW);
end

Pt_W = 10^(Pt_dBW/10);      % Convert to Watts
Gt = 10^(Gt_dB/10);         % Transmit antenna gain (linear)
freq_GHz = 10;              % Operating frequency (GHz)
freq_Hz = freq_GHz * 1e9;   % Convert to Hz
lambda = c / freq_Hz;       % Wavelength (m)

% Receiver Parameters
Gr_dB = Gt_dB;              % Receive antenna gain (dB) - monostatic radar
Gr = 10^(Gr_dB/10);         % Receive antenna gain (linear)
NF_dB = 3;                  % System noise figure (dB)
NF = 10^(NF_dB/10);         % System noise figure (linear)
BW_MHz = 1;                 % Receiver bandwidth (MHz)
BW_Hz = BW_MHz * 1e6;       % Convert to Hz
SNR_req_dB = 13;            % Required SNR for detection (dB)
SNR_req = 10^(SNR_req_dB/10); % Required SNR (linear)

% Processing Parameters
proc_gain_dB = 20;          % Processing gain (dB)
                            % Typical: 15-20 dB (conservative)
                            %          20-25 dB (typical modern)
                            %          25-35 dB (advanced/optimized)
proc_gain = 10^(proc_gain_dB/10); % Processing gain (linear)

% System Losses
L_dB = 6;                   % Total system losses (dB)
                            % Includes: atmospheric, transmission line,
                            % scanning losses, mismatch, etc.
L = 10^(L_dB/10);           % Total losses (linear)

% Target Parameters - Define multiple target types
targets = {
    'Fighter Aircraft',     5;      % RCS in m²
    'Bomber Aircraft',      40;
    'Small Drone',          0.01;
    'Large Drone',          0.1;
    'Cruise Missile',       0.5;
    'Ship (Frigate)',       10000;
    'Human',                1;
    'Car/Truck',            100;
};

fprintf('RADAR PARAMETERS:\n');
if use_eirp
    fprintf('  EIRP: %.1f dBW (%.1f W)\n', EIRP_dBW, 10^(EIRP_dBW/10));
    fprintf('  (Antenna Gain: %.1f dB, Implied Pt: %.1f dBW)\n', Gt_dB, Pt_dBW);
else
    fprintf('  Peak Power: %.1f dBW (%.1f W)\n', Pt_dBW, Pt_W);
    fprintf('  Transmit Gain: %.1f dB\n', Gt_dB);
    fprintf('  EIRP: %.1f dBW\n', EIRP_dBW);
end
fprintf('  Frequency: %.2f GHz (λ = %.3f m)\n', freq_GHz, lambda);
fprintf('  Receive Gain: %.1f dB\n', Gr_dB);
fprintf('  Noise Figure: %.1f dB\n', NF_dB);
fprintf('  Bandwidth: %.2f MHz\n', BW_MHz);
fprintf('  Required SNR: %.1f dB\n', SNR_req_dB);
fprintf('  Processing Gain: %.1f dB\n', proc_gain_dB);
fprintf('  System Losses: %.1f dB\n\n', L_dB);

%% Calculate Noise Power
noise_power_W = kB * T0 * BW_Hz * NF;
noise_power_dBW = 10*log10(noise_power_W);
noise_power_dBm = noise_power_dBW + 30;

fprintf('RECEIVER NOISE:\n');
fprintf('  Noise Power: %.2f dBm (%.2e W)\n\n', noise_power_dBm, noise_power_W);

%% Calculate Detection Range for Each Target
num_targets = size(targets, 1);
ranges_km = zeros(num_targets, 1);

fprintf('DETECTION RANGES:\n');
fprintf('%-20s %10s %15s\n', 'Target Type', 'RCS (m²)', 'Max Range (km)');
fprintf('%s\n', repmat('-', 1, 50));

for i = 1:num_targets
    target_name = targets{i, 1};
    sigma = targets{i, 2};  % RCS in m²
    
    % Radar Range Equation (solving for R_max)
    % R_max = [(Pt × Gt × Gr × λ² × σ × G_proc) / ((4π)³ × k × T × B × NF × SNR × L)]^(1/4)
    
    numerator = Pt_W * Gt * Gr * lambda^2 * sigma * proc_gain;
    denominator = (4*pi)^3 * kB * T0 * BW_Hz * NF * SNR_req * L;
    
    R_max_m = (numerator / denominator)^(1/4);
    R_max_km = R_max_m / 1000;
    
    ranges_km(i) = R_max_km;
    
    fprintf('%-20s %10.2f %15.2f\n', target_name, sigma, R_max_km);
end

fprintf('\n');

%% Sensitivity Analysis - How range varies with key parameters

% 1. Range vs RCS
rcs_range = logspace(-3, 5, 100);  % 0.001 m² to 100,000 m²
range_vs_rcs = zeros(size(rcs_range));

for i = 1:length(rcs_range)
    sigma = rcs_range(i);
    numerator = Pt_W * Gt * Gr * lambda^2 * sigma * proc_gain;
    denominator = (4*pi)^3 * kB * T0 * BW_Hz * NF * SNR_req * L;
    range_vs_rcs(i) = (numerator / denominator)^(1/4) / 1000; % km
end

% 2. Range vs Transmit Power
power_range_dBW = 30:1:70;  % 30 dBW to 70 dBW (1W to 10MW)
range_vs_power = zeros(size(power_range_dBW));
baseline_sigma = 5;  % Use fighter aircraft as reference

for i = 1:length(power_range_dBW)
    Pt_temp = 10^(power_range_dBW(i)/10);
    numerator = Pt_temp * Gt * Gr * lambda^2 * baseline_sigma * proc_gain;
    denominator = (4*pi)^3 * kB * T0 * BW_Hz * NF * SNR_req * L;
    range_vs_power(i) = (numerator / denominator)^(1/4) / 1000; % km
end

% 3. Range vs Processing Gain
proc_gain_range_dB = 0:1:40;  % 0 to 40 dB
range_vs_proc_gain = zeros(size(proc_gain_range_dB));

for i = 1:length(proc_gain_range_dB)
    pg_temp = 10^(proc_gain_range_dB(i)/10);
    numerator = Pt_W * Gt * Gr * lambda^2 * baseline_sigma * pg_temp;
    denominator = (4*pi)^3 * kB * T0 * BW_Hz * NF * SNR_req * L;
    range_vs_proc_gain(i) = (numerator / denominator)^(1/4) / 1000; % km
end

% 4. Range vs Frequency
freq_range_GHz = logspace(-1, 2, 100);  % 0.1 GHz to 100 GHz
range_vs_freq = zeros(size(freq_range_GHz));

for i = 1:length(freq_range_GHz)
    freq_temp = freq_range_GHz(i) * 1e9;
    lambda_temp = c / freq_temp;
    numerator = Pt_W * Gt * Gr * lambda_temp^2 * baseline_sigma * proc_gain;
    denominator = (4*pi)^3 * kB * T0 * BW_Hz * NF * SNR_req * L;
    range_vs_freq(i) = (numerator / denominator)^(1/4) / 1000; % km
end

%% Plotting
figure('Position', [100 100 1400 900], 'Color', 'w');

% Plot 1: Detection Ranges by Target Type
subplot(2,3,1)
target_names = targets(:, 1);
barh(1:num_targets, ranges_km, 'FaceColor', [0.2 0.6 0.8]);
set(gca, 'YTick', 1:num_targets, 'YTickLabel', target_names);
xlabel('Detection Range (km)', 'FontSize', 10);
ylabel('Target Type', 'FontSize', 10);
title('Maximum Detection Range by Target', 'FontSize', 11, 'FontWeight', 'bold');
grid on;
xlim([0 max(ranges_km)*1.1]);

% Add range labels
for i = 1:num_targets
    text(ranges_km(i), i, sprintf(' %.1f km', ranges_km(i)), ...
        'VerticalAlignment', 'middle', 'FontSize', 8);
end

% Plot 2: Range vs RCS
subplot(2,3,2)
loglog(rcs_range, range_vs_rcs, 'b-', 'LineWidth', 2);
hold on;
% Mark the predefined targets
for i = 1:num_targets
    sigma = targets{i, 2};
    loglog(sigma, ranges_km(i), 'ro', 'MarkerSize', 8, 'MarkerFaceColor', 'r');
end
xlabel('Radar Cross Section (m²)', 'FontSize', 10);
ylabel('Detection Range (km)', 'FontSize', 10);
title('Detection Range vs Target RCS', 'FontSize', 11, 'FontWeight', 'bold');
grid on;
legend('Range Curve', 'Defined Targets', 'Location', 'northwest');

% Plot 3: Range vs Transmit Power
subplot(2,3,3)
plot(power_range_dBW, range_vs_power, 'r-', 'LineWidth', 2);
hold on;
plot(Pt_dBW, range_vs_power(find(power_range_dBW >= Pt_dBW, 1)), ...
    'go', 'MarkerSize', 10, 'MarkerFaceColor', 'g');
xlabel('Transmit Power (dBW)', 'FontSize', 10);
ylabel('Detection Range (km)', 'FontSize', 10);
title(sprintf('Range vs Power (RCS = %.0f m²)', baseline_sigma), 'FontSize', 11, 'FontWeight', 'bold');
grid on;
legend('Range Curve', 'Current System', 'Location', 'northwest');

% Plot 4: Range vs Processing Gain
subplot(2,3,4)
plot(proc_gain_range_dB, range_vs_proc_gain, 'g-', 'LineWidth', 2);
hold on;
plot(proc_gain_dB, range_vs_proc_gain(proc_gain_dB+1), ...
    'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
xlabel('Processing Gain (dB)', 'FontSize', 10);
ylabel('Detection Range (km)', 'FontSize', 10);
title(sprintf('Range vs Processing Gain (RCS = %.0f m²)', baseline_sigma), ...
    'FontSize', 11, 'FontWeight', 'bold');
grid on;
legend('Range Curve', 'Current System', 'Location', 'northwest');

% Plot 5: Range vs Frequency
subplot(2,3,5)
loglog(freq_range_GHz, range_vs_freq, 'm-', 'LineWidth', 2);
hold on;
loglog(freq_GHz, range_vs_freq(find(freq_range_GHz >= freq_GHz, 1)), ...
    'ko', 'MarkerSize', 10, 'MarkerFaceColor', 'k');
xlabel('Frequency (GHz)', 'FontSize', 10);
ylabel('Detection Range (km)', 'FontSize', 10);
title(sprintf('Range vs Frequency (RCS = %.0f m²)', baseline_sigma), ...
    'FontSize', 11, 'FontWeight', 'bold');
grid on;
legend('Range Curve', 'Current System', 'Location', 'northeast');

% Plot 6: System Parameters Summary
subplot(2,3,6)
axis off;

summary_text = {
    'RADAR SYSTEM SUMMARY', ...
    '', ...
    sprintf('Peak Power: %.1f dBW', Pt_dBW), ...
    sprintf('Frequency: %.2f GHz', freq_GHz), ...
    sprintf('Antenna Gain: %.1f dB', Gt_dB), ...
    sprintf('Noise Figure: %.1f dB', NF_dB), ...
    sprintf('Bandwidth: %.2f MHz', BW_MHz), ...
    sprintf('Required SNR: %.1f dB', SNR_req_dB), ...
    sprintf('Processing Gain: %.1f dB', proc_gain_dB), ...
    sprintf('System Losses: %.1f dB', L_dB), ...
    '', ...
    sprintf('Noise Floor: %.2f dBm', noise_power_dBm), ...
    '', ...
    'PROCESSING GAIN GUIDE:', ...
    '  Conservative: 15-20 dB', ...
    '  Typical: 20-25 dB', ...
    '  Advanced: 25-35 dB'
};

text(0.1, 0.5, summary_text, 'FontSize', 9, 'VerticalAlignment', 'middle', ...
    'FontName', 'FixedWidth');

sgtitle('Radar Detection Range Analysis', 'FontSize', 14, 'FontWeight', 'bold');

%% Additional Analysis Figure - Range Contours
figure('Position', [150 150 1000 700], 'Color', 'w');

% Create contour plot: Range vs Power and RCS
power_contour = 30:2:70;  % 30 to 70 dBW
rcs_contour = logspace(-3, 5, 50);    % 0.001 to 100,000 m²
[P_grid, RCS_grid] = meshgrid(power_contour, rcs_contour);
Range_grid = zeros(size(P_grid));

for i = 1:size(P_grid, 1)
    for j = 1:size(P_grid, 2)
        Pt_temp = 10^(P_grid(i,j)/10);
        sigma_temp = RCS_grid(i,j);
        numerator = Pt_temp * Gt * Gr * lambda^2 * sigma_temp * proc_gain;
        denominator = (4*pi)^3 * kB * T0 * BW_Hz * NF * SNR_req * L;
        Range_grid(i,j) = (numerator / denominator)^(1/4) / 1000;
    end
end

[C, h] = contourf(P_grid, RCS_grid, Range_grid, [5 10 20 30 50 75 100 150 200 300 500 750 1000 1500 2000]);
colorbar;
set(gca, 'YScale', 'log');
xlabel('Transmit Power (dBW)', 'FontSize', 11);
ylabel('Target RCS (m²)', 'FontSize', 11);
title('Detection Range Contours (km)', 'FontSize', 12, 'FontWeight', 'bold');
clabel(C, h, 'FontSize', 8, 'Color', 'white');
colormap(jet);

% Mark current system and targets
hold on;
for i = 1:num_targets
    sigma = targets{i, 2};
    plot(Pt_dBW, sigma, 'wo', 'MarkerSize', 8, 'MarkerFaceColor', 'white', ...
        'LineWidth', 1.5);
    % Place text to the right, with offset based on plot range
    x_offset = 2;  % Fixed 2 dB offset instead of percentage
    text(Pt_dBW + x_offset, sigma, targets{i,1}, 'Color', 'white', 'FontSize', 8, ...
        'FontWeight', 'bold');
end

grid on;

fprintf('Analysis complete. Plots generated.\n');

%% Passive Receiver Detection Analysis
fprintf('\n=== PASSIVE RECEIVER DETECTION ANALYSIS ===\n');
fprintf('Analyzing receiver capability to detect this radar\n\n');

% Receiver parameters (configurable)
detection_range_multiplier = 2.0;  % Detect radar at 200% of radar's range
rx_antenna_gain_dB = 0;            % Receiver antenna gain (dB) - typically low gain omni
rx_NF_dB = 5;                      % Receiver system noise figure (dB) - conservative
rx_BW_MHz = 20;                    % Receiver analysis bandwidth (MHz)
rx_SNR_req_dB = 13;                % Required SNR for detection (dB)

% Calculate receiver detection range using one-way radar equation
% For receiver detecting radar: R_rx = sqrt[(Pt * Gt * Gr_rx * λ²) / ((4π)² * kTB * NF * SNR * L)]
% This is R^2 not R^4 because it's one-way propagation

fprintf('RECEIVER PARAMETERS:\n');
fprintf('  Detection Range Goal: %.0f%% of radar range\n', detection_range_multiplier * 100);
fprintf('  Antenna Gain: %.1f dB (omni-directional)\n', rx_antenna_gain_dB);
fprintf('  Noise Figure: %.1f dB\n', rx_NF_dB);
fprintf('  Bandwidth: %.1f MHz\n', rx_BW_MHz);
fprintf('  Required SNR: %.1f dB\n\n', rx_SNR_req_dB);

% Convert to linear
rx_Gr = 10^(rx_antenna_gain_dB/10);
rx_NF = 10^(rx_NF_dB/10);
rx_BW_Hz = rx_BW_MHz * 1e6;
rx_SNR_req = 10^(rx_SNR_req_dB/10);

% Calculate receiver detection ranges for each target
fprintf('RECEIVER DETECTION RANGES:\n');
fprintf('%-20s %15s %15s %15s\n', 'Target Type', 'Radar Range (km)', 'RX Range (km)', 'Multiplier');
fprintf('%s\n', repmat('-', 1, 70));

rx_ranges_km = zeros(num_targets, 1);
actual_multipliers = zeros(num_targets, 1);

for i = 1:num_targets
    % One-way link budget for passive receiver
    numerator = Pt_W * Gt * rx_Gr * lambda^2;
    denominator = (4*pi)^2 * kB * T0 * rx_BW_Hz * rx_NF * rx_SNR_req * L;
    
    R_rx_m = sqrt(numerator / denominator);
    R_rx_km = R_rx_m / 1000;
    
    rx_ranges_km(i) = R_rx_km;
    actual_multipliers(i) = R_rx_km / ranges_km(i);
    
    fprintf('%-20s %15.1f %15.1f %15.2fx\n', targets{i,1}, ranges_km(i), R_rx_km, actual_multipliers(i));
end

fprintf('\n');

% Determine if receiver meets the detection range goal
if min(actual_multipliers) >= detection_range_multiplier
    fprintf('✓ RECEIVER MEETS GOAL: All targets detectable at %.1fx radar range or better\n', detection_range_multiplier);
else
    fprintf('✗ RECEIVER INSUFFICIENT: Some targets below %.1fx goal\n', detection_range_multiplier);
    fprintf('  Minimum multiplier achieved: %.2fx\n', min(actual_multipliers));
    fprintf('  Shortfall: %.2fx\n', detection_range_multiplier / min(actual_multipliers));
end

fprintf('\n');

% Calculate required receiver sensitivity for the goal
fprintf('RECEIVER SENSITIVITY ANALYSIS:\n');
target_rx_range_m = detection_range_multiplier * mean(ranges_km) * 1000;  % Use mean as reference
received_power_dBm = 10*log10(Pt_W * Gt * rx_Gr * lambda^2 / ((4*pi*target_rx_range_m)^2 * L)) + 30;
noise_floor_rx_dBm = 10*log10(kB * T0 * rx_BW_Hz * rx_NF) + 30;
required_sensitivity_dBm = noise_floor_rx_dBm + rx_SNR_req_dB;

fprintf('  Target detection range: %.1f km (%.0f%% of radar range)\n', ...
    target_rx_range_m/1000, detection_range_multiplier*100);
fprintf('  Received signal power: %.1f dBm\n', received_power_dBm);
fprintf('  Receiver noise floor: %.1f dBm\n', noise_floor_rx_dBm);
fprintf('  Required sensitivity: %.1f dBm (for %.1f dB SNR)\n', required_sensitivity_dBm, rx_SNR_req_dB);
fprintf('  Margin: %.1f dB\n', received_power_dBm - required_sensitivity_dBm);

%% Additional Receiver Detection Figure
figure('Position', [200 200 1000 500], 'Color', 'w');

% Plot 1: Comparison of radar vs receiver ranges (SIMPLIFIED)
subplot(1,2,1)
x_pos = 1:num_targets;
bar(x_pos, ranges_km, 0.6, 'FaceColor', [0.8 0.2 0.2], 'DisplayName', 'Radar Detection Range');
hold on;
% Add single receiver range bar at the end
bar(num_targets + 1.5, rx_ranges_km(1), 0.6, 'FaceColor', [0.2 0.6 0.8], 'DisplayName', 'Receiver Detection Range');
% Add reference line for receiver range
plot([0.5 num_targets+0.5], [rx_ranges_km(1) rx_ranges_km(1)], 'b--', 'LineWidth', 1.5, ...
    'HandleVisibility', 'off');
xlabel('Target Type', 'FontSize', 10);
ylabel('Detection Range (km)', 'FontSize', 10);
title('Radar Detection Range by Target vs Receiver Range', 'FontSize', 11, 'FontWeight', 'bold');
set(gca, 'XTick', [x_pos num_targets+1.5], 'XTickLabel', [targets(:,1); {'Receiver (any target)'}]);
xtickangle(45);
legend('Location', 'best');
grid on;

% Plot 2: Receiver parameters summary
subplot(1,2,2)
axis off;

rx_summary_text = {
    'RECEIVER SYSTEM SUMMARY', ...
    '', ...
    sprintf('Goal: Detect at %.0f%% radar range', detection_range_multiplier*100), ...
    '', ...
    sprintf('Antenna Gain: %.1f dB', rx_antenna_gain_dB), ...
    sprintf('Noise Figure: %.1f dB', rx_NF_dB), ...
    sprintf('Bandwidth: %.1f MHz', rx_BW_MHz), ...
    sprintf('Required SNR: %.1f dB', rx_SNR_req_dB), ...
    '', ...
    sprintf('Noise Floor: %.1f dBm', noise_floor_rx_dBm), ...
    sprintf('Required Sensitivity: %.1f dBm', required_sensitivity_dBm), ...
    '', ...
    sprintf('Detection Range: %.1f km', rx_ranges_km(1)), ...
    sprintf('Avg Multiplier: %.2fx radar range', mean(actual_multipliers)), ...
    '', ...
    'KEY POINTS:', ...
    '• Receiver range is constant', ...
    '  (independent of target RCS)', ...
    '', ...
    '• Passive detection uses one-way', ...
    '  propagation (R² not R⁴)', ...
    '', ...
    '• Much easier to detect the', ...
    '  radar than for radar to', ...
    '  detect targets'
};

text(0.1, 0.5, rx_summary_text, 'FontSize', 9, 'VerticalAlignment', 'middle', ...
    'FontName', 'FixedWidth');

sgtitle('Passive Receiver Detection Analysis', 'FontSize', 14, 'FontWeight', 'bold');

%% Receiver Sensitivity Trade Study
fprintf('\n=== RECEIVER SENSITIVITY TRADE STUDY ===\n');
fprintf('Finding worst-case receiver that still meets %.0f%% detection goal\n\n', detection_range_multiplier*100);

% Define parameter ranges to sweep
bw_sweep_MHz = [1 5 10 20 50 100];  % Bandwidth options (MHz)
nf_sweep_dB = [3 5 10 15 20 25];    % Noise figure options (dB)
loss_sweep_dB = [0 3 6 10 15];      % System losses (dB)

% Reference target for analysis
ref_target_idx = 1;  % Use first target (fighter aircraft) as reference
ref_radar_range_km = ranges_km(ref_target_idx);
target_rx_range_km = detection_range_multiplier * ref_radar_range_km;

fprintf('Reference: %s\n', targets{ref_target_idx, 1});
fprintf('  Radar detection range: %.1f km\n', ref_radar_range_km);
fprintf('  Required receiver range: %.1f km (%.0f%% of radar range)\n\n', ...
    target_rx_range_km, detection_range_multiplier*100);

% Create results matrices
n_bw = length(bw_sweep_MHz);
n_nf = length(nf_sweep_dB);
n_loss = length(loss_sweep_dB);

rx_range_vs_bw_nf = zeros(n_bw, n_nf);
rx_range_vs_nf_loss = zeros(n_nf, n_loss);
meets_goal_bw_nf = zeros(n_bw, n_nf);
meets_goal_nf_loss = zeros(n_nf, n_loss);

% Sweep 1: Bandwidth vs Noise Figure (with nominal losses)
fprintf('TRADE 1: Bandwidth vs Noise Figure (Loss = %.1f dB)\n', rx_SNR_req_dB);
fprintf('%-10s', 'BW (MHz)');
for j = 1:n_nf
    fprintf(' %6.1f dB', nf_sweep_dB(j));
end
fprintf('\n%s\n', repmat('-', 1, 70));

for i = 1:n_bw
    fprintf('%-10.0f', bw_sweep_MHz(i));
    for j = 1:n_nf
        bw_temp = bw_sweep_MHz(i) * 1e6;
        nf_temp = 10^(nf_sweep_dB(j)/10);
        
        numerator = Pt_W * Gt * rx_Gr * lambda^2;
        denominator = (4*pi)^2 * kB * T0 * bw_temp * nf_temp * rx_SNR_req * L;
        
        rx_range_m = sqrt(numerator / denominator);
        rx_range_km = rx_range_m / 1000;
        
        rx_range_vs_bw_nf(i,j) = rx_range_km;
        meets_goal_bw_nf(i,j) = (rx_range_km >= target_rx_range_km);
        
        if meets_goal_bw_nf(i,j)
            fprintf(' %6.0f✓', rx_range_km);
        else
            fprintf(' %6.0f ', rx_range_km);
        end
    end
    fprintf('\n');
end
fprintf('\n');

% Sweep 2: Noise Figure vs System Losses (with nominal bandwidth)
fprintf('TRADE 2: Noise Figure vs System Losses (BW = %.0f MHz)\n', rx_BW_MHz);
fprintf('%-10s', 'NF (dB)');
for j = 1:n_loss
    fprintf(' %6.1f dB', loss_sweep_dB(j));
end
fprintf('\n%s\n', repmat('-', 1, 70));

for i = 1:n_nf
    fprintf('%-10.1f', nf_sweep_dB(i));
    for j = 1:n_loss
        nf_temp = 10^(nf_sweep_dB(i)/10);
        loss_temp = 10^(loss_sweep_dB(j)/10);
        
        numerator = Pt_W * Gt * rx_Gr * lambda^2;
        denominator = (4*pi)^2 * kB * T0 * rx_BW_Hz * nf_temp * rx_SNR_req * loss_temp;
        
        rx_range_m = sqrt(numerator / denominator);
        rx_range_km = rx_range_m / 1000;
        
        rx_range_vs_nf_loss(i,j) = rx_range_km;
        meets_goal_nf_loss(i,j) = (rx_range_km >= target_rx_range_km);
        
        if meets_goal_nf_loss(i,j)
            fprintf(' %6.0f✓', rx_range_km);
        else
            fprintf(' %6.0f ', rx_range_km);
        end
    end
    fprintf('\n');
end
fprintf('\n');

% Find worst-case acceptable combinations
fprintf('WORST-CASE ACCEPTABLE RECEIVER SPECS:\n');
worst_acceptable_found = false;

% Find worst NF that still works at max bandwidth/loss
for i = n_nf:-1:1
    if meets_goal_bw_nf(n_bw, i)  % Check at widest bandwidth
        fprintf('  Max NF at BW=%.0f MHz: %.1f dB (range: %.0f km)\n', ...
            bw_sweep_MHz(n_bw), nf_sweep_dB(i), rx_range_vs_bw_nf(n_bw, i));
        worst_acceptable_found = true;
        break;
    end
end

% Find worst loss that still works at worst NF
for j = n_loss:-1:1
    if meets_goal_nf_loss(n_nf, j)  % Check at worst NF
        fprintf('  Max Loss at NF=%.1f dB: %.1f dB (range: %.0f km)\n', ...
            nf_sweep_dB(n_nf), loss_sweep_dB(j), rx_range_vs_nf_loss(n_nf, j));
        worst_acceptable_found = true;
        break;
    end
end

% Find minimum bandwidth needed at worst NF
for i = 1:n_bw
    if meets_goal_bw_nf(i, n_nf)
        fprintf('  Min BW at NF=%.1f dB: %.0f MHz (range: %.0f km)\n', ...
            nf_sweep_dB(n_nf), bw_sweep_MHz(i), rx_range_vs_bw_nf(i, n_nf));
        worst_acceptable_found = true;
        break;
    end
end

if ~worst_acceptable_found
    fprintf('  WARNING: No combination in the swept range meets the goal!\n');
    fprintf('  Need better receiver specs than tested.\n');
end

%% Receiver Trade Study Plots
figure('Position', [250 250 1400 800], 'Color', 'w');

% Plot 1: Heatmap of range vs BW and NF
subplot(2,3,1)
imagesc(nf_sweep_dB, bw_sweep_MHz, rx_range_vs_bw_nf);
colorbar;
colormap(jet);
hold on;
contour(nf_sweep_dB, bw_sweep_MHz, rx_range_vs_bw_nf, [target_rx_range_km target_rx_range_km], ...
    'r-', 'LineWidth', 3);
xlabel('Noise Figure (dB)', 'FontSize', 10);
ylabel('Bandwidth (MHz)', 'FontSize', 10);
title('Receiver Range vs BW & NF', 'FontSize', 11, 'FontWeight', 'bold');
set(gca, 'YDir', 'normal');

% Plot 2: Pass/Fail matrix BW vs NF
subplot(2,3,2)
imagesc(nf_sweep_dB, bw_sweep_MHz, meets_goal_bw_nf);
colormap(gca, [1 0.3 0.3; 0.3 1 0.3]);
colorbar('Ticks', [0.25, 0.75], 'TickLabels', {'FAIL', 'PASS'});
xlabel('Noise Figure (dB)', 'FontSize', 10);
ylabel('Bandwidth (MHz)', 'FontSize', 10);
title(sprintf('Meet %.0f%% Goal? (BW vs NF)', detection_range_multiplier*100), 'FontSize', 11, 'FontWeight', 'bold');
set(gca, 'YDir', 'normal');

% Plot 3: Heatmap of range vs NF and Loss
subplot(2,3,3)
imagesc(loss_sweep_dB, nf_sweep_dB, rx_range_vs_nf_loss);
colorbar;
colormap(jet);
hold on;
contour(loss_sweep_dB, nf_sweep_dB, rx_range_vs_nf_loss, [target_rx_range_km target_rx_range_km], ...
    'r-', 'LineWidth', 3);
xlabel('System Losses (dB)', 'FontSize', 10);
ylabel('Noise Figure (dB)', 'FontSize', 10);
title('Receiver Range vs NF & Loss', 'FontSize', 11, 'FontWeight', 'bold');
set(gca, 'YDir', 'normal');

% Plot 4: Pass/Fail matrix NF vs Loss
subplot(2,3,4)
imagesc(loss_sweep_dB, nf_sweep_dB, meets_goal_nf_loss);
colormap(gca, [1 0.3 0.3; 0.3 1 0.3]);
colorbar('Ticks', [0.25, 0.75], 'TickLabels', {'FAIL', 'PASS'});
xlabel('System Losses (dB)', 'FontSize', 10);
ylabel('Noise Figure (dB)', 'FontSize', 10);
title(sprintf('Meet %.0f%% Goal? (NF vs Loss)', detection_range_multiplier*100), 'FontSize', 11, 'FontWeight', 'bold');
set(gca, 'YDir', 'normal');

% Plot 5: Range vs BW for different NF values
subplot(2,3,5)
for j = 1:n_nf
    plot(bw_sweep_MHz, rx_range_vs_bw_nf(:,j), '-o', 'LineWidth', 1.5, ...
        'DisplayName', sprintf('NF = %.0f dB', nf_sweep_dB(j)));
    hold on;
end
plot([min(bw_sweep_MHz) max(bw_sweep_MHz)], [target_rx_range_km target_rx_range_km], ...
    'r--', 'LineWidth', 2, 'DisplayName', 'Goal');
xlabel('Bandwidth (MHz)', 'FontSize', 10);
ylabel('Detection Range (km)', 'FontSize', 10);
title('Range vs Bandwidth (various NF)', 'FontSize', 11, 'FontWeight', 'bold');
legend('Location', 'best', 'FontSize', 8);
grid on;
set(gca, 'XScale', 'log');

% Plot 6: Summary text
subplot(2,3,6)
axis off;

trade_summary = {
    'RECEIVER TRADE STUDY', ...
    '', ...
    sprintf('Goal: %.0f%% of radar range', detection_range_multiplier*100), ...
    sprintf('Target: %.0f km', target_rx_range_km), ...
    '', ...
    'KEY INSIGHTS:', ...
    '', ...
    '• Bandwidth has moderate impact', ...
    '  (√BW in denominator)', ...
    '', ...
    '• NF has moderate impact', ...
    '  (√NF in denominator)', ...
    '', ...
    '• One-way propagation gives', ...
    '  huge advantage (R² not R⁴)', ...
    '', ...
    '• Green cells = meet goal', ...
    '• Red cells = miss goal', ...
    '', ...
    '✓ = Meets requirement'
};

text(0.1, 0.5, trade_summary, 'FontSize', 9, 'VerticalAlignment', 'middle', ...
    'FontName', 'FixedWidth');

sgtitle('Receiver Sensitivity Trade Study', 'FontSize', 14, 'FontWeight', 'bold');

%% Monte Carlo Analysis
fprintf('\n=== MONTE CARLO ANALYSIS ===\n');
fprintf('Running %d random parameter combinations\n\n', 10000);

% Define parameter bounds
n_iterations = 10000;
mc_params = struct();
mc_params.eirp_min = 30;        mc_params.eirp_max = 100;       % dBW
mc_params.pg_min = 20;          mc_params.pg_max = 30;          % dB
mc_params.freq_min = 2;         mc_params.freq_max = 18;        % GHz
mc_params.rcs_min = 0.1;        mc_params.rcs_max = 2;          % m²
mc_params.rx_nf_min = 8;        mc_params.rx_nf_max = 20;       % dB
mc_params.rx_bw_min = 10;       mc_params.rx_bw_max = 50;       % MHz
mc_params.rx_loss_min = 3;      mc_params.rx_loss_max = 6;      % dB
mc_params.rx_gain_min = -3;     mc_params.rx_gain_max = 3;      % dB

% Fixed parameters
mc_snr_req_dB = 13;             % Required SNR (dB)
mc_snr_req = 10^(mc_snr_req_dB/10);
mc_det_mult = detection_range_multiplier;  % Detection range multiplier goal

% Preallocate results
mc_radar_range = zeros(n_iterations, 1);
mc_rx_range = zeros(n_iterations, 1);
mc_range_multiplier = zeros(n_iterations, 1);
mc_meets_goal = zeros(n_iterations, 1);

% Store parameters for sensitivity analysis
mc_eirp = zeros(n_iterations, 1);
mc_pg = zeros(n_iterations, 1);
mc_freq = zeros(n_iterations, 1);
mc_rcs = zeros(n_iterations, 1);
mc_rx_nf = zeros(n_iterations, 1);
mc_rx_bw = zeros(n_iterations, 1);
mc_rx_loss = zeros(n_iterations, 1);
mc_rx_gain = zeros(n_iterations, 1);

fprintf('Running simulations...\n');
for i = 1:n_iterations
    % Generate random parameters (uniform distribution)
    mc_eirp(i) = mc_params.eirp_min + (mc_params.eirp_max - mc_params.eirp_min) * rand();
    mc_pg(i) = mc_params.pg_min + (mc_params.pg_max - mc_params.pg_min) * rand();
    mc_freq(i) = mc_params.freq_min + (mc_params.freq_max - mc_params.freq_min) * rand();
    mc_rcs(i) = mc_params.rcs_min + (mc_params.rcs_max - mc_params.rcs_min) * rand();
    mc_rx_nf(i) = mc_params.rx_nf_min + (mc_params.rx_nf_max - mc_params.rx_nf_min) * rand();
    mc_rx_bw(i) = mc_params.rx_bw_min + (mc_params.rx_bw_max - mc_params.rx_bw_min) * rand();
    mc_rx_loss(i) = mc_params.rx_loss_min + (mc_params.rx_loss_max - mc_params.rx_loss_min) * rand();
    mc_rx_gain(i) = mc_params.rx_gain_min + (mc_params.rx_gain_max - mc_params.rx_gain_min) * rand();
    
    % Convert to linear and calculate derived values
    eirp_W = 10^(mc_eirp(i)/10);
    pg_linear = 10^(mc_pg(i)/10);
    freq_Hz = mc_freq(i) * 1e9;
    lambda_mc = c / freq_Hz;
    rx_nf_linear = 10^(mc_rx_nf(i)/10);
    rx_bw_Hz = mc_rx_bw(i) * 1e6;
    rx_loss_linear = 10^(mc_rx_loss(i)/10);
    rx_gain_linear = 10^(mc_rx_gain(i)/10);
    
    % Calculate radar detection range (assuming Gt and Gr from EIRP, monostatic)
    % For simplicity, assume transmit power = EIRP and Gt = Gr = 1 (already in EIRP)
    % This is a simplification but reasonable for this analysis
    Pt_mc = eirp_W;
    Gt_mc = 1;  % EIRP already includes antenna gain
    Gr_mc = 1;
    
    % Radar range equation (R^4)
    numerator_radar = Pt_mc * Gt_mc * Gr_mc * lambda_mc^2 * mc_rcs(i) * pg_linear;
    denominator_radar = (4*pi)^3 * kB * T0 * BW_Hz * NF * mc_snr_req * L;
    mc_radar_range(i) = (numerator_radar / denominator_radar)^(1/4) / 1000; % km
    
    % Receiver detection range (R^2, one-way)
    numerator_rx = Pt_mc * Gt_mc * rx_gain_linear * lambda_mc^2;
    denominator_rx = (4*pi)^2 * kB * T0 * rx_bw_Hz * rx_nf_linear * mc_snr_req * rx_loss_linear;
    mc_rx_range(i) = sqrt(numerator_rx / denominator_rx) / 1000; % km
    
    % Calculate multiplier and check if goal is met
    mc_range_multiplier(i) = mc_rx_range(i) / mc_radar_range(i);
    mc_meets_goal(i) = (mc_range_multiplier(i) >= mc_det_mult);
end

% Calculate statistics
success_rate = sum(mc_meets_goal) / n_iterations * 100;
mean_multiplier = mean(mc_range_multiplier);
median_multiplier = median(mc_range_multiplier);
p95_multiplier = prctile(mc_range_multiplier, 95);
p5_multiplier = prctile(mc_range_multiplier, 5);

fprintf('\nMONTE CARLO RESULTS:\n');
fprintf('  Iterations: %d\n', n_iterations);
fprintf('  Success Rate: %.1f%% (meet %.0f%% goal)\n', success_rate, mc_det_mult*100);
fprintf('  Range Multiplier Statistics:\n');
fprintf('    Mean: %.2fx\n', mean_multiplier);
fprintf('    Median: %.2fx\n', median_multiplier);
fprintf('    5th percentile: %.2fx\n', p5_multiplier);
fprintf('    95th percentile: %.2fx\n', p95_multiplier);
fprintf('    Min: %.2fx, Max: %.2fx\n', min(mc_range_multiplier), max(mc_range_multiplier));

%% Sensitivity Analysis (Correlation with meeting goal)
fprintf('\n=== SENSITIVITY ANALYSIS ===\n');
fprintf('Correlation of parameters with range multiplier:\n\n');

% Calculate correlations
params_matrix = [mc_eirp, mc_pg, mc_freq, mc_rcs, mc_rx_nf, mc_rx_bw, mc_rx_loss, mc_rx_gain];
param_names = {'Radar EIRP', 'Processing Gain', 'Frequency', 'Target RCS', ...
               'RX Noise Figure', 'RX Bandwidth', 'RX Losses', 'RX Antenna Gain'};

correlations = zeros(8, 1);
for i = 1:8
    correlations(i) = corr(params_matrix(:,i), mc_range_multiplier);
end

% Sort by absolute correlation
[~, sort_idx] = sort(abs(correlations), 'descend');

fprintf('%-20s %12s %15s\n', 'Parameter', 'Correlation', 'Impact');
fprintf('%s\n', repmat('-', 1, 50));
for i = 1:8
    idx = sort_idx(i);
    impact_str = '';
    if abs(correlations(idx)) > 0.5
        impact_str = 'HIGH';
    elseif abs(correlations(idx)) > 0.2
        impact_str = 'MODERATE';
    else
        impact_str = 'LOW';
    end
    fprintf('%-20s %12.3f %15s\n', param_names{idx}, correlations(idx), impact_str);
end

%% Monte Carlo Visualization
figure('Position', [300 300 1400 900], 'Color', 'w');

% Plot 1: Histogram of range multipliers
subplot(3,3,1)
histogram(mc_range_multiplier, 50, 'FaceColor', [0.3 0.6 0.8]);
hold on;
xline(mc_det_mult, 'r--', 'LineWidth', 2, 'Label', sprintf('Goal (%.0fx)', mc_det_mult));
xline(median_multiplier, 'g--', 'LineWidth', 2, 'Label', 'Median');
xlabel('Range Multiplier (Rx/Radar)', 'FontSize', 10);
ylabel('Count', 'FontSize', 10);
title('Distribution of Range Multipliers', 'FontSize', 11, 'FontWeight', 'bold');
legend('Location', 'best');
grid on;

% Plot 2: Success rate pie chart
subplot(3,3,2)
pie([sum(mc_meets_goal), n_iterations - sum(mc_meets_goal)], ...
    {sprintf('Meet Goal\n%.1f%%', success_rate), sprintf('Miss Goal\n%.1f%%', 100-success_rate)});
colormap([0.3 0.8 0.3; 0.8 0.3 0.3]);
title('Monte Carlo Success Rate', 'FontSize', 11, 'FontWeight', 'bold');

% Plot 3: Sensitivity bar chart
subplot(3,3,3)
barh(correlations(sort_idx), 'FaceColor', [0.5 0.5 0.8]);
set(gca, 'YTick', 1:8, 'YTickLabel', param_names(sort_idx));
xlabel('Correlation with Range Multiplier', 'FontSize', 10);
title('Parameter Sensitivity', 'FontSize', 11, 'FontWeight', 'bold');
grid on;

% Plots 4-9: Scatter plots of key parameters vs range multiplier
key_params = sort_idx(1:6);  % Top 6 most sensitive parameters
for plot_idx = 1:6
    subplot(3,3,3+plot_idx)
    param_idx = key_params(plot_idx);
    
    % Color by success/failure
    scatter(params_matrix(mc_meets_goal==1, param_idx), mc_range_multiplier(mc_meets_goal==1), ...
        10, [0.3 0.8 0.3], 'filled', 'MarkerFaceAlpha', 0.3);
    hold on;
    scatter(params_matrix(mc_meets_goal==0, param_idx), mc_range_multiplier(mc_meets_goal==0), ...
        10, [0.8 0.3 0.3], 'filled', 'MarkerFaceAlpha', 0.3);
    yline(mc_det_mult, 'r--', 'LineWidth', 1.5);
    
    xlabel(param_names{param_idx}, 'FontSize', 9);
    ylabel('Range Multiplier', 'FontSize', 9);
    title(sprintf('%s (ρ=%.2f)', param_names{param_idx}, correlations(param_idx)), ...
        'FontSize', 10, 'FontWeight', 'bold');
    grid on;
    
    if plot_idx == 1
        legend('Meet Goal', 'Miss Goal', 'Goal Line', 'Location', 'best', 'FontSize', 7);
    end
end

sgtitle('Monte Carlo Analysis - 10,000 Random Configurations', 'FontSize', 14, 'FontWeight', 'bold');

%% Tornado Diagram - One-at-a-time Sensitivity
fprintf('\n=== TORNADO DIAGRAM ANALYSIS ===\n');
fprintf('Varying each parameter ±20%% from baseline\n\n');

% Define baseline values (midpoint of ranges)
baseline = struct();
baseline.eirp = (mc_params.eirp_min + mc_params.eirp_max) / 2;
baseline.pg = (mc_params.pg_min + mc_params.pg_max) / 2;
baseline.freq = (mc_params.freq_min + mc_params.freq_max) / 2;
baseline.rcs = (mc_params.rcs_min + mc_params.rcs_max) / 2;
baseline.rx_nf = (mc_params.rx_nf_min + mc_params.rx_nf_max) / 2;
baseline.rx_bw = (mc_params.rx_bw_min + mc_params.rx_bw_max) / 2;
baseline.rx_loss = (mc_params.rx_loss_min + mc_params.rx_loss_max) / 2;
baseline.rx_gain = (mc_params.rx_gain_min + mc_params.rx_gain_max) / 2;

% Calculate baseline range multiplier
lambda_base = c / (baseline.freq * 1e9);
eirp_W_base = 10^(baseline.eirp/10);
pg_linear_base = 10^(baseline.pg/10);
rx_nf_linear_base = 10^(baseline.rx_nf/10);
rx_bw_Hz_base = baseline.rx_bw * 1e6;
rx_loss_linear_base = 10^(baseline.rx_loss/10);
rx_gain_linear_base = 10^(baseline.rx_gain/10);

% Baseline radar range
num_radar_base = eirp_W_base * 1 * 1 * lambda_base^2 * baseline.rcs * pg_linear_base;
den_radar_base = (4*pi)^3 * kB * T0 * BW_Hz * NF * mc_snr_req * L;
radar_range_base = (num_radar_base / den_radar_base)^(1/4) / 1000;

% Baseline receiver range
num_rx_base = eirp_W_base * 1 * rx_gain_linear_base * lambda_base^2;
den_rx_base = (4*pi)^2 * kB * T0 * rx_bw_Hz_base * rx_nf_linear_base * mc_snr_req * rx_loss_linear_base;
rx_range_base = sqrt(num_rx_base / den_rx_base) / 1000;

multiplier_base = rx_range_base / radar_range_base;

fprintf('BASELINE VALUES:\n');
fprintf('  EIRP: %.1f dBW\n', baseline.eirp);
fprintf('  Processing Gain: %.1f dB\n', baseline.pg);
fprintf('  Frequency: %.1f GHz\n', baseline.freq);
fprintf('  Target RCS: %.2f m²\n', baseline.rcs);
fprintf('  RX NF: %.1f dB\n', baseline.rx_nf);
fprintf('  RX BW: %.1f MHz\n', baseline.rx_bw);
fprintf('  RX Loss: %.1f dB\n', baseline.rx_loss);
fprintf('  RX Gain: %.1f dB\n', baseline.rx_gain);
fprintf('  Baseline Range Multiplier: %.2fx\n\n', multiplier_base);

% Vary each parameter ±20%
variation = 0.20;  % 20% variation
tornado_params = {'EIRP', 'Proc Gain', 'Frequency', 'Target RCS', 'RX NF', 'RX BW', 'RX Loss', 'RX Gain'};
tornado_low = zeros(8, 1);
tornado_high = zeros(8, 1);
tornado_range = zeros(8, 1);

for i = 1:8
    % Set all to baseline
    vals = baseline;
    
    % Calculate low case (-20%)
    switch i
        case 1  % EIRP
            vals.eirp = baseline.eirp * (1 - variation);
            eirp_temp = 10^(vals.eirp/10);
            num_radar = eirp_temp * lambda_base^2 * baseline.rcs * pg_linear_base;
            den_radar = (4*pi)^3 * kB * T0 * BW_Hz * NF * mc_snr_req * L;
            radar_temp = (num_radar / den_radar)^(1/4) / 1000;
            num_rx = eirp_temp * rx_gain_linear_base * lambda_base^2;
            den_rx = (4*pi)^2 * kB * T0 * rx_bw_Hz_base * rx_nf_linear_base * mc_snr_req * rx_loss_linear_base;
            rx_temp = sqrt(num_rx / den_rx) / 1000;
            tornado_low(i) = rx_temp / radar_temp;
            
            vals.eirp = baseline.eirp * (1 + variation);
            eirp_temp = 10^(vals.eirp/10);
            num_radar = eirp_temp * lambda_base^2 * baseline.rcs * pg_linear_base;
            radar_temp = (num_radar / den_radar)^(1/4) / 1000;
            num_rx = eirp_temp * rx_gain_linear_base * lambda_base^2;
            rx_temp = sqrt(num_rx / den_rx) / 1000;
            tornado_high(i) = rx_temp / radar_temp;
            
        case 2  % Processing Gain
            vals.pg = baseline.pg * (1 - variation);
            pg_temp = 10^(vals.pg/10);
            num_radar = eirp_W_base * lambda_base^2 * baseline.rcs * pg_temp;
            den_radar = (4*pi)^3 * kB * T0 * BW_Hz * NF * mc_snr_req * L;
            radar_temp = (num_radar / den_radar)^(1/4) / 1000;
            tornado_low(i) = rx_range_base / radar_temp;
            
            vals.pg = baseline.pg * (1 + variation);
            pg_temp = 10^(vals.pg/10);
            num_radar = eirp_W_base * lambda_base^2 * baseline.rcs * pg_temp;
            radar_temp = (num_radar / den_radar)^(1/4) / 1000;
            tornado_high(i) = rx_range_base / radar_temp;
            
        case 3  % Frequency
            vals.freq = baseline.freq * (1 - variation);
            lambda_temp = c / (vals.freq * 1e9);
            num_radar = eirp_W_base * lambda_temp^2 * baseline.rcs * pg_linear_base;
            den_radar = (4*pi)^3 * kB * T0 * BW_Hz * NF * mc_snr_req * L;
            radar_temp = (num_radar / den_radar)^(1/4) / 1000;
            num_rx = eirp_W_base * rx_gain_linear_base * lambda_temp^2;
            den_rx = (4*pi)^2 * kB * T0 * rx_bw_Hz_base * rx_nf_linear_base * mc_snr_req * rx_loss_linear_base;
            rx_temp = sqrt(num_rx / den_rx) / 1000;
            tornado_low(i) = rx_temp / radar_temp;
            
            vals.freq = baseline.freq * (1 + variation);
            lambda_temp = c / (vals.freq * 1e9);
            num_radar = eirp_W_base * lambda_temp^2 * baseline.rcs * pg_linear_base;
            radar_temp = (num_radar / den_radar)^(1/4) / 1000;
            num_rx = eirp_W_base * rx_gain_linear_base * lambda_temp^2;
            rx_temp = sqrt(num_rx / den_rx) / 1000;
            tornado_high(i) = rx_temp / radar_temp;
            
        case 4  % RCS
            vals.rcs = baseline.rcs * (1 - variation);
            num_radar = eirp_W_base * lambda_base^2 * vals.rcs * pg_linear_base;
            den_radar = (4*pi)^3 * kB * T0 * BW_Hz * NF * mc_snr_req * L;
            radar_temp = (num_radar / den_radar)^(1/4) / 1000;
            tornado_low(i) = rx_range_base / radar_temp;
            
            vals.rcs = baseline.rcs * (1 + variation);
            num_radar = eirp_W_base * lambda_base^2 * vals.rcs * pg_linear_base;
            radar_temp = (num_radar / den_radar)^(1/4) / 1000;
            tornado_high(i) = rx_range_base / radar_temp;
            
        case 5  % RX NF
            vals.rx_nf = baseline.rx_nf * (1 - variation);
            nf_temp = 10^(vals.rx_nf/10);
            den_rx = (4*pi)^2 * kB * T0 * rx_bw_Hz_base * nf_temp * mc_snr_req * rx_loss_linear_base;
            rx_temp = sqrt(num_rx_base / den_rx) / 1000;
            tornado_low(i) = rx_temp / radar_range_base;
            
            vals.rx_nf = baseline.rx_nf * (1 + variation);
            nf_temp = 10^(vals.rx_nf/10);
            den_rx = (4*pi)^2 * kB * T0 * rx_bw_Hz_base * nf_temp * mc_snr_req * rx_loss_linear_base;
            rx_temp = sqrt(num_rx_base / den_rx) / 1000;
            tornado_high(i) = rx_temp / radar_range_base;
            
        case 6  % RX BW
            vals.rx_bw = baseline.rx_bw * (1 - variation);
            bw_temp = vals.rx_bw * 1e6;
            den_rx = (4*pi)^2 * kB * T0 * bw_temp * rx_nf_linear_base * mc_snr_req * rx_loss_linear_base;
            rx_temp = sqrt(num_rx_base / den_rx) / 1000;
            tornado_low(i) = rx_temp / radar_range_base;
            
            vals.rx_bw = baseline.rx_bw * (1 + variation);
            bw_temp = vals.rx_bw * 1e6;
            den_rx = (4*pi)^2 * kB * T0 * bw_temp * rx_nf_linear_base * mc_snr_req * rx_loss_linear_base;
            rx_temp = sqrt(num_rx_base / den_rx) / 1000;
            tornado_high(i) = rx_temp / radar_range_base;
            
        case 7  % RX Loss
            vals.rx_loss = baseline.rx_loss * (1 - variation);
            loss_temp = 10^(vals.rx_loss/10);
            den_rx = (4*pi)^2 * kB * T0 * rx_bw_Hz_base * rx_nf_linear_base * mc_snr_req * loss_temp;
            rx_temp = sqrt(num_rx_base / den_rx) / 1000;
            tornado_low(i) = rx_temp / radar_range_base;
            
            vals.rx_loss = baseline.rx_loss * (1 + variation);
            loss_temp = 10^(vals.rx_loss/10);
            den_rx = (4*pi)^2 * kB * T0 * rx_bw_Hz_base * rx_nf_linear_base * mc_snr_req * loss_temp;
            rx_temp = sqrt(num_rx_base / den_rx) / 1000;
            tornado_high(i) = rx_temp / radar_range_base;
            
        case 8  % RX Gain
            vals.rx_gain = baseline.rx_gain * (1 - variation);
            gain_temp = 10^(vals.rx_gain/10);
            num_rx = eirp_W_base * gain_temp * lambda_base^2;
            den_rx = (4*pi)^2 * kB * T0 * rx_bw_Hz_base * rx_nf_linear_base * mc_snr_req * rx_loss_linear_base;
            rx_temp = sqrt(num_rx / den_rx) / 1000;
            tornado_low(i) = rx_temp / radar_range_base;
            
            vals.rx_gain = baseline.rx_gain * (1 + variation);
            gain_temp = 10^(vals.rx_gain/10);
            num_rx = eirp_W_base * gain_temp * lambda_base^2;
            rx_temp = sqrt(num_rx / den_rx) / 1000;
            tornado_high(i) = rx_temp / radar_range_base;
    end
    
    tornado_range(i) = abs(tornado_high(i) - tornado_low(i));
end

% Sort by range (sensitivity)
[tornado_sorted, sort_idx_tornado] = sort(tornado_range, 'descend');

fprintf('TORNADO RESULTS (±20%% variation):\n');
fprintf('%-15s %12s %12s %12s\n', 'Parameter', 'Low (-20%)', 'High (+20%)', 'Range');
fprintf('%s\n', repmat('-', 1, 55));
for i = 1:8
    idx = sort_idx_tornado(i);
    fprintf('%-15s %12.2fx %12.2fx %12.2fx\n', tornado_params{idx}, ...
        tornado_low(idx), tornado_high(idx), tornado_range(idx));
end

%% Tornado Diagram Plot
figure('Position', [350 350 1000 600], 'Color', 'w');

subplot(1,2,1)
% Create horizontal bars
for i = 1:8
    idx = sort_idx_tornado(i);
    low_val = min(tornado_low(idx), tornado_high(idx));
    high_val = max(tornado_low(idx), tornado_high(idx));
    barh(i, [low_val - multiplier_base, high_val - low_val], 'stacked');
    hold on;
end
xline(0, 'k--', 'LineWidth', 1.5, 'Label', 'Baseline');
xline(mc_det_mult - multiplier_base, 'r--', 'LineWidth', 1.5, 'Label', 'Goal Offset');
xlabel('Change in Range Multiplier from Baseline', 'FontSize', 10);
set(gca, 'YTick', 1:8, 'YTickLabel', tornado_params(sort_idx_tornado));
title('Tornado Diagram (±20% Parameter Variation)', 'FontSize', 11, 'FontWeight', 'bold');
grid on;
xlim([min(tornado_low - multiplier_base)*1.2, max(tornado_high - multiplier_base)*1.2]);

subplot(1,2,2)
barh(tornado_sorted, 'FaceColor', [0.4 0.6 0.8]);
set(gca, 'YTick', 1:8, 'YTickLabel', tornado_params(sort_idx_tornado));
xlabel('Sensitivity (Range of Multiplier)', 'FontSize', 10);
title('Parameter Sensitivity Ranking', 'FontSize', 11, 'FontWeight', 'bold');
grid on;

sgtitle('Tornado Diagram - One-at-a-Time Sensitivity Analysis', 'FontSize', 13, 'FontWeight', 'bold');

%% Targeted 2D Heatmaps for Top Parameter Pairs
fprintf('\n=== TARGETED 2D HEATMAP ANALYSIS ===\n');
fprintf('Creating detailed heatmaps for top parameter pairs\n\n');

% Identify top 4 most sensitive parameters from tornado analysis
top_params_idx = sort_idx_tornado(1:4);
fprintf('Top 4 most sensitive parameters:\n');
for i = 1:4
    fprintf('  %d. %s\n', i, tornado_params{top_params_idx(i)});
end
fprintf('\n');

% Create 3 key heatmap combinations
% Combination 1: Top 2 parameters
% Combination 2: Parameter 1 vs Parameter 3
% Combination 3: Parameter 2 vs Parameter 4

figure('Position', [400 400 1400 500], 'Color', 'w');

% Helper function to create parameter sweep
create_param_sweep = @(param_idx, n_points) ...
    linspace(get_param_min(param_idx), get_param_max(param_idx), n_points);

% Define sweep resolution
n_sweep = 40;

% Heatmap 1: Top 2 parameters
subplot(1,3,1)
param1_idx = top_params_idx(1);
param2_idx = top_params_idx(2);
sweep1 = create_param_sweep(param1_idx, n_sweep);
sweep2 = create_param_sweep(param2_idx, n_sweep);
[X1, Y1] = meshgrid(sweep1, sweep2);
Z1 = zeros(size(X1));

for ii = 1:n_sweep
    for jj = 1:n_sweep
        Z1(ii,jj) = calc_multiplier_at_params(param1_idx, X1(ii,jj), param2_idx, Y1(ii,jj), baseline, ...
            lambda_base, eirp_W_base, pg_linear_base, rx_nf_linear_base, rx_bw_Hz_base, ...
            rx_loss_linear_base, rx_gain_linear_base, radar_range_base, rx_range_base);
    end
end

imagesc(sweep1, sweep2, Z1);
hold on;
contour(sweep1, sweep2, Z1, [mc_det_mult mc_det_mult], 'r-', 'LineWidth', 2);
colorbar;
colormap(jet);
xlabel(get_param_label(param1_idx), 'FontSize', 10);
ylabel(get_param_label(param2_idx), 'FontSize', 10);
title(sprintf('%s vs %s', tornado_params{param1_idx}, tornado_params{param2_idx}), ...
    'FontSize', 11, 'FontWeight', 'bold');
set(gca, 'YDir', 'normal');

% Heatmap 2: Param 1 vs Param 3
subplot(1,3,2)
param1_idx = top_params_idx(1);
param2_idx = top_params_idx(3);
sweep1 = create_param_sweep(param1_idx, n_sweep);
sweep2 = create_param_sweep(param2_idx, n_sweep);
[X2, Y2] = meshgrid(sweep1, sweep2);
Z2 = zeros(size(X2));

for ii = 1:n_sweep
    for jj = 1:n_sweep
        Z2(ii,jj) = calc_multiplier_at_params(param1_idx, X2(ii,jj), param2_idx, Y2(ii,jj), baseline, ...
            lambda_base, eirp_W_base, pg_linear_base, rx_nf_linear_base, rx_bw_Hz_base, ...
            rx_loss_linear_base, rx_gain_linear_base, radar_range_base, rx_range_base);
    end
end

imagesc(sweep1, sweep2, Z2);
hold on;
contour(sweep1, sweep2, Z2, [mc_det_mult mc_det_mult], 'r-', 'LineWidth', 2);
colorbar;
colormap(jet);
xlabel(get_param_label(param1_idx), 'FontSize', 10);
ylabel(get_param_label(param2_idx), 'FontSize', 10);
title(sprintf('%s vs %s', tornado_params{param1_idx}, tornado_params{param2_idx}), ...
    'FontSize', 11, 'FontWeight', 'bold');
set(gca, 'YDir', 'normal');

% Heatmap 3: Param 2 vs Param 4
subplot(1,3,3)
param1_idx = top_params_idx(2);
param2_idx = top_params_idx(4);
sweep1 = create_param_sweep(param1_idx, n_sweep);
sweep2 = create_param_sweep(param2_idx, n_sweep);
[X3, Y3] = meshgrid(sweep1, sweep2);
Z3 = zeros(size(X3));

for ii = 1:n_sweep
    for jj = 1:n_sweep
        Z3(ii,jj) = calc_multiplier_at_params(param1_idx, X3(ii,jj), param2_idx, Y3(ii,jj), baseline, ...
            lambda_base, eirp_W_base, pg_linear_base, rx_nf_linear_base, rx_bw_Hz_base, ...
            rx_loss_linear_base, rx_gain_linear_base, radar_range_base, rx_range_base);
    end
end

imagesc(sweep1, sweep2, Z3);
hold on;
contour(sweep1, sweep2, Z3, [mc_det_mult mc_det_mult], 'r-', 'LineWidth', 2);
colorbar;
colormap(jet);
xlabel(get_param_label(param1_idx), 'FontSize', 10);
ylabel(get_param_label(param2_idx), 'FontSize', 10);
title(sprintf('%s vs %s', tornado_params{param1_idx}, tornado_params{param2_idx}), ...
    'FontSize', 11, 'FontWeight', 'bold');
set(gca, 'YDir', 'normal');

sgtitle('Targeted 2D Heatmaps - Top Parameter Pairs', 'FontSize', 13, 'FontWeight', 'bold');

%% Helper functions for targeted heatmaps
function val = get_param_min(idx)
    mins = [30, 20, 2, 0.1, 8, 10, 3, -3];
    val = mins(idx);
end

function val = get_param_max(idx)
    maxs = [100, 30, 18, 2, 20, 50, 6, 3];
    val = maxs(idx);
end

function label = get_param_label(idx)
    labels = {'EIRP (dBW)', 'Proc Gain (dB)', 'Freq (GHz)', 'RCS (m²)', ...
              'RX NF (dB)', 'RX BW (MHz)', 'RX Loss (dB)', 'RX Gain (dB)'};
    label = labels{idx};
end

function mult = calc_multiplier_at_params(param1_idx, val1, param2_idx, val2, baseline, ...
    lambda_base, eirp_W_base, pg_linear_base, rx_nf_linear_base, rx_bw_Hz_base, ...
    rx_loss_linear_base, rx_gain_linear_base, radar_range_base, rx_range_base)
    
    % Start with baseline
    vals = baseline;
    c = 3e8;
    kB = 1.380649e-23;
    T0 = 290;
    BW_Hz = 20e6;
    NF = 10^(3/10);
    L = 10^(6/10);
    mc_snr_req = 10^(13/10);
    
    % Update param1
    vals = update_param(vals, param1_idx, val1);
    % Update param2
    vals = update_param(vals, param2_idx, val2);
    
    % Recalculate ranges with updated params
    lambda_temp = c / (vals.freq * 1e9);
    eirp_temp = 10^(vals.eirp/10);
    pg_temp = 10^(vals.pg/10);
    
    % Radar range
    num_radar = eirp_temp * lambda_temp^2 * vals.rcs * pg_temp;
    den_radar = (4*pi)^3 * kB * T0 * BW_Hz * NF * mc_snr_req * L;
    radar_range = (num_radar / den_radar)^(1/4) / 1000;
    
    % Receiver range
    rx_nf_temp = 10^(vals.rx_nf/10);
    rx_bw_temp = vals.rx_bw * 1e6;
    rx_loss_temp = 10^(vals.rx_loss/10);
    rx_gain_temp = 10^(vals.rx_gain/10);
    
    num_rx = eirp_temp * rx_gain_temp * lambda_temp^2;
    den_rx = (4*pi)^2 * kB * T0 * rx_bw_temp * rx_nf_temp * mc_snr_req * rx_loss_temp;
    rx_range = sqrt(num_rx / den_rx) / 1000;
    
    mult = rx_range / radar_range;
end

function vals = update_param(vals, param_idx, value)
    switch param_idx
        case 1
            vals.eirp = value;
        case 2
            vals.pg = value;
        case 3
            vals.freq = value;
        case 4
            vals.rcs = value;
        case 5
            vals.rx_nf = value;
        case 6
            vals.rx_bw = value;
        case 7
            vals.rx_loss = value;
        case 8
            vals.rx_gain = value;
    end
end
