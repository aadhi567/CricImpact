# Phase 4A: Situational Batter Expectation & Trajectory Engine (Audited & Chase Corrected)

## Overview

Phase 4A establishes the situational foundation for measuring a batter's performance relative to the exact context in which they batted. 

A central principle of this architecture is that **a batter must NOT be judged using runs alone**. Runs and Strike Rate are separate, distinct performance dimensions that are preserved independently:
- **Run Deviation**: $\text{actual\_runs} - \text{expected\_runs}$
- **SR Deviation**: $\text{actual\_sr} - \text{expected\_sr}$
- **Run Performance Ratio**: $\frac{\text{actual\_runs}}{\text{expected\_runs}}$
- **SR Performance Ratio**: $\frac{\text{actual\_sr}}{\text{expected\_sr}}$

These are **not** combined into a single arbitrary score in Phase 4A.

---

## 1. Strict Separation: First Innings vs Second Innings (Chase)

The Phase 3 Expected Final Score model was trained specifically for **first-innings final-score prediction** (where the team maximizes its total). 

In Phase 4A, we enforce a strict separation between first-innings scoring maximization and second-innings target chasing:

### Pathway 1: First Innings (Maximizing Total)
- Evaluated against the Phase 3 Expected Final Score model:
  - `expected_final_entry`: Projected final score at exact entry ball.
  - `expected_final_exit`: Projected final score at exact exit ball.
  - `expected_final_change`: $\text{expected\_final\_exit} - \text{expected\_final\_entry}$
  - `entry_score_deviation`: Team runs vs historical par curve at entry.
  - `exit_score_deviation`: Team runs vs historical par curve at exit.
  - `trajectory_deviation_change`: $\text{exit\_score\_deviation} - \text{entry\_score\_deviation}$
- Excludes the 26 rain-shortened / incomplete 1st innings (<19.5 overs & <10 wickets), where trajectory fields are set to `NaN`.
- Chase context fields are strictly `NaN` / `NULL`.

### Pathway 2: Second Innings / Chase (Fixed Target)
- The first-innings Expected Final Score model is **strictly NOT used** as the chase trajectory model (its fields are set to `NaN` / `NULL`).
- Instead, exact chase context is tracked:
  - `target`: Target runs to win.
  - `runs_required_entry`: $\max(0, \text{target} - \text{entry\_score})$
  - `runs_required_exit`: $\max(0, \text{target} - \text{exit\_score})$
  - `required_rr_entry`: $\frac{\text{runs\_required\_entry} \times 6}{\text{entry\_balls\_remaining}}$
  - `required_rr_exit`: $\frac{\text{runs\_required\_exit} \times 6}{\text{exit\_balls\_remaining}}$
  - `entry_team_rr` & `exit_team_rr`: Live team run rate at entry and exit.
  - `rr_gap_entry`: $\text{entry\_team\_rr} - \text{required\_rr\_entry}$
  - `rr_gap_exit`: $\text{exit\_team\_rr} - \text{required\_rr\_exit}$
  - `required_rr_change`: $\text{required\_rr\_entry} - \text{required\_rr\_exit}$ *(positive means required run rate has decreased)*.
  - `rr_gap_change`: $\text{rr\_gap\_exit} - \text{rr\_gap\_entry}$ *(positive means current scoring rate moved closer to or beyond required rate)*.
  - `runs_required_reduction`: $\text{runs\_required\_entry} - \text{runs\_required\_exit}$
  - `target_progress_entry`: $\frac{\text{entry\_score}}{\text{target}}$
  - `target_progress_exit`: $\frac{\text{exit\_score}}{\text{target}}$
  - `target_progress_change`: $\text{target\_progress\_exit} - \text{target\_progress\_entry}$
- First-innings trajectory fields are strictly `NaN` / `NULL`.

---

## 2. Exact Entry and Exit Points

An individual batter is evaluated strictly over their **exact crease window**:
- **Exact Entry State**: Measured at the precise ball the batter arrived (e.g. Over 7.2 = 44 legal balls bowled).
- **Exact Exit State**: Measured at the precise ball of departure or innings end (e.g. Over 13.4 = 82 legal balls bowled).
- **No Forcing to Checkpoints**: A batter entering at 7.2 and dismissed at 13.4 is evaluated strictly between 7.2 and 13.4, not forced to over 15.0.

---

## 3. Machine Learning Models & Baselines

Two distinct Random Forest models predict contextual expectations given **only** the entry state:

### Model 1: Expected Batter Runs (`ExpectedRunsRFModel`)
- **Target**: Actual batter runs (`actual_runs`).
- **Features**: Batting position, entry over, entry balls remaining, entry wickets remaining, entry score, entry team run rate, entry phase, chase flag, chase required RR, runs required at entry, situational benchmark at entry (`expected_final_entry` for 1st innings; `target` for chases).
- **Leakage Prevention**: Strictly zero in-innings outcome features (no actual balls faced, strike rate, boundaries, dismissal kind, or match result).

### Model 2: Expected Strike Rate (`ExpectedSRRFModel`)
- **Target**: Actual batter strike rate for innings with `balls_faced > 0`.
- **Features**: Strictly situational entry features matching Model 1.

### Baseline Comparisons (Test Set, 249 Unseen Matches, 3,795 Batter Innings):

| Model / Baseline | Expected Runs MAE | Expected Runs RMSE | Expected Runs $R^2$ |
|---|---|---|---|
| **Global Mean Baseline** | 16.96 | 21.84 | -0.0002 |
| **Batting Position Baseline** | 15.12 | 20.24 | 0.1410 |
| **Innings Phase Baseline** | 15.13 | 20.14 | 0.1492 |
| **Entry Over Baseline** | 14.76 | 19.94 | 0.1660 |
| **Random Forest (Situational)** | **14.55** | **19.78** | **0.1789** |

| Model / Baseline | Expected SR MAE | Expected SR RMSE | Expected SR $R^2$ |
|---|---|---|---|
| **Global Mean SR Baseline** | 52.84 | 69.08 | -0.0001 |
| **Batting Position SR Baseline** | 51.76 | 67.94 | 0.0326 |
| **Innings Phase SR Baseline** | 52.95 | 69.08 | -0.0001 |
| **Entry Over SR Baseline** | 52.90 | 69.07 | 0.0004 |
| **Random Forest (Situational)** | **51.51** | **67.31** | **0.0505** |

Both Random Forest models outperform all historical baselines.

---

## 4. Standardized Dataset Schema (`data/processed/batter_performance_dataset.csv`)

The dataset comprises **19,196 rows** across 1,243 matches:

```
Match Context:
  match_id, season, innings, team, opponent, target

Batter Context:
  player, batting_position, entry_ball, exit_ball, entry_over, exit_over

Entry State:
  entry_score, entry_wickets_lost, entry_wickets_remaining, entry_balls_remaining, entry_team_rr

Exit State:
  exit_score, exit_wickets_lost, exit_wickets_remaining, exit_balls_remaining, exit_team_rr

Dismissal Context:
  dismissal_status, dismissal_kind

Batter Performance:
  actual_runs, expected_runs, run_deviation, run_performance_ratio,
  actual_sr, expected_sr, sr_deviation, sr_performance_ratio,
  balls_faced, dot_balls, dot_ball_percentage, fours, sixes, boundary_runs

Partnership Context:
  partnership_runs, batter_partnership_runs, partner_runs,
  batter_partnership_share, partnership_duration

First-Innings Trajectory (ONLY for 1st innings; NULL for 2nd innings):
  expected_final_entry, expected_final_exit, expected_final_change,
  entry_score_deviation, exit_score_deviation, trajectory_deviation_change

Chase Context (ONLY for 2nd innings; NULL for 1st innings):
  runs_required_entry, runs_required_exit, required_rr_entry, required_rr_exit,
  required_rr_change, rr_gap_entry, rr_gap_exit, rr_gap_change,
  runs_required_reduction, target_progress_entry, target_progress_exit, target_progress_change
```

---

## 5. Rain & Incomplete Innings Audit

- **Total Matches in Dataset**: 1,243 matches.
- **Rain-Shortened First Innings**: 26 matches (<19.5 overs bowled and <10 wickets lost).
  - In Phase 3, these 26 matches were excluded from training `ExpectedScoreRFModel`.
  - In Phase 4A, all 172 first-innings batter innings from these 26 matches are retained in the dataset, but their 20-over trajectory fields (`expected_final_entry`, `expected_final_exit`, `expected_final_change`) are set to `NaN` because a 20-over projection model cannot validly score truncated 10-over innings.
- **Super Overs**: 16 matches with innings > 2 (85 batter innings).
  - As 1-over shootouts, neither 20-over first-innings trajectories nor standard chase calculations apply; both trajectory and chase columns are set to `NaN`.
- **Standard First Innings with Complete Trajectory**: 9,614 batter innings.
- **Standard Chase Innings with Complete Chase Context**: 9,325 batter innings.
