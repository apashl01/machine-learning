% buildPCB_chains.m
% NOTE: These functions have been integrated into hw_library.m
% This file is kept for reference only and is not needed
%
% The PCB chain builder functions are now accessed via:
%   HW = hw_library();
%   rx_chain = HW.PCB.buildRxChain();
%   tx_chain = HW.PCB.buildTxChain();

function components = buildPCB_RxChain(HW)
    % buildPCB_RxChain - Builds the Config 1 PCB receive chain
    % 
    % Chain: Switch -> Switch -> Switchable Filter -> Switch -> 
    %        Amp -> Switch -> VarAtt -> Amp -> VarAtt -> 
    %        Anti-Aliasing Filter -> Balun -> ADC
    %
    % Input: HW - hardware library struct
    % Output: components - cell array of RF elements in order
    
    components = {
        HW.Switches.PCB_Switch           % Switch 1
        HW.Switches.PCB_Switch           % Switch 2
        HW.Filters.PCB_Switchable        % Switchable Filter
        HW.Switches.PCB_Switch           % Switch 3
        HW.Amplifiers.PCB_RX_Amp1        % Amplifier 1
        HW.Switches.PCB_Switch           % Switch 4
        HW.Attenuators.PCB_VarAtt1       % Variable Attenuator 1
        HW.Amplifiers.PCB_RX_Amp2        % Amplifier 2
        HW.Attenuators.PCB_VarAtt2       % Variable Attenuator 2
        HW.Filters.AntiAliasing_RX       % Anti-Aliasing Filter
        HW.Baluns.Standard               % Balun
        HW.ADC.Config1                   % ADC interface
    };
end

function components = buildPCB_TxChain(HW)
    % buildPCB_TxChain - Builds the Config 1 PCB transmit chain
    %
    % Chain: DAC -> VarAtt -> Balun -> Anti-Aliasing Filter -> 
    %        Amp -> VarAtt -> Amp -> VarAtt -> Amp -> Switch
    %
    % Input: HW - hardware library struct
    % Output: components - cell array of RF elements in order
    
    components = {
        HW.DAC.Config1                   % DAC interface
        HW.Attenuators.PCB_VarAtt_TX1    % Variable Attenuator 1
        HW.Baluns.Standard               % Balun
        HW.Filters.AntiAliasing_TX       % Anti-Aliasing Filter
        HW.Amplifiers.PCB_TX_Amp1        % Amplifier 1
        HW.Attenuators.PCB_VarAtt_TX2    % Variable Attenuator 2
        HW.Amplifiers.PCB_TX_Amp2        % Amplifier 2
        HW.Attenuators.PCB_VarAtt_TX3    % Variable Attenuator 3
        HW.Amplifiers.PCB_TX_Amp3        % Amplifier 3
        HW.Switches.PCB_Switch           % Switch
    };
end
