# Technical Implementation Guide (Phase 2)

**Target Repository:** Electronic Warfare System Analysis Framework
**Objective:** Complete the remaining architectural refactoring and integration tasks.

### Task 1: Enforce Centralized Configuration & Unified Architecture
**Goal:** Consolidate all system parameters into `system_config.yaml` and `rf_chains.yaml`. Ensure all analysis modules read from these central files.

*   **Sub-task 1.0: Centralize Config Directory & Move Files**
    *   **Action:** Create a top-level `config/` directory.
    *   **Move:** Move `system_config/system_config.yaml` and `rf_chain_analysis/config/rf_chains.yaml` to `config/`.
    *   **Update:** Update `system_config/loader.py` to point to this new location.

*   **Sub-task 1.1: Consolidate Hardware Definitions (Data Migration)**
    *   **ADC Specs:**
        *   **Source:** `adc_analysis/config/adc_specs_model1.yaml`.
        *   **Dest:** Merge these parameters (sample rate, bits, bands, spurious) into `config/system_config.yaml` under the `adc` section.
    *   **Interferometer Specs:**
        *   **Source:** `direction_finding_analysis/config/interferometer_config.yaml`.
        *   **Dest:** Ensure `config/system_config.yaml` has the correct `element_positions`, `n_elements`, and `phase_error`.
    *   **Antenna Specs:**
        *   **Source:** `antenna_coverage_analysis/config/uav_config.yaml`.
        *   **Dest:** Merge antenna definitions (gain, beamwidth) into `config/system_config.yaml` under the `antennas` section.

*   **Sub-task 1.2: Refactor RF Chain Architecture (Linked Files)**
    *   **`config/rf_chains.yaml`**: Modify this file to contain **ONLY** the `components` section (The Component Library).
    *   **`config/system_config.yaml`**: Move the `chain_archetypes` and `paths` sections here (The System Blueprint).
    *   **Update `system_config/loader.py`**:
        *   Load both files.
        *   Resolve component references: When parsing a chain in `system_config`, look up the component details in `rf_chains`.
        *   **Fix Gain Bug:** Implement the dynamic `total_gain_db` calculation (sum of components) and remove the hardcoded field.
        *   **Unify Antennas:** When parsing an RF chain component of type `antenna`, resolve its specs by looking up the ID in the `antennas` section of `system_config`.

*   **Sub-task 1.3: Update Analysis Loaders (Code Updates)**
    *   **`adc_analysis/config/loader.py`**:
        *   Import `system_config.load_system_config`.
        *   Map `system_config.adc` data to the `ADCSpecs` class.
        *   Remove dependency on local `adc_specs.yaml`.
    *   **`direction_finding_analysis/config/loader.py`**:
        *   Import `system_config.load_system_config`.
        *   Load hardware specs (positions, etc.) from `system_config.interferometer`.
        *   Load *only* simulation settings (angles, test freqs) from local `interferometer_config.yaml`.
    *   **`antenna_coverage_analysis/config/loader.py`**:
        *   Import `system_config.load_system_config`.
        *   Load antenna definitions from `system_config.antennas`.
    *   **`ekf_geolocation/config/loader.py`**:
        *   Import `system_config.load_system_config`.
        *   Replace local interferometer/emitter config with data from `system_config`.
    *   **`rf_chain_analysis/example_analysis.py`**:
        *   Update to use `load_system_config` (or the new RF library loader) instead of the legacy `load_chain_config`.

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

### Task 8: Repository Cleanup
**Goal:** Organize file structure for clarity.

*   **MATLAB Files:**
    *   **Action:** Create a `matlab_reference/` directory at the project root.
    *   **Move:** Move all `.m` files from the root and subdirectories into this new folder.
    *   **Rationale:** Separates legacy reference code from the active Python implementation.
