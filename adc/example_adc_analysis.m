%% Simple ADC Analysis Example
% Quick example showing how to analyze a single ADC at one frequency
%
% Author: Andrew's Analysis Tools
% Date: November 2025

clear; clc;

%% Step 1: Load ADC specifications
% Choose which ADC to analyze
adc = adc_specs_model1();  % or adc_specs_model2()

%% Step 2: Configure analysis parameters
config = struct();
config.rf_input_freq = 10e9;     % 10 GHz operating frequency
config.analysis_bw = 20e6;       % 20 MHz analysis bandwidth
config.input_impedance = 50;     % 50 ohm differential (optional, has default)

%% Step 3: Run analysis
results = analyze_rf_adc(adc, config);

%% Step 4: Display key results
fprintf('\n=== ADC Analysis Results ===\n');
fprintf('ADC: %s\n', adc.name);
fprintf('Frequency: %.2f GHz\n', config.rf_input_freq/1e9);
fprintf('Analysis BW: %.1f MHz\n', config.analysis_bw/1e6);
fprintf('Operating Band: %s\n\n', results.operating_band_ghz);

fprintf('Key Performance Metrics:\n');
fprintf('  Full Scale Power:     %6.1f dBm\n', results.full_scale_dbm);
fprintf('  Noise Floor:          %6.1f dBm\n', results.noise_floor_dbm);
fprintf('  Sensitivity:          %6.1f dBm (at 10 dB SNR)\n', results.sensitivity_dbm);
fprintf('  SNR at Full Scale:    %6.1f dB\n', results.snr_at_full_scale_db);
fprintf('  SFDR:                 %6.1f dB\n', results.sfdr_db);
fprintf('  Dynamic Range:        %6.1f dB\n', results.dynamic_range_db);
fprintf('  Equivalent NF:        %6.1f dB\n', results.equivalent_noise_figure_db);
fprintf('  THD:                  %6.1f dB (%.2f%%)\n', results.thd_db, results.thd_percent);
fprintf('  IM3:                  %6.1f dBc\n', results.im3_dbc);

%% Step 5: Use results in your RF chain analysis
fprintf('\n=== For Integration into RF Chain Analysis ===\n');
fprintf('Use these values in your receiver chain scripts:\n');
fprintf('  adc_noise_figure = %.1f dB\n', results.equivalent_noise_figure_db);
fprintf('  adc_sensitivity = %.1f dBm\n', results.sensitivity_dbm);
fprintf('  adc_full_scale = %.1f dBm\n', results.full_scale_dbm);
fprintf('  adc_dynamic_range = %.1f dB\n\n', results.dynamic_range_db);

%% Optional: Quick visualization of input signal levels
figure('Position', [100, 100, 800, 500]);
hold on; grid on;

% Mark key levels
input_levels_dbm = linspace(results.noise_floor_dbm - 10, results.full_scale_dbm + 5, 100);
snr_db = input_levels_dbm - results.noise_floor_dbm;

% Plot SNR vs input level
plot(input_levels_dbm, snr_db, 'b-', 'LineWidth', 2);

% Mark key points
plot(results.noise_floor_dbm, 0, 'ro', 'MarkerSize', 10, 'LineWidth', 2);
plot(results.sensitivity_dbm, 10, 'go', 'MarkerSize', 10, 'LineWidth', 2);
plot(results.full_scale_dbm, results.snr_at_full_scale_db, 'mo', 'MarkerSize', 10, 'LineWidth', 2);

% Add reference lines
yline(10, 'g--', 'Min SNR (10 dB)', 'LineWidth', 1.5);
xline(results.noise_floor_dbm, 'r--', 'Noise Floor', 'LineWidth', 1.5);
xline(results.sensitivity_dbm, 'g--', 'Sensitivity', 'LineWidth', 1.5);
xline(results.full_scale_dbm, 'm--', 'Full Scale', 'LineWidth', 1.5);

xlabel('Input Signal Level (dBm)');
ylabel('SNR (dB)');
title(sprintf('ADC SNR vs Input Level - %s @ %.1f GHz', adc.name, config.rf_input_freq/1e9));
ylim([-10, max(snr_db) + 10]);
legend('SNR Curve', 'Noise Floor (0 dB SNR)', 'Sensitivity (10 dB SNR)', 'Full Scale', ...
    'Location', 'northwest');

fprintf('Example complete!\n');
fprintf('Run compare_adcs.m to see ADC1 vs ADC2 comparison\n\n');
