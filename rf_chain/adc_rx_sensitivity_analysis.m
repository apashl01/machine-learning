% ADC Receiver Sensitivity Analysis
% Compares passive-only vs LNA configurations
% Accounts for channelization processing gain

clear all; close all; clc;

%% System Parameters
% ADC Specifications (Real Mode - 10 bit)
ADC_NSD_dBFS_Hz = -153;           % Noise spectral density in dBFS/Hz (real mode)
FS_power_dBm = -1.1;              % Full scale power per datasheet
ADC_impedance = 100;              % Differential impedance (ohms)
sample_rate_GSPS = 64;            % Sample rate in GSPS
analysis_BW_MHz = 20;             % Channelized bandwidth in MHz
detection_threshold_dB = 13;      % SNR threshold for detection

% ADC performance specs from datasheet
ADC_SFDR_dBc = 55;                % Spurious-Free Dynamic Range
ADC_THD_dBc = -60;                % Total Harmonic Distortion
ADC_IMD3_dBc = -60;               % 3rd Order Intermodulation

% Convert NSD to absolute power
ADC_NSD_dBm_Hz = ADC_NSD_dBFS_Hz + FS_power_dBm;

fprintf('=== ADC Characteristics (Real Mode - 10 bit) ===\n');
fprintf('Full Scale Power: %.2f dBm\n', FS_power_dBm);
fprintf('ADC Input-Referred NSD: %.2f dBm/Hz\n', ADC_NSD_dBm_Hz);
fprintf('ADC Nyquist BW: %.1f GHz\n', sample_rate_GSPS/2);
fprintf('Analysis BW: %.1f MHz\n', analysis_BW_MHz);
fprintf('SFDR: %.0f dBc\n', ADC_SFDR_dBc);
fprintf('THD: %.0f dBc\n', ADC_THD_dBc);
fprintf('IMD3: %.0f dBc\n\n', ADC_IMD3_dBc);

% Passive Component Losses (dB)
cable_loss_dB = 3.0;
coupler_loss_dB = 0.5;
switch_loss_dB = 1.0;
filter_loss_dB = 0.8;
total_passive_loss_dB = cable_loss_dB + coupler_loss_dB + switch_loss_dB + filter_loss_dB;

fprintf('=== Passive Losses ===\n');
fprintf('Cable Loss: %.1f dB\n', cable_loss_dB);
fprintf('Coupler Loss: %.1f dB\n', coupler_loss_dB);
fprintf('RF Switch Loss: %.1f dB\n', switch_loss_dB);
fprintf('AA Filter Loss: %.1f dB\n', filter_loss_dB);
fprintf('Total Passive Loss: %.1f dB\n\n', total_passive_loss_dB);

% Physical constants
k_Boltzmann = 1.38e-23;  % J/K
T0 = 290;                % K (reference temperature)
thermal_noise_dBm_Hz = 10*log10(k_Boltzmann * T0 * 1000);  % -174 dBm/Hz

%% Processing Gain from Channelization
nyquist_BW_Hz = sample_rate_GSPS * 1e9 / 2;
analysis_BW_Hz = analysis_BW_MHz * 1e6;
processing_gain_dB = 10*log10(nyquist_BW_Hz / analysis_BW_Hz);

fprintf('=== Channelization Bandwidth ===\n');
fprintf('Nyquist BW: %.1f GHz\n', nyquist_BW_Hz/1e9);
fprintf('Analysis BW: %.1f MHz\n', analysis_BW_MHz);
fprintf('Note: Analysis uses noise in 20 MHz bandwidth directly\n\n');

%% CASE 1: Passive-Only Configuration (No LNA)
fprintf('====================================\n');
fprintf('CASE 1: PASSIVE-ONLY (No LNA)\n');
fprintf('====================================\n');

% Thermal noise attenuated by passive losses at ADC input
thermal_at_ADC_dBm_Hz = thermal_noise_dBm_Hz - total_passive_loss_dB;

% ADC noise at ADC input
ADC_noise_at_ADC_dBm_Hz = ADC_NSD_dBm_Hz;

% Total noise at ADC input (RSS combination)
total_noise_at_ADC_dBm_Hz = 10*log10(10^(thermal_at_ADC_dBm_Hz/10) + 10^(ADC_noise_at_ADC_dBm_Hz/10));

% ADC noise dominates since thermal is attenuated
fprintf('Thermal noise at ADC input: %.2f dBm/Hz\n', thermal_at_ADC_dBm_Hz);
fprintf('ADC noise at ADC input: %.2f dBm/Hz\n', ADC_noise_at_ADC_dBm_Hz);
fprintf('Total noise at ADC input: %.2f dBm/Hz\n', total_noise_at_ADC_dBm_Hz);

% Noise power in analysis bandwidth (at ADC input)
noise_power_at_ADC_20MHz_dBm = total_noise_at_ADC_dBm_Hz + 10*log10(analysis_BW_Hz);
fprintf('Noise power at ADC (20 MHz): %.2f dBm\n', noise_power_at_ADC_20MHz_dBm);

% For detection, need signal at ADC to be 13 dB above this noise
signal_required_at_ADC_dBm = noise_power_at_ADC_20MHz_dBm + detection_threshold_dB;
fprintf('Signal required at ADC for detection: %.2f dBm\n', signal_required_at_ADC_dBm);

% Minimum detectable signal at antenna (add back passive losses)
MDS_passive_dBm = signal_required_at_ADC_dBm + total_passive_loss_dB;

% Calculate system NF by referring noise back to antenna
system_NSD_at_antenna_dBm_Hz = total_noise_at_ADC_dBm_Hz + total_passive_loss_dB;
NF_passive_system_dB = system_NSD_at_antenna_dBm_Hz - thermal_noise_dBm_Hz;

fprintf('System NSD (at antenna): %.2f dBm/Hz\n', system_NSD_at_antenna_dBm_Hz);
fprintf('System NF: %.2f dB\n', NF_passive_system_dB);
fprintf('Minimum Detectable Signal (at antenna): %.2f dBm\n\n', MDS_passive_dBm);

%% CASE 2: With LNA (Sweep through different options)
fprintf('====================================\n');
fprintf('CASE 2: WITH LNA\n');
fprintf('====================================\n');

% LNA parameter sweeps
LNA_gain_range_dB = [10, 15, 20, 25, 30, 35, 40];
LNA_NF_range_dB = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0];

% Storage for results
results = struct();
result_idx = 1;

fprintf('Analyzing LNA configurations...\n\n');
fprintf('%-10s %-10s %-15s %-15s %-20s\n', 'Gain(dB)', 'NF(dB)', 'Sys NF(dB)', 'MDS(dBm)', 'Improvement(dB)');
fprintf('------------------------------------------------------------------------\n');

for LNA_gain_dB = LNA_gain_range_dB
    for LNA_NF_dB = LNA_NF_range_dB
        
        % Cascaded NF through LNA → Passive losses (Friis equation)
        % NF_total = NF1 + (NF2-1)/G1 + (NF3-1)/(G1*G2) + ...
        
        % Convert to linear
        F_LNA = 10^(LNA_NF_dB/10);
        G_LNA = 10^(LNA_gain_dB/10);
        L_passive = 10^(total_passive_loss_dB/10);  % Loss as linear value
        G_passive = 1/L_passive;  % Gain of passive (< 1)
        F_passive = L_passive;    % NF = Loss for passive components
        
        % Cascaded NF through LNA → Passive (standard Friis)
        F_RF_chain = F_LNA + (F_passive - 1)/G_LNA;
        
        % Now compare RF chain noise to ADC noise at ADC input
        % Noise at ADC input from RF chain (dBm/Hz)
        RF_noise_at_ADC_dBm_Hz = thermal_noise_dBm_Hz + 10*log10(F_RF_chain) + LNA_gain_dB - total_passive_loss_dB;
        
        % ADC input noise (dBm/Hz)
        ADC_noise_dBm_Hz = ADC_NSD_dBm_Hz;
        
        % Total noise at ADC input (RSS - root sum square)
        total_noise_at_ADC_dBm_Hz = 10*log10(10^(RF_noise_at_ADC_dBm_Hz/10) + 10^(ADC_noise_dBm_Hz/10));
        
        % Noise power at ADC in 20 MHz bandwidth
        noise_power_at_ADC_20MHz_dBm = total_noise_at_ADC_dBm_Hz + 10*log10(analysis_BW_Hz);
        
        % Signal required at ADC for detection (13 dB above noise)
        signal_required_at_ADC_dBm = noise_power_at_ADC_20MHz_dBm + detection_threshold_dB;
        
        % MDS at antenna (refer signal back through gain and losses)
        % Signal at antenna needs to be amplified by LNA and attenuated by passive to reach required level at ADC
        MDS_with_LNA_dBm = signal_required_at_ADC_dBm - LNA_gain_dB + total_passive_loss_dB;
        
        % System NF (refer total noise back to antenna)
        total_noise_at_antenna_dBm_Hz = total_noise_at_ADC_dBm_Hz - LNA_gain_dB + total_passive_loss_dB;
        NF_total_dB = total_noise_at_antenna_dBm_Hz - thermal_noise_dBm_Hz;
        
        % System noise spectral density at antenna
        system_NSD_with_LNA_dBm_Hz = thermal_noise_dBm_Hz + NF_total_dB;
        
        % Improvement over passive-only
        improvement_dB = MDS_passive_dBm - MDS_with_LNA_dBm;
        
        % Store results
        results(result_idx).gain = LNA_gain_dB;
        results(result_idx).nf = LNA_NF_dB;
        results(result_idx).sys_nf = NF_total_dB;
        results(result_idx).mds = MDS_with_LNA_dBm;
        results(result_idx).improvement = improvement_dB;
        result_idx = result_idx + 1;
        
        fprintf('%-10.1f %-10.1f %-15.2f %-15.2f %-20.2f\n', ...
                LNA_gain_dB, LNA_NF_dB, NF_total_dB, MDS_with_LNA_dBm, improvement_dB);
    end
end

%% Find optimal LNA configuration
improvements = [results.improvement];
[max_improvement, max_idx] = max(improvements);
optimal_LNA = results(max_idx);

fprintf('\n====================================\n');
fprintf('OPTIMAL LNA CONFIGURATION\n');
fprintf('====================================\n');
fprintf('LNA Gain: %.1f dB\n', optimal_LNA.gain);
fprintf('LNA NF: %.1f dB\n', optimal_LNA.nf);
fprintf('System NF: %.2f dB\n', optimal_LNA.sys_nf);
fprintf('MDS: %.2f dBm\n', optimal_LNA.mds);
fprintf('Improvement vs Passive: %.2f dB\n\n', optimal_LNA.improvement);

%% Dynamic Range Analysis
fprintf('====================================\n');
fprintf('DYNAMIC RANGE ANALYSIS\n');
fprintf('====================================\n');

% Noise-limited dynamic range (in 20 MHz bandwidth)
noise_floor_20MHz_passive = noise_power_at_ADC_20MHz_dBm;
DR_noise_limited_passive = FS_power_dBm - noise_floor_20MHz_passive;

% SFDR-limited dynamic range
DR_SFDR_limited = ADC_SFDR_dBc;

% Effective dynamic range (limited by worse of the two)
DR_effective_passive = min(DR_noise_limited_passive, DR_SFDR_limited);

fprintf('\nPassive-Only Configuration:\n');
fprintf('  Noise floor (20 MHz): %.1f dBm\n', noise_floor_20MHz_passive);
fprintf('  Full-scale: %.1f dBm\n', FS_power_dBm);
fprintf('  Noise-limited DR: %.1f dB\n', DR_noise_limited_passive);
fprintf('  SFDR-limited DR: %.1f dB\n', DR_SFDR_limited);
fprintf('  Effective DR: %.1f dB (limited by %s)\n\n', DR_effective_passive, ...
    iif(DR_noise_limited_passive < DR_SFDR_limited, 'noise', 'SFDR'));

% For best LNA case
% Calculate from optimal LNA values
F_LNA = 10^(optimal_LNA.nf/10);
G_LNA = 10^(optimal_LNA.gain/10);
L_passive = 10^(total_passive_loss_dB/10);
F_passive = L_passive;
F_RF_chain = F_LNA + (F_passive - 1)/G_LNA;

RF_noise_at_ADC_dBm_Hz = thermal_noise_dBm_Hz + 10*log10(F_RF_chain) + optimal_LNA.gain - total_passive_loss_dB;
total_noise_at_ADC_dBm_Hz = 10*log10(10^(RF_noise_at_ADC_dBm_Hz/10) + 10^(ADC_NSD_dBm_Hz/10));
noise_floor_20MHz_LNA = total_noise_at_ADC_dBm_Hz + 10*log10(analysis_BW_Hz);

DR_noise_limited_LNA = FS_power_dBm - noise_floor_20MHz_LNA;
DR_effective_LNA = min(DR_noise_limited_LNA, DR_SFDR_limited);

fprintf('Optimal LNA Configuration (Gain=%.0f dB, NF=%.1f dB):\n', optimal_LNA.gain, optimal_LNA.nf);
fprintf('  Noise floor (20 MHz): %.1f dBm\n', noise_floor_20MHz_LNA);
fprintf('  Full-scale: %.1f dBm\n', FS_power_dBm);
fprintf('  Noise-limited DR: %.1f dB\n', DR_noise_limited_LNA);
fprintf('  SFDR-limited DR: %.1f dB\n', DR_SFDR_limited);
fprintf('  Effective DR: %.1f dB (limited by %s)\n\n', DR_effective_LNA, ...
    iif(DR_noise_limited_LNA < DR_SFDR_limited, 'noise', 'SFDR'));

fprintf('Note: Dynamic range analysis assumes:\n');
fprintf('  - Single-tone input for SFDR measurement\n');
fprintf('  - 20 MHz analysis bandwidth\n');
fprintf('  - Strong signals limited by SFDR (%.0f dBc)\n', ADC_SFDR_dBc);
fprintf('  - Weak signals limited by noise floor\n\n');

%% Visualization
figure('Position', [100, 100, 1200, 800]);

% Plot 1: MDS vs LNA Gain for different NF values
subplot(2,2,1);
hold on; grid on;
for LNA_NF_dB = LNA_NF_range_dB
    idx = find([results.nf] == LNA_NF_dB);
    gains = [results(idx).gain];
    mds_vals = [results(idx).mds];
    plot(gains, mds_vals, '-o', 'LineWidth', 2, 'DisplayName', sprintf('NF = %.1f dB', LNA_NF_dB));
end
yline(MDS_passive_dBm, 'r--', 'LineWidth', 2, 'DisplayName', 'Passive Only');
xlabel('LNA Gain (dB)');
ylabel('MDS (dBm)');
title('Minimum Detectable Signal vs LNA Gain');
legend('Location', 'best');
ylim([min([results.mds])-2, MDS_passive_dBm+2]);

% Plot 2: System NF vs LNA Gain
subplot(2,2,2);
hold on; grid on;
for LNA_NF_dB = LNA_NF_range_dB
    idx = find([results.nf] == LNA_NF_dB);
    gains = [results(idx).gain];
    sys_nf_vals = [results(idx).sys_nf];
    plot(gains, sys_nf_vals, '-o', 'LineWidth', 2, 'DisplayName', sprintf('NF = %.1f dB', LNA_NF_dB));
end
yline(NF_passive_system_dB, 'r--', 'LineWidth', 2, 'DisplayName', 'Passive Only');
xlabel('LNA Gain (dB)');
ylabel('System NF (dB)');
title('System Noise Figure vs LNA Gain');
legend('Location', 'best');

% Plot 3: Improvement over Passive
subplot(2,2,3);
hold on; grid on;
for LNA_NF_dB = LNA_NF_range_dB
    idx = find([results.nf] == LNA_NF_dB);
    gains = [results(idx).gain];
    improvements = [results(idx).improvement];
    plot(gains, improvements, '-o', 'LineWidth', 2, 'DisplayName', sprintf('NF = %.1f dB', LNA_NF_dB));
end
yline(0, 'r--', 'LineWidth', 2);
xlabel('LNA Gain (dB)');
ylabel('Sensitivity Improvement (dB)');
title('Improvement Over Passive-Only Configuration');
legend('Location', 'best');
grid on;

% Plot 4: 2D heatmap of improvement
subplot(2,2,4);
gain_vals = unique([results.gain]);
nf_vals = unique([results.nf]);
improvement_matrix = zeros(length(nf_vals), length(gain_vals));
for i = 1:length(nf_vals)
    for j = 1:length(gain_vals)
        idx = find([results.nf] == nf_vals(i) & [results.gain] == gain_vals(j));
        improvement_matrix(i,j) = results(idx).improvement;
    end
end
imagesc(gain_vals, nf_vals, improvement_matrix);
colorbar;
xlabel('LNA Gain (dB)');
ylabel('LNA NF (dB)');
title('Sensitivity Improvement Heatmap (dB)');
set(gca, 'YDir', 'normal');
colormap(jet);

sgtitle('ADC Receiver Sensitivity Analysis', 'FontSize', 14, 'FontWeight', 'bold');

%% Summary Table
fprintf('====================================\n');
fprintf('SUMMARY\n');
fprintf('====================================\n');
fprintf('Passive-Only MDS: %.2f dBm\n', MDS_passive_dBm);
fprintf('Best LNA Config MDS: %.2f dBm\n', optimal_LNA.mds);
fprintf('Maximum Improvement: %.2f dB\n\n', max_improvement);

if max_improvement > 3
    fprintf('RECOMMENDATION: Adding an LNA improves sensitivity significantly.\n');
    fprintf('Suggested LNA: Gain = %.1f dB, NF ≤ %.1f dB\n', optimal_LNA.gain, optimal_LNA.nf);
elseif max_improvement > 0
    fprintf('RECOMMENDATION: LNA provides modest improvement (%.1f dB).\n', max_improvement);
    fprintf('Consider cost/complexity trade-offs.\n');
else
    fprintf('RECOMMENDATION: Passive-only configuration is optimal.\n');
    fprintf('The high processing gain from channelization makes LNA unnecessary.\n');
end

fprintf('\nNote: This analysis assumes:\n');
fprintf('- 50 ohm system impedance\n');
fprintf('- Noise calculated in %.1f MHz bandwidth (post-channelization)\n', analysis_BW_MHz);
fprintf('- %.1f dB SNR detection threshold\n', detection_threshold_dB);
fprintf('- Operating up to 18 GHz (component specs should be verified at frequency)\n');
fprintf('- ADC noise floor is the limiting factor without sufficient RF gain\n');

% Helper function for inline conditional
function result = iif(condition, true_val, false_val)
    if condition
        result = true_val;
    else
        result = false_val;
    end
end
