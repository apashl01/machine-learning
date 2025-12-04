%% ADC Measurement Accuracy Analysis
% Analyzes measurement accuracy for pulse descriptor words (PDW)
% based on ADC characteristics and processing methods
% MATLAB R2024a

clear; close all; clc;

%% ADC and System Parameters
fprintf('=== ADC MEASUREMENT ACCURACY ANALYSIS ===\n\n');

% ADC Specifications
analysis_bw_MHz = 20;           % Analysis bandwidth after channelization (MHz)
effective_fs_MSPS = 50;         % Effective sample rate at analysis stage (MSPS)
                                % (Typically 2-2.5x the analysis bandwidth)
enob = 8;                       % Effective number of bits
sfdr_dB = 55;                   % Spurious-free dynamic range (dBc)
aperture_jitter_ps = 0.5;       % Aperture jitter (ps RMS)
clock_jitter_fs = 100;          % Clock jitter (fs RMS)
fullscale_dBm = -1.1;           % ADC full-scale input power (dBm)
adc_bits = 10;                  % Nominal ADC resolution (bits)

% Convert parameters
analysis_bw_Hz = analysis_bw_MHz * 1e6;
effective_fs_Hz = effective_fs_MSPS * 1e6;
aperture_jitter_s = aperture_jitter_ps * 1e-12;
clock_jitter_s = clock_jitter_fs * 1e-15;
fullscale_W = 10^(fullscale_dBm/10) / 1000;
fullscale_V = sqrt(fullscale_W * 50);  % Assuming 50 ohm impedance

% Signal Parameters
input_signal_dBm = -30;         % Input signal level (dBm) - adjustable
signal_freq_GHz = 10;           % Signal center frequency (GHz)
pulse_width_us = [0.1, 1, 10, 100];  % Pulse widths to analyze (μs)

% Processing Parameters
fft_lengths = [1024, 4096, 16384];      % FFT sizes
ifm_delay_ns = 1;                       % IFM delay line (ns)

fprintf('ADC PARAMETERS:\n');
fprintf('  Analysis Bandwidth: %.1f MHz\n', analysis_bw_MHz);
fprintf('  Effective Sample Rate: %.1f MSPS\n', effective_fs_MSPS);
fprintf('  ENOB: %.1f bits\n', enob);
fprintf('  SFDR: %.1f dBc\n', sfdr_dB);
fprintf('  Aperture Jitter: %.2f ps\n', aperture_jitter_ps);
fprintf('  Clock Jitter: %.1f fs\n', clock_jitter_fs);
fprintf('  Full-Scale Input: %.2f dBm\n', fullscale_dBm);
fprintf('  Signal Frequency: %.1f GHz\n\n', signal_freq_GHz);

%% Calculate SNR from ENOB and Input Level
% Ideal SNR from ENOB
snr_ideal_dB = 6.02 * enob + 1.76;

% Input signal relative to full-scale
signal_backoff_dB = fullscale_dBm - input_signal_dBm;

% Effective SNR (accounts for input level)
if signal_backoff_dB > 0
    % Signal is below full-scale (good)
    snr_effective_dB = snr_ideal_dB - signal_backoff_dB;
else
    % Signal would clip
    snr_effective_dB = 0;
    fprintf('WARNING: Input signal exceeds full-scale!\n');
end

snr_linear = 10^(snr_effective_dB/10);

fprintf('SNR ANALYSIS:\n');
fprintf('  Ideal SNR (from ENOB): %.1f dB\n', snr_ideal_dB);
fprintf('  Input Signal Level: %.1f dBm\n', input_signal_dBm);
fprintf('  Full-Scale Backoff: %.1f dB\n', signal_backoff_dB);
fprintf('  Effective SNR: %.1f dB\n\n', snr_effective_dB);

%% 1. AMPLITUDE MEASUREMENT ACCURACY

% Quantization noise
lsb_voltage = fullscale_V / (2^adc_bits);
quantization_noise_rms = lsb_voltage / sqrt(12);

% Amplitude resolution (1 LSB)
amp_resolution_dB = 20 * log10(1 + 1/(2^enob));

% Amplitude accuracy (RMS error from quantization)
amp_accuracy_dB = 20 * log10(quantization_noise_rms / fullscale_V);

% Dynamic range
dynamic_range_dB = snr_ideal_dB;

fprintf('AMPLITUDE MEASUREMENTS:\n');
fprintf('  Amplitude Resolution: %.3f dB (1 LSB)\n', amp_resolution_dB);
fprintf('  Amplitude Accuracy (RMS): %.2f dB\n', amp_accuracy_dB);
fprintf('  Dynamic Range: %.1f dB\n', dynamic_range_dB);
fprintf('  SFDR: %.1f dBc\n\n', sfdr_dB);

%% 2. TIMING MEASUREMENTS

% Time resolution (sample period)
sample_period_ns = 1e9 / effective_fs_Hz;
time_resolution_ns = sample_period_ns;

% TOA accuracy (limited by SNR and jitter)
% σ_TOA ≈ 1/(2πf × SNR) for high SNR
% For pulse: also limited by rise time and sample rate
signal_freq_Hz = signal_freq_GHz * 1e9;
toa_accuracy_snr_limited_ns = 1e9 / (2 * pi * signal_freq_Hz * sqrt(snr_linear));
toa_accuracy_jitter_limited_ns = aperture_jitter_ps / 1000;  % Convert to ns
toa_accuracy_ns = sqrt(toa_accuracy_snr_limited_ns^2 + toa_accuracy_jitter_limited_ns^2);

% Pulse width accuracy
% Limited by sample rate and SNR
pw_accuracy_ns = zeros(length(pulse_width_us), 1);
for i = 1:length(pulse_width_us)
    pw_us = pulse_width_us(i);
    pw_ns = pw_us * 1000;
    
    % Number of samples in pulse
    n_samples = pw_ns / sample_period_ns;
    
    % PW accuracy improves with more samples (averaging effect)
    % But limited by minimum of 2x sample period
    if n_samples >= 10
        pw_accuracy_ns(i) = max(2 * sample_period_ns, sample_period_ns / sqrt(snr_linear));
    else
        pw_accuracy_ns(i) = 2 * sample_period_ns;  % Limited by sample rate
    end
end

% PRI accuracy (for repetitive pulses)
% Essentially TOA accuracy for each pulse
pri_accuracy_ns = toa_accuracy_ns;

fprintf('TIMING MEASUREMENTS:\n');
fprintf('  Time Resolution: %.2f ns (sample period)\n', time_resolution_ns);
fprintf('  TOA Accuracy: %.3f ns (RMS)\n', toa_accuracy_ns);
fprintf('    - SNR-limited: %.3f ns\n', toa_accuracy_snr_limited_ns);
fprintf('    - Jitter-limited: %.3f ns\n', toa_accuracy_jitter_limited_ns);
fprintf('  PRI Accuracy: %.3f ns (RMS)\n', pri_accuracy_ns);
fprintf('  Pulse Width Accuracy:\n');
for i = 1:length(pulse_width_us)
    fprintf('    - PW = %.1f μs: %.2f ns (RMS)\n', pulse_width_us(i), pw_accuracy_ns(i));
end
fprintf('\n');

%% 3. FREQUENCY MEASUREMENT ACCURACY

fprintf('FREQUENCY MEASUREMENTS:\n\n');

% Method 1: FFT-Based
fprintf('METHOD 1: FFT-BASED FREQUENCY MEASUREMENT\n');
freq_fft_accuracy_Hz = zeros(length(fft_lengths), length(pulse_width_us));
freq_fft_resolution_Hz = zeros(length(fft_lengths), 1);

for i = 1:length(fft_lengths)
    N_fft = fft_lengths(i);
    
    % Frequency resolution (bin spacing)
    freq_fft_resolution_Hz(i) = effective_fs_Hz / N_fft;
    
    % Processing time required
    fft_time_us = N_fft / effective_fs_Hz * 1e6;
    
    fprintf('  FFT Length = %d:\n', N_fft);
    fprintf('    Frequency Resolution: %.2f Hz\n', freq_fft_resolution_Hz(i));
    fprintf('    Processing Time Required: %.2f μs\n', fft_time_us);
    
    for j = 1:length(pulse_width_us)
        pw_us = pulse_width_us(j);
        
        if pw_us >= fft_time_us
            % Pulse long enough for this FFT
            % Accuracy improves with SNR (interpolation between bins)
            freq_fft_accuracy_Hz(i,j) = freq_fft_resolution_Hz(i) / (2 * sqrt(snr_linear));
            fprintf('    PW = %.1f μs: Accuracy = %.2f Hz\n', pw_us, freq_fft_accuracy_Hz(i,j));
        else
            % Pulse too short for this FFT length
            freq_fft_accuracy_Hz(i,j) = NaN;
            fprintf('    PW = %.1f μs: Pulse too short\n', pw_us);
        end
    end
    fprintf('\n');
end

% Method 2: IFM / Delay-Line Discriminator
fprintf('METHOD 2: IFM / DELAY-LINE DISCRIMINATOR\n');
ifm_delay_s = ifm_delay_ns * 1e-9;

% Frequency range (unambiguous)
freq_ifm_range_MHz = 1 / (2 * ifm_delay_s) / 1e6;

% Frequency accuracy
% Δf ≈ 1 / (2π × τ × SNR)
freq_ifm_accuracy_Hz = 1 / (2 * pi * ifm_delay_s * sqrt(snr_linear));

% Phase noise contribution from clock jitter
phase_noise_rad = 2 * pi * signal_freq_Hz * clock_jitter_s;
freq_ifm_jitter_Hz = phase_noise_rad * signal_freq_Hz / (2 * pi);

% Total IFM accuracy
freq_ifm_total_Hz = sqrt(freq_ifm_accuracy_Hz^2 + freq_ifm_jitter_Hz^2);

fprintf('  Delay Line: %.1f ns\n', ifm_delay_ns);
fprintf('  Unambiguous Frequency Range: ±%.1f MHz\n', freq_ifm_range_MHz);
fprintf('  Frequency Accuracy: %.1f Hz (RMS)\n', freq_ifm_total_Hz);
fprintf('    - SNR-limited: %.1f Hz\n', freq_ifm_accuracy_Hz);
fprintf('    - Jitter-limited: %.1f Hz\n', freq_ifm_jitter_Hz);
fprintf('  Latency: ~%.1f ns (near-instantaneous)\n', ifm_delay_ns * 2);
fprintf('  Works for ALL pulse widths (>%.1f ns)\n\n', ifm_delay_ns * 10);

%% 4. PHASE MEASUREMENT ACCURACY (Critical for Interferometer)

% Phase noise from multiple sources
phase_noise_quantization_rad = 1 / (2^enob * sqrt(6));  % From ADC quantization
phase_noise_thermal_rad = 1 / sqrt(2 * snr_linear);     % From thermal noise
phase_noise_jitter_rad = 2 * pi * signal_freq_Hz * aperture_jitter_s;  % From aperture jitter

% Total phase accuracy (RMS)
phase_accuracy_rad = sqrt(phase_noise_quantization_rad^2 + ...
                         phase_noise_thermal_rad^2 + ...
                         phase_noise_jitter_rad^2);
phase_accuracy_deg = rad2deg(phase_accuracy_rad);

% AOA accuracy (for interferometer)
% Assuming baseline distance d and wavelength λ
% Typical baseline might be 0.5-2 wavelengths
lambda_m = 3e8 / signal_freq_Hz;
baseline_wavelengths = 1.0;  % Typical for interferometer
baseline_m = baseline_wavelengths * lambda_m;

% AOA error: Δθ ≈ λ/(2πd) × Δφ
aoa_accuracy_rad = (lambda_m / (2 * pi * baseline_m)) * phase_accuracy_rad;
aoa_accuracy_deg = rad2deg(aoa_accuracy_rad);

fprintf('PHASE MEASUREMENTS (for Interferometer):\n');
fprintf('  Phase Accuracy: %.3f degrees (RMS)\n', phase_accuracy_deg);
fprintf('    - Quantization noise: %.3f deg\n', rad2deg(phase_noise_quantization_rad));
fprintf('    - Thermal noise (SNR): %.3f deg\n', rad2deg(phase_noise_thermal_rad));
fprintf('    - Aperture jitter: %.3f deg\n', rad2deg(phase_noise_jitter_rad));
fprintf('  \n');
fprintf('  AOA Accuracy (%.1f λ baseline):\n', baseline_wavelengths);
fprintf('    Angle Accuracy: %.2f degrees (RMS)\n', aoa_accuracy_deg);
fprintf('    Baseline: %.3f m\n', baseline_m);
fprintf('    Wavelength: %.3f m (%.1f GHz)\n\n', lambda_m, signal_freq_GHz);

%% 5. COMPARISON TABLE

fprintf('=== MEASUREMENT ACCURACY SUMMARY ===\n\n');
fprintf('%-30s %20s\n', 'Parameter', 'Accuracy (RMS)');
fprintf('%s\n', repmat('-', 1, 52));
fprintf('%-30s %20.3f dB\n', 'Amplitude', amp_accuracy_dB);
fprintf('%-30s %20.2f ns\n', 'Time of Arrival (TOA)', toa_accuracy_ns);
fprintf('%-30s %20.2f ns\n', 'Pulse Width (0.1 μs pulse)', pw_accuracy_ns(1));
fprintf('%-30s %20.2f ns\n', 'Pulse Width (10 μs pulse)', pw_accuracy_ns(3));
fprintf('%-30s %20.2f ns\n', 'Pulse Repetition Interval', pri_accuracy_ns);
fprintf('%-30s %20.1f Hz\n', 'Frequency (IFM method)', freq_ifm_total_Hz);
fprintf('%-30s %20.1f Hz\n', 'Frequency (FFT, N=4096)', freq_fft_accuracy_Hz(2,3));
fprintf('%-30s %20.3f deg\n', 'Phase', phase_accuracy_deg);
fprintf('%-30s %20.2f deg\n', 'Angle of Arrival', aoa_accuracy_deg);
fprintf('\n');

%% Visualization

figure('Position', [100 100 1400 900], 'Color', 'w');

% Plot 1: SNR vs Input Level
subplot(3,3,1)
input_levels_dBm = -60:1:fullscale_dBm;
snr_vs_input = zeros(size(input_levels_dBm));
for i = 1:length(input_levels_dBm)
    backoff = fullscale_dBm - input_levels_dBm(i);
    if backoff > 0
        snr_vs_input(i) = snr_ideal_dB - backoff;
    else
        snr_vs_input(i) = snr_ideal_dB;  % Clipped
    end
    snr_vs_input(i) = max(0, snr_vs_input(i));
end
plot(input_levels_dBm, snr_vs_input, 'b-', 'LineWidth', 2);
hold on;
plot(input_signal_dBm, snr_effective_dB, 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
xlabel('Input Signal Level (dBm)', 'FontSize', 10);
ylabel('SNR (dB)', 'FontSize', 10);
title('SNR vs Input Level', 'FontSize', 11, 'FontWeight', 'bold');
grid on;
legend('SNR Curve', 'Operating Point', 'Location', 'northwest');

% Plot 2: TOA Accuracy vs SNR
subplot(3,3,2)
snr_sweep_dB = 0:1:60;
snr_sweep_linear = 10.^(snr_sweep_dB/10);
toa_vs_snr = 1e9 ./ (2 * pi * signal_freq_Hz * sqrt(snr_sweep_linear));
plot(snr_sweep_dB, toa_vs_snr, 'b-', 'LineWidth', 2);
hold on;
yline(toa_accuracy_jitter_limited_ns, 'r--', 'LineWidth', 1.5, 'Label', 'Jitter Floor');
plot(snr_effective_dB, toa_accuracy_snr_limited_ns, 'go', 'MarkerSize', 10, 'MarkerFaceColor', 'g');
xlabel('SNR (dB)', 'FontSize', 10);
ylabel('TOA Accuracy (ns)', 'FontSize', 10);
title('TOA Accuracy vs SNR', 'FontSize', 11, 'FontWeight', 'bold');
grid on;
set(gca, 'YScale', 'log');
legend('SNR-Limited', 'Jitter Floor', 'Operating Point', 'Location', 'northeast');

% Plot 3: Pulse Width Accuracy
subplot(3,3,3)
barh(pw_accuracy_ns, 'FaceColor', [0.4 0.6 0.8]);
set(gca, 'YTick', 1:length(pulse_width_us), 'YTickLabel', arrayfun(@(x) sprintf('%.1f μs', x), pulse_width_us, 'UniformOutput', false));
xlabel('PW Accuracy (ns)', 'FontSize', 10);
ylabel('Pulse Width', 'FontSize', 10);
title('Pulse Width Measurement Accuracy', 'FontSize', 11, 'FontWeight', 'bold');
grid on;

% Plot 4: FFT Frequency Resolution vs FFT Length
subplot(3,3,4)
semilogx(fft_lengths, freq_fft_resolution_Hz, 'bo-', 'LineWidth', 2, 'MarkerSize', 8, 'MarkerFaceColor', 'b');
xlabel('FFT Length', 'FontSize', 10);
ylabel('Frequency Resolution (Hz)', 'FontSize', 10);
title('FFT Frequency Resolution', 'FontSize', 11, 'FontWeight', 'bold');
grid on;

% Plot 5: Frequency Accuracy - FFT vs IFM
subplot(3,3,5)
pw_valid = pulse_width_us(~isnan(freq_fft_accuracy_Hz(2,:)));
fft_valid = freq_fft_accuracy_Hz(2,~isnan(freq_fft_accuracy_Hz(2,:)));
semilogx(pw_valid, fft_valid, 'b^-', 'LineWidth', 2, 'MarkerSize', 8, 'DisplayName', 'FFT (N=4096)');
hold on;
semilogx(pulse_width_us, ones(size(pulse_width_us)) * freq_ifm_total_Hz, 'ro-', 'LineWidth', 2, 'MarkerSize', 8, 'DisplayName', 'IFM');
xlabel('Pulse Width (μs)', 'FontSize', 10);
ylabel('Frequency Accuracy (Hz)', 'FontSize', 10);
title('Frequency Measurement: FFT vs IFM', 'FontSize', 11, 'FontWeight', 'bold');
legend('Location', 'best');
grid on;
set(gca, 'YScale', 'log');

% Plot 6: Phase Noise Contributors
subplot(3,3,6)
contributors = [rad2deg(phase_noise_quantization_rad); ...
                rad2deg(phase_noise_thermal_rad); ...
                rad2deg(phase_noise_jitter_rad); ...
                phase_accuracy_deg];
labels = {'Quantization', 'Thermal', 'Jitter', 'Total (RSS)'};
bar(contributors, 'FaceColor', [0.6 0.4 0.8]);
set(gca, 'XTickLabel', labels);
ylabel('Phase Error (degrees RMS)', 'FontSize', 10);
title('Phase Noise Contributors', 'FontSize', 11, 'FontWeight', 'bold');
grid on;
xtickangle(45);

% Plot 7: AOA Accuracy vs Baseline
subplot(3,3,7)
baseline_sweep = 0.25:0.25:3;  % Wavelengths
aoa_vs_baseline = (lambda_m ./ (2 * pi * baseline_sweep * lambda_m)) * phase_accuracy_rad;
plot(baseline_sweep, rad2deg(aoa_vs_baseline), 'b-', 'LineWidth', 2);
hold on;
plot(baseline_wavelengths, aoa_accuracy_deg, 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
xlabel('Baseline (wavelengths)', 'FontSize', 10);
ylabel('AOA Accuracy (degrees)', 'FontSize', 10);
title('AOA Accuracy vs Interferometer Baseline', 'FontSize', 11, 'FontWeight', 'bold');
grid on;
legend('AOA vs Baseline', 'Current System', 'Location', 'northeast');

% Plot 8: Dynamic Range Visualization
subplot(3,3,8)
axis off;
summary_text = {
    'MEASUREMENT SUMMARY', ...
    '', ...
    sprintf('SNR: %.1f dB', snr_effective_dB), ...
    sprintf('ENOB: %.1f bits', enob), ...
    sprintf('SFDR: %.1f dBc', sfdr_dB), ...
    '', ...
    'KEY ACCURACIES:', ...
    sprintf('TOA: %.2f ns', toa_accuracy_ns), ...
    sprintf('Freq (IFM): %.0f Hz', freq_ifm_total_Hz), ...
    sprintf('Phase: %.2f deg', phase_accuracy_deg), ...
    sprintf('AOA: %.2f deg', aoa_accuracy_deg), ...
    '', ...
    'TRADEOFFS:', ...
    '• FFT: High accuracy, slow', ...
    '• IFM: Lower accuracy, fast', ...
    sprintf('• IFM best for PW < %.0f μs', effective_fs_Hz * 4096 / 1e6)
};
text(0.1, 0.5, summary_text, 'FontSize', 9, 'VerticalAlignment', 'middle', ...
    'FontName', 'FixedWidth', 'FontWeight', 'bold');

% Plot 9: Frequency Method Comparison Table
subplot(3,3,9)
axis off;
method_comparison = {
    'FREQUENCY METHOD COMPARISON', ...
    '', ...
    'FFT Method:', ...
    sprintf('  Resolution: %.1f - %.1f Hz', min(freq_fft_resolution_Hz), max(freq_fft_resolution_Hz)), ...
    sprintf('  Accuracy: %.1f - %.1f Hz', min(freq_fft_accuracy_Hz(2,:), [], 'omitnan'), max(freq_fft_accuracy_Hz(2,:), [], 'omitnan')), ...
    sprintf('  Latency: %.1f - %.1f μs', min(fft_lengths)/effective_fs_MSPS, max(fft_lengths)/effective_fs_MSPS), ...
    '  Needs long pulses', ...
    '', ...
    'IFM Method:', ...
    sprintf('  Accuracy: %.0f Hz', freq_ifm_total_Hz), ...
    sprintf('  Range: ±%.0f MHz', freq_ifm_range_MHz), ...
    sprintf('  Latency: ~%.0f ns', ifm_delay_ns * 2), ...
    '  Works on short pulses', ...
    '', ...
    'Recommendation:', ...
    '  Use IFM for real-time', ...
    '  Use FFT for precision'
};
text(0.1, 0.5, method_comparison, 'FontSize', 8, 'VerticalAlignment', 'middle', ...
    'FontName', 'FixedWidth');

sgtitle('ADC Measurement Accuracy Analysis', 'FontSize', 14, 'FontWeight', 'bold');

fprintf('Analysis complete. Plots generated.\n');
