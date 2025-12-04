% hw_library.m
% RF Hardware Component Library
% This file defines all RF components used across system configurations
% Update the placeholder specs with your actual component specifications

function HW = hw_library()
    % Returns a struct containing all RF hardware components
    
    %% ===== ANTENNAS =====
    
    % For rfbudget analysis, antennas are modeled as rfelements with gain
    % Note: Actual antenna patterns can be analyzed separately with rfantenna objects
    
    % TX Wing Antenna - lower gain than horn
    HW.Antennas.TX_Wing_Element = struct(...
        'RF', rfelement('Gain', 14, 'NF', 0), ...
        'PartNumber', 'WING-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'ANT1', ...
        'Notes', 'TX Wing Antenna');
    
    % TX Dual-Pol Horn Antenna (used with SP2T switch)
    HW.Antennas.TX_DualPol_Horn = struct(...
        'RF', rfelement('Gain', 14, 'NF', 0), ...
        'PartNumber', 'HORN-DP-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'ANT2', ...
        'Notes', 'TX Dual-Pol Horn, 2 ports');
    
    % RX Spiral Antenna - 3 dB gain, 70 deg beamwidth
    % Note: For RX NF calculations, gain should be 0 dB (antenna doesn't reduce receiver noise)
    % The 3 dB directive gain is used for link budget but not NF cascade
    HW.Antennas.RX_Spiral = struct(...
        'RF', rfelement('Gain', 0, 'NF', 0), ...
        'PartNumber', 'SPIRAL-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'ANT3', ...
        'Notes', 'RX Spiral, 70deg beamwidth, 3 dB directive gain (not in NF calc)');
    
    %% ===== CABLES =====
    
    % Cable loss assumption: ~0.5 dB/ft at midband (adjust as needed)
    % Cables are created via helper function
    
    HW.Cables.BlindMate_SMA_4ft = createCable(4, 'BlindMate_to_SMA', 0.5);
    HW.Cables.SMA_SMA_1ft = createCable(1, 'SMA_to_SMA', 0.5);
    HW.Cables.SMA_SMA_2ft = createCable(2, 'SMA_to_SMA', 0.5);
    HW.Cables.SMA_SMA_3ft = createCable(3, 'SMA_to_SMA', 0.5);
    HW.Cables.SMA_SMA_4ft = createCable(4, 'SMA_to_SMA', 0.5);
    
    %% ===== AMPLIFIERS =====
    
    % TX Path Amplifiers (High Power) - External to PCB
    
    % 32 dB Gain TX Amplifier (used in both configs)
    HW.Amplifiers.TX_PA_32dB = struct(...
        'RF', amplifier('Gain', 32, 'NF', 4, 'OIP3', 45), ...
        'PartNumber', 'PA-32-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'U1', ...
        'Notes', '32dB PA for TX Path 1');
    
    % 36 dB Gain TX Amplifier (Config 1)
    HW.Amplifiers.TX_PA_36dB = struct(...
        'RF', amplifier('Gain', 36, 'NF', 4.5, 'OIP3', 45), ...
        'PartNumber', 'PA-36-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'U2', ...
        'Notes', '36dB PA for Config 1 TX Path 2, 100MHz-2GHz');
    
    % 51 dB Gain TX Amplifier (Config 2)
    HW.Amplifiers.TX_PA_51dB = struct(...
        'RF', amplifier('Gain', 51, 'NF', 5, 'OIP3', 40), ...
        'PartNumber', 'PA-51-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'U3', ...
        'Notes', '51dB PA for Config 2 TX Path 2');
    
    %% ===== SWITCHES =====
    
    % High Power SP2T Switch (TX paths)
    HW.Switches.HP_SP2T = struct(...
        'RF', rfelement('Gain', -0.8, 'NF', 0.8), ...
        'PartNumber', 'SW-HP-SP2T-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'SW1', ...
        'Notes', 'High power SP2T for TX');
    
    % Standard SP2T Switch (RX paths in Config 2)
    HW.Switches.SP2T_RX = struct(...
        'RF', rfelement('Gain', -0.5, 'NF', 0.5), ...
        'PartNumber', 'SW-SP2T-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'SW2', ...
        'Notes', 'Standard SP2T for RX');
    
    %% ===== FILTERS =====
    
    % Anti-Aliasing Filter (RX paths - Config 2 only, Config 1 has it in PCB)
    HW.Filters.AntiAliasing_RX = struct(...
        'RF', rfelement('Gain', -2, 'NF', 2), ...
        'PartNumber', 'FILT-AA-RX-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'F1', ...
        'Notes', 'Anti-aliasing filter for RX');
    
    %% ===== VARIABLE ATTENUATORS =====
    
    % Config 2 RX Variable Attenuator
    HW.Attenuators.VarAtt_RX = struct(...
        'RF', rfelement('Gain', -10, 'NF', 10), ...
        'PartNumber', 'ATT-VAR-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'ATT1', ...
        'Notes', 'Variable attenuator, 10dB nominal');
    
    %% ===== BALUNS =====
    
    % Balun (used in Config 2)
    HW.Baluns.Standard = struct(...
        'RF', rfelement('Gain', -0.5, 'NF', 0.5), ...
        'PartNumber', 'BALUN-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'BAL1', ...
        'Notes', 'Standard balun');
    
    %% ===== DIRECTIONAL COUPLER =====
    
    % Directional Coupler (Config 2 RX Category 1)
    % Main path loss
    HW.Couplers.DirectionalCoupler = struct(...
        'RF', rfelement('Gain', -0.3, 'NF', 0.3), ...
        'PartNumber', 'COUP-DIR-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'CPL1', ...
        'Notes', 'Directional coupler, main path');
    
    %% ===== ADC/DAC ELEMENTS =====
    
    % These are placeholder elements for the analog interfaces
    % Actual ADC/DAC specs are in the RFSystemConfig ADC_Specs/DAC_Specs
    
    % Config 1 ADC (51 Gsps) - no loss, just interface
    HW.ADC.Config1 = struct(...
        'RF', rfelement('Gain', 0, 'NF', 0), ...
        'PartNumber', 'ADC-51G-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'ADC1', ...
        'Notes', '51 Gsps ADC for Config 1');
    
    % Config 1 DAC (51 Gsps)
    HW.DAC.Config1 = struct(...
        'RF', rfelement('Gain', 0, 'NF', 0), ...
        'PartNumber', 'DAC-51G-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'DAC1', ...
        'Notes', '51 Gsps DAC for Config 1');
    
    % Config 2 ADC (64 Gsps)
    HW.ADC.Config2 = struct(...
        'RF', rfelement('Gain', 0, 'NF', 0), ...
        'PartNumber', 'ADC-64G-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'ADC2', ...
        'Notes', '64 Gsps ADC for Config 2');
    
    % Config 2 DAC (64 Gsps)
    HW.DAC.Config2 = struct(...
        'RF', rfelement('Gain', 0, 'NF', 0), ...
        'PartNumber', 'DAC-64G-001', ...  % UPDATE
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', 'DAC2', ...
        'Notes', '64 Gsps DAC for Config 2');
    
    %% ===== PCB CUMULATIVE ELEMENTS =====
    % Config 1 PCB chains represented as single cumulative elements
    % Update gain, NF, OIP3 with your actual measured/calculated values
    
    % PCB RX Chain: Switch -> Switch -> Filter -> Switch -> Amp -> Switch -> 
    %               VarAtt -> Amp -> VarAtt -> Filter -> Balun -> ADC
    % Placeholder values - update with actual cascaded performance
    HW.PCB.RX_Cumulative = struct(...
        'RF', rfelement('Gain', -5, 'NF', 15, 'OIP3', 20), ...
        'PartNumber', 'PCB-RX-ASSY', ...
        'Manufacturer', 'Internal', ...
        'DiagramID', 'PCB-RX', ...
        'Notes', 'PCB RX chain cumulative - UPDATE GAIN/NF/OIP3');
    
    % PCB TX Chain: DAC -> VarAtt -> Balun -> Filter -> Amp -> VarAtt -> 
    %               Amp -> VarAtt -> Amp -> Switch
    % Placeholder values - update with actual cascaded performance
    HW.PCB.TX_Cumulative = struct(...
        'RF', rfelement('Gain', 30, 'NF', 10, 'OIP3', 25), ...
        'PartNumber', 'PCB-TX-ASSY', ...
        'Manufacturer', 'Internal', ...
        'DiagramID', 'PCB-TX', ...
        'Notes', 'PCB TX chain cumulative - UPDATE GAIN/NF/OIP3');
    
    %% ===== PCB CHAIN BUILDERS (Legacy - kept for reference) =====
    % Store builder functions in HW struct for Config 1
    % These are now replaced by cumulative elements above
    HW.PCB.buildRxChain = @() {HW.PCB.RX_Cumulative};
    HW.PCB.buildTxChain = @() {HW.PCB.TX_Cumulative};
    
end

%% ===== HELPER FUNCTIONS =====

function cable = createCable(length_ft, connectorType, loss_per_ft_dB_at_1GHz)
    % Create a cable element with frequency-dependent loss
    % length_ft: cable length in feet
    % connectorType: string description  
    % loss_per_ft_dB_at_1GHz: loss in dB per foot at 1 GHz reference
    %
    % Loss model: Loss(f) = loss_per_ft * length * sqrt(f/1GHz)
    % This models skin effect in coaxial cables
    
    % Define frequency range for cable model (70 MHz to 18 GHz)
    freq = [70e6 100e6 500e6 1e9 2e9 5e9 10e9 15e9 18e9]';
    f_ref = 1e9;  % 1 GHz reference
    
    % Calculate loss at each frequency using sqrt model
    loss_dB = loss_per_ft_dB_at_1GHz * length_ft * sqrt(freq / f_ref);
    
    % Convert loss to S-parameters
    % For a lossy transmission line:
    % S11 = S22 = 0 (matched)
    % S21 = S12 = 10^(-loss_dB/20)
    num_freq = length(freq);
    s_params = zeros(2, 2, num_freq);
    
    for i = 1:num_freq
        s21 = 10^(-loss_dB(i)/20);
        s_params(:,:,i) = [0, s21; s21, 0];
    end
    
    % Create sparameters object first
    sparam_obj = sparameters(s_params, freq, 50);
    
    % Create nport object with the sparameters
    rf_obj = nport('NetworkData', sparam_obj);
    rf_obj.Name = sprintf('%s_%dft', connectorType, length_ft);
    
    % Return struct with RF object and metadata
    cable = struct(...
        'RF', rf_obj, ...
        'PartNumber', sprintf('CABLE-%s-%dFT', strrep(connectorType, '_', '-'), length_ft), ...
        'Manufacturer', 'TBD', ...  % UPDATE
        'DiagramID', sprintf('CBL-%dft', length_ft), ...
        'Notes', sprintf('%s cable, %d ft, %.2f dB/ft @ 1GHz', connectorType, length_ft, loss_per_ft_dB_at_1GHz));
end
