# Technical Implementation Guide (Phase 2)

**Target Repository:** Electronic Warfare System Analysis Framework
**Objective:** Complete the remaining architectural refactoring and integration tasks.

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

*   **Target File:** `antenna_coverage_analysis/core/analyzer.py`
    *   **Logic:**
        1.  Add a `frequency_ghz` parameter to the `analyze` method.
        2.  Inside `analyze`, use this frequency to look up beamwidth scaling factors (if implementing dynamic beamwidth).
        3.  Allow `analyze` to accept a subset list of antennas (the "group") instead of iterating over all antennas.
*   **Target File:** `antenna_coverage_analysis/example_analysis.py` (and reporting script)
    *   **Orchestration:** Loop through the 4 groups (RX Low, RX Mid, TX Low, TX Mid) defined in the config.
    *   **Execution:** Call `analyzer.analyze(antennas=group, frequency=band_center_freq)` for each.
    *   **Output:** Save 4 separate plots (e.g., `coverage_rx_mid.png`, `coverage_tx_low.png`).

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