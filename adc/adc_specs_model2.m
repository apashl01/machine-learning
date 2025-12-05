function specs = adc_specs_model2()
% ADC_SPECS_MODEL2 - Specifications for ADC Model 2
%
% High-speed RF ADC with integrated DDC capability
% Noise specified in dBFS/Hz format
% Real mode, M=1 (no decimation) for comparison with Model 1
%
% OUTPUTS:
%   specs - Struct containing all ADC specifications
%
% Author: Andrew's Analysis Tools
% Date: November 2025

specs = struct();

%% Basic Information
specs.name = 'ADC_Model_2';
specs.description = 'RF ADC with DDC, dBFS/Hz noise specs, real mode M=1';

%% Sample Rate
specs.sample_rate_gsps = 4.0;  % 4 GSPS (adjust to your actual ADC)

%% Operating Mode
specs.mode = 'real';
specs.decimation_factor = 1;  % M = 1, no decimation

%% Noise Specification Format
specs.noise_units = 'dBFS/Hz';  % Noise relative to full scale

%% Frequency Bands (GHz)
% [start_freq, end_freq] for each band
specs.freq_bands = [
    0.1,  12;    % Band 1: 0.1 - 12 GHz
    12,   22;    % Band 2: 12 - 22 GHz
    22,   32;    % Band 3: 22 - 32 GHz
    32,   36;    % Band 4: 32 - 36 GHz
];

%% Full Scale Amplitude per Band (mVppd)
% For Model 2, can use frequency-dependent dBm levels if available
% Or use mVppd format like Model 1
% Using mVppd format for consistency:
specs.full_scale_mvppd = [
    2000;   % Band 1: 2000 mVppd (adjust to actual spec)
    1900;   % Band 2: 1900 mVppd
    1700;   % Band 3: 1700 mVppd
    1500;   % Band 4: 1500 mVppd
];

% Alternative: if you have dBm levels from datasheet, you can add:
% specs.full_scale_dbm = [-5; -6; -7; -8];  % Example values per band
% The analysis function would need modification to use these directly

%% Differential Input Impedance
specs.input_impedance_ohm = 50;  % Differential

%% Differential Return Loss per Band (dB)
specs.return_loss_db = [
    -15;    % Band 1: -15 dB
    -14;    % Band 2: -14 dB
    -13;    % Band 3: -13 dB
    -12;    % Band 4: -12 dB
];

%% Spurious-Free Dynamic Range (dBFS)
specs.sfdr_db = [
    72;     % Band 1: 72 dBFS
    70;     % Band 2: 70 dBFS
    68;     % Band 3: 68 dBFS
    66;     % Band 4: 66 dBFS
];

%% Noise Spectral Density per Band (dBFS/Hz)
% Noise density relative to full scale
% Specified for "other modes" (non-x8H)
specs.noise_density = [
    -165;   % Band 1: -165 dBFS/Hz
    -163;   % Band 2: -163 dBFS/Hz
    -161;   % Band 3: -161 dBFS/Hz
    -159;   % Band 4: -159 dBFS/Hz
];

% No reference level needed for dBFS/Hz - already relative to full scale
specs.noise_ref_level_dbfs = 0;  % Not used, but included for consistency

%% Total Harmonic Distortion per Band (dBc)
% Model 2 specifies THD in dBc, not percent
% Note: These values need to be converted to % for analysis function
specs.thd_dbc = [
    -50;    % Band 1: -50 dBc
    -48;    % Band 2: -48 dBc
    -46;    % Band 3: -46 dBc
    -44;    % Band 4: -44 dBc
];

% Convert dBc to percent for compatibility with analysis function
% THD(%) = 10^(THD_dBc/20) * 100
specs.thd_percent = 10.^(specs.thd_dbc/20) * 100;

specs.thd_ref_level_dbfs = -1;  % Typical reference level

%% Third-Order Intermodulation Distortion per Band (dBc)
specs.im3_dbc = [
    -72;    % Band 1: -72 dBc
    -70;    % Band 2: -70 dBc
    -68;    % Band 3: -68 dBc
    -66;    % Band 4: -66 dBc
];

specs.im3_ref_level_dbfs = -7;  % Reference level per tone

%% Notes
specs.notes = {
    'RF ADC with integrated DDC'
    'Real mode, M=1 (no decimation) for fundamental comparison'
    'dBFS/Hz noise specification format'
    'DDC features not included in this analysis'
};

end
