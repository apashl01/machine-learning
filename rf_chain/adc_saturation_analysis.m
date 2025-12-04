% ADC Saturation and Damage Analysis
% Analyzes received power vs distance for various EIRP levels
% Identifies safe operating distances to avoid LNA compression and ADC damage

clear all; close all; clc;

%% System Parameters
% Receiver specifications
RX_antenna_gain_dBi = 2;          % RX antenna gain
frequency_GHz = 5;                % Operating frequency for path loss calc
frequency_Hz = frequency_GHz * 1e9;

% LNA specifications
LNA_gain_dB = 30;                 % LNA gain
LNA_P1dB_dBm = 25;                % LNA 1dB compression point

% Passive losses (same as sensitivity analysis)
cable_loss_dB = 3.0;
coupler_loss_dB = 0.5;
switch_loss_dB = 1.0;
filter_loss_dB = 0.8;
total_passive_loss_dB = cable_loss_dB + coupler_loss_dB + switch_loss_dB + filter_loss_dB;

% ADC specifications
ADC_fullscale_dBm = 0.2;          % Full-scale input power
ADC_max_dBm = 12;                 % Maximum input before damage

% Distance range
distance_miles = linspace(1, 50, 500);
distance_m = distance_miles * 1609.34;  % Convert to meters

% EIRP values to analyze (dBm)
% Range includes commercial (20-50 dBm) to high-power military (80-110 dBm)
EIRP_values_dBm = [20, 40, 60, 80, 90, 100, 110];

% Safe zone plot configuration
EIRP_for_safe_zone_plot_dBm = 110;  % EIRP to use for safe operating zone visualization
attenuator_calc_distance_miles = 1; % Distance for attenuator calculation (typically closest approach)

% Speed of light
c = 3e8;  % m/s

fprintf('=== ADC Saturation and Damage Analysis ===\n\n');
fprintf('Receiver Configuration:\n');
fprintf('  RX Antenna Gain: %.1f dBi\n', RX_antenna_gain_dBi);
fprintf('  LNA Gain: %.1f dB\n', LNA_gain_dB);
fprintf('  LNA P1dB: %.1f dBm\n', LNA_P1dB_dBm);
fprintf('  Passive Losses: %.1f dB\n', total_passive_loss_dB);
fprintf('  ADC Full-Scale: %.1f dBm\n', ADC_fullscale_dBm);
fprintf('  ADC Max (Damage): %.1f dBm\n\n', ADC_max_dBm);
fprintf('Path Loss Calculation:\n');
fprintf('  Frequency: %.1f GHz\n', frequency_GHz);
fprintf('  Distance Range: %.0f - %.0f miles\n\n', min(distance_miles), max(distance_miles));

%% Calculate Path Loss (Free Space Path Loss - Friis)
% FSPL (dB) = 20*log10(d) + 20*log10(f) + 20*log10(4*pi/c)
% where d is in meters, f is in Hz

wavelength_m = c / frequency_Hz;
FSPL_dB = 20*log10(distance_m) + 20*log10(frequency_Hz) + 20*log10(4*pi/c);

%% Calculate Power Levels at Each Stage
% Storage for results
power_at_antenna = zeros(length(EIRP_values_dBm), length(distance_m));
power_at_LNA_input = zeros(length(EIRP_values_dBm), length(distance_m));
power_at_LNA_output = zeros(length(EIRP_values_dBm), length(distance_m));
power_at_ADC = zeros(length(EIRP_values_dBm), length(distance_m));

% Calculate for each EIRP
for i = 1:length(EIRP_values_dBm)
    EIRP_dBm = EIRP_values_dBm(i);
    
    % Received power at antenna
    % P_RX = EIRP - FSPL + G_RX
    power_at_antenna(i,:) = EIRP_dBm - FSPL_dB + RX_antenna_gain_dBi;
    
    % Power at LNA input (same as antenna in this model)
    power_at_LNA_input(i,:) = power_at_antenna(i,:);
    
    % Power at LNA output (add gain, but check for compression)
    % For simplicity, assume linear operation below P1dB
    power_at_LNA_output(i,:) = power_at_LNA_input(i,:) + LNA_gain_dB;
    
    % Power at ADC input (subtract passive losses)
    power_at_ADC(i,:) = power_at_LNA_output(i,:) - total_passive_loss_dB;
end

%% Find Critical Distances
fprintf('=== Critical Distances ===\n\n');
fprintf('%-12s %-20s %-20s %-20s %-20s\n', 'EIRP (dBm)', 'LNA Compression', 'ADC Saturation', 'ADC Damage', 'Status');
fprintf('%-12s %-20s %-20s %-20s %-20s\n', '', '(miles)', '(miles)', '(miles)', '');
fprintf('----------------------------------------------------------------------------------------------------\n');

for i = 1:length(EIRP_values_dBm)
    EIRP_dBm = EIRP_values_dBm(i);
    
    % Find distance where LNA output reaches P1dB
    idx_lna_comp = find(power_at_LNA_output(i,:) >= LNA_P1dB_dBm, 1, 'last');
    if ~isempty(idx_lna_comp)
        dist_lna_comp = distance_miles(idx_lna_comp);
    else
        dist_lna_comp = NaN;
    end
    
    % Find distance where ADC reaches full-scale
    idx_adc_fs = find(power_at_ADC(i,:) >= ADC_fullscale_dBm, 1, 'last');
    if ~isempty(idx_adc_fs)
        dist_adc_fs = distance_miles(idx_adc_fs);
    else
        dist_adc_fs = NaN;
    end
    
    % Find distance where ADC reaches damage level
    idx_adc_damage = find(power_at_ADC(i,:) >= ADC_max_dBm, 1, 'last');
    if ~isempty(idx_adc_damage)
        dist_adc_damage = distance_miles(idx_adc_damage);
    else
        dist_adc_damage = NaN;
    end
    
    % Determine status
    if isnan(dist_adc_damage)
        status = 'SAFE';
    elseif dist_adc_damage >= 50
        status = 'CAUTION';
    else
        status = 'DANGER';
    end
    
    fprintf('%-12.0f %-20s %-20s %-20s %-20s\n', ...
        EIRP_dBm, ...
        sprintf('%.2f', dist_lna_comp), ...
        sprintf('%.2f', dist_adc_fs), ...
        sprintf('%.2f', dist_adc_damage), ...
        status);
end

fprintf('\n');
fprintf('Notes:\n');
fprintf('  - LNA Compression: Distance below which LNA output exceeds +%.0f dBm\n', LNA_P1dB_dBm);
fprintf('  - ADC Saturation: Distance below which ADC input exceeds %.1f dBm (clipping)\n', ADC_fullscale_dBm);
fprintf('  - ADC Damage: Distance below which ADC input exceeds %.0f dBm (potential damage)\n', ADC_max_dBm);
fprintf('  - SAFE: No damage risk within 50 miles\n');
fprintf('  - CAUTION: Saturation possible but no damage within 50 miles\n');
fprintf('  - DANGER: Potential ADC damage within 50 miles\n\n');

%% Visualization
figure('Position', [100, 100, 1400, 900]);

% Plot 1: Power at ADC vs Distance
subplot(2,2,1);
hold on; grid on;
for i = 1:length(EIRP_values_dBm)
    plot(distance_miles, power_at_ADC(i,:), 'LineWidth', 2, ...
        'DisplayName', sprintf('EIRP = %d dBm', EIRP_values_dBm(i)));
end
yline(ADC_fullscale_dBm, 'r--', 'LineWidth', 2, 'DisplayName', 'ADC Full-Scale');
yline(ADC_max_dBm, 'r-', 'LineWidth', 3, 'DisplayName', 'ADC Damage Level');
xlabel('Distance (miles)');
ylabel('Power at ADC Input (dBm)');
title('Power at ADC Input vs Distance');
legend('Location', 'northeast');
ylim([min(power_at_ADC(:))-5, max(power_at_ADC(:))+10]);
xlim([1, 50]);

% Plot 2: Power at LNA Output vs Distance
subplot(2,2,2);
hold on; grid on;
for i = 1:length(EIRP_values_dBm)
    plot(distance_miles, power_at_LNA_output(i,:), 'LineWidth', 2, ...
        'DisplayName', sprintf('EIRP = %d dBm', EIRP_values_dBm(i)));
end
yline(LNA_P1dB_dBm, 'r--', 'LineWidth', 2, 'DisplayName', 'LNA P1dB');
xlabel('Distance (miles)');
ylabel('Power at LNA Output (dBm)');
title('Power at LNA Output vs Distance');
legend('Location', 'northeast');
ylim([min(power_at_LNA_output(:))-5, max(LNA_P1dB_dBm+5, max(power_at_LNA_output(:))+5)]);
xlim([1, 50]);

% Plot 3: Power at Antenna vs Distance
subplot(2,2,3);
hold on; grid on;
for i = 1:length(EIRP_values_dBm)
    plot(distance_miles, power_at_antenna(i,:), 'LineWidth', 2, ...
        'DisplayName', sprintf('EIRP = %d dBm', EIRP_values_dBm(i)));
end
xlabel('Distance (miles)');
ylabel('Power at RX Antenna (dBm)');
title('Received Power at Antenna vs Distance');
legend('Location', 'northeast');
xlim([1, 50]);
grid on;

% Plot 4: Safe Operating Zones
subplot(2,2,4);
hold on; grid on;

% Find index for the user-specified EIRP for safe zone plot
[~, example_idx] = min(abs(EIRP_values_dBm - EIRP_for_safe_zone_plot_dBm));
EIRP_example = EIRP_values_dBm(example_idx);

% If exact match not found, warn user but continue with closest value
if EIRP_example ~= EIRP_for_safe_zone_plot_dBm
    warning('EIRP_for_safe_zone_plot_dBm (%.0f dBm) not in analyzed array. Using closest: %.0f dBm', ...
        EIRP_for_safe_zone_plot_dBm, EIRP_example);
end

% Find the critical distances for this EIRP
idx_damage = find(power_at_ADC(example_idx,:) >= ADC_max_dBm, 1, 'last');
idx_fs = find(power_at_ADC(example_idx,:) >= ADC_fullscale_dBm, 1, 'last');

% Determine y-axis limits for zone filling
y_min = min(power_at_ADC(example_idx,:)) - 5;
y_max = max([ADC_max_dBm + 10, max(power_at_ADC(example_idx,:)) + 5]);

if ~isempty(idx_damage)
    % Danger zone (red)
    fill([1, distance_miles(idx_damage), distance_miles(idx_damage), 1], ...
         [y_min, y_min, y_max, y_max], 'r', 'FaceAlpha', 0.3, ...
         'EdgeColor', 'none', 'DisplayName', 'Damage Risk');
end

if ~isempty(idx_fs)
    % Saturation zone (yellow)
    start_dist = 1;
    if ~isempty(idx_damage)
        start_dist = distance_miles(idx_damage);
    end
    fill([start_dist, distance_miles(idx_fs), distance_miles(idx_fs), start_dist], ...
         [y_min, y_min, y_max, y_max], 'y', 'FaceAlpha', 0.3, ...
         'EdgeColor', 'none', 'DisplayName', 'Saturation Zone');
end

% Safe zone (green)
safe_start = 1;
if ~isempty(idx_fs)
    safe_start = distance_miles(idx_fs);
end
fill([safe_start, 50, 50, safe_start], ...
     [y_min, y_min, y_max, y_max], 'g', 'FaceAlpha', 0.2, ...
     'EdgeColor', 'none', 'DisplayName', 'Safe Operation');

% Plot power curve on top
plot(distance_miles, power_at_ADC(example_idx,:), 'b-', 'LineWidth', 3, ...
    'DisplayName', sprintf('Power at ADC (EIRP=%d dBm)', EIRP_example));
yline(ADC_fullscale_dBm, 'r--', 'LineWidth', 2, 'DisplayName', 'Full-Scale');
yline(ADC_max_dBm, 'r-', 'LineWidth', 2, 'DisplayName', 'Damage Level');

% Calculate required attenuator at user-specified distance
[~, dist_idx] = min(abs(distance_miles - attenuator_calc_distance_miles));
actual_calc_distance = distance_miles(dist_idx);
power_at_calc_distance = power_at_ADC(example_idx, dist_idx);
% Target: 3 dB below full-scale for safety margin
target_power = ADC_fullscale_dBm - 3;
required_attenuation = power_at_calc_distance - target_power;

% Add attenuator recommendation if needed
if required_attenuation > 0
    % Plot the attenuated power curve
    attenuated_power = power_at_ADC(example_idx,:) - required_attenuation;
    plot(distance_miles, attenuated_power, 'g--', 'LineWidth', 2, ...
        'DisplayName', sprintf('With %.0f dB Attenuator', required_attenuation));
    
    % Add text annotation
    text_x = 25;  % Middle of distance range
    text_y = (max(power_at_ADC(example_idx,:)) + ADC_max_dBm) / 2;
    text(text_x, text_y, sprintf('Required Attenuator:\n%.0f dB\n(at %.1f miles)', required_attenuation, actual_calc_distance), ...
        'FontSize', 12, 'FontWeight', 'bold', 'BackgroundColor', 'white', ...
        'EdgeColor', 'black', 'HorizontalAlignment', 'center');
end

xlabel('Distance (miles)');
ylabel('Power (dBm)');
title(sprintf('Safe Operating Zones (EIRP = %d dBm)', EIRP_example));
legend('Location', 'northeast');
xlim([1, 50]);
ylim([y_min, y_max]);

sgtitle('ADC Saturation and Damage Analysis', 'FontSize', 14, 'FontWeight', 'bold');

%% Additional Analysis: Minimum Safe Distance Table
fprintf('=== Minimum Safe Distances (No ADC Damage) ===\n\n');
fprintf('%-12s %-30s\n', 'EIRP (dBm)', 'Minimum Safe Distance (miles)');
fprintf('------------------------------------------------\n');

for i = 1:length(EIRP_values_dBm)
    EIRP_dBm = EIRP_values_dBm(i);
    
    % Find distance where ADC is at damage level
    idx_adc_damage = find(power_at_ADC(i,:) >= ADC_max_dBm, 1, 'last');
    if ~isempty(idx_adc_damage)
        min_safe_dist = distance_miles(idx_adc_damage);
        fprintf('%-12.0f %-30.2f\n', EIRP_dBm, min_safe_dist);
    else
        fprintf('%-12.0f %-30s\n', EIRP_dBm, 'SAFE at all distances');
    end
end

fprintf('\n=== Recommendations ===\n');
fprintf('1. For high-power transmitters (EIRP > 50 dBm), maintain separation\n');
fprintf('2. Consider adding a limiter or attenuator before the LNA for near-field operation\n');
fprintf('3. Monitor LNA compression - degrades receiver performance even before ADC damage\n');
fprintf('4. If operating with variable transmit powers, ensure adequate spacing at max power\n\n');

fprintf('=== Attenuator Requirements for Analysis EIRP (%d dBm) ===\n', EIRP_example);
[~, dist_idx_print] = min(abs(distance_miles - attenuator_calc_distance_miles));
power_at_calc_dist = power_at_ADC(example_idx, dist_idx_print);
target_power_safe = ADC_fullscale_dBm - 3;  % 3 dB safety margin below full-scale
required_atten = power_at_calc_dist - target_power_safe;

if required_atten > 0
    fprintf('Power at ADC (%.1f miles): %.1f dBm\n', distance_miles(dist_idx_print), power_at_calc_dist);
    fprintf('Target safe power: %.1f dBm (3 dB below full-scale)\n', target_power_safe);
    fprintf('Required attenuator: %.0f dB\n', required_atten);
    fprintf('\nWith %.0f dB attenuator, safe operation at all distances analyzed.\n', required_atten);
else
    fprintf('No attenuator needed - system is safe at all distances for this EIRP.\n');
end
