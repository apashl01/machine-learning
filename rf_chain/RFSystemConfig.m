classdef RFSystemConfig
    % RFSystemConfig - Class for managing RF system configurations
    % Handles multiple TX/RX paths with different hardware configurations
    
    properties
        ConfigName          % Configuration name (e.g., 'Config_1_PCB', 'Config_2_NoPCB')
        TxPaths            % struct array of transmit chains
        RxPaths            % struct array of receive chains
        SampleRate         % ADC/DAC sample rate (Gsps)
        ADC_Specs          % struct with ADC characteristics
        DAC_Specs          % struct with DAC characteristics
        FrequencyRange     % [min max] in Hz
        Notes              % Any additional notes
        TxGainStates       % struct with TX gain state data from Excel
        RxGainStates       % struct with RX gain state data from Excel
    end
    
    methods
        function obj = RFSystemConfig(name, sampleRate)
            % Constructor
            obj.ConfigName = name;
            obj.TxPaths = struct([]);
            obj.RxPaths = struct([]);
            obj.SampleRate = sampleRate; % Gsps
            
            % Initialize ADC specs with placeholders
            obj.ADC_Specs = struct(...
                'SampleRate_Gsps', sampleRate, ...
                'ENOB', 10, ...  % Effective number of bits
                'FullScaleVoltage', 1.0, ...  % Vpp
                'NoiseFloor_dBFS', -150, ...
                'SFDR_dBc', 80, ...
                'InputImpedance', 50);
            
            % Initialize DAC specs with placeholders
            obj.DAC_Specs = struct(...
                'SampleRate_Gsps', sampleRate, ...
                'ENOB', 10, ...
                'FullScaleVoltage', 1.0, ...
                'NoiseFloor_dBFS', -150, ...
                'SFDR_dBc', 80, ...
                'OutputImpedance', 50, ...
                'OutputPower_Frequency_Hz', [], ...  % Optional: frequency points for power curve
                'OutputPower_dBm', []);               % Optional: power at each frequency point
            
            obj.FrequencyRange = [70e6 18e9];  % Default range
            obj.Notes = '';
            obj.TxGainStates = struct();  % Will be populated by loadTxGainStates
            obj.RxGainStates = struct();  % Will be populated by loadRxGainStates
        end
        
        function obj = addTxPath(obj, pathName, components, freqRange)
            % Add a transmit path to the configuration
            % components: cell array of RF component objects
            % freqRange: [min max] frequency range for this path
            
            idx = length(obj.TxPaths) + 1;
            obj.TxPaths(idx).Name = pathName;
            obj.TxPaths(idx).ComponentSpecs = components;  % Store specs, not objects
            obj.TxPaths(idx).FrequencyRange = freqRange;
            obj.TxPaths(idx).IsConnected = true;
        end
        
        function obj = addRxPath(obj, pathName, components, freqRange)
            % Add a receive path to the configuration
            % components: cell array of RF component objects
            % freqRange: [min max] frequency range for this path
            
            idx = length(obj.RxPaths) + 1;
            obj.RxPaths(idx).Name = pathName;
            obj.RxPaths(idx).ComponentSpecs = components;  % Store specs, not objects
            obj.RxPaths(idx).FrequencyRange = freqRange;
        end
        
        function budget = computeTxBudget(obj, pathIndex, freq)
            % Compute transmit path power budget
            % pathIndex: index of TX path to analyze
            % freq: frequency vector in Hz
            
            if pathIndex > length(obj.TxPaths)
                error('TX path index out of range');
            end
            
            path = obj.TxPaths(pathIndex);
            
            % Clone components to avoid reuse error
            clonedComponents = obj.cloneComponents(path.ComponentSpecs);
            
            % Create rfbudget object with all required properties
            budget = rfbudget('Elements', clonedComponents, ...
                'InputFrequency', freq, ...
                'AvailableInputPower', 0, ...  % 0 dBm default
                'SignalBandwidth', 1e6);  % 1 MHz default
        end
        
        function budget = computeRxBudget(obj, pathIndex, freq)
            % Compute receive path power budget
            % pathIndex: index of RX path to analyze
            % freq: frequency vector in Hz
            
            if pathIndex > length(obj.RxPaths)
                error('RX path index out of range');
            end
            
            path = obj.RxPaths(pathIndex);
            
            % Clone components to avoid reuse error
            clonedComponents = obj.cloneComponents(path.ComponentSpecs);
            
            % Create rfbudget object with all required properties
            budget = rfbudget('Elements', clonedComponents, ...
                'InputFrequency', freq, ...
                'AvailableInputPower', -30, ...  % -30 dBm default for RX
                'SignalBandwidth', 1e6);  % 1 MHz default
        end
        
        function cloned = cloneComponents(obj, components)
            % Clone a cell array of RF components
            % Components can be either:
            %   - Structs with 'RF' field and metadata
            %   - Direct RF objects (legacy support)
            cloned = cell(size(components));
            for i = 1:length(components)
                comp = components{i};
                
                % Extract RF object if this is a struct with metadata
                if isstruct(comp) && isfield(comp, 'RF')
                    rf_obj = comp.RF;
                else
                    rf_obj = comp;  % Legacy: direct RF object
                end
                
                % Clone the RF object
                if isa(rf_obj, 'amplifier')
                    cloned{i} = amplifier('Gain', rf_obj.Gain, ...
                        'NF', rf_obj.NF, 'OIP3', rf_obj.OIP3);
                elseif isa(rf_obj, 'rfelement')
                    % rfelement - only copy properties that are set
                    if rf_obj.OIP3 ~= Inf
                        cloned{i} = rfelement('Gain', rf_obj.Gain, ...
                            'NF', rf_obj.NF, 'OIP3', rf_obj.OIP3);
                    else
                        cloned{i} = rfelement('Gain', rf_obj.Gain, ...
                            'NF', rf_obj.NF);
                    end
                elseif isa(rf_obj, 'nport')
                    % nport objects must be cloned by recreating from NetworkData
                    cloned{i} = nport('NetworkData', rf_obj.NetworkData);
                    if ~isempty(rf_obj.Name)
                        cloned{i}.Name = rf_obj.Name;
                    end
                elseif isa(rf_obj, 'modulator')
                    % Modulator objects - copy main properties
                    cloned{i} = modulator('Gain', rf_obj.Gain, ...
                        'NF', rf_obj.NF, 'OIP3', rf_obj.OIP3, ...
                        'LO', rf_obj.LO, 'ConverterType', rf_obj.ConverterType);
                elseif isa(rf_obj, 'cell')
                    % Nested cell array - this is the problem!
                    error('Component %d is a nested cell array - fix component array construction', i);
                else
                    % Unknown type - this shouldn't happen
                    error('Unknown component type at index %d: %s', i, class(rf_obj));
                end
            end
        end
        
        function [gain_dB, nf_dB] = analyzeTxPath(obj, pathIndex, freq)
            % Analyze TX path gain and noise figure
            % Returns column vectors over frequency (final cascade results only)
            
            budget = obj.computeTxBudget(pathIndex, freq);
            
            % Check if results are empty
            if isempty(budget.TransducerGain) || isempty(budget.NF)
                error('Budget computation returned empty results');
            end
            
            % TransducerGain and NF are matrices: rows=freq, cols=stages
            % Take last column for final cascade result
            if size(budget.TransducerGain, 2) > 1
                gain_dB = budget.TransducerGain(:, end);
                nf_dB = budget.NF(:, end);
            else
                gain_dB = budget.TransducerGain(:);  % Force column vector
                nf_dB = budget.NF(:);  % Force column vector
            end
        end
        
        function results = analyzeTxPathPower(obj, pathIndex, freq, varargin)
            % Analyze TX path output power and EIRP with detailed power budget
            % freq: frequency vector in Hz
            % Optional: 'InputBackoff_dB' - backoff from DAC full scale (default: 0 dB)
            %           'SignalBandwidth' - signal bandwidth in Hz (default: 1 MHz)
            %
            % Returns struct with:
            %   dac_power_dBm: DAC output power
            %   power_at_antenna_dBm: Power at antenna input (before antenna gain)
            %   eirp_dBm: Equivalent Isotropic Radiated Power
            %   path_gain_dB: Total path gain (excluding antenna)
            %   antenna_gain_dB: Antenna gain
            %   frequency_Hz: Frequency vector
            
            % Parse optional inputs
            p = inputParser;
            addParameter(p, 'InputBackoff_dB', 0, @isnumeric);
            addParameter(p, 'SignalBandwidth', 1e6, @isnumeric);
            parse(p, varargin{:});
            
            backoff_dB = p.Results.InputBackoff_dB;
            
            % Get DAC output power (frequency-dependent if data available)
            if ~isempty(obj.DAC_Specs.OutputPower_Frequency_Hz) && ...
               ~isempty(obj.DAC_Specs.OutputPower_dBm)
                % Interpolate from provided frequency-dependent power curve
                dac_power_dBm = interp1(obj.DAC_Specs.OutputPower_Frequency_Hz, ...
                                        obj.DAC_Specs.OutputPower_dBm, ...
                                        freq, 'linear', 'extrap') - backoff_dB;
            else
                % Use full-scale voltage calculation (legacy method)
                dac_fullscale_V = obj.DAC_Specs.FullScaleVoltage;
                % Power into 50 ohms: P = V^2 / (8*R) for peak-to-peak voltage
                % For peak-to-peak voltage, V_rms = V_pp / (2*sqrt(2))
                % So P = (V_pp / (2*sqrt(2)))^2 / 50 = V_pp^2 / (8*50)
                dac_power_dBm = 10*log10((dac_fullscale_V^2 / (8*50)) * 1000) - backoff_dB;
            end
            
            % Get path gain (includes all components including antenna)
            [gain_total_dB, ~] = obj.analyzeTxPath(pathIndex, freq);
            
            % Get antenna gain from last component
            path = obj.TxPaths(pathIndex);
            last_comp = path.ComponentSpecs{end};
            if isstruct(last_comp) && isfield(last_comp, 'RF')
                antenna_obj = last_comp.RF;
            else
                antenna_obj = last_comp;
            end
            
            if isa(antenna_obj, 'rfelement')
                antenna_gain_dB = antenna_obj.Gain;
            else
                antenna_gain_dB = 0;  % Unknown antenna type
            end
            
            % Path gain excluding antenna
            path_gain_dB = gain_total_dB - antenna_gain_dB;
            
            % Calculate output power at antenna input (before antenna gain)
            power_at_antenna_dBm = dac_power_dBm + path_gain_dB;
            
            % Calculate EIRP (includes antenna gain)
            eirp_dBm = power_at_antenna_dBm + antenna_gain_dB;
            
            % Return results structure
            results.dac_power_dBm = dac_power_dBm;
            results.power_at_antenna_dBm = power_at_antenna_dBm;
            results.eirp_dBm = eirp_dBm;
            results.path_gain_dB = path_gain_dB;
            results.antenna_gain_dB = antenna_gain_dB;
            results.frequency_Hz = freq(:);
        end
        
        function [gain_dB, nf_dB, sensitivity_dBm] = analyzeRxPathWithADC(obj, pathIndex, freq, bandwidth_Hz, snr_required_dB)
            % Analyze RX path including ADC noise floor and sensitivity
            % freq: frequency vector in Hz
            % bandwidth_Hz: signal bandwidth
            % snr_required_dB: required SNR at ADC output
            % Returns: gain_dB - path gain
            %          nf_dB - system NF including ADC
            %          sensitivity_dBm - system sensitivity
            
            % Get RF chain performance
            [gain_rf_dB, nf_rf_dB] = obj.analyzeRxPath(pathIndex, freq);
            
            % Calculate ADC noise floor
            enob = obj.ADC_Specs.ENOB;
            fs_voltage = obj.ADC_Specs.FullScaleVoltage;
            
            % ADC quantization noise in dBFS
            adc_noise_floor_dBFS = -6.02 * enob - 1.76 - 10*log10(bandwidth_Hz / (obj.ADC_Specs.SampleRate_Gsps * 1e9));
            
            % Convert to dBm (referenced to 50 ohm)
            fs_power_dBm = 10*log10((fs_voltage^2 / (8*50)) * 1000);
            adc_noise_floor_dBm = fs_power_dBm + adc_noise_floor_dBFS;
            
            % Calculate system noise floor at ADC input
            % Thermal noise floor: -174 dBm/Hz + 10*log10(BW)
            thermal_noise_dBm = -174 + 10*log10(bandwidth_Hz);
            
            % Add RF chain NF
            rf_noise_at_input_dBm = thermal_noise_dBm + nf_rf_dB;
            
            % Noise at ADC input after RF gain
            noise_at_adc_input_dBm = rf_noise_at_input_dBm + gain_rf_dB;
            
            % Compare with ADC noise floor
            % Total noise is dominated by whichever is higher
            if noise_at_adc_input_dBm > adc_noise_floor_dBm
                % RF noise dominates
                total_noise_dBm = noise_at_adc_input_dBm;
                % System NF is just RF NF
                nf_dB = nf_rf_dB;
            else
                % ADC noise dominates
                total_noise_dBm = adc_noise_floor_dBm;
                % Calculate effective system NF
                nf_dB = nf_rf_dB + (adc_noise_floor_dBm - noise_at_adc_input_dBm);
            end
            
            gain_dB = gain_rf_dB;
            
            % Calculate sensitivity
            sensitivity_dBm = thermal_noise_dBm + nf_dB + snr_required_dB;
        end
        
        function results = analyzeRxADC(obj, pathIndex, freq, varargin)
            % Comprehensive ADC performance analysis for RX path
            % freq: frequency vector in Hz (can be scalar or vector)
            % Optional: 'SignalBandwidth' - signal bandwidth in Hz (default: 1 MHz)
            %           'RequiredSNR_dB' - required SNR at output (default: 10 dB)
            %           'InputPower_dBm' - signal power at antenna (default: -30 dBm)
            %
            % Returns struct with comprehensive ADC metrics:
            %   sensitivity_dBm: Minimum detectable signal
            %   max_input_dBm: Maximum input before ADC saturation
            %   dynamic_range_dB: Spurious-free dynamic range
            %   snr_at_adc_dB: SNR at ADC input
            %   signal_at_adc_dBm: Signal level at ADC input
            %   noise_at_adc_dBm: Noise level at ADC input
            %   adc_utilization_percent: Percentage of ADC full scale used
            %   compression_margin_dB: Margin before compression
            
            % Parse optional inputs
            p = inputParser;
            addParameter(p, 'SignalBandwidth', 1e6, @isnumeric);
            addParameter(p, 'RequiredSNR_dB', 10, @isnumeric);
            addParameter(p, 'InputPower_dBm', -30, @isnumeric);
            parse(p, varargin{:});
            
            bandwidth_Hz = p.Results.SignalBandwidth;
            snr_required_dB = p.Results.RequiredSNR_dB;
            input_power_dBm = p.Results.InputPower_dBm;
            
            % Get RF chain performance
            [gain_rf_dB, nf_rf_dB] = obj.analyzeRxPath(pathIndex, freq);
            
            % ADC specifications
            enob = obj.ADC_Specs.ENOB;
            fs_voltage = obj.ADC_Specs.FullScaleVoltage;
            sfdr_dBc = obj.ADC_Specs.SFDR_dBc;
            sample_rate_Hz = obj.ADC_Specs.SampleRate_Gsps * 1e9;
            
            % Calculate ADC full scale power in dBm
            % P = V_pp^2 / (8*R) for 50 ohm load
            adc_fullscale_dBm = 10*log10((fs_voltage^2 / (8*50)) * 1000);
            
            % Calculate ADC quantization noise floor in dBFS
            % Processing gain from oversampling
            processing_gain_dB = 10*log10(sample_rate_Hz / (2*bandwidth_Hz));
            adc_noise_floor_dBFS = -6.02 * enob - 1.76 - processing_gain_dB;
            adc_noise_floor_dBm = adc_fullscale_dBm + adc_noise_floor_dBFS;
            
            % Calculate thermal noise floor
            thermal_noise_dBm = -174 + 10*log10(bandwidth_Hz);
            
            % RF chain noise at antenna input
            rf_noise_at_input_dBm = thermal_noise_dBm + nf_rf_dB;
            
            % Signal and noise at ADC input
            signal_at_adc_dBm = input_power_dBm + gain_rf_dB;
            noise_from_rf_dBm = rf_noise_at_input_dBm + gain_rf_dB;
            
            % Total noise at ADC (RF noise + ADC quantization noise)
            % Convert to linear, add, convert back (element-wise for vectors)
            noise_rf_linear = 10.^(noise_from_rf_dBm./10);
            noise_adc_linear = 10^(adc_noise_floor_dBm/10);
            total_noise_linear = noise_rf_linear + noise_adc_linear;
            noise_at_adc_dBm = 10.*log10(total_noise_linear);
            
            % Calculate SNR at ADC
            snr_at_adc_dB = signal_at_adc_dBm - noise_at_adc_dBm;
            
            % Calculate sensitivity (minimum detectable signal)
            sensitivity_dBm = noise_at_adc_dBm + snr_required_dB - gain_rf_dB;
            
            % Calculate maximum input power (ADC saturation)
            % Leave some headroom (3 dB typical)
            compression_headroom_dB = 3;
            max_input_dBm = adc_fullscale_dBm - gain_rf_dB - compression_headroom_dB;
            
            % Calculate spurious-free dynamic range
            % SFDR limited by either ADC SFDR or two-tone IMD
            sfdr_limited_by_adc_dB = sfdr_dBc;
            dynamic_range_dB = min(sfdr_limited_by_adc_dB, ...
                                   adc_fullscale_dBm - noise_at_adc_dBm);
            
            % Calculate ADC utilization
            adc_utilization_dB = signal_at_adc_dBm - adc_fullscale_dBm;
            adc_utilization_percent = 100 .* 10.^(adc_utilization_dB./20);
            
            % Compression margin
            compression_margin_dB = adc_fullscale_dBm - signal_at_adc_dBm;
            
            % Build results structure
            results.frequency_Hz = freq(:);
            results.sensitivity_dBm = sensitivity_dBm;
            results.max_input_dBm = max_input_dBm;
            results.dynamic_range_dB = dynamic_range_dB;
            results.snr_at_adc_dB = snr_at_adc_dB;
            results.signal_at_adc_dBm = signal_at_adc_dBm;
            results.noise_at_adc_dBm = noise_at_adc_dBm;
            results.adc_fullscale_dBm = adc_fullscale_dBm;
            results.adc_utilization_percent = adc_utilization_percent;
            results.compression_margin_dB = compression_margin_dB;
            results.path_gain_dB = gain_rf_dB;
            results.path_nf_dB = nf_rf_dB;
            results.thermal_noise_dBm = thermal_noise_dBm;
            results.adc_noise_floor_dBm = adc_noise_floor_dBm;
        end
        
        function results = analyzeRxDynamicRange(obj, pathIndex, freq, bandwidth_Hz)
            % Analyze receiver dynamic range including ADC limitations
            % freq: frequency in Hz
            % bandwidth_Hz: signal bandwidth
            %
            % Returns struct with:
            %   sensitivity_dBm: Minimum detectable signal (10 dB SNR)
            %   compression_point_dBm: 1-dB compression point at antenna
            %   spurious_free_dynamic_range_dB: SFDR
            %   blocking_dynamic_range_dB: Usable dynamic range
            %   imd3_intercept_point_dBm: Third-order intercept at antenna
            
            % Get RF chain performance
            [gain_rf_dB, nf_rf_dB] = obj.analyzeRxPath(pathIndex, freq);
            
            % Get RF chain OIP3 (need to compute from budget)
            budget = obj.computeRxBudget(pathIndex, freq);
            if size(budget.OIP3, 2) > 1
                oip3_dBm = budget.OIP3(end);  % Final cascade OIP3
            else
                oip3_dBm = budget.OIP3;
            end
            
            % Calculate IIP3 at antenna
            iip3_antenna_dBm = oip3_dBm - gain_rf_dB;
            
            % ADC specifications
            enob = obj.ADC_Specs.ENOB;
            fs_voltage = obj.ADC_Specs.FullScaleVoltage;
            sfdr_dBc = obj.ADC_Specs.SFDR_dBc;
            sample_rate_Hz = obj.ADC_Specs.SampleRate_Gsps * 1e9;
            
            % ADC full scale power
            adc_fullscale_dBm = 10*log10((fs_voltage^2 / (8*50)) * 1000);
            
            % ADC noise floor
            processing_gain_dB = 10*log10(sample_rate_Hz / (2*bandwidth_Hz));
            adc_noise_floor_dBFS = -6.02 * enob - 1.76 - processing_gain_dB;
            adc_noise_floor_dBm = adc_fullscale_dBm + adc_noise_floor_dBFS;
            
            % System noise floor
            thermal_noise_dBm = -174 + 10*log10(bandwidth_Hz);
            system_noise_dBm = thermal_noise_dBm + nf_rf_dB;
            
            % Sensitivity (10 dB SNR requirement)
            sensitivity_dBm = system_noise_dBm + 10;
            
            % 1-dB compression point (limited by ADC or RF chain)
            % ADC compression is typically at ~3 dB below full scale
            adc_p1dB_at_input = adc_fullscale_dBm - 3;
            p1dB_antenna_dBm = adc_p1dB_at_input - gain_rf_dB;
            
            % SFDR (limited by ADC SFDR or two-tone IMD)
            % Two-tone IMD limited SFDR: SFDR = 2/3 * (IIP3 - Noise Floor)
            imd_limited_sfdr_dB = (2/3) * (iip3_antenna_dBm - system_noise_dBm);
            spurious_free_dynamic_range_dB = min(sfdr_dBc, imd_limited_sfdr_dB);
            
            % Blocking dynamic range (sensitivity to compression)
            blocking_dynamic_range_dB = p1dB_antenna_dBm - sensitivity_dBm;
            
            % Build results
            results.frequency_Hz = freq;
            results.sensitivity_dBm = sensitivity_dBm;
            results.compression_point_dBm = p1dB_antenna_dBm;
            results.spurious_free_dynamic_range_dB = spurious_free_dynamic_range_dB;
            results.blocking_dynamic_range_dB = blocking_dynamic_range_dB;
            results.imd3_intercept_point_dBm = iip3_antenna_dBm;
            results.system_noise_floor_dBm = system_noise_dBm;
            results.adc_fullscale_dBm = adc_fullscale_dBm;
            results.path_gain_dB = gain_rf_dB;
            results.path_nf_dB = nf_rf_dB;
        end
        
        function obj = loadTxGainStates(obj, excelFile, sheetName)
            % Load TX gain state data from Excel file
            % excelFile: path to Excel file
            % sheetName: name of sheet (e.g., 'BDR Table (LMB)')
            %
            % Expected columns:
            %   B: DR State (gain state index)
            %   H: Freq (GHz)
            %   I: Tx Power (dBm)
            
            % Read the data
            data = readtable(excelFile, 'Sheet', sheetName);
            
            % Extract columns (adjust if column names differ)
            gain_states = data.DRState;
            freq_GHz = data.Freq_GHz_;
            tx_power_dBm = data.TxPower_dBm_;
            
            % Get unique gain states and frequencies
            unique_states = unique(gain_states);
            unique_freqs = unique(freq_GHz);
            
            % Organize data by gain state
            obj.TxGainStates.NumStates = length(unique_states);
            obj.TxGainStates.StateIndices = unique_states;
            obj.TxGainStates.Frequency_GHz = unique_freqs;
            obj.TxGainStates.Frequency_Hz = unique_freqs * 1e9;
            
            % Create matrix: rows = frequencies, cols = gain states
            obj.TxGainStates.Power_dBm = zeros(length(unique_freqs), length(unique_states));
            
            for i = 1:length(gain_states)
                state_idx = find(unique_states == gain_states(i));
                freq_idx = find(abs(unique_freqs - freq_GHz(i)) < 1e-6);
                obj.TxGainStates.Power_dBm(freq_idx, state_idx) = tx_power_dBm(i);
            end
            
            fprintf('Loaded TX gain states: %d states, %d frequencies\n', ...
                length(unique_states), length(unique_freqs));
        end
        
        function obj = loadRxGainStates(obj, excelFile, sheetName)
            % Load RX gain state data from Excel file
            % excelFile: path to Excel file
            % sheetName: name of sheet (e.g., 'BDR Table (LMB)')
            %
            % Expected columns:
            %   B: DR State (gain state index)
            %   C: Gain (dB)
            %   I: Freq (GHz)
            %   J: LL (dBm) - sensitivity/lower limit
            %   K: UL (dBm) - upper limit for spur-free
            
            % Read the data
            data = readtable(excelFile, 'Sheet', sheetName);
            
            % Extract columns (adjust if column names differ)
            gain_states = data.DRState;
            gain_dB = data.Gain_dB_;
            freq_GHz = data.Freq_GHz_;
            sensitivity_dBm = data.LL_dBm_;
            upper_limit_dBm = data.UL_dBm_;
            
            % Get unique gain states and frequencies
            unique_states = unique(gain_states);
            unique_freqs = unique(freq_GHz);
            
            % Organize data by gain state
            obj.RxGainStates.NumStates = length(unique_states);
            obj.RxGainStates.StateIndices = unique_states;
            obj.RxGainStates.Frequency_GHz = unique_freqs;
            obj.RxGainStates.Frequency_Hz = unique_freqs * 1e9;
            
            % Create matrices: rows = frequencies, cols = gain states
            obj.RxGainStates.Gain_dB = zeros(length(unique_freqs), length(unique_states));
            obj.RxGainStates.Sensitivity_dBm = zeros(length(unique_freqs), length(unique_states));
            obj.RxGainStates.UpperLimit_dBm = zeros(length(unique_freqs), length(unique_states));
            
            for i = 1:length(gain_states)
                state_idx = find(unique_states == gain_states(i));
                freq_idx = find(abs(unique_freqs - freq_GHz(i)) < 1e-6);
                obj.RxGainStates.Gain_dB(freq_idx, state_idx) = gain_dB(i);
                obj.RxGainStates.Sensitivity_dBm(freq_idx, state_idx) = sensitivity_dBm(i);
                obj.RxGainStates.UpperLimit_dBm(freq_idx, state_idx) = upper_limit_dBm(i);
            end
            
            fprintf('Loaded RX gain states: %d states, %d frequencies\n', ...
                length(unique_states), length(unique_freqs));
        end
        
        function [gain_dB, nf_dB] = analyzeRxPath(obj, pathIndex, freq)
            % Analyze RX path gain and noise figure (RF chain only)
            % For full analysis including ADC, use analyzeRxPathWithADC
            % Returns column vectors over frequency (final cascade results only)
            
            budget = obj.computeRxBudget(pathIndex, freq);
            
            % Check if results are empty
            if isempty(budget.TransducerGain) || isempty(budget.NF)
                error('Budget computation returned empty results');
            end
            
            % TransducerGain and NF are matrices: rows=freq, cols=stages
            % Take last column for final cascade result
            if size(budget.TransducerGain, 2) > 1
                gain_dB = budget.TransducerGain(:, end);
                nf_dB = budget.NF(:, end);
            else
                gain_dB = budget.TransducerGain(:);  % Force column vector
                nf_dB = budget.NF(:);  % Force column vector
            end
        end
        
        function results = analyzeTxGainStates(obj, pathIndex, freq, varargin)
            % Analyze TX path performance across all gain states
            % freq: frequency vector in Hz
            % Optional: 'GainState' - specific gain state to analyze (default: all)
            %
            % Returns struct with power at each gain state
            
            p = inputParser;
            addParameter(p, 'GainState', [], @isnumeric);
            parse(p, varargin{:});
            
            requested_state = p.Results.GainState;
            
            if isempty(obj.TxGainStates.NumStates)
                error('TX gain state data not loaded. Use loadTxGainStates() first.');
            end
            
            % Get external components (after PCB)
            path = obj.TxPaths(pathIndex);
            
            % Find where PCB ends (first component after PCB cumulative element)
            % For Config 1: PCB -> Cable -> PA -> Cable -> Antenna
            external_components = path.ComponentSpecs(2:end);  % Skip PCB element
            
            % Calculate gain of external components
            freq_mid = mean(path.FrequencyRange);
            external_gain_dB = 0;
            antenna_gain_dB = 0;
            
            for i = 1:length(external_components)
                comp = external_components{i};
                if isstruct(comp) && isfield(comp, 'RF')
                    rf_obj = comp.RF;
                else
                    rf_obj = comp;
                end
                
                if isa(rf_obj, 'amplifier') || isa(rf_obj, 'rfelement')
                    if i == length(external_components)
                        antenna_gain_dB = rf_obj.Gain;
                    else
                        external_gain_dB = external_gain_dB + rf_obj.Gain;
                    end
                elseif isa(rf_obj, 'nport')
                    s_params = sparameters(rf_obj, freq_mid);
                    s21_dB = 20*log10(abs(s_params.Parameters(2,1,1)));
                    external_gain_dB = external_gain_dB + s21_dB;
                end
            end
            
            % Determine which gain states to analyze
            if isempty(requested_state)
                states_to_analyze = obj.TxGainStates.StateIndices;
            else
                states_to_analyze = requested_state;
            end
            
            % Initialize results
            results.frequency_Hz = freq(:);
            results.gain_states = states_to_analyze;
            results.pcb_power_dBm = zeros(length(freq), length(states_to_analyze));
            results.power_at_antenna_dBm = zeros(length(freq), length(states_to_analyze));
            results.eirp_dBm = zeros(length(freq), length(states_to_analyze));
            
            % Interpolate PCB output power for each gain state
            for i = 1:length(states_to_analyze)
                state = states_to_analyze(i);
                state_idx = find(obj.TxGainStates.StateIndices == state);
                
                % Interpolate PCB power at requested frequencies
                pcb_power = interp1(obj.TxGainStates.Frequency_Hz, ...
                                   obj.TxGainStates.Power_dBm(:, state_idx), ...
                                   freq, 'linear', 'extrap');
                
                results.pcb_power_dBm(:, i) = pcb_power;
                results.power_at_antenna_dBm(:, i) = pcb_power + external_gain_dB;
                results.eirp_dBm(:, i) = results.power_at_antenna_dBm(:, i) + antenna_gain_dB;
            end
            
            results.external_gain_dB = external_gain_dB;
            results.antenna_gain_dB = antenna_gain_dB;
        end
        
        function results = analyzeRxGainStates(obj, pathIndex, freq, varargin)
            % Analyze RX path performance across all gain states
            % freq: frequency vector in Hz
            % Optional: 'GainState' - specific gain state to analyze (default: all)
            %
            % Returns struct with sensitivity and limits at each gain state
            
            p = inputParser;
            addParameter(p, 'GainState', [], @isnumeric);
            parse(p, varargin{:});
            
            requested_state = p.Results.GainState;
            
            if isempty(obj.RxGainStates.NumStates)
                error('RX gain state data not loaded. Use loadRxGainStates() first.');
            end
            
            % Determine which gain states to analyze
            if isempty(requested_state)
                states_to_analyze = obj.RxGainStates.StateIndices;
            else
                states_to_analyze = requested_state;
            end
            
            % Initialize results
            results.frequency_Hz = freq(:);
            results.gain_states = states_to_analyze;
            results.gain_dB = zeros(length(freq), length(states_to_analyze));
            results.sensitivity_dBm = zeros(length(freq), length(states_to_analyze));
            results.upper_limit_dBm = zeros(length(freq), length(states_to_analyze));
            results.dynamic_range_dB = zeros(length(freq), length(states_to_analyze));
            
            % Interpolate for each gain state
            for i = 1:length(states_to_analyze)
                state = states_to_analyze(i);
                state_idx = find(obj.RxGainStates.StateIndices == state);
                
                % Interpolate at requested frequencies
                results.gain_dB(:, i) = interp1(obj.RxGainStates.Frequency_Hz, ...
                                               obj.RxGainStates.Gain_dB(:, state_idx), ...
                                               freq, 'linear', 'extrap');
                results.sensitivity_dBm(:, i) = interp1(obj.RxGainStates.Frequency_Hz, ...
                                                       obj.RxGainStates.Sensitivity_dBm(:, state_idx), ...
                                                       freq, 'linear', 'extrap');
                results.upper_limit_dBm(:, i) = interp1(obj.RxGainStates.Frequency_Hz, ...
                                                       obj.RxGainStates.UpperLimit_dBm(:, state_idx), ...
                                                       freq, 'linear', 'extrap');
                results.dynamic_range_dB(:, i) = results.upper_limit_dBm(:, i) - results.sensitivity_dBm(:, i);
            end
        end
        
        function summary = getSummary(obj)
            % Get a summary of the configuration
            
            summary = sprintf('Configuration: %s\n', obj.ConfigName);
            summary = [summary sprintf('Sample Rate: %.1f Gsps\n', obj.SampleRate)];
            summary = [summary sprintf('TX Paths: %d\n', length(obj.TxPaths))];
            summary = [summary sprintf('RX Paths: %d\n', length(obj.RxPaths))];
            summary = [summary sprintf('Frequency Range: %.0f MHz - %.1f GHz\n', ...
                obj.FrequencyRange(1)/1e6, obj.FrequencyRange(2)/1e9)];
            
            fprintf('%s\n', summary);
        end
        
        function plotPathBudget(obj, pathType, pathIndex, freq)
            % Plot gain and noise figure for a path
            % pathType: 'tx' or 'rx'
            % pathIndex: which path to plot
            % freq: frequency vector in Hz
            
            if strcmpi(pathType, 'tx')
                [gain_dB, nf_dB] = obj.analyzeTxPath(pathIndex, freq);
                pathName = obj.TxPaths(pathIndex).Name;
            else
                [gain_dB, nf_dB] = obj.analyzeRxPath(pathIndex, freq);
                pathName = obj.RxPaths(pathIndex).Name;
            end
            
            figure;
            subplot(2,1,1);
            plot(freq/1e9, gain_dB, 'LineWidth', 2);
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Gain (dB)');
            title([obj.ConfigName ' - ' pathName ' Gain']);
            
            subplot(2,1,2);
            plot(freq/1e9, nf_dB, 'LineWidth', 2);
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Noise Figure (dB)');
            title([obj.ConfigName ' - ' pathName ' Noise Figure']);
        end
        
        function plotTxPowerBudget(obj, pathIndex, freq, varargin)
            % Plot comprehensive TX power budget analysis
            % freq: frequency vector in Hz
            % Optional: 'InputBackoff_dB' - backoff from full scale
            
            results = obj.analyzeTxPathPower(pathIndex, freq, varargin{:});
            pathName = obj.TxPaths(pathIndex).Name;
            
            figure('Position', [100 100 1200 800]);
            
            % Plot 1: Power levels through chain
            subplot(2,2,1);
            % DAC power might be scalar or vector depending on if freq-dependent power is specified
            if isscalar(results.dac_power_dBm)
                dac_power_vec = results.dac_power_dBm .* ones(size(freq));
            else
                dac_power_vec = results.dac_power_dBm;
            end
            plot(freq/1e9, dac_power_vec, 'b-', 'LineWidth', 2, 'DisplayName', 'DAC Output');
            hold on;
            plot(freq/1e9, results.power_at_antenna_dBm, 'r-', 'LineWidth', 2, 'DisplayName', 'At Antenna Input');
            plot(freq/1e9, results.eirp_dBm, 'g-', 'LineWidth', 2, 'DisplayName', 'EIRP');
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Power (dBm)');
            title([obj.ConfigName ' - ' pathName ' - Power Levels']);
            legend('show', 'Location', 'best');
            
            % Plot 2: Path gain breakdown
            subplot(2,2,2);
            plot(freq/1e9, results.path_gain_dB, 'b-', 'LineWidth', 2, 'DisplayName', 'Path Gain (no ant)');
            hold on;
            % Antenna gain is scalar
            ant_gain_vec = results.antenna_gain_dB .* ones(size(freq));
            plot(freq/1e9, ant_gain_vec, 'r--', 'LineWidth', 2, 'DisplayName', 'Antenna Gain');
            yline(0, 'k--', 'LineWidth', 1);
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Gain (dB)');
            title('Gain Breakdown');
            legend('show', 'Location', 'best');
            
            % Plot 3: EIRP vs Frequency (larger)
            subplot(2,2,3:4);
            plot(freq/1e9, results.eirp_dBm, 'LineWidth', 3, 'Color', [0 0.5 0]);
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('EIRP (dBm)');
            title([obj.ConfigName ' - ' pathName ' - Equivalent Isotropic Radiated Power']);
            set(gca, 'FontSize', 12);
            
            % Add summary text
            avg_eirp = mean(results.eirp_dBm);
            min_eirp = min(results.eirp_dBm);
            max_eirp = max(results.eirp_dBm);
            if isscalar(results.dac_power_dBm)
                dac_power_str = sprintf('%.1f dBm', results.dac_power_dBm);
            else
                dac_power_str = sprintf('%.1f to %.1f dBm', min(results.dac_power_dBm), max(results.dac_power_dBm));
            end
            str = sprintf('DAC: %s\nAvg EIRP: %.1f dBm\nMin/Max: %.1f / %.1f dBm', ...
                         dac_power_str, avg_eirp, min_eirp, max_eirp);
            text(0.02, 0.98, str, 'Units', 'normalized', 'VerticalAlignment', 'top', ...
                 'BackgroundColor', 'white', 'EdgeColor', 'black', 'FontSize', 10);
        end
        
        function plotRxADCPerformance(obj, pathIndex, freq, varargin)
            % Plot comprehensive RX ADC performance analysis
            % freq: frequency vector in Hz
            % Optional: 'SignalBandwidth', 'InputPower_dBm', 'RequiredSNR_dB'
            
            results = obj.analyzeRxADC(pathIndex, freq, varargin{:});
            pathName = obj.RxPaths(pathIndex).Name;
            
            figure('Position', [100 100 1400 900]);
            
            % Plot 1: Signal and noise levels
            subplot(3,2,1);
            plot(freq/1e9, results.signal_at_adc_dBm, 'b-', 'LineWidth', 2, 'DisplayName', 'Signal');
            hold on;
            plot(freq/1e9, results.noise_at_adc_dBm, 'r-', 'LineWidth', 2, 'DisplayName', 'Total Noise');
            plot(freq/1e9, results.adc_fullscale_dBm * ones(size(freq)), 'k--', 'LineWidth', 1.5, 'DisplayName', 'ADC Full Scale');
            plot(freq/1e9, results.adc_noise_floor_dBm * ones(size(freq)), 'm--', 'LineWidth', 1, 'DisplayName', 'ADC Noise Floor');
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Power (dBm)');
            title('Signal and Noise Levels at ADC');
            legend('show', 'Location', 'best');
            
            % Plot 2: SNR
            subplot(3,2,2);
            plot(freq/1e9, results.snr_at_adc_dB, 'LineWidth', 2, 'Color', [0 0.5 0]);
            hold on;
            yline(10, 'r--', 'LineWidth', 1.5, 'DisplayName', '10 dB (typical min)');
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('SNR (dB)');
            title('SNR at ADC Input');
            legend('show');
            
            % Plot 3: Dynamic Range
            subplot(3,2,3);
            dr_vec = results.dynamic_range_dB .* ones(size(freq));
            plot(freq/1e9, dr_vec, 'LineWidth', 2, 'Color', [0.5 0 0.5]);
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Dynamic Range (dB)');
            title('Spurious-Free Dynamic Range');
            ylim([min(dr_vec)-5, max(dr_vec)+5]);
            
            % Plot 4: ADC Utilization
            subplot(3,2,4);
            plot(freq/1e9, results.adc_utilization_percent, 'LineWidth', 2, 'Color', [1 0.5 0]);
            hold on;
            yline(100, 'r--', 'LineWidth', 1.5, 'DisplayName', '100% (Full Scale)');
            yline(70, 'g--', 'LineWidth', 1, 'DisplayName', '70% (typical target)');
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Utilization (%)');
            title('ADC Utilization');
            legend('show', 'Location', 'best');
            
            % Plot 5: Sensitivity and Max Input
            subplot(3,2,5);
            plot(freq/1e9, results.sensitivity_dBm, 'b-', 'LineWidth', 2, 'DisplayName', 'Sensitivity');
            hold on;
            plot(freq/1e9, results.max_input_dBm, 'r-', 'LineWidth', 2, 'DisplayName', 'Max Input');
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Power (dBm)');
            title('Input Power Range');
            legend('show');
            
            % Plot 6: Compression Margin
            subplot(3,2,6);
            plot(freq/1e9, results.compression_margin_dB, 'LineWidth', 2, 'Color', [0.8 0.2 0.2]);
            hold on;
            yline(3, 'g--', 'LineWidth', 1.5, 'DisplayName', '3 dB (min margin)');
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Margin (dB)');
            title('Compression Margin');
            legend('show');
            
            sgtitle([obj.ConfigName ' - ' pathName ' - ADC Performance Analysis'], 'FontSize', 14, 'FontWeight', 'bold');
        end
        
        function plotTxGainStates(obj, pathIndex, freq)
            % Plot TX performance across all gain states
            % freq: frequency vector in Hz
            
            results = obj.analyzeTxGainStates(pathIndex, freq);
            pathName = obj.TxPaths(pathIndex).Name;
            
            figure('Position', [100 100 1400 800]);
            
            % Plot 1: PCB Output Power
            subplot(2,2,1);
            for i = 1:length(results.gain_states)
                plot(freq/1e9, results.pcb_power_dBm(:,i), 'LineWidth', 2, ...
                    'DisplayName', sprintf('State %d', results.gain_states(i)));
                hold on;
            end
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Power (dBm)');
            title('PCB Output Power');
            legend('show', 'Location', 'best');
            
            % Plot 2: Power at Antenna Input
            subplot(2,2,2);
            for i = 1:length(results.gain_states)
                plot(freq/1e9, results.power_at_antenna_dBm(:,i), 'LineWidth', 2, ...
                    'DisplayName', sprintf('State %d', results.gain_states(i)));
                hold on;
            end
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Power (dBm)');
            title('Power at Antenna Input');
            legend('show', 'Location', 'best');
            
            % Plot 3: EIRP
            subplot(2,2,3:4);
            for i = 1:length(results.gain_states)
                plot(freq/1e9, results.eirp_dBm(:,i), 'LineWidth', 2, ...
                    'DisplayName', sprintf('State %d', results.gain_states(i)));
                hold on;
            end
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('EIRP (dBm)');
            title('Equivalent Isotropic Radiated Power');
            legend('show', 'Location', 'best');
            set(gca, 'FontSize', 12);
            
            sgtitle([obj.ConfigName ' - ' pathName ' - TX Gain State Comparison'], ...
                'FontSize', 14, 'FontWeight', 'bold');
        end
        
        function plotRxGainStates(obj, pathIndex, freq)
            % Plot RX performance across all gain states
            % freq: frequency vector in Hz
            
            results = obj.analyzeRxGainStates(pathIndex, freq);
            pathName = obj.RxPaths(pathIndex).Name;
            
            figure('Position', [100 100 1400 900]);
            
            % Plot 1: Gain
            subplot(2,2,1);
            for i = 1:length(results.gain_states)
                plot(freq/1e9, results.gain_dB(:,i), 'LineWidth', 2, ...
                    'DisplayName', sprintf('State %d', results.gain_states(i)));
                hold on;
            end
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Gain (dB)');
            title('RX Gain');
            legend('show', 'Location', 'best');
            
            % Plot 2: Sensitivity
            subplot(2,2,2);
            for i = 1:length(results.gain_states)
                plot(freq/1e9, results.sensitivity_dBm(:,i), 'LineWidth', 2, ...
                    'DisplayName', sprintf('State %d', results.gain_states(i)));
                hold on;
            end
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Sensitivity (dBm)');
            title('Sensitivity (Lower Limit)');
            legend('show', 'Location', 'best');
            
            % Plot 3: Upper Limit
            subplot(2,2,3);
            for i = 1:length(results.gain_states)
                plot(freq/1e9, results.upper_limit_dBm(:,i), 'LineWidth', 2, ...
                    'DisplayName', sprintf('State %d', results.gain_states(i)));
                hold on;
            end
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Upper Limit (dBm)');
            title('Spur-Free Upper Limit');
            legend('show', 'Location', 'best');
            
            % Plot 4: Dynamic Range
            subplot(2,2,4);
            for i = 1:length(results.gain_states)
                plot(freq/1e9, results.dynamic_range_dB(:,i), 'LineWidth', 2, ...
                    'DisplayName', sprintf('State %d', results.gain_states(i)));
                hold on;
            end
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Dynamic Range (dB)');
            title('Dynamic Range (UL - LL)');
            legend('show', 'Location', 'best');
            
            sgtitle([obj.ConfigName ' - ' pathName ' - RX Gain State Comparison'], ...
                'FontSize', 14, 'FontWeight', 'bold');
        end
        
        function printTxPowerSummary(obj, pathIndex, freq_test)
            % Print summary of TX power performance at test frequencies
            % freq_test: vector of test frequencies in Hz
            
            pathName = obj.TxPaths(pathIndex).Name;
            fprintf('\n========================================\n');
            fprintf('TX Power Summary: %s - %s\n', obj.ConfigName, pathName);
            fprintf('========================================\n');
            fprintf('DAC Full Scale: %.2f Vpp, Sample Rate: %.1f Gsps\n', ...
                    obj.DAC_Specs.FullScaleVoltage, obj.DAC_Specs.SampleRate_Gsps);
            fprintf('\nFrequency Analysis:\n');
            fprintf('%-12s %-12s %-12s %-12s %-12s\n', ...
                    'Freq (GHz)', 'DAC (dBm)', 'Path Gain', 'At Ant (dBm)', 'EIRP (dBm)');
            fprintf('------------------------------------------------------------------------\n');
            
            for f = freq_test(:)'
                results = obj.analyzeTxPathPower(pathIndex, f);
                fprintf('%-12.2f %-12.1f %-12.1f %-12.1f %-12.1f\n', ...
                        f/1e9, results.dac_power_dBm, results.path_gain_dB, ...
                        results.power_at_antenna_dBm, results.eirp_dBm);
            end
            fprintf('========================================\n\n');
        end
        
        function printRxADCSummary(obj, pathIndex, freq_test, varargin)
            % Print summary of RX ADC performance at test frequencies
            % freq_test: vector of test frequencies in Hz
            % Optional: 'SignalBandwidth', 'InputPower_dBm'
            
            pathName = obj.RxPaths(pathIndex).Name;
            fprintf('\n========================================\n');
            fprintf('RX ADC Summary: %s - %s\n', obj.ConfigName, pathName);
            fprintf('========================================\n');
            fprintf('ADC: %.1f Gsps, ENOB: %.1f bits, Full Scale: %.2f Vpp\n', ...
                    obj.ADC_Specs.SampleRate_Gsps, obj.ADC_Specs.ENOB, obj.ADC_Specs.FullScaleVoltage);
            fprintf('\nFrequency Analysis:\n');
            fprintf('%-10s %-10s %-10s %-10s %-10s %-10s\n', ...
                    'Freq (GHz)', 'Sens(dBm)', 'SNR (dB)', 'DR (dB)', 'Max In', 'Util(%)');
            fprintf('------------------------------------------------------------------------\n');
            
            for f = freq_test(:)'
                results = obj.analyzeRxADC(pathIndex, f, varargin{:});
                fprintf('%-10.2f %-10.1f %-10.1f %-10.1f %-10.1f %-10.1f\n', ...
                        f/1e9, results.sensitivity_dBm, results.snr_at_adc_dB, ...
                        results.dynamic_range_dB, results.max_input_dBm, ...
                        results.adc_utilization_percent);
            end
            fprintf('========================================\n\n');
        end
        
        function exportToExcel(obj, filename)
            % Export system configuration to Excel with metadata and performance
            % filename: output Excel filename (e.g., 'system_config.xlsx')
            
            fprintf('Exporting %s to Excel...\n', obj.ConfigName);
            
            % Export each RX path
            for i = 1:length(obj.RxPaths)
                path = obj.RxPaths(i);
                sheetName = sprintf('RX_%d_%s', i, matlab.lang.makeValidName(path.Name));
                sheetName = sheetName(1:min(31, length(sheetName)));  % Excel limit
                
                obj.exportPathToSheet(filename, sheetName, path, 'RX', i);
            end
            
            % Export each TX path
            for i = 1:length(obj.TxPaths)
                path = obj.TxPaths(i);
                if ~path.IsConnected
                    continue;  % Skip unused paths
                end
                sheetName = sprintf('TX_%d_%s', i, matlab.lang.makeValidName(path.Name));
                sheetName = sheetName(1:min(31, length(sheetName)));
                
                obj.exportPathToSheet(filename, sheetName, path, 'TX', i);
            end
            
            fprintf('Export complete: %s\n', filename);
        end
        
        function exportPathToSheet(obj, filename, sheetName, path, pathType, pathIndex)
            % Export a single path to an Excel sheet
            
            % Create component list with metadata
            components = path.ComponentSpecs;
            numComps = length(components);
            
            % Build component table
            compData = cell(numComps + 1, 6);  % +1 for header
            compData(1,:) = {'Component', 'Part Number', 'Manufacturer', 'Diagram ID', 'Gain (dB)', 'NF (dB)'};
            
            % Calculate mid-frequency for nport components
            freq_mid = mean(path.FrequencyRange);
            
            for i = 1:numComps
                comp = components{i};
                if isstruct(comp) && isfield(comp, 'RF')
                    rf_obj = comp.RF;
                    pn = comp.PartNumber;
                    mfg = comp.Manufacturer;
                    did = comp.DiagramID;
                else
                    rf_obj = comp;
                    pn = 'N/A';
                    mfg = 'N/A';
                    did = 'N/A';
                end
                
                % Get RF specs
                if isa(rf_obj, 'amplifier') || isa(rf_obj, 'rfelement')
                    gain = rf_obj.Gain;
                    nf = rf_obj.NF;
                elseif isa(rf_obj, 'nport')
                    % For nport (cables), calculate S21 at mid-frequency
                    try
                        s_params = sparameters(rf_obj, freq_mid);
                        s21_mag = abs(s_params.Parameters(2,1,1));
                        gain_linear = s21_mag;
                        gain = 20*log10(gain_linear);  % Convert to dB
                        nf = -gain;  % For passive device, NF = Loss
                    catch
                        gain = 'Error';
                        nf = 'Error';
                    end
                else
                    gain = 'N/A';
                    nf = 'N/A';
                end
                
                compData{i+1, 1} = sprintf('Stage %d', i);
                compData{i+1, 2} = pn;
                compData{i+1, 3} = mfg;
                compData{i+1, 4} = did;
                compData{i+1, 5} = gain;
                compData{i+1, 6} = nf;
            end
            
            % Add cumulative performance at key frequencies
            freq_points = [500e6 1e9 2e9 5e9 10e9 15e9];  % Test frequencies
            
            if strcmp(pathType, 'TX')
                % Check if gain state data is available
                if ~isempty(obj.TxGainStates) && isfield(obj.TxGainStates, 'NumStates')
                    % TX Path with gain states
                    num_states = obj.TxGainStates.NumStates;
                    
                    % Create header row
                    cumData = cell(length(freq_points) * num_states + 2, 6);
                    cumData{1,1} = '';
                    cumData{2,1} = 'Gain State';
                    cumData{2,2} = 'Frequency (GHz)';
                    cumData{2,3} = 'PCB Power (dBm)';
                    cumData{2,4} = 'Power at Antenna (dBm)';
                    cumData{2,5} = 'EIRP (dBm)';
                    cumData{2,6} = 'EIRP (Watts)';
                    
                    % Analyze all gain states
                    tx_results = obj.analyzeTxGainStates(pathIndex, freq_points);
                    
                    row_idx = 3;
                    for state_idx = 1:num_states
                        for freq_idx = 1:length(freq_points)
                            freq = freq_points(freq_idx);
                            
                            % Extract data for this state and frequency
                            pcb_power = tx_results.pcb_power_dBm(freq_idx, state_idx);
                            power_at_ant = tx_results.power_at_antenna_dBm(freq_idx, state_idx);
                            eirp_dBm = tx_results.eirp_dBm(freq_idx, state_idx);
                            eirp_watts = 10^((eirp_dBm - 30)/10);
                            
                            cumData{row_idx, 1} = obj.TxGainStates.StateIndices(state_idx);
                            cumData{row_idx, 2} = freq/1e9;
                            cumData{row_idx, 3} = pcb_power;
                            cumData{row_idx, 4} = power_at_ant;
                            cumData{row_idx, 5} = eirp_dBm;
                            cumData{row_idx, 6} = eirp_watts;
                            row_idx = row_idx + 1;
                        end
                    end
                else
                    % TX Path without gain states (legacy)
                    cumData = cell(length(freq_points) + 2, 6);
                    cumData{1,1} = '';
                    cumData{2,1} = 'Frequency (GHz)';
                    cumData{2,2} = 'Cumulative Gain (dB)';
                    cumData{2,3} = 'DAC Power (dBm)';
                    cumData{2,4} = 'Power at Antenna (dBm)';
                    cumData{2,5} = 'EIRP (dBm)';
                    cumData{2,6} = 'EIRP (Watts)';
                    
                    for i = 1:length(freq_points)
                        freq = freq_points(i);
                        if freq >= path.FrequencyRange(1) && freq <= path.FrequencyRange(2)
                            [gain, ~] = obj.analyzeTxPath(pathIndex, freq);
                            tx_power = obj.analyzeTxPathPower(pathIndex, freq);
                            eirp_watts = 10^((tx_power.eirp_dBm - 30)/10);
                            
                            cumData{i+2, 1} = freq/1e9;
                            cumData{i+2, 2} = gain;
                            cumData{i+2, 3} = tx_power.dac_power_dBm;
                            cumData{i+2, 4} = tx_power.power_at_antenna_dBm;
                            cumData{i+2, 5} = tx_power.eirp_dBm;
                            cumData{i+2, 6} = eirp_watts;
                        else
                            cumData{i+2, 1} = freq/1e9;
                            cumData{i+2, 2} = 'Out of range';
                            cumData{i+2, 3} = 'Out of range';
                            cumData{i+2, 4} = 'Out of range';
                            cumData{i+2, 5} = 'Out of range';
                            cumData{i+2, 6} = 'Out of range';
                        end
                    end
                end
            else
                % RX Path
                if ~isempty(obj.RxGainStates) && isfield(obj.RxGainStates, 'NumStates')
                    % RX Path with gain states
                    num_states = obj.RxGainStates.NumStates;
                    
                    % Create header row
                    cumData = cell(length(freq_points) * num_states + 2, 5);
                    cumData{1,1} = '';
                    cumData{2,1} = 'Gain State';
                    cumData{2,2} = 'Frequency (GHz)';
                    cumData{2,3} = 'Gain (dB)';
                    cumData{2,4} = 'Sensitivity (dBm)';
                    cumData{2,5} = 'Upper Limit (dBm)';
                    
                    % Analyze all gain states
                    rx_results = obj.analyzeRxGainStates(pathIndex, freq_points);
                    
                    row_idx = 3;
                    for state_idx = 1:num_states
                        for freq_idx = 1:length(freq_points)
                            freq = freq_points(freq_idx);
                            
                            cumData{row_idx, 1} = obj.RxGainStates.StateIndices(state_idx);
                            cumData{row_idx, 2} = freq/1e9;
                            cumData{row_idx, 3} = rx_results.gain_dB(freq_idx, state_idx);
                            cumData{row_idx, 4} = rx_results.sensitivity_dBm(freq_idx, state_idx);
                            cumData{row_idx, 5} = rx_results.upper_limit_dBm(freq_idx, state_idx);
                            row_idx = row_idx + 1;
                        end
                    end
                else
                    % RX Path without gain states (legacy)
                    cumData = cell(length(freq_points) + 2, 3);
                    cumData{1,1} = '';
                    cumData{2,1} = 'Frequency (GHz)';
                    cumData{2,2} = 'Cumulative Gain (dB)';
                    cumData{2,3} = 'Cumulative NF (dB)';
                    
                    for i = 1:length(freq_points)
                        freq = freq_points(i);
                        if freq >= path.FrequencyRange(1) && freq <= path.FrequencyRange(2)
                            [gain, nf] = obj.analyzeRxPath(pathIndex, freq);
                            cumData{i+2, 1} = freq/1e9;
                            cumData{i+2, 2} = gain;
                            cumData{i+2, 3} = nf;
                        else
                            cumData{i+2, 1} = freq/1e9;
                            cumData{i+2, 2} = 'Out of range';
                            cumData{i+2, 3} = 'Out of range';
                        end
                    end
                end
            end
            
            % Write to Excel
            writecell(compData, filename, 'Sheet', sheetName, 'Range', 'A1');
            writecell(cumData, filename, 'Sheet', sheetName, 'Range', sprintf('A%d', numComps + 3));
        end
        
    end
    
    methods (Static)
        function compareConfigs(config1, config2, pathType, pathIdx, freq)
            % Static method to compare two configurations
            % pathType: 'tx' or 'rx'
            % pathIdx: which path to compare
            % freq: frequency vector
            
            if strcmpi(pathType, 'tx')
                [g1, nf1] = config1.analyzeTxPath(pathIdx, freq);
                [g2, nf2] = config2.analyzeTxPath(pathIdx, freq);
                name1 = config1.TxPaths(pathIdx).Name;
                name2 = config2.TxPaths(pathIdx).Name;
            else
                [g1, nf1] = config1.analyzeRxPath(pathIdx, freq);
                [g2, nf2] = config2.analyzeRxPath(pathIdx, freq);
                name1 = config1.RxPaths(pathIdx).Name;
                name2 = config2.RxPaths(pathIdx).Name;
            end
            
            figure;
            subplot(2,1,1);
            plot(freq/1e9, g1, 'LineWidth', 2, 'DisplayName', config1.ConfigName);
            hold on;
            plot(freq/1e9, g2, 'LineWidth', 2, 'DisplayName', config2.ConfigName);
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Gain (dB)');
            title(sprintf('Gain Comparison - %s', name1));
            legend('show');
            
            subplot(2,1,2);
            plot(freq/1e9, nf1, 'LineWidth', 2, 'DisplayName', config1.ConfigName);
            hold on;
            plot(freq/1e9, nf2, 'LineWidth', 2, 'DisplayName', config2.ConfigName);
            grid on;
            xlabel('Frequency (GHz)');
            ylabel('Noise Figure (dB)');
            title(sprintf('NF Comparison - %s', name1));
            legend('show');
        end
    end
end
