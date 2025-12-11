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