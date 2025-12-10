# Project Analysis Report: Electronic Warfare System Analysis Framework

## Project Summary

This project is a sophisticated Python-based framework designed for the simulation, analysis, and design review of complex radio frequency (RF) systems, likely for Electronic Warfare (EW) or SIGINT applications.

**Key Aspects:**

*   **Purpose:** The main goal is to automate the generation of technical design reviews by running various analyses on a consistent system model and compiling the results into a PowerPoint presentation.
*   **Recent Improvements:** The framework has been recently upgraded to include:
    *   **Pulse Parameter Analysis:** Detailed modeling of measurement accuracy for Frequency (DLFD), Time of Arrival (TOA), and Pulse Width.
    *   **Requirements Verification:** A formal compliance engine (`system_config/compliance.py`) that checks system performance against defined specifications.
    *   **Spurious Analysis:** Modeling of ADC spurious performance and statistical false alarm rates.
    *   **Multi-Band Reporting:** Improved reporting that correctly handles split Low/Mid band architectures.
*   **Centralized Configuration:** A critical architectural element is the `system_config` module. A single `system_config.yaml` file acts as the "single source of truth" for all hardware parameters.

## Current State Assessment

**Strengths:**
*   **Architecture:** The `system_config` central "source of truth" pattern is excellent and now integrates well with sensitivity and noise floor calculations.
*   **Verification:** The new compliance matrix feature allows for automated pass/fail checks, moving the tool towards verification utility.
*   **Fidelity:** The addition of spurious analysis and pulse parameter modeling adds significant depth to the simulation.

**Remaining Gaps & Weaknesses:**
1.  **Fragmented Detection Logic:** The `esm_analysis` module currently contains competing detection models: a simple binary threshold model in `core/detection_model.py` and a more detailed statistical model in `esm_detection.py`.
2.  **Isolated Jamming Analysis:** While a `jamming_analysis` module was created, it operates in isolation. It is not yet integrated into the trajectory simulations (`ekf_geolocation`) to model J/S ratios over a dynamic mission profile.
3.  **Static Pfa Logic:** The scheduler and detection probabilities rely on a hardcoded $P_{fa}$ ($10^{-6}$) rather than deriving it dynamically from the user's SNR threshold setting.
4.  **Verbose Configuration:** The `rf_chains.yaml` configuration is repetitive. It defines components inline for every path rather than using a reusable "library & archetype" approach.
5.  **Configuration Disconnect:** Individual analysis modules (ADC, Antenna Coverage, RF Chain, EKF Geolocation) currently default to using their own isolated, often outdated, local YAML files instead of the central `system_config.yaml`.
6.  **Hardcoded Simulation Parameters:** The EKF simulation hardcodes critical system parameters like Bandwidth (1 MHz), Noise Figure (3 dB), and Interferometer Geometry inside internal modules (`signal_propagation.py`, `interferometer.py`), creating a risk of divergence from the system design.
7.  **Single-Frequency Antenna Analysis:** The `antenna_coverage_analysis` module only analyzes a single frequency at a time and merges all antennas. It cannot currently produce separate coverage maps for Low/Mid bands or Transmit vs. Receive paths.

## Recommended Updates (Phase 2)

The following updates focus on architectural refactoring and deeper integration of the analysis modules.

### 1. Enforce Centralized Configuration (Architecture)
**Justification:** Currently, running an individual analysis script (e.g., `adc_analysis/example_analysis.py`) uses local, isolated configuration files that may contradict the central system design. All modules must explicitly use `system_config.yaml` as the primary source of truth.
**Action:**
*   **Refactor Loaders:** Update `loader.py` in all analysis packages (`adc`, `antenna`, `rf_chain`, `direction_finding`, `ekf_geolocation`) to mandatorily load shared parameters from `system_config.yaml`.
*   **EKF Integration:** Specifically update `ekf_geolocation/config/loader.py` to overwrite its local `interferometer` config with the one from `system_config`.
*   **Signal Propagation Fix:** Update `ekf_geolocation/core/signal_propagation.py` to accept dynamic `bandwidth_hz` and `noise_figure_db` (from `system_config` RF Chain/ADC specs) instead of using hardcoded values (1 MHz / 3 dB).
*   **Deprecate Local Overrides:** Remove high-level system parameters from local YAML files to force dependency on the central config.
*   **Standardize Defaults:** Ensure fallback values in code match the system baseline (e.g., default ADC rate = 40 GSPS, not 3 GSPS).

### 2. Multi-Band & Multi-Role Antenna Coverage Analysis
**Justification:** The system operates in multiple bands (Low/Mid) and has distinct Transmit and Receive paths. The current analysis merges all antennas into a single map at a single frequency, obscuring gaps and performance differences.
**Action:**
*   **Grouping Logic:** Update `antenna_coverage_analysis` to group antennas by **Role** (TX/RX) and **Band** (Low/Mid) based on their `freq_band` tag.
*   **Looping Analysis:** Modify the main analysis loop to run coverage calculations independently for each group (e.g., "RX Low Band", "TX Mid Band").
*   **Frequency-Dependent Patterns:** Implement logic to adjust beamwidth based on frequency (e.g., horn antenna beamwidth narrowing at higher frequencies) if specific data is available, or use band-center frequencies for calculation.
*   **Output:** Generate 4 distinct sets of coverage plots: RX Low, RX Mid, TX Low, TX Mid.

### 3. Refactor RF Chain Management Strategy (Architectural Improvement)
**Justification:** The current system defines RF paths individually. As complexity grows (e.g., varying cable lengths or element counts), a "Library & Archetype" pattern is needed to avoid configuration duplication and errors.
**Action:**
*   **Refactor `rf_chains.yaml`:**
    *   **Component Library:** Ensure *every* unique hardware component (e.g., "LNA Type A", "Cable 1m") is defined strictly in the `components` section.
    *   **Chain Archetypes:** Define chain configurations (e.g., "Standard Channel", "Long-Cable Channel") solely by referencing components from the library.
*   **Update `system_config.yaml`:** Implement a mapping structure that assigns physical path IDs (e.g., "RX_Channel_1") to specific Chain Archetypes.

### 4. Restore Trajectory Jamming Simulation (Integration)
**Justification:** The system now has a `jamming_analysis` module, but it only performs static calculations. The capability to analyze jamming effectiveness (J/S ratio) dynamically over a flight path needs to be restored and integrated.
**Action:**
*   **Integrate into `ekf_geolocation`:** Update the trajectory simulation to calculate J/S (Jamming-to-Signal) ratios at each time step.
*   **Dynamic Geometry:** Use the dynamic geometry between the jammer (platform) and the victim (emitter) to calculate antenna gains based on off-boresight angles.
*   **Output:** Generate plots showing "J/S vs Time" and "Burn-through Range" for the specific simulated trajectory.

### 5. Refine ESM Analysis Architecture (Refactoring)
**Justification:** The `esm_analysis` module currently has two "brains": `core/detection_model.py` (Binary) and `esm_detection.py` (Probabilistic). This causes confusion and potential inconsistency.
**Action:**
*   **Unify Detection Logic:** Refactor `esm_analysis` to use a single, unified detection engine. Promote the statistical approach in `esm_detection.py` to be the core model.
*   **Remove Redundancy:** Deprecate or remove the binary model in `core/detection_model.py`, ensuring all parts of the system (scheduler, reporting) call the unified engine.

### 6. Dynamic Pfa Derivation
**Justification:** The current Albersheim's equation implementation hardcodes $P_{fa}$ ($10^{-6}$) and ignores the user-specified threshold setting. This decouples the simulation from the actual system configuration.
**Action:**
*   **Cohesive $P_{fa}$ Derivation:** Calculate $P_{fa}$ dynamically from the user's configured ratio of `snr_threshold_db` to `noise_floor_db` (using `erfc` logic).
*   **Update `dwell_scheduler.py`:** Ensure the scheduler uses this dynamic $P_{fa}$ logic. This guarantees that changing the threshold in `system_config.yaml` correctly ripples through to update the Probability of Intercept (POI).

### 7. Refine Analysis Visualizations and Metrics (Visualization Improvement)
**Justification:** Specific metrics and visualizations are needed to better communicate system limitations.
**Action:**
*   **Blind Spot Visualization:** Enhance `antenna_coverage_analysis` plots to explicitly color-code or overlay "Blind Spot" regions (where Gain < Threshold) on the 2D coverage map.
*   **Geolocation Convergence Metric:** Add a new metric to the EKF simulation results: **"Error after N valid measurements"** (e.g., N=10). This provides a more robust measure of system settling time than just "Time to Convergence".

---

# Technical Implementation Guide (Phase 2)

**Target Repository:** Electronic Warfare System Analysis Framework
**Objective:** Implement architectural refactoring and integration tasks defined in Phase 2.

### Task 1: Enforce Centralized Configuration
**Goal:** Force all analysis modules to load primary parameters from `system_config.yaml`.

*   **Target Files:** `adc_analysis/config/loader.py`, `antenna_coverage_analysis/config/loader.py`, `rf_chain_analysis/config/loader.py`, `direction_finding_analysis/config/loader.py`, `ekf_geolocation/config/loader.py`.
    *   **Logic Update:** Modify the `load_config()` function in each loader.
    *   **Dependency:** Import `system_config.load_system_config`.
    *   **Implementation:**
        1.  Load the central `system_config` object.
        2.  Load the local YAML (only for module-specific details like jitter or simulation steps).
        3.  **Overwrite** local values with system values:
            *   ADC: `sample_rate`, `resolution`.
            *   RF Chain: `freq_range`.
            *   Antenna: `n_elements`, `positions`, `gain`.
            *   Direction Finding: `n_elements`, `baseline`, `phase_error`.
            *   EKF: Overwrite the entire `interferometer` object in `SimulationConfig` with data from `system_config.interferometer`.
*   **Target File:** `ekf_geolocation/core/signal_propagation.py`
    *   **Update:** Modify `calculate_signal_propagation` to accept `bandwidth_hz` and `noise_figure_db` as arguments (sourced from system config) rather than hardcoding `1e6` and `3.0`.

### Task 2: Multi-Band & Multi-Role Antenna Coverage
**Goal:** Generate separate coverage maps for Low/Mid bands and TX/RX paths.

*   **Target File:** `antenna_coverage_analysis/config/loader.py`
    *   **Logic:** Update `load_uav_config` to explicitly group antennas into dictionary lists: `{'rx_low': [], 'rx_mid': [], 'tx_low': [], 'tx_mid': []}`.
*   **Target File:** `antenna_coverage_analysis/core/analyzer.py`
    *   **Logic:**
        1.  Add a `frequency_ghz` parameter to the `analyze` method.
        2.  Inside `analyze`, use this frequency to look up beamwidth scaling factors (if implementing dynamic beamwidth).
        3.  Allow `analyze` to accept a subset list of antennas (the "group").
*   **Target File:** `antenna_coverage_analysis/example_analysis.py` (and reporting script)
    *   **Orchestration:** Loop through the 4 groups defined in the config.
    *   **Execution:** Call `analyzer.analyze(antennas=group, frequency=band_center_freq)` for each.
    *   **Output:** Save 4 separate plots (e.g., `coverage_rx_mid.png`, `coverage_tx_low.png`).

### Task 3: RF Chain Architecture Refactor
**Goal:** Eliminate configuration duplication in `rf_chains.yaml` by implementing a "Library & Archetype" pattern.

*   **Target File:** `system_config/rf_chains.yaml`
    *   **Schema Change:** Restructure the YAML to have three distinct sections:
        1.  `component_library`: A list of named components (e.g., "LNA_Type_A", "RG58_Cable").
        2.  `chain_archetypes`: Defined chains that reference components by name (e.g., "Standard_MidBand_RX").
        3.  `paths`: The physical paths (e.g., "rx_path_1") that reference an `archetype_id`.
*   **Target File:** `system_config/loader.py`
    *   **Logic Update:** Update the `_parse_rf_chains` function.
    *   **Step 1:** Parse the library into a dictionary of component objects.
    *   **Step 2:** Parse archetypes, resolving component names to objects.
    *   **Step 3:** Parse paths, instantiating the specific chain based on the archetype.

### Task 4: Trajectory Jamming Integration
**Goal:** Enable dynamic Jamming-to-Signal (J/S) analysis within the EKF trajectory simulation.

*   **Target File:** `ekf_geolocation/core/simulation.py`
    *   **Dependency:** Import `JammingAnalyzer` and `JammerConfig` from `jamming_analysis`.
    *   **Logic Update:** Inside the `run_simulation` loop (where signal propagation is calculated):
        1.  Instantiate `JammingAnalyzer` using the jammer config from `system_config`.
        2.  For each time step $t$:
            *   Calculate the relative angle (off-boresight) between the Platform's Jammer antenna and the Emitter.
            *   Call `analyzer.analyze(range_m[t], angle_deg[t])`.
            *   Store the resulting `js_ratio_db` and `burn_through_margin_db`.
    *   **Output:** Append these metrics to the `SimulationResult` object.
*   **Target File:** `ekf_geolocation/example_simulation.py`
    *   **Visualization:** Add a new subplot to the results figure showing "J/S Ratio vs. Time" with a red line indicating the 0 dB burn-through threshold.

### Task 5: Unified ESM Detection Logic
**Goal:** Remove the binary detection model and use the probabilistic Albersheim model everywhere.

*   **Target File:** `esm_analysis/core/detection_model.py`
    *   **Action:** Deprecate the hardcoded `evaluate_detection` logic.
    *   **Logic Update:** Import `ESMDetector` from `esm_analysis.esm_detection`.
    *   **Refactor:** Change `evaluate_detection` to:
        1.  Instantiate `ESMDetector`.
        2.  Call `calculate_detection_probability(radar, range, n_pulses)`.
        3.  Set the `DetectionResult.status` based on a probability threshold (e.g., $P_d > 50\%$) rather than a raw SNR threshold, or simply pass the probability through.
*   **Target File:** `esm_analysis/core/analyzer.py` (if exists) or `threat_categorizer.py`
    *   **Update:** Ensure threat categorization uses the computed $P_d$ (Probability of Detection) to determine if a threat is "Detectable" rather than a simple `SNR > Threshold` check.

### Task 6: Dynamic Pfa Derivation
**Goal:** Ensure the False Alarm Rate ($P_{fa}$) is derived from the SNR threshold, not hardcoded.

*   **Target File:** `esm_analysis/config/loader.py`
    *   **Logic Update:** In `load_receiver_from_system_config`:
        1.  Read `snr_threshold_db` from the config.
        2.  Import `SpuriousAnalyzer` from `esm_analysis.spurious_analysis`.
        3.  Calculate $P_{fa}$ using `compute_pfa_for_threshold(snr_threshold_db)`.
        4.  Assign this calculated value to `ReceiverConfig.pfa` instead of the default `1e-6`.
*   **Target File:** `esm_analysis/dwell_scheduler.py`
    *   **Verification:** Ensure `ESMDetector` is initialized using `receiver.pfa` (which is now dynamic) rather than a default value.

### Task 7: Enhanced Visualizations
**Goal:** Add specific metrics and overlays to plots.

*   **Target File:** `antenna_coverage_analysis/core/analyzer.py`
    *   **Logic Update:** In the `analyze` function, create a boolean mask `blind_spot_mask = coverage_db < min_gain_threshold`.
*   **Target File:** `antenna_coverage_analysis/visualization/plots.py` (or `example_analysis.py`)
    *   **Plotting:** When plotting the 2D coverage map, overlay the `blind_spot_mask` using a specific color (e.g., semi-transparent red) or hatching to clearly mark areas of no coverage.
*   **Target File:** `ekf_geolocation/core/ekf.py`
    *   **Metric Calculation:** Add a function `calculate_convergence_metrics(errors, threshold)`.
    *   **New Metric:** Implement "Error after N valid measurements". Find the index where `cumulative_valid_measurements == N`, and report the position error at that index.
