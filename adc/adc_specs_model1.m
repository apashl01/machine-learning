function specs = adc_specs_model1()
% ADC_SPECS_MODEL1 - Specifications for ADC Model 1
%
% High-speed RF ADC with direct sampling capability up to 36 GHz
% Noise specified in dBc/Hz format
%
% OUTPUTS:
%   specs - Struct containing all ADC specifications
%
% Author: Andrew's Analysis Tools
% Date: November 2025

specs = struct();

%% Basic Information
specs.name = 'ADC_Model_1';
specs.description = 'Direct RF sampling ADC, dBc/Hz noise specs';

%% Sample Rate
specs.sample_rate_gsps = 4.0;  % 4 GSPS (adjust to your actual ADC)

%% Noise Specification Format
specs.noise_units = 'dBc/Hz';  % Noise relative to carrier

%% Frequency Bands (GHz)
% [start_freq, end_freq] for each band
specs.freq_bands = [
    0.1,  20;    % Band 1: 0.1 - 20 GHz
    20,   32;    % Band 2: 20 - 32 GHz
    32,   36;    % Band 3: 32 - 36 GHz
];

%% Full Scale Amplitude per Band (mVppd)
% Full scale input amplitude in millivolts peak-to-peak differential
specs.full_scale_mvppd = [
    2000;   % Band 1: 2000 mVppd
    1800;   % Band 2: 1800 mVppd
    1600;   % Band 3: 1600 mVppd
];

%% Analog Input Bandwidth
specs.input_bandwidth_ghz = 36;  % Half-power bandwidth

%% Non-Harmonic SFDR per Band (dB)
% Spurious-free dynamic range (non-harmonic spurs only)
specs.sfdr_db = [
    75;     % Band 1: 75 dB
    72;     % Band 2: 72 dB
    70;     % Band 3: 70 dB
];

%% Wideband Noise Density per Band (dBc/Hz)
% Noise density relative to carrier
% Measured at -10 dBFS input loading level
% At frequency offsets > 100 MHz
% Not including spurs or distortion terms
specs.noise_density = [
    -155;   % Band 1: -155 dBc/Hz
    -152;   % Band 2: -152 dBc/Hz
    -150;   % Band 3: -150 dBc/Hz
];

specs.noise_ref_level_dbfs = -10;  % Reference input level for noise spec

%% Total Harmonic Distortion per Band (%)
% Specified at -1 dBFS input loading level
specs.thd_percent = [
    0.5;    % Band 1: 0.5%
    0.6;    % Band 2: 0.6%
    0.7;    % Band 3: 0.7%
];

specs.thd_ref_level_dbfs = -1;  % Reference input level for THD spec

%% Two-Tone IM3 Distortion per Band (dBc)
% Third-order intermodulation distortion
% Two input tones at specified levels per tone
specs.im3_dbc = [
    -70;    % Band 1: -70 dBc (at -7 dBFS per tone)
    -68;    % Band 2: -68 dBc (at -7 dBFS per tone)
    -65;    % Band 3: -65 dBc (at -15 dBFS per tone for this band)
];

specs.im3_ref_level_dbfs = -7;  % Reference level per tone (adjust as needed)

%% Notes
specs.notes = {
    'Direct RF sampling ADC'
    'Noise density excludes spurs and distortion'
    'Noise measured at offsets > 100 MHz from carrier'
    'dBc/Hz noise specification format'
};

end
