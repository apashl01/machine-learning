% config_2_no_pcb.m
% Configuration 2: System without PCB
% 8 RX paths (4 with directional coupler, 4 without), 4 TX paths (2 connected)
% Sample Rate: 64 Gsps
% Frequency Range: 70 MHz - 18 GHz (except TX Path 1: 100 MHz - 2 GHz)

function config2 = config_2_no_pcb()
    
    % Load hardware library
    HW = hw_library();
    
    % Create configuration
    config2 = RFSystemConfig('Config_2_NoPCB', 64);
    
    % Set frequency range
    config2.FrequencyRange = [70e6 18e9];
    
    % Update ADC/DAC specs for Config 2
    config2.ADC_Specs.SampleRate_Gsps = 64;
    config2.ADC_Specs.ENOB = 10;  % Update with actual spec
    config2.ADC_Specs.FullScaleVoltage = 1.0;  % Update
    config2.ADC_Specs.NoiseFloor_dBFS = -150;  % Update
    config2.ADC_Specs.SFDR_dBc = 80;  % Update
    
    config2.DAC_Specs.SampleRate_Gsps = 64;
    config2.DAC_Specs.ENOB = 10;  % Update
    config2.DAC_Specs.FullScaleVoltage = 1.0;  % Update
    config2.DAC_Specs.NoiseFloor_dBFS = -150;  % Update
    config2.DAC_Specs.SFDR_dBc = 80;  % Update
    
    % Optional: Specify frequency-dependent DAC output power from datasheet
    % If not specified, will use FullScaleVoltage calculation
    % Example: DAC output power varies ~10 dB from low to high frequency
    % Uncomment and update with actual datasheet values:
    % config2.DAC_Specs.OutputPower_Frequency_Hz = [100e6 500e6 1e9 2e9 5e9 10e9 15e9 18e9];
    % config2.DAC_Specs.OutputPower_dBm = [10 9 8 6 4 2 0 -1];  % Higher power at low freq
    
    %% ===== BUILD RX PATHS =====
    
    freq_wide = [70e6 18e9];
    freq_mid = [2e9 18e9];      % 2-18 GHz for coupler paths
    freq_narrow = [100e6 2e9];  % 100 MHz - 2 GHz for special path
    
    % RX Category 1 (4 paths with directional coupler): 2-18 GHz
    % ADC -> Balun -> VarAtt -> Anti-Aliasing -> SP2T -> 2ft cable -> 
    % Coupler -> 3ft cable -> Spiral antenna
    
    for i = 1:4
        rx_cat1_components = {
            HW.ADC.Config2                    % ADC interface
            HW.Baluns.Standard                % Balun
            HW.Attenuators.VarAtt_RX          % Variable attenuator
            HW.Filters.AntiAliasing_RX        % Anti-aliasing filter
            HW.Switches.SP2T_RX               % SP2T switch
            HW.Cables.SMA_SMA_2ft             % 2ft cable to coupler
            HW.Couplers.DirectionalCoupler    % Directional coupler (main path)
            HW.Cables.SMA_SMA_3ft             % 3ft cable to antenna
            HW.Antennas.RX_Spiral             % Spiral antenna
        };
        
        config2 = config2.addRxPath(...
            sprintf('RX_Cat1_Path_%d', i), ...
            rx_cat1_components, ...
            freq_mid);  % 2-18 GHz
    end
    
    % RX Category 2 (4 paths without directional coupler):
    % Path 1: 100 MHz - 2 GHz with Wing antenna
    % Paths 2-4: 2-18 GHz with Spiral antennas
    % ADC -> Balun -> VarAtt -> Anti-Aliasing -> SP2T -> 4ft cable -> antenna
    
    for i = 1:4
        rx_cat2_components = {
            HW.ADC.Config2                    % ADC interface
            HW.Baluns.Standard                % Balun
            HW.Attenuators.VarAtt_RX          % Variable attenuator
            HW.Filters.AntiAliasing_RX        % Anti-aliasing filter
            HW.Switches.SP2T_RX               % SP2T switch
            HW.Cables.SMA_SMA_4ft             % 4ft cable to antenna
        };
        
        % Path 1 is special: 100 MHz - 2 GHz with Wing antenna
        if i == 1
            rx_cat2_components{end+1} = HW.Antennas.TX_Wing_Element;  % Wing antenna
            freq_range = freq_narrow;  % 100 MHz - 2 GHz
        else
            rx_cat2_components{end+1} = HW.Antennas.RX_Spiral;  % Spiral antenna
            freq_range = freq_mid;  % 2-18 GHz
        end
        
        config2 = config2.addRxPath(...
            sprintf('RX_Cat2_Path_%d', i), ...
            rx_cat2_components, ...
            freq_range);
    end
    
    %% ===== BUILD TX PATHS =====
    
    % TX Path 1: DAC -> Balun -> 1ft cable -> 32dB PA -> 2ft cable -> TX antenna
    tx1_components = {
        HW.DAC.Config2                    % DAC interface
        HW.Baluns.Standard                % Balun
        HW.Cables.SMA_SMA_1ft             % 1ft cable from DAC
        HW.Amplifiers.TX_PA_32dB          % 32 dB PA
        HW.Cables.SMA_SMA_2ft             % 2ft cable to antenna
        HW.Antennas.TX_Wing_Element       % TX Wing antenna
    };
    
    config2 = config2.addTxPath('TX_Path_1', tx1_components, freq_narrow);
    
    % TX Path 2: DAC -> Balun -> 1ft cable -> 51dB PA -> HP SP2T -> 2ft cable -> Dual Pol Horn
    tx2_components = {
        HW.DAC.Config2                    % DAC interface
        HW.Baluns.Standard                % Balun
        HW.Cables.SMA_SMA_1ft             % 1ft cable from DAC
        HW.Amplifiers.TX_PA_51dB          % 51 dB PA
        HW.Switches.HP_SP2T               % High power SP2T switch
        HW.Cables.SMA_SMA_2ft             % 2ft cable to antenna
        HW.Antennas.TX_DualPol_Horn       % Dual pol TX Horn (one port)
    };
    
    config2 = config2.addTxPath('TX_Path_2', tx2_components, freq_wide);
    
    % TX Paths 3 & 4: Unused/not connected
    tx3_components = {HW.DAC.Config2};
    config2 = config2.addTxPath('TX_Path_3_Unused', tx3_components, freq_wide);
    config2.TxPaths(3).IsConnected = false;
    
    tx4_components = {HW.DAC.Config2};
    config2 = config2.addTxPath('TX_Path_4_Unused', tx4_components, freq_wide);
    config2.TxPaths(4).IsConnected = false;
    
    %% ===== NOTES =====
    config2.Notes = sprintf([...
        'Configuration 2 without PCB\n' ...
        '- 8 RX paths total\n' ...
        '  * Category 1 (paths 1-4): includes directional coupler, 2-18 GHz\n' ...
        '  * Category 2 (paths 5-8):\n' ...
        '    - Path 1: 100 MHz - 2 GHz with Wing antenna\n' ...
        '    - Paths 2-4: 2-18 GHz with Spiral antennas\n' ...
        '- TX Path 1 operates 100 MHz - 2 GHz\n' ...
        '- 4 TX paths, 2 connected (Path 1 to horn, Path 2 to dual-pol horn)\n' ...
        '- TX Path 2 and most RX paths operate 2-18 GHz\n' ...
        '- Sample rate: 64 Gsps\n' ...
        '- 4 SP2T switches on RX allow selection of 8 total antennas']);
    
    fprintf('Config 2 (No PCB) created successfully.\n');
    config2.getSummary();
    
end
