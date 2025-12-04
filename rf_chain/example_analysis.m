% example_analysis.m
% Example script demonstrating how to use the RF system framework
% for various types of analysis

clear; close all; clc;

%% Load Configurations

fprintf('Loading configurations...\n');
config1 = config_1_with_pcb();
fprintf('\n');
config2 = config_2_no_pcb();
fprintf('\n');

%% Define Frequency Vectors for Analysis

% Wide band analysis (70 MHz - 18 GHz)
freq_wide = linspace(70e6, 18e9, 200)';  % Column vector

% Narrow band analysis (100 MHz - 2 GHz)
freq_narrow = linspace(100e6, 2e9, 100)';  % Column vector

%% Example 1: Analyze Single RX Path

fprintf('=== Example 1: Single RX Path Analysis ===\n');

% Analyze Config 1, RX Path 1
[gain_dB, nf_dB] = config1.analyzeRxPath(1, freq_wide);

fprintf('Config 1, RX Path 1:\n');
fprintf('  Frequency vector size: %d x %d\n', size(freq_wide));
fprintf('  Gain vector size: %d x %d\n', size(gain_dB));
fprintf('  NF vector size: %d x %d\n', size(nf_dB));

if length(freq_wide) == length(gain_dB)
    fprintf('  Gain at 1 GHz: %.2f dB\n', interp1(freq_wide, gain_dB, 1e9));
    fprintf('  NF at 1 GHz: %.2f dB\n', interp1(freq_wide, nf_dB, 1e9));
    fprintf('  Gain at 10 GHz: %.2f dB\n', interp1(freq_wide, gain_dB, 10e9));
    fprintf('  NF at 10 GHz: %.2f dB\n', interp1(freq_wide, nf_dB, 10e9));
else
    fprintf('  ERROR: Size mismatch between frequency and results!\n');
    fprintf('  Gain at first frequency: %.2f dB\n', gain_dB(1));
    fprintf('  NF at first frequency: %.2f dB\n', nf_dB(1));
end

%% Example 2: Analyze Single TX Path

fprintf('\n=== Example 2: Single TX Path Analysis ===\n');

% Analyze Config 2, TX Path 1 (narrow band)
[gain_dB, nf_dB] = config2.analyzeTxPath(1, freq_narrow);

fprintf('Config 2, TX Path 1:\n');
fprintf('  Gain at 500 MHz: %.2f dB\n', interp1(freq_narrow, gain_dB, 500e6));
fprintf('  NF at 500 MHz: %.2f dB\n', interp1(freq_narrow, nf_dB, 500e6));
fprintf('  Gain at 1.5 GHz: %.2f dB\n', interp1(freq_narrow, gain_dB, 1.5e9));
fprintf('  NF at 1.5 GHz: %.2f dB\n', interp1(freq_narrow, nf_dB, 1.5e9));

%% Example 3: Compare Multiple RX Paths in Same Config

fprintf('\n=== Example 3: Compare RX Paths within Config 2 ===\n');

figure;

% Compare Category 1 (with coupler, 2-18 GHz) vs Category 2 Path 1 (no coupler, 100 MHz-2 GHz)
freq_cat1 = linspace(2e9, 18e9, 100)';      % Cat 1: 2-18 GHz
freq_cat2_p1 = linspace(100e6, 2e9, 100)';  % Cat 2 Path 1: 100 MHz-2 GHz

[g_cat1, nf_cat1] = config2.analyzeRxPath(1, freq_cat1);    % Cat 1, Path 1 (with coupler, 2-18 GHz)
[g_cat2, nf_cat2] = config2.analyzeRxPath(5, freq_cat2_p1); % Cat 2, Path 1 (no coupler, 100 MHz-2 GHz, Wing antenna)

subplot(2,1,1);
plot(freq_cat1/1e9, g_cat1, 'LineWidth', 2, 'DisplayName', 'Cat 1 (with coupler, 2-18 GHz)');
hold on;
plot(freq_cat2_p1/1e9, g_cat2, 'LineWidth', 2, 'DisplayName', 'Cat 2 Path 1 (no coupler, 100 MHz-2 GHz, Wing)');
grid on;
xlabel('Frequency (GHz)');
ylabel('Gain (dB)');
title('Config 2: RX Category Comparison - Gain');
legend('show');

subplot(2,1,2);
plot(freq_cat1/1e9, nf_cat1, 'LineWidth', 2, 'DisplayName', 'Cat 1 (with coupler, 2-18 GHz)');
hold on;
plot(freq_cat2_p1/1e9, nf_cat2, 'LineWidth', 2, 'DisplayName', 'Cat 2 Path 1 (no coupler, 100 MHz-2 GHz, Wing)');
grid on;
xlabel('Frequency (GHz)');
ylabel('Noise Figure (dB)');
title('Config 2: RX Category Comparison - NF');
legend('show');

%% Example 4: Detailed Budget Analysis with rfbudget

fprintf('\n=== Example 4: Detailed rfbudget Analysis ===\n');

% Get full budget object for detailed analysis
budget_rx = config1.computeRxBudget(1, freq_wide);

% Display budget summary
fprintf('\nConfig 1, RX Path 1 Budget:\n');
disp(budget_rx);

% Note: rfplot can be used for detailed cascade visualization
% figure;
% rfplot(budget_rx);
% Uncomment above if rfplot works with your MATLAB version

%% Example 5: TX Output Power and EIRP Analysis

fprintf('\n=== Example 5: TX Output Power and EIRP ===\n');

% Analyze TX Path 1 at multiple frequencies with DAC backoff
freq_tx_test = [500e6 1e9 5e9 10e9];
dac_backoff = 3;  % 3 dB backoff from full scale

fprintf('Config 1, TX Path 1 - Power Analysis:\n');
fprintf('DAC Backoff: %.1f dB from full scale\n\n', dac_backoff);

% If gain state data is loaded, use state 1 (max power) for comparisons
if ~isempty(config1.TxGainStates) && isfield(config1.TxGainStates, 'NumStates')
    fprintf('Using Gain State 1 (max power)\n\n');
    tx_results = config1.analyzeTxGainStates(1, freq_tx_test, 'GainState', 1);
    
    fprintf('%-12s %-12s %-12s %-12s\n', ...
        'Freq (GHz)', 'PCB Power', 'At Ant (dBm)', 'EIRP (dBm)');
    fprintf('------------------------------------------------------------------------\n');
    
    for i = 1:length(freq_tx_test)
        fprintf('%-12.2f %-12.1f %-12.1f %-12.1f\n', ...
            freq_tx_test(i)/1e9, ...
            tx_results.pcb_power_dBm(i), ...
            tx_results.power_at_antenna_dBm(i), ...
            tx_results.eirp_dBm(i));
    end
else
    % Legacy analysis without gain states
    fprintf('%-12s %-12s %-12s %-12s %-12s\n', ...
        'Freq (GHz)', 'DAC (dBm)', 'Path Gain', 'At Ant (dBm)', 'EIRP (dBm)');
    fprintf('------------------------------------------------------------------------\n');
    
    for f = freq_tx_test
        tx_results = config1.analyzeTxPathPower(1, f, 'InputBackoff_dB', dac_backoff);
        fprintf('%-12.2f %-12.1f %-12.1f %-12.1f %-12.1f\n', ...
            f/1e9, tx_results.dac_power_dBm, tx_results.path_gain_dB, ...
            tx_results.power_at_antenna_dBm, tx_results.eirp_dBm);
    end
end

% Plot detailed TX power budget
figure;
config1.plotTxPowerBudget(1, freq_wide, 'InputBackoff_dB', dac_backoff);

%% Example 6: RX Sensitivity with ADC

fprintf('\n=== Example 6: RX Sensitivity with ADC ===\n');

% Analyze with ADC effects
bandwidth = 100e6;  % 100 MHz
snr_required = 10;  % 10 dB SNR required
freq_point = 1e9;

[gain, nf_system, sensitivity] = config1.analyzeRxPathWithADC(1, freq_point, bandwidth, snr_required);

fprintf('Config 1, RX Path 1 at 1 GHz:\n');
fprintf('  RF Chain Gain: %.2f dB\n', gain);
fprintf('  System NF (including ADC): %.2f dB\n', nf_system);
fprintf('  Sensitivity (%.0f MHz BW, %d dB SNR): %.2f dBm\n', ...
    bandwidth/1e6, snr_required, sensitivity);

%% Example 7: Comprehensive RX ADC Performance Analysis

fprintf('\n=== Example 7: RX ADC Performance Analysis ===\n');

% Comprehensive ADC analysis at multiple frequencies
input_power = -40;  % -40 dBm input signal
signal_bw = 10e6;   % 10 MHz signal bandwidth

fprintf('Config 1, RX Path 1 - ADC Performance:\n');
config1.printRxADCSummary(1, freq_tx_test, ...
    'SignalBandwidth', signal_bw, ...
    'InputPower_dBm', input_power);

% Detailed ADC performance at 5 GHz
adc_results = config1.analyzeRxADC(1, 5e9, ...
    'SignalBandwidth', signal_bw, ...
    'InputPower_dBm', input_power, ...
    'RequiredSNR_dB', snr_required);

fprintf('\nDetailed ADC Analysis at 5 GHz:\n');
fprintf('  Signal at ADC:           %.2f dBm\n', adc_results.signal_at_adc_dBm);
fprintf('  Noise at ADC:            %.2f dBm\n', adc_results.noise_at_adc_dBm);
fprintf('  SNR at ADC:              %.2f dB\n', adc_results.snr_at_adc_dB);
fprintf('  ADC Full Scale:          %.2f dBm\n', adc_results.adc_fullscale_dBm);
fprintf('  ADC Utilization:         %.1f %%\n', adc_results.adc_utilization_percent);
fprintf('  Compression Margin:      %.2f dB\n', adc_results.compression_margin_dB);
fprintf('  Dynamic Range:           %.2f dB\n', adc_results.dynamic_range_dB);

% Plot comprehensive ADC performance
figure;
config1.plotRxADCPerformance(1, freq_wide, ...
    'SignalBandwidth', signal_bw, ...
    'InputPower_dBm', input_power, ...
    'RequiredSNR_dB', snr_required);

%% Example 8: Dynamic Range Analysis

fprintf('\n=== Example 8: RX Dynamic Range Analysis ===\n');

% Analyze dynamic range at 5 GHz
dr_config1 = config1.analyzeRxDynamicRange(1, 5e9, signal_bw);
dr_config2 = config2.analyzeRxDynamicRange(1, 5e9, signal_bw);

fprintf('\nDynamic Range Comparison at 5 GHz:\n');
fprintf('                          Config 1 (PCB)  Config 2 (No PCB)\n');
fprintf('----------------------------------------------------------------\n');
fprintf('Sensitivity:              %8.2f dBm    %8.2f dBm\n', ...
    dr_config1.sensitivity_dBm, dr_config2.sensitivity_dBm);
fprintf('Compression Point:        %8.2f dBm    %8.2f dBm\n', ...
    dr_config1.compression_point_dBm, dr_config2.compression_point_dBm);
fprintf('SFDR:                     %8.2f dB     %8.2f dB\n', ...
    dr_config1.spurious_free_dynamic_range_dB, dr_config2.spurious_free_dynamic_range_dB);
fprintf('Blocking DR:              %8.2f dB     %8.2f dB\n', ...
    dr_config1.blocking_dynamic_range_dB, dr_config2.blocking_dynamic_range_dB);
fprintf('IIP3:                     %8.2f dBm    %8.2f dBm\n', ...
    dr_config1.imd3_intercept_point_dBm, dr_config2.imd3_intercept_point_dBm);

%% Example 9: Sensitivity vs Bandwidth Sweep

fprintf('\n=== Example 9: Sensitivity vs Bandwidth ===\n');

bandwidths = [1e6 5e6 10e6 20e6 50e6 100e6];  % 1 MHz to 100 MHz

fprintf('\nConfig 1 RX Path 1 Sensitivity at 2 GHz:\n');
fprintf('%-15s %-15s\n', 'Bandwidth', 'Sensitivity');
fprintf('----------------------------------------\n');
for bw = bandwidths
    [~, ~, sens] = config1.analyzeRxPathWithADC(1, 2e9, bw, snr_required);
    fprintf('%-15s %-15.2f dBm\n', sprintf('%d MHz', round(bw/1e6)), sens);
end

%% Example 10: ADC Utilization vs Input Power

fprintf('\n=== Example 10: ADC Utilization Sweep ===\n');

input_powers = -80:10:-10;  % -80 dBm to -10 dBm
utilization = zeros(size(input_powers));

for i = 1:length(input_powers)
    res = config1.analyzeRxADC(1, 5e9, ...
        'SignalBandwidth', signal_bw, ...
        'InputPower_dBm', input_powers(i));
    utilization(i) = res.adc_utilization_percent;
end

figure;
plot(input_powers, utilization, 'LineWidth', 2);
hold on;
yline(100, 'r--', 'LineWidth', 1.5, 'DisplayName', '100% (Full Scale)');
yline(70, 'g--', 'LineWidth', 1, 'DisplayName', '70% (Typical Target)');
grid on;
xlabel('Input Power (dBm)');
ylabel('ADC Utilization (%)');
title('Config 1 RX Path 1 - ADC Utilization vs Input Power (5 GHz)');
legend('show', 'Location', 'northwest');

%% Example 11: Compute System Noise Temperature

fprintf('\n=== Example 11: System Noise Temperature ===\n');

% For a receive path, compute system noise temperature
% T_sys = T0 * (F - 1), where T0 = 290K and F is noise factor (linear)

freq_point = 1e9;  % 1 GHz
[~, nf_dB] = config1.analyzeRxPath(1, freq_point);
F = 10^(nf_dB/10);  % Convert NF to noise factor
T0 = 290;  % K
T_sys = T0 * (F - 1);

fprintf('Config 1, RX Path 1 at 1 GHz:\n');
fprintf('  Noise Figure: %.2f dB\n', nf_dB);
fprintf('  System Noise Temperature: %.1f K\n', T_sys);

%% Example 12: Access ADC/DAC Specifications

fprintf('\n=== Example 12: ADC/DAC Specs ===\n');

fprintf('Config 1 ADC Specs:\n');
disp(config1.ADC_Specs);

fprintf('Config 2 DAC Specs:\n');
disp(config2.DAC_Specs);

%% Example 13: Compare All RX Paths in a Config

fprintf('\n=== Example 13: Compare All RX Paths ===\n');

figure;
freq_test = linspace(1e9, 10e9, 50);  % 1-10 GHz

% If RX gain state data is loaded, use state 1 (max gain) for comparison
if ~isempty(config1.RxGainStates) && isfield(config1.RxGainStates, 'NumStates')
    fprintf('Using RX Gain State 1 (max gain) for all paths\n');
    for i = 1:length(config1.RxPaths)
        rx_results = config1.analyzeRxGainStates(i, freq_test, 'GainState', 1);
        plot(freq_test/1e9, rx_results.gain_dB, 'LineWidth', 1.5, ...
            'DisplayName', sprintf('RX Path %d', i));
        hold on;
    end
else
    % Legacy analysis without gain states
    for i = 1:length(config1.RxPaths)
        [gain_dB, ~] = config1.analyzeRxPath(i, freq_test);
        plot(freq_test/1e9, gain_dB, 'LineWidth', 1.5, ...
            'DisplayName', sprintf('RX Path %d', i));
        hold on;
    end
end

grid on;
xlabel('Frequency (GHz)');
ylabel('Gain (dB)');
title('Config 1: All RX Paths Gain Comparison');
legend('show', 'Location', 'best');

%% Example 14: Export to Excel

fprintf('\n=== Example 14: Export Configuration to Excel ===\n');

% Export Config 1 to Excel
config1.exportToExcel('Config_1_Analysis.xlsx');

% Export Config 2 to Excel  
config2.exportToExcel('Config_2_Analysis.xlsx');

fprintf('\nExcel files created with component metadata and cumulative performance!\n');

%% Example 15: PCB Gain State Analysis (if data loaded)

fprintf('\n=== Example 15: PCB Gain State Analysis ===\n');

% Check if gain state data is loaded for Config 1
if ~isempty(config1.TxGainStates) && isfield(config1.TxGainStates, 'NumStates')
    fprintf('TX Gain state data loaded: %d states\n', config1.TxGainStates.NumStates);
    
    % Analyze TX gain states
    freq_test_gs = linspace(100e6, 18e9, 100);
    tx_gs_results = config1.analyzeTxGainStates(1, freq_test_gs);
    
    % Plot all gain states
    config1.plotTxGainStates(1, freq_test_gs);
    
    % Print summary at 5 GHz
    fprintf('\nTX Path 1 at 5 GHz across gain states:\n');
    fprintf('%-12s %-15s %-15s %-15s\n', 'Gain State', 'PCB Power', 'At Antenna', 'EIRP');
    fprintf('------------------------------------------------------------------\n');
    freq_5g_idx = find(abs(freq_test_gs - 5e9) == min(abs(freq_test_gs - 5e9)), 1);
    for i = 1:length(tx_gs_results.gain_states)
        fprintf('%-12d %-15.2f %-15.2f %-15.2f dBm\n', ...
            tx_gs_results.gain_states(i), ...
            tx_gs_results.pcb_power_dBm(freq_5g_idx, i), ...
            tx_gs_results.power_at_antenna_dBm(freq_5g_idx, i), ...
            tx_gs_results.eirp_dBm(freq_5g_idx, i));
    end
else
    fprintf('No TX gain state data loaded.\n');
    fprintf('To load gain state data, use:\n');
    fprintf('  config1 = config1.loadTxGainStates(''tx_data.xlsx'', ''BDR Table (LMB)'');\n');
end

% Check RX gain states
if ~isempty(config1.RxGainStates) && isfield(config1.RxGainStates, 'NumStates')
    fprintf('\nRX Gain state data loaded: %d states\n', config1.RxGainStates.NumStates);
    
    % Analyze RX gain states
    rx_gs_results = config1.analyzeRxGainStates(1, freq_test_gs);
    
    % Plot all gain states
    config1.plotRxGainStates(1, freq_test_gs);
    
    % Print summary at 5 GHz
    fprintf('\nRX Path 1 at 5 GHz across gain states:\n');
    fprintf('%-12s %-12s %-15s %-15s %-15s\n', ...
        'Gain State', 'Gain (dB)', 'Sens (dBm)', 'UL (dBm)', 'DR (dB)');
    fprintf('------------------------------------------------------------------------\n');
    for i = 1:length(rx_gs_results.gain_states)
        fprintf('%-12d %-12.2f %-15.2f %-15.2f %-15.2f\n', ...
            rx_gs_results.gain_states(i), ...
            rx_gs_results.gain_dB(freq_5g_idx, i), ...
            rx_gs_results.sensitivity_dBm(freq_5g_idx, i), ...
            rx_gs_results.upper_limit_dBm(freq_5g_idx, i), ...
            rx_gs_results.dynamic_range_dB(freq_5g_idx, i));
    end
else
    fprintf('\nNo RX gain state data loaded.\n');
    fprintf('To load gain state data, use:\n');
    fprintf('  config1 = config1.loadRxGainStates(''rx_data.xlsx'', ''BDR Table (LMB)'');\n');
end

fprintf('\n=======================================================\n');
fprintf('Analysis complete!\n');
fprintf('=======================================================\n');
