function results = analyze_rf_chain(chain_config)
% ANALYZE_RF_CHAIN - Analyze cascaded RF chain performance
%
% Computes gain/loss and noise figure across frequency for a chain of
% cables, attenuators, and amplifiers. Components can be in any order.
% For transmit chains, tracks power through chain and checks saturation.
%
% INPUTS:
%   chain_config - Struct from rf_chain_config_*.m file containing:
%       .type - 'transmit' or 'receive'
%       .source_power_dbm - Input power (for transmit only)
%       .freq_range_ghz - [min, max] frequency range in GHz
%       .components - Struct of components with fields:
%           .type - 'cable', 'attenuator', or 'amplifier'
%           .order - Position in chain (1, 2, 3, ...)
%           ... (type-specific parameters)
%
% OUTPUTS:
%   results - Struct containing:
%       .freq_ghz - Frequency vector in GHz
%       .total_gain_db - Total cascaded gain/loss vs frequency
%       .cascaded_nf_db - Cascaded noise figure vs frequency (if NFs provided)
%       .component_gains - Individual component gains vs frequency
%       .component_names - Names of components in order
%       .mid_freq_summary - Performance at middle frequency
%       For transmit mode:
%           .power_through_chain_dbm - Power after each component
%           .power_through_chain_watts - Power in watts after each component
%           .final_output_power_dbm - Final output power
%           .final_output_power_watts - Final output power in watts
%           .saturation_flags - Flags for saturated amplifiers
%
% EXAMPLE:
%   chain = rf_chain_config_example();
%   results = analyze_rf_chain(chain);
%   plot(results.freq_ghz, results.total_gain_db);
%
% Author: Andrew's Analysis Tools
% Date: November 2025

%% Validate chain type and power settings
if ~isfield(chain_config, 'type')
    chain_config.type = 'receive';  % Default
end

is_transmit = strcmpi(chain_config.type, 'transmit');

if is_transmit && ~isfield(chain_config, 'source_power_dbm')
    error('Transmit chain requires source_power_dbm to be specified');
end

% For receive mode, check if we should do power sweep
do_rx_power_sweep = false;
if ~is_transmit && isfield(chain_config, 'input_power_range_dbm') && ...
   isfield(chain_config, 'damage_level_dbm')
    do_rx_power_sweep = true;
    rx_power_sweep_dbm = linspace(chain_config.input_power_range_dbm(1), ...
                                   chain_config.input_power_range_dbm(2), 100);
end

%% Extract and sort components by order
comp_names = fieldnames(chain_config.components);
n_components = length(comp_names);

% Build array of [order, component_index]
order_array = zeros(n_components, 2);
for i = 1:n_components
    comp = chain_config.components.(comp_names{i});
    order_array(i, 1) = comp.order;
    order_array(i, 2) = i;
end

% Sort by order
[~, sort_idx] = sort(order_array(:, 1));
ordered_indices = order_array(sort_idx, 2);

%% Create frequency vector for analysis
freq_min = chain_config.freq_range_ghz(1);
freq_max = chain_config.freq_range_ghz(2);
freq_ghz = linspace(freq_min, freq_max, 200);  % 200 points for smooth curves
n_freq = length(freq_ghz);

%% Pre-allocate arrays
component_gains = zeros(n_components, n_freq);  % Gain of each component vs freq
component_nfs = nan(n_components, n_freq);      % NF of each component vs freq (NaN if not specified)
component_names_ordered = cell(n_components, 1);
component_psat = nan(n_components, 1);          % Saturation power for amplifiers

%% Compute performance for each component
for idx = 1:n_components
    comp_idx = ordered_indices(idx);
    comp_name = comp_names{comp_idx};
    comp = chain_config.components.(comp_name);
    component_names_ordered{idx} = comp.name;
    
    switch comp.type
        case 'antenna'
            % Antenna has flat gain across frequency
            % Antennas are passive/reciprocal - gain without added noise
            component_gains(idx, :) = comp.gain_db * ones(1, n_freq);
            
            % Antennas don't add noise (passive device at ambient temp)
            % NF = 0 dB for ideal antenna
            component_nfs(idx, :) = zeros(1, n_freq);
            
        case 'cable'
            % Cable loss follows sqrt(f) model: Loss(f) = k * sqrt(f)
            % Given two points, solve for k
            f1 = comp.loss_point1_ghz;
            loss1 = comp.loss_point1_db;
            f2 = comp.loss_point2_ghz;
            loss2 = comp.loss_point2_db;
            
            % Two equations: loss1 = k*sqrt(f1), loss2 = k*sqrt(f2)
            % Average the two k values for robustness
            k = (loss1/sqrt(f1) + loss2/sqrt(f2)) / 2;
            
            % Calculate loss across frequency (negative gain)
            cable_loss = k * sqrt(freq_ghz);
            component_gains(idx, :) = -cable_loss;
            
            % Cables don't add noise figure (passive, room temp)
            % NF of passive loss = Loss (in linear)
            component_nfs(idx, :) = cable_loss;  % NF in dB equals loss in dB
            
        case 'attenuator'
            % Attenuator varies linearly from min to max across freq range
            atten_min = comp.atten_min_db;
            atten_max = comp.atten_max_db;
            
            % Linear interpolation
            atten = atten_min + (atten_max - atten_min) * (freq_ghz - freq_min) / (freq_max - freq_min);
            component_gains(idx, :) = -atten;
            
            % Attenuators: NF equals attenuation (passive device)
            component_nfs(idx, :) = atten;
            
        case 'amplifier'
            % Amplifier has flat gain across frequency
            component_gains(idx, :) = comp.gain_db * ones(1, n_freq);
            
            % Noise figure (if specified)
            if isfield(comp, 'noise_figure_db') && ~isnan(comp.noise_figure_db)
                component_nfs(idx, :) = comp.noise_figure_db * ones(1, n_freq);
            else
                component_nfs(idx, :) = nan(1, n_freq);
            end
            
            % Saturation power (for transmit mode)
            if isfield(comp, 'psat_dbm')
                component_psat(idx) = comp.psat_dbm;
            end
            
        otherwise
            error('Unknown component type: %s', comp.type);
    end
end

%% Compute cascaded gain
total_gain_db = sum(component_gains, 1);  % Sum gains of all components

%% Calculate mid-frequency index (needed for various calculations)
mid_freq_ghz = (freq_min + freq_max) / 2;
[~, mid_idx] = min(abs(freq_ghz - mid_freq_ghz));

%% Transmit mode: Track power through chain and check saturation
%% Receive mode: Sweep input power and find damage thresholds
if is_transmit && isfield(chain_config, 'source_power_dbm')
    % Transmit mode power tracking
    power_through_chain_dbm = zeros(n_components + 1, n_freq);
    saturation_flags = false(n_components, n_freq);
    
    % Initial power (source)
    power_through_chain_dbm(1, :) = chain_config.source_power_dbm;
    
    % Track power through each component
    for comp_idx = 1:n_components
        power_after = power_through_chain_dbm(comp_idx, :) + component_gains(comp_idx, :);
        
        % Check for amplifier saturation
        comp_struct_idx = ordered_indices(comp_idx);
        comp = chain_config.components.(comp_names{comp_struct_idx});
        
        if strcmp(comp.type, 'amplifier') && ~isnan(component_psat(comp_idx))
            saturated = power_after > component_psat(comp_idx);
            saturation_flags(comp_idx, saturated) = true;
            power_after(saturated) = component_psat(comp_idx);
        end
        
        power_through_chain_dbm(comp_idx + 1, :) = power_after;
    end
    
    final_output_power_dbm = power_through_chain_dbm(end, :);
    final_output_power_watts = 10.^((final_output_power_dbm - 30) / 10);
    power_through_chain_watts = 10.^((power_through_chain_dbm - 30) / 10);
    
    has_power_tracking = true;
    
elseif do_rx_power_sweep
    % Receive mode: sweep input power to find damage threshold at ADC input
    % Damage occurs at the END of the chain (ADC input), not at individual components
    
    n_power_sweep = length(rx_power_sweep_dbm);
    
    % For each frequency, find max input power before output exceeds damage level
    min_damage_threshold_dbm = zeros(1, n_freq);
    
    for f_idx = 1:n_freq
        % Calculate total gain through entire chain
        total_chain_gain = sum(component_gains(:, f_idx));
        
        % Max safe input = damage level - total gain
        min_damage_threshold_dbm(f_idx) = chain_config.damage_level_dbm - total_chain_gain;
    end
    
    % Compute power through chain at mid-frequency with max safe input
    % This will be used for the cascade plot
    mid_safe_power = min_damage_threshold_dbm(mid_idx);
    power_through_chain_at_threshold = zeros(n_components + 2, 1);  % +2 for input and ADC
    power_through_chain_at_threshold(1) = mid_safe_power;
    
    for comp_idx = 1:n_components
        power_through_chain_at_threshold(comp_idx + 1) = ...
            power_through_chain_at_threshold(comp_idx) + component_gains(comp_idx, mid_idx);
    end
    
    % ADC input (where damage occurs) = output of last component
    power_through_chain_at_threshold(end) = power_through_chain_at_threshold(n_components + 1);
    
    has_power_tracking = false;
    has_rx_sweep = true;
    
else
    has_power_tracking = false;
    has_rx_sweep = false;
end

%% Compute cascaded noise figure using Friis formula
% NF_total = NF1 + (NF2-1)/G1 + (NF3-1)/(G1*G2) + ...
% All in linear units, then convert back to dB

cascaded_nf_linear = zeros(1, n_freq);
has_nf_data = false;

for f_idx = 1:n_freq
    nf_total_linear = 0;
    gain_product_linear = 1;  % Cumulative gain up to current stage
    
    for comp_idx = 1:n_components
        nf_db = component_nfs(comp_idx, f_idx);
        gain_db = component_gains(comp_idx, f_idx);
        
        if ~isnan(nf_db)
            has_nf_data = true;
            nf_linear = 10^(nf_db/10);
            
            % Add this stage's contribution
            if comp_idx == 1
                nf_total_linear = nf_linear;
            else
                nf_total_linear = nf_total_linear + (nf_linear - 1) / gain_product_linear;
            end
        end
        
        % Update cumulative gain for next stage
        gain_linear = 10^(gain_db/10);
        gain_product_linear = gain_product_linear * gain_linear;
    end
    
    cascaded_nf_linear(f_idx) = nf_total_linear;
end

% Convert back to dB
if has_nf_data
    cascaded_nf_db = 10*log10(cascaded_nf_linear);
else
    cascaded_nf_db = nan(1, n_freq);
end

%% Mid-frequency analysis
mid_freq_summary = struct();
mid_freq_summary.frequency_ghz = freq_ghz(mid_idx);
mid_freq_summary.total_gain_db = total_gain_db(mid_idx);
if has_nf_data
    mid_freq_summary.cascaded_nf_db = cascaded_nf_db(mid_idx);
else
    mid_freq_summary.cascaded_nf_db = NaN;
end

% Transmit/Receive mode mid-frequency summary
if has_power_tracking
    mid_freq_summary.input_power_dbm = chain_config.source_power_dbm;
    mid_freq_summary.output_power_dbm = final_output_power_dbm(mid_idx);
    mid_freq_summary.output_power_watts = final_output_power_watts(mid_idx);
    
    % Check for saturation at mid-frequency
    saturated_amps = find(saturation_flags(:, mid_idx));
    if ~isempty(saturated_amps)
        mid_freq_summary.saturated_amplifiers = component_names_ordered(saturated_amps);
    else
        mid_freq_summary.saturated_amplifiers = {};
    end
    
elseif has_rx_sweep
    % Receive mode with power sweep
    mid_freq_summary.damage_level_dbm = chain_config.damage_level_dbm;
    mid_freq_summary.min_safe_input_power_dbm = min_damage_threshold_dbm(mid_idx);
    mid_freq_summary.adc_input_power_at_threshold_dbm = power_through_chain_at_threshold(end);
    mid_freq_summary.power_through_chain_at_threshold = power_through_chain_at_threshold;
end

% Individual component contributions at mid frequency
mid_freq_summary.component_contributions = struct();
for idx = 1:n_components
    comp_name = component_names_ordered{idx};
    % Replace problematic characters for struct field names
    safe_name = strrep(comp_name, '.', 'p');
    safe_name = strrep(safe_name, '-', '_');
    
    mid_freq_summary.component_contributions.(safe_name) = struct();
    mid_freq_summary.component_contributions.(safe_name).name = comp_name;
    mid_freq_summary.component_contributions.(safe_name).gain_db = component_gains(idx, mid_idx);
    if ~isnan(component_nfs(idx, mid_idx))
        mid_freq_summary.component_contributions.(safe_name).nf_db = component_nfs(idx, mid_idx);
    end
    
    if has_power_tracking
        mid_freq_summary.component_contributions.(safe_name).output_power_dbm = power_through_chain_dbm(idx+1, mid_idx);
        mid_freq_summary.component_contributions.(safe_name).output_power_watts = power_through_chain_watts(idx+1, mid_idx);
        if saturation_flags(idx, mid_idx)
            mid_freq_summary.component_contributions.(safe_name).saturated = true;
        end
    elseif has_rx_sweep
        % Show actual power at this component when at damage threshold
        mid_freq_summary.component_contributions.(safe_name).power_at_threshold_dbm = ...
            power_through_chain_at_threshold(idx + 1);
    end
end

%% Package results
results = struct();
results.freq_ghz = freq_ghz;
results.total_gain_db = total_gain_db;
results.cascaded_nf_db = cascaded_nf_db;
results.component_gains = component_gains;
results.component_nfs = component_nfs;
results.component_names = component_names_ordered;
results.mid_freq_summary = mid_freq_summary;
results.has_nf_data = has_nf_data;
results.is_transmit = is_transmit;
results.has_power_tracking = has_power_tracking;

% Power tracking results (TX mode)
if has_power_tracking
    results.power_through_chain_dbm = power_through_chain_dbm;
    results.power_through_chain_watts = power_through_chain_watts;
    results.final_output_power_dbm = final_output_power_dbm;
    results.final_output_power_watts = final_output_power_watts;
    results.saturation_flags = saturation_flags;
end

% RX power sweep results
if has_rx_sweep
    results.has_rx_sweep = true;
    results.damage_level_dbm = chain_config.damage_level_dbm;
    results.min_damage_threshold_dbm = min_damage_threshold_dbm;
    results.input_power_range_dbm = chain_config.input_power_range_dbm;
    results.power_through_chain_at_threshold = power_through_chain_at_threshold;
else
    results.has_rx_sweep = false;
end

% Store chain config for reference
results.chain_config = chain_config;

end
