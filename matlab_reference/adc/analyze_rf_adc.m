function adc_results = analyze_rf_adc(adc_specs, config)
% ANALYZE_RF_ADC - Comprehensive RF ADC performance analysis
%
% Analyzes RF ADC performance including noise floor, dynamic range, 
% sensitivity, and distortion characteristics. Handles both dBc/Hz and 
% dBFS/Hz noise specifications.
%
% INPUTS:
%   adc_specs - Struct containing ADC specifications (from spec file)
%       .name - ADC model name
%       .sample_rate_gsps - Sample rate in GSPS
%       .noise_units - 'dBc/Hz' or 'dBFS/Hz'
%       .freq_bands - [N x 2] matrix of frequency bands in GHz
%       .full_scale_mvppd - Full scale amplitude per band (mVppd)
%       .sfdr_db - SFDR per band (dB)
%       .noise_density - Noise density per band (dBc/Hz or dBFS/Hz)
%       .thd_percent - THD per band (%)
%       .im3_dbc - IM3 per band (dBc)
%       And optional reference levels...
%
%   config - Analysis configuration struct
%       .rf_input_freq - RF input frequency (Hz)
%       .analysis_bw - Analysis bandwidth (Hz), default = 20 MHz
%       .input_impedance - Input impedance (ohms), default = 50 differential
%
% OUTPUTS:
%   adc_results - Comprehensive results struct containing:
%       .specs - Echo of input specs used
%       .config - Echo of config used
%       .operating_band - Which frequency band was selected
%       .full_scale_dbm - Full scale power in dBm
%       .noise_floor_dbm - Noise floor in analysis BW (dBm)
%       .noise_floor_dbfs - Noise floor relative to full scale (dBFS)
%       .sensitivity_dbm - Minimum detectable signal (dBm)
%       .snr_at_full_scale_db - SNR with full scale input
%       .sfdr_db - Spurious free dynamic range
%       .dynamic_range_db - Effective dynamic range
%       .equivalent_noise_figure_db - For link budget integration
%       .thd_db - Total harmonic distortion
%       .im3_dbc - Third-order intermodulation distortion
%
% EXAMPLE:
%   adc1 = adc_specs_model1();
%   config.rf_input_freq = 10e9;  % 10 GHz
%   config.analysis_bw = 20e6;     % 20 MHz
%   results = analyze_rf_adc(adc1, config);
%
% Author: Andrew's Analysis Tools
% Date: November 2025

%% Input validation and defaults
if nargin < 2
    error('analyze_rf_adc requires both adc_specs and config inputs');
end

% Set defaults
if ~isfield(config, 'analysis_bw')
    config.analysis_bw = 20e6;  % 20 MHz default
end

if ~isfield(config, 'input_impedance')
    config.input_impedance = 50;  % 50 ohm differential default
end

%% Select appropriate frequency band
rf_freq_ghz = config.rf_input_freq / 1e9;

% Find which band the operating frequency falls into
band_idx = [];
for i = 1:size(adc_specs.freq_bands, 1)
    if rf_freq_ghz >= adc_specs.freq_bands(i,1) && rf_freq_ghz <= adc_specs.freq_bands(i,2)
        band_idx = i;
        break;
    end
end

if isempty(band_idx)
    error('RF frequency %.2f GHz is outside ADC specified range', rf_freq_ghz);
end

%% Extract specs for the selected band
fs_mvppd = adc_specs.full_scale_mvppd(band_idx);
sfdr_db = adc_specs.sfdr_db(band_idx);
noise_density = adc_specs.noise_density(band_idx);
thd_percent = adc_specs.thd_percent(band_idx);
im3_dbc = adc_specs.im3_dbc(band_idx);

%% Convert full scale to dBm
% Vppd to Vrms: Vrms = Vppd / (2 * sqrt(2))
fs_vrms = (fs_mvppd / 1000) / (2 * sqrt(2));

% Power in dBm: P = V^2 / R, then 10*log10(P/0.001)
fs_power_watts = fs_vrms^2 / config.input_impedance;
full_scale_dbm = 10*log10(fs_power_watts / 0.001);

%% Calculate noise floor in analysis bandwidth
% Get reference level for noise measurement (default -10 dBFS if not specified)
if isfield(adc_specs, 'noise_ref_level_dbfs')
    noise_ref_dbfs = adc_specs.noise_ref_level_dbfs;
else
    noise_ref_dbfs = -10;  % Common default
end

% Convert noise density to noise in analysis bandwidth
% Noise in BW = Noise_density + 10*log10(BW)
bw_factor_db = 10*log10(config.analysis_bw);

if strcmp(adc_specs.noise_units, 'dBc/Hz')
    % Noise relative to carrier (at noise_ref_dbfs level)
    % Total noise in BW relative to reference carrier
    noise_rel_carrier_db = noise_density + bw_factor_db;
    
    % Convert to dBFS: noise was measured with ref level input
    % So noise in dBFS = noise_ref_dbfs + noise_rel_carrier
    noise_floor_dbfs = noise_ref_dbfs + noise_rel_carrier_db;
    
elseif strcmp(adc_specs.noise_units, 'dBFS/Hz')
    % Noise already relative to full scale
    noise_floor_dbfs = noise_density + bw_factor_db;
    
else
    error('Unknown noise units: %s. Must be dBc/Hz or dBFS/Hz', adc_specs.noise_units);
end

% Convert noise floor to dBm
noise_floor_dbm = full_scale_dbm + noise_floor_dbfs;

%% Calculate SNR at full scale
% SNR = Full_scale - Noise_floor (in dBFS)
snr_at_full_scale_db = 0 - noise_floor_dbfs;  % 0 dBFS is full scale

%% Calculate sensitivity (minimum detectable signal)
% Typically defined as noise floor + some margin (e.g., 10 dB SNR required)
snr_required_db = 10;  % Can be made configurable if needed
sensitivity_dbm = noise_floor_dbm + snr_required_db;

%% Calculate dynamic range
% Limited by both noise floor and SFDR
% Noise-limited DR: from noise floor to full scale
noise_limited_dr_db = snr_at_full_scale_db;

% SFDR-limited DR: from largest spur to full scale
sfdr_limited_dr_db = sfdr_db;

% Effective DR is the smaller of the two
dynamic_range_db = min(noise_limited_dr_db, sfdr_limited_dr_db);

%% Calculate equivalent noise figure
% NF allows integration into RF link budget calculations
% NF = SNR_in / SNR_out, but we need to reference to standard conditions

% Thermal noise floor at room temp: -174 dBm/Hz
thermal_noise_dbm_hz = -174;

% Noise in analysis bandwidth
thermal_noise_in_bw_dbm = thermal_noise_dbm_hz + bw_factor_db;

% ADC adds noise above thermal noise
% Equivalent NF = (Total_noise) - (Thermal_noise)
equivalent_nf_db = noise_floor_dbm - thermal_noise_in_bw_dbm;

%% Convert THD to dB
thd_db = 20*log10(thd_percent / 100);

%% Package results
adc_results = struct();

% Echo inputs
adc_results.specs = adc_specs;
adc_results.config = config;

% Operating conditions
adc_results.operating_band = adc_specs.freq_bands(band_idx, :);
adc_results.operating_band_ghz = sprintf('%.1f - %.1f GHz', ...
    adc_specs.freq_bands(band_idx,1), adc_specs.freq_bands(band_idx,2));

% Key performance metrics
adc_results.full_scale_dbm = full_scale_dbm;
adc_results.noise_floor_dbm = noise_floor_dbm;
adc_results.noise_floor_dbfs = noise_floor_dbfs;
adc_results.sensitivity_dbm = sensitivity_dbm;
adc_results.snr_at_full_scale_db = snr_at_full_scale_db;
adc_results.sfdr_db = sfdr_db;
adc_results.dynamic_range_db = dynamic_range_db;
adc_results.noise_limited_dr_db = noise_limited_dr_db;
adc_results.sfdr_limited_dr_db = sfdr_limited_dr_db;
adc_results.equivalent_noise_figure_db = equivalent_nf_db;
adc_results.thd_db = thd_db;
adc_results.thd_percent = thd_percent;
adc_results.im3_dbc = im3_dbc;

% Calculated intermediate values (useful for debugging)
adc_results.full_scale_vrms = fs_vrms;
adc_results.noise_density_used = noise_density;
adc_results.bw_factor_db = bw_factor_db;

end
