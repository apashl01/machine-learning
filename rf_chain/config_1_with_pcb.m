% config_1_with_pcb.m
% Configuration 1: System with PCB on all TX/RX paths
% 8 RX paths, 4 TX paths (2 connected)
% Sample Rate: 51 Gsps
% Frequency Range: 70 MHz - 18 GHz (except TX Path 2: 100 MHz - 2 GHz)

function config1 = config_1_with_pcb()
    
    % Load hardware library
    HW = hw_library();
    
    % Create configuration
    config1 = RFSystemConfig('Config_1_PCB', 51);
    
    % Set frequency range
    config1.FrequencyRange = [70e6 18e9];
    
    % Update ADC/DAC specs for Config 1
    config1.ADC_Specs.SampleRate_Gsps = 51;
    config1.ADC_Specs.ENOB = 10;  % Update with actual spec
    config1.ADC_Specs.FullScaleVoltage = 1.0;  % Update
    config1.ADC_Specs.NoiseFloor_dBFS = -150;  % Update
    config1.ADC_Specs.SFDR_dBc = 80;  % Update
    
    config1.DAC_Specs.SampleRate_Gsps = 51;
    config1.DAC_Specs.ENOB = 10;  % Update
    config1.DAC_Specs.FullScaleVoltage = 1.0;  % Update
    config1.DAC_Specs.NoiseFloor_dBFS = -150;  % Update
    config1.DAC_Specs.SFDR_dBc = 80;  % Update
    
    % Optional: Specify frequency-dependent DAC output power from datasheet
    % If not specified, will use FullScaleVoltage calculation
    % Example: DAC output power varies ~10 dB from low to high frequency
    % Uncomment and update with actual datasheet values:
    % config1.DAC_Specs.OutputPower_Frequency_Hz = [100e6 500e6 1e9 2e9 5e9 10e9 15e9 18e9];
    % config1.DAC_Specs.OutputPower_dBm = [10 9 8 6 4 2 0 -1];  % Higher power at low freq
    
    %% ===== BUILD RX PATHS =====
    % All 8 RX paths: PCB chain -> 4ft cable -> Spiral antenna
    
    freq_wide = [70e6 18e9];
    
    for i = 1:8
        % Build complete RX chain
        pcb_chain = HW.PCB.buildRxChain();  % Returns cell array
        rx_components = [
            pcb_chain                        % PCB chain ending at ADC
            {HW.Cables.BlindMate_SMA_4ft}    % 4ft blind mate to SMA cable
            {HW.Antennas.RX_Spiral}          % Spiral RX antenna
        ];
        
        config1 = config1.addRxPath(...
            sprintf('RX_Path_%d', i), ...
            rx_components, ...
            freq_wide);
    end
    
    %% ===== BUILD TX PATHS =====
    
    % TX Path 1: PCB -> 4ft cable -> 32dB PA -> 2ft cable -> TX Wing
    pcb_chain = HW.PCB.buildTxChain();  % Returns cell array
    tx1_components = [
        pcb_chain                         % PCB chain starting from DAC
        {HW.Cables.BlindMate_SMA_4ft}     % 4ft blind mate to SMA
        {HW.Amplifiers.TX_PA_32dB}        % 32 dB PA
        {HW.Cables.SMA_SMA_2ft}           % 2ft SMA-SMA
        {HW.Antennas.TX_Wing_Element}     % TX Wing antenna
    ];
    
    config1 = config1.addTxPath('TX_Path_1', tx1_components, freq_wide);
    
    % TX Path 2: PCB -> 4ft cable -> 36dB PA -> HP SP2T -> 2ft cables -> Dual Pol Horn
    % Note: This models one port of the dual pol antenna
    % For full analysis, you'd need separate paths for each polarization
    pcb_chain = HW.PCB.buildTxChain();  % Returns cell array
    tx2_components = [
        pcb_chain                         % PCB chain
        {HW.Cables.BlindMate_SMA_4ft}     % 4ft blind mate to SMA
        {HW.Amplifiers.TX_PA_36dB}        % 36 dB PA
        {HW.Switches.HP_SP2T}             % High power SP2T switch
        {HW.Cables.SMA_SMA_2ft}           % 2ft SMA-SMA
        {HW.Antennas.TX_DualPol_Horn}     % Dual pol TX Horn (one port)
    ];
    
    freq_narrow = [100e6 2e9];  % TX Path 2 has narrower frequency range
    config1 = config1.addTxPath('TX_Path_2', tx2_components, freq_narrow);
    
    % TX Paths 3 & 4: Unused/not connected
    % You can still add them with IsConnected = false if you want to track them
    tx3_components = HW.PCB.buildTxChain();
    config1 = config1.addTxPath('TX_Path_3_Unused', tx3_components, freq_wide);
    config1.TxPaths(3).IsConnected = false;
    
    tx4_components = HW.PCB.buildTxChain();
    config1 = config1.addTxPath('TX_Path_4_Unused', tx4_components, freq_wide);
    config1.TxPaths(4).IsConnected = false;
    
    %% ===== NOTES =====
    config1.Notes = sprintf([...
        'Configuration 1 with PCB on all paths\n' ...
        '- 8 RX paths, all connected to spiral antennas\n' ...
        '- 4 TX paths, 2 connected (Path 1 to horn, Path 2 to dual-pol horn)\n' ...
        '- TX Path 2 operates 100 MHz - 2 GHz\n' ...
        '- All other paths operate 70 MHz - 18 GHz\n' ...
        '- Sample rate: 51 Gsps']);
    
    %% ===== LOAD GAIN STATE DATA (OPTIONAL) =====
    % If you have measured PCB gain state data in Excel format, load it here
    % This will replace the PCB cumulative element with actual measured data
    %
    % Example usage:
    % config1 = config1.loadTxGainStates('path/to/tx_data.xlsx', 'BDR Table (LMB)');
    % config1 = config1.loadRxGainStates('path/to/rx_data.xlsx', 'BDR Table (LMB)');
    %
    % Expected TX Excel columns: DR State, Freq (GHz), Tx Power (dBm)
    % Expected RX Excel columns: DR State, Gain (dB), Freq (GHz), LL (dBm), UL (dBm)
    
    fprintf('Config 1 (PCB) created successfully.\n');
    config1.getSummary();
    
end
