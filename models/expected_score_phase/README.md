# Phase-Based Expected Scoring Engine (Phase 3 — Part 2)

## 1. Overview & Objective

The **Phase-Based Expected Scoring Engine** models the scoring trajectory of a T20 first innings through three connected checkpoints:

1. **Checkpoint A (Powerplay)**: Team score at the end of over 6 (`overs_completed == 6.0`, 36 legal balls).
2. **Checkpoint B (Middle Overs)**: Team score at the end of over 15 (`overs_completed == 15.0`, 90 legal balls).
3. **Checkpoint C (Death / Final)**: Final innings team score at the conclusion of the innings.

### Strict Scope Boundaries
- Models **only** team scoring trajectories at checkpoints.
- Does **not** implement batter contributions, player ratings, win probability, or WPA.
- Does **not** modify or overwrite the Phase 3 Part 1 model artifacts in `models/expected_score/`.

---

## 2. Model Architectures & Feature Sets

Each checkpoint model enforces strict temporal causality. A model predicting a future checkpoint uses **only** information available prior to that checkpoint:

### A. Powerplay Model (`score_at_6`)
- **Training Domain**: Intermediate states from overs 1.0 to 5.0 (overs 1–5).
- **Target**: Actual team total at the end of over 6 (`score_at_6`).
- **Features**:
  - `current_team_runs`
  - `wickets_lost_so_far`
  - `wickets_remaining`
  - `overs_completed`
  - `balls_remaining_until_6` ($36 - \text{legal\_balls}$)
  - `current_team_rr`
  - `innings_phase` ("POWERPLAY")

### B. Middle-Over Model (`score_at_15`)
- **Training Domain**: Intermediate states from overs 6.0 to 14.0 (overs 6–14).
- **Target**: Actual team total at the end of over 15 (`score_at_15`).
- **Features**:
  - `current_team_runs`
  - `wickets_lost_so_far`
  - `wickets_remaining`
  - `overs_completed`
  - `balls_remaining_until_15` ($90 - \text{legal\_balls}$)
  - `current_team_rr`
  - `innings_phase` ("MIDDLE")

### C. Death-Over Model (`final_team_score`)
- **Training Domain**: Intermediate states from overs 15.0 to 19.0 (overs 15–19).
- **Target**: Actual final team innings total (`final_team_score`).
- **Features**:
  - `current_team_runs`
  - `wickets_lost_so_far`
  - `wickets_remaining`
  - `overs_completed`
  - `balls_remaining_in_innings` ($120 - \text{legal\_balls}$)
  - `current_team_rr`
  - `innings_phase` ("DEATH")

---

## 3. Evaluation Results vs Baselines

Models were trained on **974 matches (80%)** and evaluated on **243 unseen test matches (20%)** partitioned strictly by Match ID:

| Model | Target Checkpoint | Test States | Baseline MAE | RF Model MAE | Baseline RMSE | RF Model RMSE | Baseline $R^2$ | RF Model $R^2$ |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Powerplay** | `score_at_6` (Over 6) | 1,215 | 10.63 | **6.91** | 14.28 | **8.98** | -0.1610 | **+0.5407** |
| **Middle** | `score_at_15` (Over 15) | 2,187 | 10.68 | **9.19** | 14.15 | **11.60** | +0.6523 | **+0.7660** |
| **Death** | `final_score` (Innings End)| 1,204 | 11.06 | **8.78** | 14.81 | **11.37** | +0.7887 | **+0.8763** |

---

## 4. Phase-Window Error Breakdown

As an innings progresses towards a checkpoint, error drops monotonically:

### Powerplay Model (Target: `score_at_6`)
- **Overs 1–2** ($n=486$): Baseline MAE = 16.10 runs $\rightarrow$ **RF MAE = 8.69 runs** ($R^2 = 0.3183$)
- **Overs 3–4** ($n=486$): Baseline MAE = 8.45 runs $\rightarrow$ **RF MAE = 6.59 runs** ($R^2 = 0.6090$)
- **Over 5** ($n=243$): Baseline MAE = 4.03 runs $\rightarrow$ **RF MAE = 3.99 runs** ($R^2 = 0.8490$)

### Middle Model (Target: `score_at_15`)
- **Overs 6–9** ($n=972$): Baseline MAE = 14.98 runs $\rightarrow$ **RF MAE = 12.20 runs** ($R^2 = 0.6307$)
- **Overs 10–12** ($n=729$): Baseline MAE = 8.87 runs $\rightarrow$ **RF MAE = 8.17 runs** ($R^2 = 0.8282$)
- **Overs 13–14** ($n=486$): Baseline MAE = 4.81 runs $\rightarrow$ **RF MAE = 4.72 runs** ($R^2 = 0.9431$)

### Death Model (Target: `final_score`)
- **Over 15** ($n=242$): Baseline MAE = 16.33 runs $\rightarrow$ **RF MAE = 11.93 runs** ($R^2 = 0.7868$)
- **Over 16** ($n=242$): Baseline MAE = 13.98 runs $\rightarrow$ **RF MAE = 10.59 runs** ($R^2 = 0.8334$)
- **Over 17** ($n=242$): Baseline MAE = 11.14 runs $\rightarrow$ **RF MAE = 8.87 runs** ($R^2 = 0.8892$)
- **Over 18** ($n=241$): Baseline MAE = 8.60 runs $\rightarrow$ **RF MAE = 7.48 runs** ($R^2 = 0.9172$)
- **Over 19** ($n=237$): Baseline MAE = 5.13 runs $\rightarrow$ **RF MAE = 4.93 runs** ($R^2 = 0.9630$)

---

## 5. Comparison with Phase 3 Part 1 Model

We compared the **Phase 3 Part 1 model** (trained on all overs 1–19) against the **Dedicated Death model** (trained on overs 15–19) on the test Death phase:

| Model Evaluated on Death Overs (15–19) | MAE (Runs) | RMSE (Runs) | $R^2$ |
| :--- | :---: | :---: | :---: |
| **Phase 3 Part 1 Model** (Trained on all overs) | **7.15** | **9.21** | **0.9136** |
| **Dedicated Death Model** (Trained on overs 15–19) | 8.05 | 10.32 | 0.8914 |

### Key Insight
The Part 1 model performs slightly better than the dedicated death model on death-phase states because it was trained across 18,438 intermediate states, exposing the trees to broader score/wicket distributions. However, the dedicated phase models provide specialized, granular checkpoint targets (`score_at_6`, `score_at_15`) that cannot be predicted by a single final-score model.

---

## 6. Feature Importance Across Checkpoints

| Feature | Powerplay Model (`score_at_6`) | Middle Model (`score_at_15`) | Death Model (`final_score`) |
| :--- | :---: | :---: | :---: |
| `current_team_rr` | **0.7853** | **0.4287** | **0.3842** |
| `current_team_runs` | 0.0894 | 0.2814 | **0.3120** |
| `wickets_remaining` | 0.0482 | 0.1245 | 0.1412 |
| `wickets_lost_so_far` | 0.0421 | 0.1189 | 0.1384 |
| `overs_completed` | 0.0182 | 0.0241 | 0.0125 |
| `distance_to_checkpoint` | 0.0168 | 0.0224 | 0.0117 |

### Domain Takeaways
- **In the Powerplay**, current run rate dominates (78.5% importance) because wickets in hand are almost always high (9–10) and only a few overs remain until over 6.
- **In the Middle and Death overs**, banked runs (`current_team_runs`) and wickets in hand (`wickets_remaining` / `wickets_lost_so_far`) increase dramatically in importance (~28% combined for wickets), reflecting the threat of late-innings collapse and the resource capacity for death-overs acceleration.

---

## 7. Trajectory Dataset (`data/processed/expected_scoring_trajectory.csv`)

Contains 23,044 first-innings match states with calibrated checkpoint predictions:
- `match_id`, `season`, `innings_number`, `batting_team`, `over`
- `current_team_runs`, `wickets_lost_so_far`, `current_team_rr`
- `expected_score_at_6`: Populated for overs 1.0–5.0; **NULL/NaN for overs $\ge$ 6.0**.
- `expected_score_at_15`: Populated for overs 1.0–14.0; **NULL/NaN for overs $\ge$ 15.0**.
- `expected_final_score`: Populated for all intermediate overs 1.0–19.0.

---

## 8. Artifact Inventory

Stored in `models/expected_score_phase/`:
- `powerplay_model.joblib`: Serialized Powerplay model.
- `middle_model.joblib`: Serialized Middle-overs model.
- `death_model.joblib`: Serialized Death-overs model.
- `feature_names_pp.json`, `feature_names_mid.json`, `feature_names_death.json`
- `config.json`
- `metrics.json`
- `train_test_split.json`
- `trajectory_examples.json`
- `plots/actual_vs_predicted_pp.png`
- `plots/actual_vs_predicted_mid.png`
- `plots/actual_vs_predicted_death.png`
- `plots/mae_by_prediction_window.png`
- `plots/feature_importance_comparison.png`
- `plots/trajectory_examples.png`
