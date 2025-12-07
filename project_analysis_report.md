# Project Analysis Report: Electronic Warfare System Analysis Framework

## Project Summary

This project is a sophisticated Python-based framework designed for the simulation, analysis, and design review of complex radio frequency (RF) systems, likely for Electronic Warfare (EW) or SIGINT applications.

**Key Aspects:**

*   **Purpose:** The main goal is to automate the generation of technical design reviews by running various analyses on a consistent system model and compiling the results into a PowerPoint presentation.
*   **Evolution:** The project shows a clear transition from standalone MATLAB analysis scripts (found in directories like `adc`, `direction_finding`) to a more integrated and modular Python framework. The Python packages (`adc_analysis`, `direction_finding_analysis`, etc.) are essentially robust versions of these MATLAB prototypes.
*   **Centralized Configuration:** A critical architectural element is the `system_config` module. A single `system_config.yaml` file acts as the "single source of truth" for all hardware parameters (e.g., ADC, RF Chains, Antennas). This configuration is loaded into type-safe Python dataclasses, ensuring consistency across all analyses.
*   **Modular Analysis:** The project is structured with several distinct analysis modules, each focusing on a specific aspect of system performance:
    *   `adc_analysis`: Analyzes digitizer performance.
    *   `antenna_coverage_analysis`: Evaluates overall antenna gain patterns.
    *   `direction_finding_analysis`: Determines angle of arrival estimation accuracy.
    *   `ekf_geolocation`: Assesses emitter geolocation performance using an Extended Kalman Filter.
    *   `esm_analysis`: Calculates detection range and sensitivity against defined threats.
    *   `rf_chain_analysis`: Performs signal path link budget calculations (gain, noise figure).
*   **Flexible Architecture:** Each Python analysis module is designed to be run independently using local configuration files for development, but it also includes a `load_from_system_config` function to integrate seamlessly with the central `system_config` for broader workflows.
*   **Automated Reporting:** The `reporting` module, particularly `generate_design_review.py`, is where all analyses converge. It orchestrates the execution of each analysis, collects key results and plots, and then programmatically generates a complete PowerPoint design review presentation.

In essence, this project functions as a Model-Based Systems Engineering (MBSE) tool, leveraging a central system model to automate performance analysis and generate engineering documentation, which is crucial for rapid design iterations and trade studies.

## Current State Assessment

**Strengths:**
*   **Architecture:** The `system_config` central "source of truth" pattern is excellent. `direction_finding_analysis` and `esm_analysis` correctly link back to the `rf_chain` noise figure calculations when using the `load_from_system_config` loaders.
*   **Modularity:** The separation of concerns (RF chain vs. ESM vs. DF) is clean.

**Gaps & Weaknesses:**
1.  **Missing Pulse Analysis:** While `esm_analysis` defines pulse parameters (PRI, Pulse Width) for threats, it **does not analyze them**. It only checks "Detection" (SNR > Threshold). It completely lacks logic for "Measurement Accuracy" (e.g., "Can I measure the frequency to within 1 MHz?" or "What is the Probability of Intercept for a given pulse train?").
2.  **ADC Isolation:** `adc_analysis` is currently a silo. It calculates detailed metrics like SFDR and SINAD, but these do not explicitly feed into the ESM False Alarm Rate or Sensitivity calculations beyond a simple noise figure number.
3.  **Lack of Formal Requirements:** The project has *Hardware Specifications* (what we built) but lacks *System Requirements* (what we need). There is no automated check to say "Pass/Fail" against a requirement like "Frequency Accuracy < 1 MHz" or "Direction Finding Accuracy < 2 degrees RMS".

## Recommended Updates for Comprehensive EW System Analysis

Here is a prioritized list of updates to make the system more comprehensive and cohesive for Electronic Warfare system analysis:

### 1. Implement Pulse Parameter Measurement Analysis (High Priority)
**Justification:** An EW system's primary function is not just to detect but to accurately characterize emitter pulses. The current framework only models detection. The analysis must account for the specific digital signal processing chain (High-Speed ADC $\rightarrow$ DDC $\rightarrow$ Narrowband Channelizer) and the specific measurement algorithms used (e.g., DLFM).
**Action:**
*   **Update `system_config.yaml`:** Explicitly define the bandwidth hierarchy: `adc_sample_rate_gsps` (40+), `instantaneous_bandwidth_ghz` (1.0), and `channel_bandwidth_mhz` (20.0).
*   **Expand `esm_analysis`:** Add a `MeasurementAccuracy` module that models the specific signal chain:
    *   **Noise Rejection (Process Gain):** Calculate effective SNR at the measurement point (e.g., 20 MHz channel) by adding noise rejection gain: $10 \log_{10}(BW_{adc}/BW_{channel})$. *Note: Explicitly distinguish this from coherent integration gain; we are rejecting noise, not summing signal.*
*   **Apply Specific Error Models:**
    *   **Frequency Accuracy (DLFM):** Model using **Delay Line Frequency Measurement** physics. Accuracy $\propto \frac{1}{SNR \cdot \tau_{delay}}$. Longer delays improve accuracy but risk ambiguity.
    *   **Time of Arrival (TOA):** Model as a function of **Channel Bandwidth** (Rise Time) and SNR. Explicitly account for the degradation in timing resolution due to the 20 MHz bandwidth limiting, despite the high ADC rate.
    *   **Pulse Width:** Derived from the variance of two TOA measurements ($\sigma_{PW} \approx \sqrt{2} \cdot \sigma_{TOA}$). 
*   **Outputs:** Produce plots of "RMS Error vs. Input SNR" for each parameter, clearly showing the system's limit of precision.

### 2. Create a `system_requirements` Module and Compliance Matrix (High Priority)
**Justification:** To transition from a "simulation tool" to a "verification tool", the project needs a formal way to define and check against system-level performance requirements.
**Action:**
*   **New Configuration File:** Create a new YAML file (e.g., `system_config/requirements.yaml`) to formally define key system performance requirements (e.g., `req_freq_accuracy_rms_mhz: 1.0`, `req_direction_finding_accuracy_rms_deg: 2.0`, `req_dynamic_range_db: 60.0`).
*   **Integrate Checker:** Develop a Python module to load these requirements and compare them against the calculated performance from `esm_analysis`, `direction_finding_analysis`, `ekf_geolocation`, etc.
*   **Reporting:** Update `reporting/generate_design_review.py` to include a "Compliance Matrix" that explicitly shows a Pass/Fail status for each requirement, along with the calculated value.

### 3. Integrate ADC Spurious Performance & Distinguish False Alarm Types (Medium Priority)
**Justification:** A robust analysis must distinguish between *statistical* false alarms (noise) and *deterministic* false alarms (hardware artifacts).
**Action:**
*   **Statistical False Alarm Rate (FAR) Analysis:**
    *   **Threshold Setting:** The analysis should explicitly account for the threshold being set a certain dB level *above the noise floor* (e.g., in `esm_analysis`), which is a common technique to manage and reduce the statistical false alarm rate.
    *   **Question:** "How low can I set my threshold to see weak signals without random noise triggering detection?"
    *   **Driver:** Thermal Noise Floor (from `rf_chain`), Receiver Bandwidth, Integration Time, and the specific Threshold setting relative to the noise floor.
    *   **Metric:** "Sensitivity at target $P_{fa}$ (e.g., $10^{-6}$ false alarms per second)."
*   **Deterministic Spurious Analysis (Dynamic Range):**
    *   **New Logic:** Implement a specific check for **High-Power False Alarms** driven by ADC SFDR.
    *   **Scenario:** When a strong signal is present (e.g., a jammer or nearby radar), calculate the magnitude of generated spurs (`Signal Power - SFDR`).
    *   **Failure Condition:** If `Spur Power > Detection Threshold`, report a **"Spurious False Alarm"**.
    *   **Metric:** Report "Instantaneous Dynamic Range" — the power range between the Sensitivity floor and the level where spurs become visible.

### 4. Refine Unified Sensitivity and Noise Modeling (Medium Priority)
**Justification:** While `esm_analysis` and `direction_finding_analysis` currently fetch noise figures from `rf_chain`, ensuring a truly unified and consistent approach, especially considering ADC quantization noise contributions, is crucial.
**Action:**
*   **Centralize `calculate_system_noise_floor`:** Ensure that the `system_config/calculate_system_noise_floor` or a similar central utility is the single authoritative source for system noise floor and sensitivity calculations, explicitly incorporating all relevant contributions (thermal, RF chain, ADC).
*   **ADC Integration:** Modify `adc_analysis` to contribute its quantization noise and effective noise figure directly to the `system_config` for a more accurate overall system sensitivity.

### 5. Incorporate Pulse Density / Throughput Analysis (Advanced Feature)
**Justification:** EW systems operating in dense signal environments face challenges with pulse collisions and processing overload. Modeling this is vital for understanding system limits.
**Action:**
*   **New Module:** Consider a new module or extension to `esm_analysis` to model pulse density effects.
*   **Metrics:** Calculate metrics such as `probability_of_intercept` given a specific pulse density, `pulse_desensitization` due to high instantaneous pulse rates, and `processing_latency`. This would involve defining a simplified model for the receiver's instantaneous bandwidth and processing capabilities.

### 6. Refactor RF Chain Management Strategy (Architectural Improvement)
**Justification:** The current system defines RF paths individually or in simple groups. As the complexity grows (e.g., different cable lengths for different array elements, or manufacturing tolerances), a more robust "Library & Archetype" pattern is needed to avoid configuration duplication and errors.
**Action:**
*   **Refactor `rf_chains.yaml`:**
    *   **Component Library:** Ensure *every* unique hardware component (e.g., "LNA Type A", "Cable 1m") is defined strictly in the `components` section.
    *   **Chain Archetypes:** Define chain configurations (e.g., "Standard Channel", "Long-Cable Channel") solely by referencing components from the library. Do not define component parameters inline within a chain definition.
*   **Update `system_config.yaml`:**
    *   Implement a mapping structure that assigns physical path IDs (e.g., "RX_Channel_1" through "RX_Channel_4") to specific Chain Archetypes defined in `rf_chains.yaml`.
    *   This allows for handling "groups" of identical paths while easily accommodating single paths with unique variances (e.g., "RX_Channel_4" uses "Long-Cable Channel" archetype).

### 7. Optional PowerPoint Template for Design Review (Reporting Enhancement)
**Justification:** To provide greater flexibility and control over the generated design review's aesthetics and branding, allowing users to specify a custom PowerPoint template is essential.
**Action:**
*   **Modify `generate_design_review.py`:** Update the script to accept an optional command-line argument or configuration parameter for a PowerPoint template file path (.potx or .pptx).
*   **Apply Template:** When generating the PowerPoint, apply the specified template to the presentation to inherit its slide masters, layouts, and theme.

### 8. Jamming Performance Analysis (New Capability)
**Justification:** The system lacks analysis for its jamming capabilities. A previous capability allowed for analyzing jamming effectiveness over a trajectory, considering antenna patterns and power. This functionality needs to be restored and formalized.
**Action:**
*   **Correct Configuration:** Update `system_config.yaml` to correctly reflect the transmit and receive path hardware for the low-band:
    *   Change `tx_low_band` `num_paths` from 2 to 1.
    *   The now 'available' path (which was previously a second low-band TX path) should be configured as the `rx_low_band` path. This ensures a final configuration of one `tx_2_18ghz` path, one `tx_low_band` path, and one `rx_low_band` path.
*   **Create `jamming_analysis` Module:** Develop a new Python module to analyze the standalone performance of each unique transmit chain (EIRP, Jamming-to-Signal Ratio capability vs Range).
*   **Restore Trajectory Jamming Simulation:**
    *   Integrate jamming effectiveness calculations into the `ekf_geolocation` or `demo` trajectory simulations.
    *   Calculate J/S (Jamming-to-Signal) ratio at each time step based on the dynamic geometry between the jammer (platform) and the victim (emitter).
    *   **Critical Input:** Use the `beamwidth_deg` and antenna orientation from `system_config.yaml` to apply a realistic gain pattern (e.g., Gaussian or Cosine-squared) instead of assuming isotropic radiation.
    *   **Reference:** Refer to `jamming/jamming_effectiveness_analysis.m` (reference MATLAB file to be provided) for the specific algorithms and logic used in the legacy implementation.

### 9. Refine ESM Analysis Architecture (Refactoring)
**Justification:** The `esm_analysis` module currently contains competing detection models: a simple binary threshold model in `core/detection_model.py` and a more detailed statistical model (using Albersheim's equation) in `esm_detection.py`. This duplication leads to inconsistency.
**Action:**
*   **Unify Detection Logic:** Refactor `esm_analysis` to use a single, unified detection engine. Recommend promoting the statistical approach in `esm_detection.py` to be the core model, as it provides more fidelity (Pd vs SNR) than the binary model.
*   **Integrate New Capabilities:** Ensure this unified engine directly calls the new `MeasurementAccuracy` (Pulse Parameter) and `FalseAlarmAnalysis` (Spurious) modules defined in previous steps.

### 10. Refine Dwell Scheduler & Detection Probability Logic (Algorithmic Improvement)
**Justification:** The current Albersheim's equation implementation hardcodes $P_{fa} = 10^{-6}$ and ignores the user-specified threshold setting. This decouples the simulation from the actual system configuration.
**Action:**
*   **Cohesive $P_{fa}$ Derivation:** Calculate $P_{fa}$ dynamically from the user's configured ratio of `snr_threshold_db` to `noise_floor_db`. This derived $P_{fa}$ must be the single source of truth passed into all detection probability calculations.
*   **Update `esm_detection.py`:** Modify `calculate_detection_probability` to accept this variable $P_{fa}$ instead of using a hardcoded value.
*   **Update `dwell_scheduler.py`:** Ensure the scheduler uses this dynamic $P_{fa}$ logic. This guarantees that changing the threshold in `system_config.yaml` correctly ripples through to update the Probability of Intercept (POI) and optimized dwell times.

### 11. Update Reporting to Reflect Multi-Band Capabilities (Reporting Accuracy)
**Justification:** The current Design Review slides report a single value for key metrics (Frequency Range, Sensitivity, RF Chain Gain/NF), often defaulting to the 2-18 GHz "Mid Band" and ignoring the <2 GHz Low Band. This misrepresents the system's full capabilities.
**Action:**
*   **Update `generate_design_review.py`:** Modify the metric collection logic to explicitly loop through all defined frequency bands (Low, Mid, etc.) defined in `system_config`.
*   **Rename High Band:** Update references of "High Band" (2-18 GHz) to **"Mid Band"** to align with standard nomenclature (since 18 GHz+ would be High Band).
*   **Multi-Band Metrics:** Report metrics like **Noise Floor**, **Sensitivity**, and **Frequency Range** as a table or list (e.g., "Sensitivity: -90 dBm (Low) / -85 dBm (Mid)") rather than a single average.
*   **RF Chain Summary:** Update the "RF Chain Performance" slide to explicitly list performance (Gain, NF) for *each* unique chain type (e.g., "Mid Band RX", "Low Band RX") instead of a single summary value.
*   **Simplify Interferometer Summary:** Remove specific element counts and baseline details from the high-level summary slide, focusing instead on the frequency coverage (2-18 GHz only) to avoid clutter.
*   **Verify ESM Plots:** Ensure the generated ESM analysis plots (SNR vs Range) explicitly include example emitters for *both* the Low (<2 GHz) and Mid (2-18 GHz) bands to demonstrate full-spectrum capability.

### 12. Refine Analysis Visualizations and Metrics (Visualization Improvement)
**Justification:** Several analysis plots simplify data in ways that can be misleading (e.g., isotropic interferometer elements, combined antenna coverage). Key performance metrics for geolocation convergence are also missing.
**Action:**
*   **Interferometer SNR:** Update `direction_finding_analysis` to use a realistic element gain pattern (e.g., Cosine-squared or user-provided file) instead of isotropic. This should result in SNR degradation at high incident angles in the "SNR vs Angle" plot.
*   **Blind Spot Visualization:** Enhance `antenna_coverage_analysis` plots to explicitly color-code or overlay "Blind Spot" regions (where Gain < Threshold) on the 2D coverage map.
*   **Split Coverage Maps:** Generate separate coverage maps for **Low Band** (<2 GHz) and **Mid Band** (2-18 GHz) antennas. Merging them into a single map obscures the gaps inherent in each specific band.
*   **Geolocation Convergence Metric:** Add a new metric to the EKF simulation results: **"Error after N valid measurements"** (e.g., N=10). This provides a more robust measure of system settling time than just "Time to Convergence," which depends heavily on trajectory.
