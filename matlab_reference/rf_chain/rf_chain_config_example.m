function chain = rf_chain_config_example()
% RF_CHAIN_CONFIG_EXAMPLE - Example RF chain configuration
%
% Defines an RF chain with cables, attenuators, amplifiers, and antennas
% This is a template - create your own config files for different chains
%
% OUTPUTS:
%   chain - Struct containing all chain components and configuration
%
% Author: Andrew's Analysis Tools
% Date: November 2025

chain = struct();

%% Chain Type and Power Levels
chain.type = 'transmit';  % 'transmit' or 'receive'

% For transmit chains, specify source power
chain.source_power_dbm = 0;  % Input signal power in dBm (e.g., 0 dBm)

% For receive chains, specify:
% - input_power_range_dbm: [min, max] range to sweep input power
% - damage_level_dbm: power level that damages components (e.g., LNA damage threshold)
% chain.input_power_range_dbm = [-60, 20];  % Example: sweep from -60 to +20 dBm
% chain.damage_level_dbm = 10;              % Example: +10 dBm damages LNA

%% Analysis Frequency Range
chain.freq_range_ghz = [0.1, 36];  % Min and max frequency in GHz

%% Component Definitions
% Each component has:
%   .type - 'antenna', 'cable', 'attenuator', or 'amplifier'
%   .name - descriptive name
%   .order - position in chain (1 = first, 2 = second, etc.)
%   ... type-specific parameters

%% Cable 1 - RG316 Coax, 1 meter
chain.components.cable1 = struct();
chain.components.cable1.type = 'cable';
chain.components.cable1.name = 'RG316_1m';
chain.components.cable1.order = 1;
% Loss follows sqrt(f) curve, defined by two points
chain.components.cable1.loss_point1_ghz = 1;    % 1 GHz
chain.components.cable1.loss_point1_db = 0.5;   % 0.5 dB loss at 1 GHz
chain.components.cable1.loss_point2_ghz = 18;   % 18 GHz
chain.components.cable1.loss_point2_db = 2.0;   % 2.0 dB loss at 18 GHz

%% Amplifier 1 - Low Noise Amplifier
chain.components.amp1 = struct();
chain.components.amp1.type = 'amplifier';
chain.components.amp1.name = 'LNA_34dB';
chain.components.amp1.order = 2;
chain.components.amp1.gain_db = 34;             % Flat gain across band
chain.components.amp1.noise_figure_db = 2.0;    % Optional, use NaN if not specified
chain.components.amp1.psat_dbm = 20;            % Output saturation power

%% Attenuator 1 - Variable attenuator
chain.components.atten1 = struct();
chain.components.atten1.type = 'attenuator';
chain.components.atten1.name = 'VarAtten_0to10dB';
chain.components.atten1.order = 3;
% Attenuation varies linearly across frequency range
chain.components.atten1.atten_min_db = 0.5;     % Min attenuation (at freq_range min)
chain.components.atten1.atten_max_db = 1.5;     % Max attenuation (at freq_range max)

%% Cable 2 - Another coax run
chain.components.cable2 = struct();
chain.components.cable2.type = 'cable';
chain.components.cable2.name = 'RG316_0p5m';
chain.components.cable2.order = 4;
chain.components.cable2.loss_point1_ghz = 1;    % 1 GHz
chain.components.cable2.loss_point1_db = 0.25;  % 0.25 dB loss at 1 GHz
chain.components.cable2.loss_point2_ghz = 18;   % 18 GHz
chain.components.cable2.loss_point2_db = 1.0;   % 1.0 dB loss at 18 GHz

%% Amplifier 2 - Power amplifier (transmit, no NF specified)
chain.components.amp2 = struct();
chain.components.amp2.type = 'amplifier';
chain.components.amp2.name = 'PA_20dB';
chain.components.amp2.order = 5;
chain.components.amp2.gain_db = 20;             % Flat gain
chain.components.amp2.noise_figure_db = NaN;    % Not specified for TX amp
chain.components.amp2.psat_dbm = 35;            % Output saturation power

%% Example Antenna (commented out - use for RX chains)
% chain.components.ant1 = struct();
% chain.components.ant1.type = 'antenna';
% chain.components.ant1.name = 'Patch_Antenna';
% chain.components.ant1.order = 1;  % Usually first in RX chain
% chain.components.ant1.gain_db = 8;  % Antenna gain in dBi

%% Notes
chain.notes = 'Example transmit chain: Cable -> LNA -> Attenuator -> Cable -> PA';
chain.description = 'Demonstration of scalable RF chain configuration';

end
