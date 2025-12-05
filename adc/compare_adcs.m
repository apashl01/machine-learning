%% ADC Comparison Script
% Compares fundamental performance of ADC Model 1 vs Model 2
% Focuses on key ADC metrics: noise floor, dynamic range, distortion
%
% Author: Andrew's Analysis Tools
% Date: November 2025

clear; close all; clc;

%% Configuration
config = struct();
config.analysis_bw = 20e6;      % 20 MHz analysis bandwidth
config.input_impedance = 50;    % 50 ohm differential

%% Load ADC Specifications
adc1 = adc_specs_model1();
adc2 = adc_specs_model2();

%% Single Point Analysis Example
fprintf('=== Single Point Analysis ===\n\n');

% Pick a frequency for detailed analysis
config.rf_input_freq = 10e9;  % 10 GHz

% Analyze both ADCs
results1 = analyze_rf_adc(adc1, config);
results2 = analyze_rf_adc(adc2, config);

% Display results
fprintf('Operating Frequency: %.1f GHz\n', config.rf_input_freq/1e9);
fprintf('Analysis Bandwidth: %.1f MHz\n\n', config.analysis_bw/1e6);

fprintf('%-30s %15s %15s\n', 'Metric', adc1.name, adc2.name);
fprintf('%s\n', repmat('-', 1, 62));
fprintf('%-30s %12.1f dBm %12.1f dBm\n', 'Full Scale Power', ...
    results1.full_scale_dbm, results2.full_scale_dbm);
fprintf('%-30s %12.1f dBm %12.1f dBm\n', 'Noise Floor', ...
    results1.noise_floor_dbm, results2.noise_floor_dbm);
fprintf('%-30s %12.1f dBFS %12.1f dBFS\n', 'Noise Floor', ...
    results1.noise_floor_dbfs, results2.noise_floor_dbfs);
fprintf('%-30s %12.1f dB  %12.1f dB\n', 'SNR at Full Scale', ...
    results1.snr_at_full_scale_db, results2.snr_at_full_scale_db);
fprintf('%-30s %12.1f dB  %12.1f dB\n', 'SFDR', ...
    results1.sfdr_db, results2.sfdr_db);
fprintf('%-30s %12.1f dB  %12.1f dB\n', 'Dynamic Range', ...
    results1.dynamic_range_db, results2.dynamic_range_db);
fprintf('%-30s %12.1f dB  %12.1f dB\n', 'THD', ...
    results1.thd_db, results2.thd_db);
fprintf('%-30s %12.1f dBc %12.1f dBc\n', 'IM3', ...
    results1.im3_dbc, results2.im3_dbc);
fprintf('\n');

%% Frequency Sweep Comparison
fprintf('=== Frequency Sweep Analysis ===\n');
fprintf('Analyzing ADC performance across frequency range...\n\n');

% Create frequency vector covering both ADC ranges
freq_sweep_ghz = linspace(0.1, 36, 100);
freq_sweep_hz = freq_sweep_ghz * 1e9;

% Pre-allocate results - only fundamental ADC metrics
n_freq = length(freq_sweep_hz);
noise_floor_dbfs_1 = nan(n_freq, 1);
snr_1 = nan(n_freq, 1);
sfdr_1 = nan(n_freq, 1);
dr_1 = nan(n_freq, 1);
thd_db_1 = nan(n_freq, 1);

noise_floor_dbfs_2 = nan(n_freq, 1);
snr_2 = nan(n_freq, 1);
sfdr_2 = nan(n_freq, 1);
dr_2 = nan(n_freq, 1);
thd_db_2 = nan(n_freq, 1);

% Sweep through frequencies
for i = 1:n_freq
    config.rf_input_freq = freq_sweep_hz(i);
    
    % ADC 1 - only within its valid range
    try
        r1 = analyze_rf_adc(adc1, config);
        noise_floor_dbfs_1(i) = r1.noise_floor_dbfs;
        snr_1(i) = r1.snr_at_full_scale_db;
        sfdr_1(i) = r1.sfdr_db;
        dr_1(i) = r1.dynamic_range_db;
        thd_db_1(i) = r1.thd_db;
    catch
        % Outside ADC1's frequency range
    end
    
    % ADC 2 - only within its valid range
    try
        r2 = analyze_rf_adc(adc2, config);
        noise_floor_dbfs_2(i) = r2.noise_floor_dbfs;
        snr_2(i) = r2.snr_at_full_scale_db;
        sfdr_2(i) = r2.sfdr_db;
        dr_2(i) = r2.dynamic_range_db;
        thd_db_2(i) = r2.thd_db;
    catch
        % Outside ADC2's frequency range
    end
end

%% Generate Comparison Plots - Fundamental ADC Metrics Only
figure('Position', [100, 100, 1400, 900]);

% Plot 1: Noise Floor (dBFS) vs Frequency
subplot(2,3,1);
hold on; grid on;
plot(freq_sweep_ghz, noise_floor_dbfs_1, 'b-', 'LineWidth', 2, 'DisplayName', adc1.name);
plot(freq_sweep_ghz, noise_floor_dbfs_2, 'r-', 'LineWidth', 2, 'DisplayName', adc2.name);
xlabel('Frequency (GHz)');
ylabel('Noise Floor (dBFS)');
title(sprintf('Noise Floor in %.0f MHz BW', config.analysis_bw/1e6));
legend('Location', 'best');
ylim([-100, -40]);

% Plot 2: SNR at Full Scale vs Frequency
subplot(2,3,2);
hold on; grid on;
plot(freq_sweep_ghz, snr_1, 'b-', 'LineWidth', 2, 'DisplayName', adc1.name);
plot(freq_sweep_ghz, snr_2, 'r-', 'LineWidth', 2, 'DisplayName', adc2.name);
xlabel('Frequency (GHz)');
ylabel('SNR (dB)');
title('SNR at Full Scale Input');
legend('Location', 'best');
grid on;

% Plot 3: SFDR vs Frequency
subplot(2,3,3);
hold on; grid on;
plot(freq_sweep_ghz, sfdr_1, 'b-', 'LineWidth', 2, 'DisplayName', adc1.name);
plot(freq_sweep_ghz, sfdr_2, 'r-', 'LineWidth', 2, 'DisplayName', adc2.name);
xlabel('Frequency (GHz)');
ylabel('SFDR (dB)');
title('Spurious-Free Dynamic Range');
legend('Location', 'best');
grid on;

% Plot 4: Effective Dynamic Range vs Frequency
subplot(2,3,4);
hold on; grid on;
plot(freq_sweep_ghz, dr_1, 'b-', 'LineWidth', 2, 'DisplayName', adc1.name);
plot(freq_sweep_ghz, dr_2, 'r-', 'LineWidth', 2, 'DisplayName', adc2.name);
xlabel('Frequency (GHz)');
ylabel('Dynamic Range (dB)');
title('Effective Dynamic Range');
legend('Location', 'best');
grid on;

% Plot 5: THD vs Frequency
subplot(2,3,5);
hold on; grid on;
plot(freq_sweep_ghz, thd_db_1, 'b-', 'LineWidth', 2, 'DisplayName', adc1.name);
plot(freq_sweep_ghz, thd_db_2, 'r-', 'LineWidth', 2, 'DisplayName', adc2.name);
xlabel('Frequency (GHz)');
ylabel('THD (dB)');
title('Total Harmonic Distortion');
legend('Location', 'best');
grid on;

% Plot 6: Performance Summary Bar Chart at 10 GHz
subplot(2,3,6);
test_freq = 10;  % GHz
% Find closest frequency point
[~, idx] = min(abs(freq_sweep_ghz - test_freq));

% Only plot if we have valid data at this frequency
if ~isnan(noise_floor_dbfs_1(idx)) && ~isnan(noise_floor_dbfs_2(idx))
    metrics = {'Noise Floor', 'SNR@FS', 'SFDR', 'Dyn Range', 'THD'};
    adc1_vals = [noise_floor_dbfs_1(idx), snr_1(idx), sfdr_1(idx), dr_1(idx), thd_db_1(idx)];
    adc2_vals = [noise_floor_dbfs_2(idx), snr_2(idx), sfdr_2(idx), dr_2(idx), thd_db_2(idx)];
    
    x = 1:length(metrics);
    width = 0.35;
    bar(x - width/2, adc1_vals, width, 'FaceColor', 'b', 'DisplayName', adc1.name);
    hold on;
    bar(x + width/2, adc2_vals, width, 'FaceColor', 'r', 'DisplayName', adc2.name);
    set(gca, 'XTick', x, 'XTickLabel', metrics);
    ylabel('Value (dB or dBFS)');
    title(sprintf('Performance at %.0f GHz', test_freq));
    legend('Location', 'best');
    grid on;
    xtickangle(45);
else
    % If no data at 10 GHz, show message
    text(0.5, 0.5, sprintf('No data at %.0f GHz\nBoth ADCs outside operating range', test_freq), ...
        'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', 'FontSize', 12);
    axis off;
end

sgtitle('ADC Fundamental Performance Comparison', 'FontSize', 14, 'FontWeight', 'bold');

%% Generate Simulated FFT Comparison - Full Operational Range
% This shows what ADC performance looks like across the full RF input range
figure('Position', [150, 150, 1400, 700]);

% Create RF frequency vector for both ADCs (their operational ranges)
rf_freq_1_min = min(adc1.freq_bands(:,1));
rf_freq_1_max = max(adc1.freq_bands(:,2));
rf_freq_2_min = min(adc2.freq_bands(:,1));
rf_freq_2_max = max(adc2.freq_bands(:,2));

% Denser frequency sweep for smooth curves
rf_sweep_1 = linspace(rf_freq_1_min, rf_freq_1_max, 200);  % GHz
rf_sweep_2 = linspace(rf_freq_2_min, rf_freq_2_max, 200);  % GHz

% Pre-allocate for ADC 1 performance across frequency
nf_1_sweep = nan(size(rf_sweep_1));
sfdr_1_sweep = nan(size(rf_sweep_1));
thd_1_sweep = nan(size(rf_sweep_1));

% Pre-allocate for ADC 2 performance across frequency  
nf_2_sweep = nan(size(rf_sweep_2));
sfdr_2_sweep = nan(size(rf_sweep_2));
thd_2_sweep = nan(size(rf_sweep_2));

% Get performance vs frequency for ADC 1
for i = 1:length(rf_sweep_1)
    config.rf_input_freq = rf_sweep_1(i) * 1e9;
    try
        r = analyze_rf_adc(adc1, config);
        nf_1_sweep(i) = r.noise_floor_dbfs;
        sfdr_1_sweep(i) = -r.sfdr_db;  % Convert to level below FS
        thd_1_sweep(i) = r.thd_db;
    catch
        % Outside range
    end
end

% Get performance vs frequency for ADC 2
for i = 1:length(rf_sweep_2)
    config.rf_input_freq = rf_sweep_2(i) * 1e9;
    try
        r = analyze_rf_adc(adc2, config);
        nf_2_sweep(i) = r.noise_floor_dbfs;
        sfdr_2_sweep(i) = -r.sfdr_db;  % Convert to level below FS
        thd_2_sweep(i) = r.thd_db;
    catch
        % Outside range
    end
end

% ADC 1 Spectrum
subplot(1,2,1);
hold on; grid on;

% Signal at 0 dBFS (reference)
plot([rf_freq_1_min, rf_freq_1_max], [0, 0], 'k-', 'LineWidth', 3, 'DisplayName', 'Full Scale (0 dBFS)');

% Noise floor across frequency
plot(rf_sweep_1, nf_1_sweep, 'b-', 'LineWidth', 2.5, 'DisplayName', 'Noise Floor');

% Largest spur (from SFDR) across frequency
plot(rf_sweep_1, sfdr_1_sweep, 'r-', 'LineWidth', 2, 'DisplayName', 'Largest Spur');

% 2nd Harmonic (from THD) across frequency
plot(rf_sweep_1, thd_1_sweep, 'm-', 'LineWidth', 2, 'DisplayName', '2nd Harmonic (THD)');

% Fill noise floor area
fill([rf_sweep_1, fliplr(rf_sweep_1)], ...
     [nf_1_sweep, ones(size(nf_1_sweep))*-120], ...
     'b', 'FaceAlpha', 0.1, 'EdgeColor', 'none', 'HandleVisibility', 'off');

xlabel('RF Input Frequency (GHz)');
ylabel('Magnitude (dBFS)');
title(sprintf('%s - Performance Across Operational Range', adc1.name));
legend('Location', 'southwest');
ylim([-120, 10]);
xlim([rf_freq_1_min, rf_freq_1_max]);

% Add performance annotation
avg_snr = nanmean(0 - nf_1_sweep);
avg_dr = nanmean(0 - max(nf_1_sweep, sfdr_1_sweep));
text(rf_freq_1_min + (rf_freq_1_max-rf_freq_1_min)*0.05, -15, ...
    sprintf('Avg SNR@FS: %.1f dB', avg_snr), 'FontSize', 10, 'FontWeight', 'bold', 'BackgroundColor', 'white');
text(rf_freq_1_min + (rf_freq_1_max-rf_freq_1_min)*0.05, -25, ...
    sprintf('Avg Dyn Range: %.1f dB', avg_dr), 'FontSize', 10, 'BackgroundColor', 'white');

% ADC 2 Spectrum
subplot(1,2,2);
hold on; grid on;

% Signal at 0 dBFS (reference)
plot([rf_freq_2_min, rf_freq_2_max], [0, 0], 'k-', 'LineWidth', 3, 'DisplayName', 'Full Scale (0 dBFS)');

% Noise floor across frequency
plot(rf_sweep_2, nf_2_sweep, 'b-', 'LineWidth', 2.5, 'DisplayName', 'Noise Floor');

% Largest spur (from SFDR) across frequency
plot(rf_sweep_2, sfdr_2_sweep, 'r-', 'LineWidth', 2, 'DisplayName', 'Largest Spur');

% 2nd Harmonic (from THD) across frequency
plot(rf_sweep_2, thd_2_sweep, 'm-', 'LineWidth', 2, 'DisplayName', '2nd Harmonic (THD)');

% Fill noise floor area
fill([rf_sweep_2, fliplr(rf_sweep_2)], ...
     [nf_2_sweep, ones(size(nf_2_sweep))*-120], ...
     'b', 'FaceAlpha', 0.1, 'EdgeColor', 'none', 'HandleVisibility', 'off');

xlabel('RF Input Frequency (GHz)');
ylabel('Magnitude (dBFS)');
title(sprintf('%s - Performance Across Operational Range', adc2.name));
legend('Location', 'southwest');
ylim([-120, 10]);
xlim([rf_freq_2_min, rf_freq_2_max]);

% Add performance annotation
avg_snr = nanmean(0 - nf_2_sweep);
avg_dr = nanmean(0 - max(nf_2_sweep, sfdr_2_sweep));
text(rf_freq_2_min + (rf_freq_2_max-rf_freq_2_min)*0.05, -15, ...
    sprintf('Avg SNR@FS: %.1f dB', avg_snr), 'FontSize', 10, 'FontWeight', 'bold', 'BackgroundColor', 'white');
text(rf_freq_2_min + (rf_freq_2_max-rf_freq_2_min)*0.05, -25, ...
    sprintf('Avg Dyn Range: %.1f dB', avg_dr), 'FontSize', 10, 'BackgroundColor', 'white');

sgtitle(sprintf('ADC Performance vs RF Input Frequency (%.0f MHz Analysis BW)', config.analysis_bw/1e6), ...
    'FontSize', 14, 'FontWeight', 'bold');

%% Performance Summary Table
fprintf('=== Performance Summary at Key Frequencies ===\n\n');

test_freqs_ghz = [3, 10, 18, 28, 35];

fprintf('%-20s', 'Frequency (GHz)');
for f = test_freqs_ghz
    fprintf('%12.0f', f);
end
fprintf('\n%s\n', repmat('-', 1, 80));

% Function to print comparison row
print_row = @(metric_name, data1, data2, unit) fprintf(['%-20s' repmat('%6.1f/%5.1f', 1, length(test_freqs_ghz)) ' %s\n'], ...
    metric_name, reshape([data1; data2], 1, []), unit);

% Extract values at test frequencies
nf_1_vals = interp1(freq_sweep_ghz, noise_floor_dbfs_1, test_freqs_ghz, 'linear', nan);
nf_2_vals = interp1(freq_sweep_ghz, noise_floor_dbfs_2, test_freqs_ghz, 'linear', nan);
print_row('Noise Floor', nf_1_vals, nf_2_vals, 'dBFS');

snr_1_vals = interp1(freq_sweep_ghz, snr_1, test_freqs_ghz, 'linear', nan);
snr_2_vals = interp1(freq_sweep_ghz, snr_2, test_freqs_ghz, 'linear', nan);
print_row('SNR @ FS', snr_1_vals, snr_2_vals, 'dB');

sfdr_1_vals = interp1(freq_sweep_ghz, sfdr_1, test_freqs_ghz, 'linear', nan);
sfdr_2_vals = interp1(freq_sweep_ghz, sfdr_2, test_freqs_ghz, 'linear', nan);
print_row('SFDR', sfdr_1_vals, sfdr_2_vals, 'dB');

dr_1_vals = interp1(freq_sweep_ghz, dr_1, test_freqs_ghz, 'linear', nan);
dr_2_vals = interp1(freq_sweep_ghz, dr_2, test_freqs_ghz, 'linear', nan);
print_row('Dynamic Range', dr_1_vals, dr_2_vals, 'dB');

thd_1_vals = interp1(freq_sweep_ghz, thd_db_1, test_freqs_ghz, 'linear', nan);
thd_2_vals = interp1(freq_sweep_ghz, thd_db_2, test_freqs_ghz, 'linear', nan);
print_row('THD', thd_1_vals, thd_2_vals, 'dB');

fprintf('\nFormat: ADC1/ADC2 at each frequency\n');
fprintf('Note: NaN values indicate frequency outside ADC operating range\n\n');

fprintf('Analysis complete!\n');
