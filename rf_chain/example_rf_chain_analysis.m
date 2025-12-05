%% RF Chain Analysis Example
% Demonstrates RF chain analysis with cascaded components
% Shows transmit mode with power tracking and saturation checking
%
% Author: Andrew's Analysis Tools
% Date: November 2025

clear; close all; clc;

%% Load chain configuration
chain = rf_chain_config_example();

fprintf('=== RF Chain Configuration ===\n');
fprintf('Chain Type: %s\n', chain.type);
fprintf('Chain: %s\n', chain.description);
fprintf('Frequency Range: %.1f - %.1f GHz\n', chain.freq_range_ghz(1), chain.freq_range_ghz(2));
if strcmpi(chain.type, 'transmit')
    fprintf('Source Power: %.1f dBm\n', chain.source_power_dbm);
end
fprintf('\n');

% Display components in order
comp_names = fieldnames(chain.components);
n_comp = length(comp_names);

% Sort by order
order_array = zeros(n_comp, 2);
for i = 1:n_comp
    order_array(i,1) = chain.components.(comp_names{i}).order;
    order_array(i,2) = i;
end
[~, sort_idx] = sort(order_array(:,1));

fprintf('Component Order:\n');
for i = 1:n_comp
    idx = order_array(sort_idx(i), 2);
    comp = chain.components.(comp_names{idx});
    fprintf('  %d. %s (%s)\n', comp.order, comp.name, comp.type);
end
fprintf('\n');

%% Analyze chain
results = analyze_rf_chain(chain);

%% Display mid-frequency results
fprintf('=== Performance at Mid-Frequency (%.2f GHz) ===\n', results.mid_freq_summary.frequency_ghz);
if results.has_power_tracking
    fprintf('Input Power: %.2f dBm\n', results.mid_freq_summary.input_power_dbm);
    fprintf('Output Power: %.2f dBm (%.4f W)\n', ...
        results.mid_freq_summary.output_power_dbm, ...
        results.mid_freq_summary.output_power_watts);
end
fprintf('Total Gain: %.2f dB\n', results.mid_freq_summary.total_gain_db);
if results.has_nf_data
    fprintf('Cascaded NF: %.2f dB\n', results.mid_freq_summary.cascaded_nf_db);
end

% RX sweep results
if results.has_rx_sweep
    fprintf('\n=== Damage Threshold Analysis ===\n');
    fprintf('Damage Level (at ADC): %.1f dBm\n', results.mid_freq_summary.damage_level_dbm);
    fprintf('Maximum Safe Input Power: %.1f dBm\n', results.mid_freq_summary.min_safe_input_power_dbm);
    fprintf('ADC Input Power @ Threshold: %.1f dBm\n', results.mid_freq_summary.adc_input_power_at_threshold_dbm);
end

% TX saturation warnings
if results.has_power_tracking && isfield(results.mid_freq_summary, 'saturated_amplifiers') && ...
   ~isempty(results.mid_freq_summary.saturated_amplifiers)
    fprintf('\n*** SATURATION WARNING ***\n');
    fprintf('The following amplifiers are saturated:\n');
    for i = 1:length(results.mid_freq_summary.saturated_amplifiers)
        fprintf('  - %s\n', results.mid_freq_summary.saturated_amplifiers{i});
    end
end

fprintf('\nComponent Contributions:\n');
contrib_names = fieldnames(results.mid_freq_summary.component_contributions);
for i = 1:length(contrib_names)
    contrib = results.mid_freq_summary.component_contributions.(contrib_names{i});
    fprintf('  %s: Gain = %.2f dB', contrib.name, contrib.gain_db);
    if isfield(contrib, 'nf_db')
        fprintf(', NF = %.2f dB', contrib.nf_db);
    end
    if results.has_power_tracking
        fprintf(', Pout = %.2f dBm (%.4f W)', contrib.output_power_dbm, contrib.output_power_watts);
        if isfield(contrib, 'saturated') && contrib.saturated
            fprintf(' [SATURATED]');
        end
    elseif results.has_rx_sweep
        fprintf(', Pout@Threshold = %.1f dBm', contrib.power_at_threshold_dbm);
    end
    fprintf('\n');
end
fprintf('\n');

%% Generate plots
figure('Position', [100, 100, 1400, 900]);

% Plot 1: Individual component gains vs frequency
subplot(2,3,1);
hold on; grid on;
colors = lines(n_comp);
for i = 1:n_comp
    plot(results.freq_ghz, results.component_gains(i,:), '-', ...
        'LineWidth', 2, 'Color', colors(i,:), 'DisplayName', results.component_names{i});
end
xlabel('Frequency (GHz)', 'Interpreter', 'none');
ylabel('Gain (dB)', 'Interpreter', 'none');
title('Individual Component Gain vs Frequency', 'Interpreter', 'none');
legend('Location', 'best', 'Interpreter', 'none');
yline(0, 'k--', 'LineWidth', 1);

% Plot 2: Cascaded total gain vs frequency
subplot(2,3,2);
hold on; grid on;
plot(results.freq_ghz, results.total_gain_db, 'b-', 'LineWidth', 2.5);
% Mark mid-frequency point
mid_idx = find(abs(results.freq_ghz - results.mid_freq_summary.frequency_ghz) < 0.1, 1);
plot(results.mid_freq_summary.frequency_ghz, results.mid_freq_summary.total_gain_db, ...
    'ro', 'MarkerSize', 10, 'LineWidth', 2, ...
    'DisplayName', sprintf('Mid-Freq: %.2f dB', results.mid_freq_summary.total_gain_db));
xlabel('Frequency (GHz)', 'Interpreter', 'none');
ylabel('Total Gain (dB)', 'Interpreter', 'none');
title('Cascaded Total Gain vs Frequency', 'Interpreter', 'none');
legend('Location', 'best', 'Interpreter', 'none');
grid on;
yline(0, 'k--', 'LineWidth', 1);

% Plot 3: TX output power OR RX damage threshold OR cascaded NF
subplot(2,3,3);
if results.has_power_tracking
    hold on; grid on;
    plot(results.freq_ghz, results.final_output_power_dbm, 'r-', 'LineWidth', 2.5, 'DisplayName', 'Output Power');
    plot(results.freq_ghz, ones(size(results.freq_ghz))*chain.source_power_dbm, 'k--', ...
        'LineWidth', 1.5, 'DisplayName', 'Source Power');
    xlabel('Frequency (GHz)', 'Interpreter', 'none');
    ylabel('Power (dBm)', 'Interpreter', 'none');
    title('Output Power vs Frequency', 'Interpreter', 'none');
    legend('Location', 'best', 'Interpreter', 'none');
    grid on;
elseif results.has_rx_sweep
    hold on; grid on;
    % Plot maximum safe input power vs frequency
    plot(results.freq_ghz, results.min_damage_threshold_dbm, 'b-', 'LineWidth', 2.5, ...
        'DisplayName', 'Max Safe Input Power');
    yline(results.damage_level_dbm, 'r--', 'LineWidth', 2, ...
        'DisplayName', sprintf('Damage Level: %.1f dBm', results.damage_level_dbm));
    xlabel('Frequency (GHz)', 'Interpreter', 'none');
    ylabel('Input Power (dBm)', 'Interpreter', 'none');
    title('Maximum Safe Input Power vs Frequency', 'Interpreter', 'none');
    legend('Location', 'best', 'Interpreter', 'none');
    grid on;
else
    if results.has_nf_data
        hold on; grid on;
        plot(results.freq_ghz, results.cascaded_nf_db, 'r-', 'LineWidth', 2.5);
        plot(results.mid_freq_summary.frequency_ghz, results.mid_freq_summary.cascaded_nf_db, ...
            'bo', 'MarkerSize', 10, 'LineWidth', 2, ...
            'DisplayName', sprintf('Mid-Freq: %.2f dB', results.mid_freq_summary.cascaded_nf_db));
        xlabel('Frequency (GHz)', 'Interpreter', 'none');
        ylabel('Cascaded NF (dB)', 'Interpreter', 'none');
        title('Cascaded Noise Figure vs Frequency', 'Interpreter', 'none');
        legend('Location', 'best', 'Interpreter', 'none');
        grid on;
    else
        text(0.5, 0.5, 'No NF data available', ...
            'HorizontalAlignment', 'center', 'VerticalAlignment', 'middle', ...
            'FontSize', 14, 'Color', 'r', 'Interpreter', 'none');
        axis off;
    end
end

% Plot 4: Cumulative gain through chain at mid-frequency
subplot(2,3,4);
cumulative_gain = cumsum(results.component_gains(:, mid_idx));
hold on; grid on;
bar(1:n_comp, cumulative_gain, 'FaceColor', [0.3 0.6 0.9]);
set(gca, 'XTick', 1:n_comp, 'XTickLabel', results.component_names, 'TickLabelInterpreter', 'none');
ylabel('Cumulative Gain (dB)', 'Interpreter', 'none');
title(sprintf('Cumulative Gain Through Chain @ %.2f GHz', results.mid_freq_summary.frequency_ghz), 'Interpreter', 'none');
xtickangle(45);
yline(0, 'k--', 'LineWidth', 1.5);
grid on;

% Add value labels on bars
for i = 1:n_comp
    text(i, cumulative_gain(i), sprintf('%.1f', cumulative_gain(i)), ...
        'HorizontalAlignment', 'center', 'VerticalAlignment', 'bottom', ...
        'FontWeight', 'bold', 'Interpreter', 'none');
end

% Plot 5: Power through each stage (TX or RX sweep)
subplot(2,3,5);
if results.has_power_tracking
    hold on; grid on;
    % TX mode: Plot power after each component at mid-frequency
    power_after_each = results.power_through_chain_dbm(:, mid_idx);
    stairs(0:n_comp, power_after_each, 'b-', 'LineWidth', 2);
    plot(0:n_comp, power_after_each, 'ro', 'MarkerSize', 8, 'LineWidth', 2);
    
    % Mark saturated amplifiers
    for i = 1:n_comp
        if results.saturation_flags(i, mid_idx)
            plot(i, power_after_each(i+1), 'rx', 'MarkerSize', 15, 'LineWidth', 3);
        end
    end
    
    set(gca, 'XTick', 0:n_comp);
    xticklabels = ['Source'; results.component_names];
    set(gca, 'XTickLabel', xticklabels, 'TickLabelInterpreter', 'none');
    xtickangle(45);
    ylabel('Power (dBm)', 'Interpreter', 'none');
    title(sprintf('Power Through Chain @ %.2f GHz', results.mid_freq_summary.frequency_ghz), 'Interpreter', 'none');
    grid on;
    
    if any(results.saturation_flags(:, mid_idx))
        legend('Power Level', 'Stage Output', 'Saturated', 'Location', 'best', 'Interpreter', 'none');
    end
    
elseif results.has_rx_sweep
    hold on; grid on;
    % RX mode: Plot power cascade at damage threshold with ADC at the end
    power_after_each = results.mid_freq_summary.power_through_chain_at_threshold;
    n_stages = length(power_after_each) - 1;  % Includes input + components + ADC
    
    stairs(0:n_stages, power_after_each, 'b-', 'LineWidth', 2, 'DisplayName', 'Power Level');
    plot(0:n_stages, power_after_each, 'ro', 'MarkerSize', 8, 'LineWidth', 2, 'DisplayName', 'Stage Output');
    
    % Mark damage at ADC input (last stage)
    adc_idx = n_stages;
    plot(adc_idx, power_after_each(end), 'rx', 'MarkerSize', 15, 'LineWidth', 3, ...
        'DisplayName', 'Damage Point');
    
    % Show damage level reference at ADC
    plot(adc_idx, results.damage_level_dbm, 'r^', 'MarkerSize', 10, 'MarkerFaceColor', 'r', ...
        'DisplayName', sprintf('Damage Threshold: %.1f dBm', results.damage_level_dbm));
    
    % Connect current power to damage threshold with dashed line
    plot([adc_idx adc_idx], [power_after_each(end), results.damage_level_dbm], ...
        'r--', 'LineWidth', 1.5, 'HandleVisibility', 'off');
    
    set(gca, 'XTick', 0:n_stages);
    xticklabels = [{'Input'}; results.component_names; {'ADC'}];
    set(gca, 'XTickLabel', xticklabels, 'TickLabelInterpreter', 'none');
    xtickangle(45);
    ylabel('Power (dBm)', 'Interpreter', 'none');
    title(sprintf('Power Through Chain @ Max Safe Input (%.2f GHz)', results.mid_freq_summary.frequency_ghz), 'Interpreter', 'none');
    legend('Location', 'best', 'Interpreter', 'none');
    grid on;
    
else
    axis off;
end

% Plot 6: Output power in watts (TX) OR max safe input vs frequency (RX)
subplot(2,3,6);
if results.has_power_tracking
    % TX mode: output power in watts
    hold on; grid on;
    plot(results.freq_ghz, results.final_output_power_watts, 'r-', 'LineWidth', 2.5);
    xlabel('Frequency (GHz)', 'Interpreter', 'none');
    ylabel('Output Power (W)', 'Interpreter', 'none');
    title('Output Power (Watts) vs Frequency', 'Interpreter', 'none');
    grid on;
elseif results.has_rx_sweep
    % RX mode: max safe input power vs frequency
    hold on; grid on;
    plot(results.freq_ghz, results.min_damage_threshold_dbm, 'b-', 'LineWidth', 2.5, ...
        'DisplayName', 'Max Safe Input Power');
    yline(results.damage_level_dbm, 'r--', 'LineWidth', 2, ...
        'DisplayName', sprintf('Damage Level: %.1f dBm', results.damage_level_dbm));
    
    % Mark mid-frequency point
    plot(results.mid_freq_summary.frequency_ghz, results.mid_freq_summary.min_safe_input_power_dbm, ...
        'ro', 'MarkerSize', 10, 'LineWidth', 2, ...
        'DisplayName', sprintf('Mid-Freq: %.1f dBm', results.mid_freq_summary.min_safe_input_power_dbm));
    
    xlabel('Frequency (GHz)', 'Interpreter', 'none');
    ylabel('Input Power (dBm)', 'Interpreter', 'none');
    title('Maximum Safe Input Power vs Frequency', 'Interpreter', 'none');
    legend('Location', 'best', 'Interpreter', 'none');
    grid on;
else
    axis off;
end

sgtitle(sprintf('RF Chain Analysis: %s', chain.description), 'FontSize', 14, 'FontWeight', 'bold', 'Interpreter', 'none');

%% Generate component breakdown table
fprintf('=== Gain Breakdown Across Frequency ===\n\n');
test_freqs = [results.freq_ghz(1), results.mid_freq_summary.frequency_ghz, results.freq_ghz(end)];
fprintf('%-20s', 'Component');
for f = test_freqs
    fprintf('%12.1f GHz', f);
end
fprintf('\n%s\n', repmat('-', 1, 60));

for i = 1:n_comp
    fprintf('%-20s', results.component_names{i});
    for f = test_freqs
        [~, f_idx] = min(abs(results.freq_ghz - f));
        fprintf('%12.2f dB ', results.component_gains(i, f_idx));
    end
    fprintf('\n');
end
fprintf('%s\n', repmat('-', 1, 60));
fprintf('%-20s', 'TOTAL');
for f = test_freqs
    [~, f_idx] = min(abs(results.freq_ghz - f));
    fprintf('%12.2f dB ', results.total_gain_db(f_idx));
end
fprintf('\n\n');

fprintf('Analysis complete!\n');
