% Received Power Analysis with Atmospheric Losses
% Calculates received power at antenna terminals vs frequency
% Includes free space path loss and atmospheric attenuation (ITU-R P.676)
%
% Author: Generated for RF Link Analysis
% Date: 2024

clear; close all; clc;

%% ========================================================================
%  USER INPUTS
% =========================================================================

% Transmitter Parameters
P_tx_dBW = 40;              % Transmit power (dBW)
G_tx_dBi = 10;              % Transmit antenna gain (dBi)

% Link Geometry
distance_miles = 50;        % Distance between transmitter and receiver (miles)
altitude_km = 5;            % Altitude MSL (km) - for atmospheric model

% Frequency Range
f_min_GHz = 0.1;            % Minimum frequency (GHz)
f_max_GHz = 18;             % Maximum frequency (GHz)
num_points = 1000;          % Number of frequency points

%% ========================================================================
%  CONSTANTS
% =========================================================================

c = 299792458;              % Speed of light (m/s)
miles_to_km = 1.60934;      % Conversion factor

%% ========================================================================
%  DERIVED PARAMETERS
% =========================================================================

% Convert distance to km
distance_km = distance_miles * miles_to_km;

% Frequency vector
f_GHz = linspace(f_min_GHz, f_max_GHz, num_points);
f_MHz = f_GHz * 1000;
f_Hz = f_GHz * 1e9;

% Calculate EIRP
EIRP_dBm = P_tx_dBW + 30 + G_tx_dBi;

%% ========================================================================
%  FREE SPACE PATH LOSS
% =========================================================================

% FSPL (dB) = 32.45 + 20*log10(d_km) + 20*log10(f_MHz)
FSPL_dB = 32.45 + 20*log10(distance_km) + 20*log10(f_MHz);

%% ========================================================================
%  ATMOSPHERIC ATTENUATION (ITU-R P.676)
% =========================================================================

% Standard atmosphere parameters at given altitude
[T_K, P_hPa, rho_gm3] = standard_atmosphere(altitude_km);

% Calculate specific attenuation for oxygen and water vapor
gamma_o = zeros(size(f_GHz));  % Oxygen attenuation (dB/km)
gamma_w = zeros(size(f_GHz));  % Water vapor attenuation (dB/km)

for idx = 1:length(f_GHz)
    [gamma_o(idx), gamma_w(idx)] = atmospheric_attenuation_ITU676(f_GHz(idx), T_K, P_hPa, rho_gm3);
end

% Total atmospheric loss over the path
atmos_loss_dB = (gamma_o + gamma_w) * distance_km;

%% ========================================================================
%  RECEIVED POWER CALCULATION
% =========================================================================

% Power at receive antenna terminals (before Rx gain)
P_rx_dBm = EIRP_dBm - FSPL_dB - atmos_loss_dB;

%% ========================================================================
%  RESULTS DISPLAY
% =========================================================================

fprintf('========================================\n');
fprintf('RECEIVED POWER ANALYSIS\n');
fprintf('========================================\n\n');

fprintf('Transmitter Parameters:\n');
fprintf('  Transmit Power:        %.1f dBW\n', P_tx_dBW);
fprintf('  Transmit Antenna Gain: %.1f dBi\n', G_tx_dBi);
fprintf('  EIRP:                  %.1f dBm\n', EIRP_dBm);
fprintf('\n');

fprintf('Link Geometry:\n');
fprintf('  Distance:              %.1f miles (%.2f km)\n', distance_miles, distance_km);
fprintf('  Altitude:              %.1f km MSL\n', altitude_km);
fprintf('\n');

fprintf('Atmospheric Conditions:\n');
fprintf('  Temperature:           %.1f K (%.1f °C)\n', T_K, T_K-273.15);
fprintf('  Pressure:              %.1f hPa\n', P_hPa);
fprintf('  Water Vapor Density:   %.2f g/m³\n', rho_gm3);
fprintf('\n');

% Find and display key frequency points
[~, idx_1GHz] = min(abs(f_GHz - 1));
[~, idx_10GHz] = min(abs(f_GHz - 10));
[~, idx_18GHz] = min(abs(f_GHz - 18));

fprintf('Received Power at Key Frequencies:\n');
fprintf('  @ 1 GHz:   %.2f dBm  (FSPL: %.1f dB, Atmos: %.3f dB)\n', ...
    P_rx_dBm(idx_1GHz), FSPL_dB(idx_1GHz), atmos_loss_dB(idx_1GHz));
fprintf('  @ 10 GHz:  %.2f dBm  (FSPL: %.1f dB, Atmos: %.3f dB)\n', ...
    P_rx_dBm(idx_10GHz), FSPL_dB(idx_10GHz), atmos_loss_dB(idx_10GHz));
fprintf('  @ 18 GHz:  %.2f dBm  (FSPL: %.1f dB, Atmos: %.3f dB)\n', ...
    P_rx_dBm(idx_18GHz), FSPL_dB(idx_18GHz), atmos_loss_dB(idx_18GHz));
fprintf('\n');

%% ========================================================================
%  PLOTTING
% =========================================================================

figure('Position', [100 100 1200 800]);

% Main plot: Received Power vs Frequency
subplot(2,1,1);
plot(f_GHz, P_rx_dBm, 'b-', 'LineWidth', 2);
grid on;
xlabel('Frequency (GHz)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('Received Power (dBm)', 'FontSize', 12, 'FontWeight', 'bold');
title(sprintf('Received Power at Antenna Terminals\nDistance: %.1f miles, Altitude: %.1f km MSL', ...
    distance_miles, altitude_km), 'FontSize', 14, 'FontWeight', 'bold');
xlim([f_min_GHz f_max_GHz]);

% Loss breakdown plot
subplot(2,1,2);
plot(f_GHz, FSPL_dB, 'r-', 'LineWidth', 2, 'DisplayName', 'Free Space Path Loss');
hold on;
plot(f_GHz, atmos_loss_dB, 'g-', 'LineWidth', 2, 'DisplayName', 'Atmospheric Loss');
plot(f_GHz, FSPL_dB + atmos_loss_dB, 'k--', 'LineWidth', 2, 'DisplayName', 'Total Loss');
grid on;
xlabel('Frequency (GHz)', 'FontSize', 12, 'FontWeight', 'bold');
ylabel('Loss (dB)', 'FontSize', 12, 'FontWeight', 'bold');
title('Loss Components vs Frequency', 'FontSize', 14, 'FontWeight', 'bold');
legend('Location', 'best', 'FontSize', 10);
xlim([f_min_GHz f_max_GHz]);

%% ========================================================================
%  SUPPORTING FUNCTIONS
% =========================================================================

function [T, P, rho] = standard_atmosphere(h_km)
    % Standard atmosphere model (ISA)
    % Inputs:
    %   h_km: Altitude in km MSL
    % Outputs:
    %   T: Temperature (K)
    %   P: Pressure (hPa)
    %   rho: Water vapor density (g/m³)
    
    % Constants
    T0 = 288.15;        % Sea level temperature (K)
    P0 = 1013.25;       % Sea level pressure (hPa)
    L = -6.5;           % Temperature lapse rate (K/km)
    g = 9.80665;        % Gravitational acceleration (m/s²)
    M = 0.0289644;      % Molar mass of air (kg/mol)
    R = 8.31447;        % Universal gas constant (J/(mol·K))
    
    % Temperature at altitude
    if h_km <= 11
        T = T0 + L * h_km;
    else
        T = 216.65;     % Stratosphere (constant temp)
    end
    
    % Pressure at altitude (barometric formula)
    if h_km <= 11
        P = P0 * (T / T0)^(-g * M / (R * L / 1000));
    else
        T11 = 216.65;
        P11 = P0 * (T11 / T0)^(-g * M / (R * L / 1000));
        P = P11 * exp(-g * M * (h_km - 11) * 1000 / (R * T11));
    end
    
    % Water vapor density (simplified model)
    % Assumes standard relative humidity profile
    if h_km <= 2
        RH = 0.50;      % 50% at low altitude
    elseif h_km <= 10
        RH = 0.50 * exp(-(h_km - 2) / 3);
    else
        RH = 0.01;      % Very dry in stratosphere
    end
    
    % Saturation vapor pressure (Tetens equation)
    T_C = T - 273.15;
    es = 6.1078 * exp(17.27 * T_C / (T_C + 237.3));  % hPa
    
    % Actual vapor pressure
    e = RH * es;
    
    % Water vapor density (g/m³)
    rho = 216.7 * e / T;
end

function [gamma_o, gamma_w] = atmospheric_attenuation_ITU676(f_GHz, T, P, rho)
    % Simplified ITU-R P.676 atmospheric attenuation model
    % Valid for 1-350 GHz
    % Inputs:
    %   f_GHz: Frequency (GHz)
    %   T: Temperature (K)
    %   P: Pressure (hPa)
    %   rho: Water vapor density (g/m³)
    % Outputs:
    %   gamma_o: Oxygen attenuation (dB/km)
    %   gamma_w: Water vapor attenuation (dB/km)
    
    % For frequencies below 1 GHz, attenuation is negligible
    if f_GHz < 1
        gamma_o = 0;
        gamma_w = 0;
        return;
    end
    
    % Oxygen attenuation (simplified for f < 60 GHz)
    % Full model has resonance lines at 60 GHz and 118 GHz
    theta = 300 / T;
    
    % Non-resonant Debye spectrum for oxygen
    delta_o = (P / 1013.25) * theta^2;
    f_o = 0.6 + 0.0005 * f_GHz;  % Simplified
    
    N_o = (f_GHz^2 + f_o^2) / (f_GHz^2);
    gamma_o = 7.2 * theta^2 * (f_GHz^2) * 1e-3 * delta_o * N_o;
    
    % Water vapor attenuation (simplified)
    % Main resonance at 22 GHz, others at 183 GHz, 325 GHz
    rho_ref = 7.5;  % Reference density (g/m³)
    
    % Simplified water vapor model
    delta_w = rho / rho_ref;
    f_w = 22.235;  % Primary water vapor line (GHz)
    
    % Resonance contribution (simplified Van Vleck-Weisskopf line shape)
    df = abs(f_GHz - f_w);
    width = 2.8;  % Line width (GHz)
    
    if f_GHz < 20
        gamma_w = 0.05 * (f_GHz^2) * delta_w * 1e-3;
    else
        gamma_w = 0.1 * (f_GHz^2) * delta_w / ((df^2 + width^2)^0.5) * 1e-1;
    end
    
    % Ensure non-negative
    gamma_o = max(0, gamma_o);
    gamma_w = max(0, gamma_w);
end
