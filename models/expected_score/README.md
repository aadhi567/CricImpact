# Expected Final Score Model (Phase 3 — Part 1)

## 1. Overview & Objective

The **Expected Final Score Model** estimates the expected final team total for a first-innings T20 batting side given an intermediate match state:

> *"Given the current state of a first-innings T20 batting innings, what final team score would historically be expected?"*

### Critical Scope Boundaries
- **Target**: Expected final **team** score for the 1st innings.
- **NOT** an individual batter contribution model (comes in future phases).
- **NOT** an individual batter expected score model.
- **NOT** a win probability model or Win Probability Added (WPA) framework.
- **NOT** a player rating or leaderboard.

---

## 2. Training Data & Preprocessing

- **Primary Source**: `data/processed/match_state.csv` and `data/processed/innings.csv`.
- **Scope**: First-innings, non-chase T20 deliveries (`innings_number == 1`, `is_chase == False`).
- **Total Raw 1st Innings**: 1,243 matches across IPL seasons (2007/08 through 2026).
- **Usable 1st Innings**: **1,217 matches**.
- **Excluded Matches**: **26 matches** were identified and excluded due to rain truncation, bad light, abandonment, or incomplete innings (`overs_completed < 19.5` and `total_wickets < 10`). Innings where all 10 wickets fell (all-out) were retained as standard complete T20 cricket innings.

---

## 3. Sampling Strategy

To prevent high correlation and duplicate state bias across consecutive balls within the same innings, a configurable sampling strategy was designed:
- **Strategy**: End-of-completed-over states (`overs 1.0, 2.0, ..., 19.0`).
- **Selection Rule**: Filtered for `is_legal == True` at `legal_balls_bowled_so_far in [6, 12, ..., 114]`. This ensures exactly one observation per completed over.
- **Terminal State Exclusion**: Innings-ending deliveries (`balls_remaining == 0` or `wickets_remaining == 0`) were excluded from training/testing because at the conclusion of an innings, the current score trivially equals the final score.
- **Total Sampled Observations**: **23,044 match states**.

---

## 4. Feature Set & Data Leakage Prevention Audit

All features were audited to guarantee that only information available at the exact moment of the completed over is utilized:

| Feature Name | Type | Real-Time Availability & Rationale |
| :--- | :--- | :--- |
| `current_team_runs` | Numeric | Cumulative runs scored up to current completed over. Live scoreboard state. |
| `wickets_lost_so_far` | Integer | Total wickets lost up to current completed over. Live scoreboard state. |
| `wickets_remaining` | Integer | Batting wickets in hand (`10 - wickets_lost_so_far`). Live resource indicator. |
| `overs_completed` | Numeric | Completed overs in cricket notation (e.g. 1.0, 2.0, ..., 19.0). |
| `balls_remaining_in_innings`| Integer | Scheduled legal balls remaining (`120 - legal_balls_bowled`). |
| `current_team_rr` | Numeric | Current scoring rate (`current_team_runs / (legal_balls / 6)`). Live metric. |
| `innings_phase` | Categorical | Chronological phase (Powerplay: 1–6, Middle: 7–15, Death: 16–19). |

### Explicitly Excluded (Leakage Prevention)
- Match winner / result.
- Post-delivery accelerations or future dismissals.
- Second-innings chase requirements or targets.
- Individual batter identity or future player performance.

---

## 5. Train / Test Methodology

To prevent data leakage caused by training and testing on different deliveries from the same match, splits were partitioned strictly by **Match ID**:

### Primary Evaluation Split (Match ID)
- **Train Set**: 974 matches (18,438 match states, ~80%)
- **Test Set**: 243 matches (4,606 match states, ~20%)
- **Random Seed**: Fixed `random_state = 42` for exact reproducibility.

### Secondary Evaluation Split (Season-based Holdout)
- **Train Set**: Seasons 2007/08 through 2024 (1,074 matches)
- **Test Set**: Recent Seasons 2025 and 2026 (143 matches)

---

## 6. Baselines & Machine Learning Model

1. **Baseline 1 (Simple Projection)**:
   $$\text{Projected Score} = \text{Current Score} + \left(\text{Current RR} \times \frac{\text{Balls Remaining}}{6}\right)$$
2. **Baseline 2A (Global Historical Mean)**:
   Predicts the training set global mean ($\approx 168.6$ runs).
3. **Baseline 2B (Conditional Historical Average)**:
   Predicts $\text{Current Score} + \mathbb{E}[\text{Remaining Runs} \mid \text{Overs Completed}]$.
4. **Random Forest Regressor**:
   Modest, interpretable hyperparameters to capture non-linear wicket-depletion and death-overs acceleration:
   - `n_estimators`: 100
   - `max_depth`: 12
   - `min_samples_split`: 10
   - `min_samples_leaf`: 5
   - `random_state`: 42

---

## 7. Evaluation Results

### Overall Test Set Performance (Match-Level Split)

| Model | MAE (Runs) | RMSE (Runs) | $R^2$ | Outperformed Baseline? |
| :--- | :---: | :---: | :---: | :---: |
| **Simple Projection Baseline** | 28.35 | 40.55 | -0.5412 | Reference |
| **Historical Global Mean** | 25.88 | 32.75 | -0.0055 | Reference |
| **Historical Over Mean** | 17.46 | 22.97 | 0.5055 | Reference |
| **Random Forest Regressor** | **16.69** | **22.09** | **0.5426** | **YES (+41.1% MAE improvement over Simple)** |

### Error by Innings Phase

| Phase | Samples | Simple Baseline MAE | Simple Baseline RMSE | RF Model MAE | RF Model RMSE | RF $R^2$ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Powerplay (Overs 1–6)** | 1,458 | 48.47 | 62.00 | **22.61** | **28.72** | 0.2366 |
| **Middle (Overs 7–15)** | 2,186 | 23.12 | 28.75 | **16.59** | **20.83** | 0.5972 |
| **Death (Overs 16–19)** | 962 | 9.74 | 12.95 | **7.94** | **10.01** | 0.9020 |
| **Overall (Overs 1–19)** | 4,606 | 28.35 | 40.55 | **16.69** | **22.09** | 0.5426 |

### Season Holdout Validation (Train $\le$ 2024, Test 2025–2026)
- **Baseline MAE**: 25.98 | **RMSE**: 37.99 | $R^2$: -0.1382
- **Random Forest MAE**: 19.06 | **RMSE**: 25.69 | $R^2$: 0.4794

---

## 8. Feature Importances (Gini)

| Feature | Importance | Interpretation |
| :--- | :---: | :--- |
| `current_team_rr` | **0.7694** | Scoring tempo established up to the current stage. |
| `current_team_runs` | **0.0845** | Absolute runs already banked on the scoreboard. |
| `wickets_remaining` | **0.0657** | Resource depth available for late-innings acceleration. |
| `wickets_lost_so_far` | **0.0639** | Pressure and risk of premature collapse. |
| `overs_completed` | **0.0083** | Match progression coordinate. |
| `balls_remaining_in_innings` | **0.0082** | Opportunity space remaining. |
| `innings_phase` | **0.0000** | Redundant when `overs_completed` and `balls_remaining` are present. |

*(Note: Feature importances reflect relative split criteria frequency in tree ensembles, not direct causal effects).*

---

## 9. Generated Artifacts & Plots

All saved under `models/expected_score/`:
- `expected_score_rf.joblib`: Serialized scikit-learn model.
- `feature_names.json`: Audited feature list.
- `config.json`: Hyperparameters configuration.
- `metrics.json`: Detailed evaluation numbers (overall and phase-wise).
- `train_test_split.json`: Exact match IDs for train/test sets.
- `test_prediction_examples.json`: Real unseen prediction evaluations.
- `plots/actual_vs_predicted.png`: Scatter plot with $y=x$ perfect prediction line.
- `plots/prediction_error_distribution.png`: Error residuals histogram (Baseline vs RF).
- `plots/mae_by_phase.png`: Comparative bar chart across innings phases.
- `plots/feature_importance.png`: Ranked feature importance chart.

---

## 10. Limitations & Assumptions

1. **Pre-match Context**: Model currently uses only in-game match state features. Pitch conditions, boundary dimensions, venue scoring trends, and specific batter/bowler match-ups are intentionally excluded at this baseline stage.
2. **First Innings Only**: Not applicable to 2nd innings run chases where the target imposes a fixed upper bound.
3. **Rain-Shortened Matches**: The model is calibrated on standard 20-over matches and completed all-out innings; it is not suited for matches shortened prior to the start of play.
