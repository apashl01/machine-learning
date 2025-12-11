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
**Objective:** Complete the remaining architectural refactoring and integration tasks.

### Task 1: Enforce Centralized Configuration & Unified Architecture
**Goal:** Make `system_config.yaml` the single source of truth for system architecture, while keeping component specifications modular. Consolidate all configuration files into a single location.

*   **Sub-task 1.0: Centralize Config Directory & Move Files**
    *   **Action:** Create a top-level `config/` directory (or rename `system_config/` to `config/`).
    *   **Move:** Move `system_config/system_config.yaml` and `rf_chain_analysis/config/rf_chains.yaml` to `config/`.
    *   **Update:** Update `system_config/loader.py` to point to this new location.

*   **Architectural Split (File Contents):**
    *   **`rf_chains.yaml`**: Becomes the **Component Library**. It should only contain the `components` section (definitions of Cables, LNAs, etc.).
    *   **`system_config.yaml`**: Becomes the **System Blueprint**. It should contain the `chain_archetypes` and `paths` sections. This defines the **order** and composition of the RF chains by referencing components from the library.
*   **Target File:** `system_config/loader.py` (or `config/loader.py`)
    *   **Logic Update:** Update the `load_system_config` function to:
        1.  Load `system_config.yaml` (Architecture).
        2.  Load `rf_chains.yaml` (Component Specs).
        3.  Resolve the component references in the system config using the library from rf_chains.
*   **Target Files:** Analysis Loaders (`adc`, `antenna`, `ekf`)
    *   **Update:** Ensure all loaders import this unified `system_config` object.

*   **Sub-task 1.1: Remove Legacy Single-Chain Reference**
    *   **Problem:** The `rf_chain` section in `system_config.yaml` is a legacy "one-size-fits-all" model.
    *   **Target Files:**
        *   `system_config/loader.py`: Remove references to the legacy `rf_chain` section.
        *   `system_config/system_config.yaml`: **Delete** the entire `rf_chain` block.

*   **Sub-task 1.2: Unify Antenna Definitions**
    *   **Problem:** Antenna specifications are duplicated in RF chain and Antenna sections.
    *   **Solution:** Define antenna parameters *only* in the `antennas` section.
    *   **Implementation:** Replace explicit antenna definitions in RF chains with references (`{type: "antenna", ref: "esm_antenna"}`).

*   **Sub-task 1.3: Update `rf_chain_analysis/example_analysis.py` and Clean Up Legacy Config**
    *   **Target File:** `rf_chain_analysis/example_analysis.py`
        *   **Update:** Change `load_chain_config()` to `load_rf_chain_library()`.
    *   **Cleanup:** Delete `rf_chain_analysis/config/rf_chain_config.yaml`.

### Task 2: Multi-Band & Multi-Role Antenna Coverage
**Goal:** Generate separate coverage maps for Low/Mid bands and TX/RX paths.

*   **Target File:** `antenna_coverage_analysis/core/analyzer.py`
    *   **Logic:** Add `frequency_ghz` parameter and support subset lists of antennas.
*   **Target File:** `antenna_coverage_analysis/example_analysis.py`
    *   **Orchestration:** Loop through the 4 groups (RX Low, RX Mid, TX Low, TX Mid).

### Task 3: Fix RF Chain Gain Mismatch (Bug Fix)
**Goal:** Resolve the discrepancy between hardcoded `total_gain_db` and the actual sum of component gains.

*   **Target File:** `system_config/loader.py`
    *   **Update:** Remove `total_gain_db` field and add a property to calculate it dynamically: `sum(comp.gain_db for comp in self.components)`.
*   **Target File:** `system_config/system_config.yaml`
    *   **Cleanup:** Remove `total_gain_db` fields.

*   **Sub-task 3.1: Correct Dynamic Range Calculation**
    *   **Target File:** `system_config/noise.py`
        *   **Update:** Change dynamic range calculation to use `(ADC Full Scale - System Noise Floor)` instead of Damage Threshold.

### Task 4: Trajectory Jamming Integration
**Goal:** Ensure jamming analysis is fully integrated into the simulation and reporting.

*   **Sub-task 4.1: Enable Jamming Slides**
    *   **Problem:** The standalone jamming analysis slides are defined in `reporting/generators/jamming.py` but are never added to the presentation.
    *   **Target File:** `reporting/generate_design_review.py`
        *   **Update:** In `generate_powerpoint`, add a call to `add_jamming_slides(gen, ...)` after `add_ekf_geolocation_slides`.
        *   **Parameters:** Pass the `jammer_config` and `radar_config` (loaded or default) and specify the output directory for plots.

### Task 5: Unified ESM Detection Logic
**Goal:** Remove the binary detection model and use the probabilistic Albersheim model.

*   **Target File:** `esm_analysis/core/detection_model.py`
    *   **Logic Update:** Import `ESMDetector` from `esm_analysis.esm_detection` and use `calculate_detection_probability`.

### Task 6: Dynamic Pfa Derivation
**Goal:** Ensure the False Alarm Rate ($P_{fa}$) is derived from the SNR threshold.

*   **Target File:** `esm_analysis/config/loader.py`
    *   **Logic Update:** Calculate $P_{fa}$ using `compute_pfa_for_threshold(snr_threshold_db)` instead of hardcoding.

### Task 7: Enhanced Visualizations
**Goal:** Add specific metrics and overlays to plots.

*   **Sub-task 7.1: Fix PowerPoint Bullet Formatting**
    *   **Problem:** Some bulleted slides show double bullets or lack proper sub-indentation because the `_add_bullets` function manually prepends bullet characters and doesn't handle indentation levels.
    *   **Target File:** `reporting/core.py`
        *   **Update:** Modify `_add_bullets` to:
            1.  Remove the manual `•` character from `p.text`.
            2.  Instead, set `p.level = 0` for main bullets.
            3.  Implement logic to detect sub-bullets (e.g., by checking if a string starts with a tab `	` or a specific marker) and set `p.level = 1` or higher accordingly.
            4.  Ensure `p.bullet_char = None` if PowerPoint's default bullet is desired, or set a custom character.
*   **Sub-task 7.2: Auto-Scale Plots on Slides**
    *   **Problem:** Some generated plots exceed the slide boundaries, especially vertically, when inserted into PowerPoint.
    *   **Target File:** `reporting/core.py`
        *   **Update:** Modify `_add_image` to implement a "scale-to-fit" logic:
            1.  Define a maximum bounding box (e.g., `max_width=Inches(10)`, `max_height=Inches(5.5)`) for plots.
            2.  When inserting an image, initially insert with the `max_width`.
            3.  *After insertion*, check the image's `height` property. If it exceeds `max_height`, rescale the image's `width` and `height` proportionally to fit `max_height`.
            4.  Ensure images are centered horizontally and vertically within their allocated space after scaling.
*   **Target File:** `antenna_coverage_analysis/core/analyzer.py`
    *   **Logic:** Create `blind_spot_mask`.
*   **Target File:** `ekf_geolocation/core/ekf.py`
    *   **Metric:** Implement "Error after N valid measurements".

### Task 8: Repository Cleanup
**Goal:** Organize file structure for clarity.

*   **MATLAB Files:**
    *   **Action:** Create a `matlab_reference/` directory at the project root.
    *   **Move:** Move all `.m` files from the root and subdirectories into this new folder. This separates the legacy reference code from the active Python implementation.

### Task 9: Improve Requirements Verification Logic
**Goal:** Replace optimistic reporting with rigorous worst-case checks against requirements.

*   **Sub-task 9.1: Worst-Case AoA Accuracy**
    *   **Problem:** AoA accuracy is currently checked only at the boresight (0°) for the mid-band frequency.
    *   **Target File:** `reporting/generate_design_review.py`
    *   **Update:** Extract the accuracy at the worst-case corner (Low Freq, Max Angle) and use this for compliance checking.

*   **Sub-task 9.2: Minimum Detection Range**
    *   **Problem:** Detection range is currently reported as the *Maximum* range achieved against *any* threat.
    *   **Target File:** `reporting/generate_design_review.py`
    *   **Update:** Report the **Minimum** detection range achieved among mandatory threats.

*   **Sub-task 9.3: Path-Specific RF Requirements**
    *   **Problem:** `requirements.yaml` applies a single global Noise Figure/Gain requirement to all RF paths, regardless of band or type.
    *   **Target File:** `system_config/requirements.yaml`
        *   **Update:** Restructure the `rf_chain` section to define requirements by path category (e.g., `rx_low_band`, `rx_mid_band`, `tx_paths`).
    *   **Target File:** `system_config/compliance.py`
        *   **Logic Update:** Iterate through the reported RF paths (available in the `performance` dictionary). Match each path to its specific requirement category. Generate pass/fail checks for each path individually.

### Task 10: Replace Static Summary with Compliance Dashboard
**Goal:** Replace hardcoded "Key Findings" and "Recommendations" with a dynamic, visual Compliance Dashboard.

*   **Problem:** The current summary slide displays hardcoded specs and static text that do not reflect the actual analysis results (Pass/Fail).
*   **Target File:** `reporting/generate_design_review.py`
    *   **Update:** Remove the hardcoded `key_findings`, `recommendations`, and `next_steps` lists. Pass the `compliance_result` object to the `add_summary_slide` function.
*   **Target File:** `reporting/generators/summary.py` (or `reporting/generate_design_review.py` if inline)
    *   **Logic:**
        1.  Group compliance checks by **Category** (e.g., Detection, Geolocation).
        2.  Calculate Pass/Fail statistics for each category.
    *   **Visualization:** Generate a high-level summary table:
        *   **Columns:** Category | Status | Metrics (Passed/Total)
        *   **Formatting:** Use Green text/background for "PASS" categories (100% checks passed) and Red for "FAIL".

### Task 11: Implement Realistic Antenna Pattern for Direction Finding (New)
**Goal:** Model realistic antenna gain roll-off over incident angle in the Direction Finding analysis to accurately reflect SNR degradation.

*   **Problem:** The Direction Finding analysis defaults to an isotropic antenna (0 dBi gain) if no pattern file is specified. This leads to an unrealistically flat SNR vs. Incident Angle, and underestimation of angle error degradation at wide angles.
*   **Target File:** `direction_finding_analysis/core/analyzer.py`
    *   **Update:** In `InterferometerAnalyzer.__init__` and `get_antenna_gain`, if `antenna_pattern_file` is `None`, use the `system_config.antennas.esm_antenna` parameters (`peak_gain_dbi`, `beamwidth_deg`) to generate a simple analytical antenna pattern (e.g., a Cosine or Gaussian model) rather than assuming 0 dBi.
    *   **Rationale:** This will correctly model the drop in SNR at wide incident angles, leading to a more realistic prediction of angle error degradation.
