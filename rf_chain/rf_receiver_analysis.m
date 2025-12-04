%% RF Receiver Chain Analysis - Design Review
% Compares two receiver configurations: RFP and non-RFP
% MATLAB R2024a
% Analysis bandwidth: 20 MHz

clear; close all; clc;

%% Global Parameters
Z0 = 50;                    % Reference impedance (Ohms)
T0 = 290;                   % Reference temperature (K)
kB = 1.380649e-23;          % Boltzmann constant (J/K)
BW = 20e6;                  % Analysis bandwidth (Hz)

% Thermal noise floor
N0_dBm_Hz = 10*log10(kB * T0 * 1000);  % dBm/Hz

%% Configuration 1: RFP (RF Conditioning PCB)
fprintf('=== Configuration 1: RFP ===\n');

% Component parameters (all in dB except where noted)
rfp_antenna_gain = 0;       % Antenna gain (dB)
rfp_cable_loss = -3;        % Cable loss (dB)
rfp_pcb_gain = 10;          % RFP gain (dB)
rfp_pcb_nf = 16;            % RFP noise figure (dB)
rfp_adc_nf = 21;            % ADC noise figure (dB)
rfp_adc_fullscale = -3.45;  % ADC input range (dBm)
rfp_adc_enob = 7.2;         % Effective number of bits

% Build chain
rfp_stages = {
    'Antenna',      rfp_antenna_gain,   0;          % Passive antenna, NF = 0
    'Cable',        rfp_cable_loss,     -rfp_cable_loss;  % Passive loss, NF = Loss
    'RFP',          rfp_pcb_gain,       rfp_pcb_nf;
    'ADC',          0,                  rfp_adc_nf;
};

% Calculate cascaded parameters
[rfp_cum_gain, rfp_cum_nf, rfp_stage_gains, rfp_stage_nfs] = ...
    cascade_analysis(rfp_stages);

% Sensitivity and dynamic range
rfp_sensitivity_dBm = N0_dBm_Hz + 10*log10(BW) + rfp_cum_nf + 13;  % +13 dB SNR
rfp_noise_floor_dBm = N0_dBm_Hz + 10*log10(BW) + rfp_cum_nf;
rfp_sfdr_dB = calculate_sfdr(rfp_adc_enob);
rfp_dynamic_range = rfp_adc_fullscale - rfp_sensitivity_dBm;

fprintf('Cascaded Gain: %.2f dB\n', rfp_cum_gain);
fprintf('Cascaded NF: %.2f dB\n', rfp_cum_nf);
fprintf('Noise Floor (20 MHz BW): %.2f dBm\n', rfp_noise_floor_dBm);
fprintf('Sensitivity (13 dB SNR): %.2f dBm\n', rfp_sensitivity_dBm);
fprintf('SFDR: %.2f dB\n', rfp_sfdr_dB);
fprintf('Dynamic Range: %.2f dB\n\n', rfp_dynamic_range);

%% Configuration 2: Non-RFP (Direct ADC with front-end components)
fprintf('=== Configuration 2: Non-RFP ===\n');

% Component parameters
norfp_antenna_gain = 0;         % Antenna gain (dB)
norfp_cable_loss = -3;          % Cable loss (dB)
norfp_coupler_loss = -0.5;      % Coupler loss (dB)
norfp_lna_gain = 34;            % LNA gain (dB)
norfp_lna_nf = 2;               % LNA noise figure (dB)
norfp_switch_loss = -1.5;       % Switch loss (dB)
norfp_filter_loss = -0.8;       % Anti-aliasing filter loss (dB)
norfp_adc_nsd = -153;           % ADC noise spectral density (dBFS/Hz)
norfp_adc_fullscale = -1.1;     % ADC input range (dBm)
norfp_adc_bits = 10;            % ADC bits

% Convert NSD to noise figure
% NSD in dBFS/Hz needs to be referenced to input
% NF = (Output noise power) / (kTB * Gain)
% For ADC: Noise power = NSD + 10*log10(BW) + Fullscale (to convert from FS to absolute)
norfp_adc_noise_power_dBm = norfp_adc_nsd + 10*log10(BW) + norfp_adc_fullscale;
norfp_input_ref_noise_dBm = norfp_adc_noise_power_dBm;  % No gain in ADC
thermal_noise_dBm = N0_dBm_Hz + 10*log10(BW);
norfp_adc_nf = norfp_input_ref_noise_dBm - thermal_noise_dBm;

fprintf('ADC NF (calculated from NSD): %.2f dB\n', norfp_adc_nf);

% Build chain (LNA after coupler for best NF)
norfp_stages = {
    'Antenna',      norfp_antenna_gain,     0;
    'Cable',        norfp_cable_loss,       -norfp_cable_loss;
    'Coupler',      norfp_coupler_loss,     -norfp_coupler_loss;
    'LNA',          norfp_lna_gain,         norfp_lna_nf;
    'Switch',       norfp_switch_loss,      -norfp_switch_loss;
    'AAF',          norfp_filter_loss,      -norfp_filter_loss;
    'ADC',          0,                      norfp_adc_nf;
};

% Calculate cascaded parameters
[norfp_cum_gain, norfp_cum_nf, norfp_stage_gains, norfp_stage_nfs] = ...
    cascade_analysis(norfp_stages);

% Sensitivity and dynamic range
norfp_sensitivity_dBm = N0_dBm_Hz + 10*log10(BW) + norfp_cum_nf + 13;
norfp_noise_floor_dBm = N0_dBm_Hz + 10*log10(BW) + norfp_cum_nf;
norfp_sfdr_dB = calculate_sfdr_from_bits(norfp_adc_bits);
norfp_dynamic_range = norfp_adc_fullscale - norfp_sensitivity_dBm;

fprintf('Cascaded Gain: %.2f dB\n', norfp_cum_gain);
fprintf('Cascaded NF: %.2f dB\n', norfp_cum_nf);
fprintf('Noise Floor (20 MHz BW): %.2f dBm\n', norfp_noise_floor_dBm);
fprintf('Sensitivity (13 dB SNR): %.2f dBm\n', norfp_sensitivity_dBm);
fprintf('SFDR: %.2f dB\n', norfp_sfdr_dB);
fprintf('Dynamic Range: %.2f dB\n\n', norfp_dynamic_range);

%% Plotting
figure('Position', [100 100 1400 900], 'Color', 'w');

% RFP Configuration Plots
subplot(2,3,1)
plot_cascade_gain(rfp_stages, rfp_stage_gains);
title('RFP Configuration: Cascaded Gain', 'FontSize', 12, 'FontWeight', 'bold');
grid on;

subplot(2,3,2)
plot_cascade_nf(rfp_stages, rfp_stage_nfs);
title('RFP Configuration: Cascaded Noise Figure', 'FontSize', 12, 'FontWeight', 'bold');
grid on;

subplot(2,3,3)
plot_performance_summary('RFP', rfp_cum_gain, rfp_cum_nf, rfp_sensitivity_dBm, ...
    rfp_adc_fullscale, rfp_dynamic_range, rfp_sfdr_dB);
title('RFP: Performance Summary', 'FontSize', 12, 'FontWeight', 'bold');

% Non-RFP Configuration Plots
subplot(2,3,4)
plot_cascade_gain(norfp_stages, norfp_stage_gains);
title('Non-RFP Configuration: Cascaded Gain', 'FontSize', 12, 'FontWeight', 'bold');
grid on;

subplot(2,3,5)
plot_cascade_nf(norfp_stages, norfp_stage_nfs);
title('Non-RFP Configuration: Cascaded Noise Figure', 'FontSize', 12, 'FontWeight', 'bold');
grid on;

subplot(2,3,6)
plot_performance_summary('Non-RFP', norfp_cum_gain, norfp_cum_nf, norfp_sensitivity_dBm, ...
    norfp_adc_fullscale, norfp_dynamic_range, norfp_sfdr_dB);
title('Non-RFP: Performance Summary', 'FontSize', 12, 'FontWeight', 'bold');

sgtitle('RF Receiver Chain Analysis - Design Review', 'FontSize', 14, 'FontWeight', 'bold');

%% Comparison Figure
figure('Position', [150 150 1200 600], 'Color', 'w');

subplot(1,2,1)
configs = categorical({'RFP', 'Non-RFP'});
gains = [rfp_cum_gain, norfp_cum_gain];
nfs = [rfp_cum_nf, norfp_cum_nf];

yyaxis left
bar(configs, gains, 0.4, 'FaceColor', [0.2 0.6 0.8]);
ylabel('Cascaded Gain (dB)', 'FontSize', 11);
ylim([min(gains)-5, max(gains)+5]);

yyaxis right
hold on;
plot(configs, nfs, 'ro-', 'LineWidth', 2, 'MarkerSize', 10, 'MarkerFaceColor', 'r');
ylabel('Cascaded Noise Figure (dB)', 'FontSize', 11);
ylim([min(nfs)-2, max(nfs)+5]);

title('Configuration Comparison: Gain & Noise Figure', 'FontSize', 12, 'FontWeight', 'bold');
grid on;
legend('Gain', 'Noise Figure', 'Location', 'northwest');

subplot(1,2,2)
metrics = {'Sensitivity', 'Noise Floor', 'ADC Max Input', 'Dynamic Range'};
rfp_vals = [rfp_sensitivity_dBm, rfp_noise_floor_dBm, rfp_adc_fullscale, rfp_dynamic_range];
norfp_vals = [norfp_sensitivity_dBm, norfp_noise_floor_dBm, norfp_adc_fullscale, norfp_dynamic_range];

x = 1:length(metrics);
width = 0.35;
bar(x - width/2, rfp_vals, width, 'FaceColor', [0.8 0.4 0.4], 'DisplayName', 'RFP');
hold on;
bar(x + width/2, norfp_vals, width, 'FaceColor', [0.4 0.8 0.4], 'DisplayName', 'Non-RFP');

set(gca, 'XTick', x, 'XTickLabel', metrics);
ylabel('Power (dBm) / Range (dB)', 'FontSize', 11);
title('Configuration Comparison: Key Metrics', 'FontSize', 12, 'FontWeight', 'bold');
legend('Location', 'best');
grid on;
xtickangle(45);

sgtitle('RFP vs Non-RFP Configuration Comparison', 'FontSize', 14, 'FontWeight', 'bold');

%% Helper Functions

function [cum_gain, cum_nf, stage_gains, stage_nfs] = cascade_analysis(stages)
    % Friis cascade analysis for gain and noise figure
    num_stages = size(stages, 1);
    stage_gains = zeros(num_stages, 1);
    stage_nfs = zeros(num_stages, 1);
    
    cum_gain = 0;  % dB
    cum_gain_linear = 1;
    cum_noise_factor = 1;
    
    for i = 1:num_stages
        gain_dB = stages{i, 2};
        nf_dB = stages{i, 3};
        
        gain_linear = 10^(gain_dB/10);
        nf_linear = 10^(nf_dB/10);
        
        % Friis formula for noise factor
        if i == 1
            cum_noise_factor = nf_linear;
        else
            cum_noise_factor = cum_noise_factor + (nf_linear - 1) / cum_gain_linear;
        end
        
        % Update cumulative gain
        cum_gain_linear = cum_gain_linear * gain_linear;
        cum_gain = cum_gain + gain_dB;
        
        % Store cumulative values at each stage
        stage_gains(i) = cum_gain;
        stage_nfs(i) = 10*log10(cum_noise_factor);
    end
    
    cum_nf = 10*log10(cum_noise_factor);
end

function plot_cascade_gain(stages, stage_gains)
    num_stages = size(stages, 1);
    stage_names = stages(:, 1);
    
    % Create stairs plot
    stairs(0:num_stages, [0; stage_gains], 'b-', 'LineWidth', 2);
    hold on;
    plot(1:num_stages, stage_gains, 'ro', 'MarkerSize', 8, 'MarkerFaceColor', 'r');
    
    xlabel('Stage', 'FontSize', 10);
    ylabel('Cumulative Gain (dB)', 'FontSize', 10);
    set(gca, 'XTick', 0:num_stages);
    set(gca, 'XTickLabel', ['Input'; stage_names]);
    xtickangle(45);
    
    % Add value labels
    for i = 1:num_stages
        text(i, stage_gains(i), sprintf('  %.1f dB', stage_gains(i)), ...
            'VerticalAlignment', 'bottom', 'FontSize', 8);
    end
end

function plot_cascade_nf(stages, stage_nfs)
    num_stages = size(stages, 1);
    stage_names = stages(:, 1);
    
    % Create stairs plot
    stairs(0:num_stages, [0; stage_nfs], 'r-', 'LineWidth', 2);
    hold on;
    plot(1:num_stages, stage_nfs, 'bo', 'MarkerSize', 8, 'MarkerFaceColor', 'b');
    
    xlabel('Stage', 'FontSize', 10);
    ylabel('Cumulative Noise Figure (dB)', 'FontSize', 10);
    set(gca, 'XTick', 0:num_stages);
    set(gca, 'XTickLabel', ['Input'; stage_names]);
    xtickangle(45);
    
    % Add value labels
    for i = 1:num_stages
        text(i, stage_nfs(i), sprintf('  %.1f dB', stage_nfs(i)), ...
            'VerticalAlignment', 'bottom', 'FontSize', 8);
    end
end

function plot_performance_summary(config_name, gain, nf, sensitivity, max_input, dyn_range, sfdr)
    % Text-based summary plot
    axis off;
    
    summary_text = {
        sprintf('Configuration: %s', config_name), ...
        '', ...
        sprintf('Cascaded Gain: %.2f dB', gain), ...
        sprintf('Cascaded NF: %.2f dB', nf), ...
        '', ...
        sprintf('Sensitivity (13dB SNR): %.2f dBm', sensitivity), ...
        sprintf('ADC Max Input: %.2f dBm', max_input), ...
        sprintf('Dynamic Range: %.2f dB', dyn_range), ...
        sprintf('SFDR: %.2f dB', sfdr)
    };
    
    text(0.1, 0.5, summary_text, 'FontSize', 10, 'VerticalAlignment', 'middle', ...
        'FontName', 'FixedWidth', 'FontWeight', 'bold');
end

function sfdr = calculate_sfdr(enob)
    % SFDR from ENOB: SFDR ≈ 6.02*ENOB + 1.76 dB
    sfdr = 6.02 * enob + 1.76;
end

function sfdr = calculate_sfdr_from_bits(bits)
    % Ideal SFDR from bit count (assumes ~1 bit lost to noise)
    enob = bits - 1;
    sfdr = 6.02 * enob + 1.76;
end
