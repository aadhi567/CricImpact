# Phase 6A: Season Aggregation & Small-Opportunity Innings Audit

## Overview & Architecture

Phase 6A transitions the batter contribution framework from Phase 5B match-level contextual evaluation to a season-level aggregation layer.

The Phase 5B four-pillar model remains completely unchanged:
- **Pillar 1 ($P_1$)**: Match Context (25%)
- **Pillar 2 ($P_2$)**: Batter Performance (25%)
- **Pillar 3 ($P_3$)**: Team-State Impact (25%)
- **Pillar 4 ($P_4$)**: Counterfactual Value (25%)

Phase 6A aggregates these validated contextual match-level outputs across entire seasons while addressing sample-size, opportunity, and participation constraints.

---

## 1. Strict Did-Not-Bat (DNB) Rule

In cricket, when a team wins with wickets to spare or bowls out the opposition, lower-order batters and specialist bowlers often never come to the crease.

### Core Invariance Principles:
- If a player did not bat:
  $$\text{contribution\_score} = \text{NULL}$$
  $$\text{raw\_contribution} = \text{NULL}$$
  $$\text{team\_contribution\_share} = \text{NULL}$$
- **DNB is NEVER treated as 0, 50, average, or negative.**
- **DNB appearances NEVER enter the denominator** of batting averages, qualified averages, or contribution-per-opportunity.
- DNB is tracked strictly as metadata:
  $$\text{matches\_played} = \text{batting\_innings} + \text{did\_not\_bat\_matches}$$
  *Example*: 16 matches, 10 batting innings, 6 DNB $\rightarrow$ Denominator for average contribution score is **10**, never 16.

Across all 1,243 matches and 27,909 player-match appearances in the IPL dataset:
- Batting appearances: 19,111 (68.48%)
- DNB appearances: 8,798 (31.52%)
Treating DNB as 0 would artificially crush 31.5% of all player appearances, penalizing teams that won easily.

---

## 2. Small-Opportunity Empirical Audit

Before proposing any threshold, an empirical audit was conducted on all 19,111 standard 20-over batting innings:

### Distribution by Balls Faced
| Balls Faced Bucket | Total Innings | % of Dataset | High Impact ($\ge 65$) | Moderate Impact ($55-65$) | Par / Negligible ($45-55$) | Negative ($< 45$) |
|:---|---:|---:|---:|---:|---:|---:|
| 0 balls | 70 | 0.37% | 3 | 5 | 28 | 34 |
| 1 ball | 1,489 | 7.79% | 239 | 148 | 496 | 606 |
| 2 balls | 1,165 | 6.10% | 235 | 108 | 215 | 607 |
| 3 balls | 1,061 | 5.55% | 158 | 109 | 234 | 560 |
| 4 balls | 986 | 5.16% | 155 | 114 | 147 | 570 |
| 5 balls | 884 | 4.63% | 143 | 106 | 129 | 506 |
| 6–10 balls | 3,495 | 18.29% | 517 | 451 | 632 | 1,895 |
| 11+ balls | 9,961 | 52.12% | 2,752 | 1,833 | 1,777 | 3,599 |

### Key Audit Findings:
1. **Short Innings $\ne$ Low Contribution**: Of 5,655 innings lasting $\le 5$ balls, **933 (16.5%) had high positive impact ($\ge 65.0$)** and 590 (10.4%) had moderate positive impact. In total, 1,523 short innings provided positive match contribution.
2. **Low Runs $\ne$ Low Contribution**: 1,172 innings of under 10 runs produced contribution scores $\ge 65.0$.
3. **Not-Out $\ne$ Bonus or Penalty**: Not-out innings are evaluated strictly on contextual tempo and state evolution.

---

## 3. Threshold Analysis & Final Verdict

Five candidate exclusion policies were evaluated:

| Candidate | Rule Description | Excluded Innings | % Excluded | High-Impact Excluded | Verdict |
|:---|:---|---:|---:|---:|:---|
| **Candidate 0** | No exclusions (All genuine batting innings) | 0 | 0.00% | 0 | **ADOPTED as Primary View A** |
| **Candidate 1** | Contextual Zero Impact (Balls $\le 2$, Not Out, $\|C_{\text{raw}}\| \le 0.10$, minimal $\Delta EFS$/$\Delta RRR$) | 95 | 0.50% | 0 | **ADOPTED as Secondary View B** |
| **Candidate 2** | Balls $\le 2$ | 2,724 | 14.25% | 477 | **REJECTED** (Destroys 477 match-winners/cameos) |
| **Candidate 3** | Balls $\le 5$ | 5,655 | 29.59% | 933 | **REJECTED** (Destroys 933 elite finishes) |
| **Candidate 4** | Runs $< 10$ | 8,758 | 45.83% | 1,172 | **REJECTED** (Destroys 45.8% of all innings) |

### Verdict:
**"Insufficient evidence for a hard exclusion threshold."**
A crude balls or runs cutoff fails because it cannot distinguish between a meaningless 1* off 1 when victory is already assured versus a match-winning 1* off 1 on the final delivery.

Therefore, the framework provides **Two Season-Level Views**:
- **View A (All-Innings Season Metrics)**: Complete, un-filtered record of all batting opportunities.
- **View B (Qualified Season Metrics)**: Only excludes Candidate 1 (95 negligible non-dismissal innings) for sensitivity comparisons.

---

## 4. Critical Edge Cases (Cases A through J)

Evaluated and confirmed in [`phase6_edge_cases.json`](file:///models/contribution/phase6/phase6_edge_cases.json):

1. **Case A (1* off 1, victory assured)**: Contribution Score = **33.9** (Low incremental value, genuine evaluation, not NULL).
2. **Case B (1* off 1, match-winning final ball)**: Contribution Score = **62.8** (Delivering victory under maximum pressure).
3. **Case C (5* off 2, normal middle overs)**: Contribution Score = **68.6** (SR 250 cameo recognized above par).
4. **Case D (8* off 3, death overs)**: Contribution Score = **73.0** (High leverage death acceleration).
5. **Case E (8* off 12, team under pressure)**: Contribution Score = **40.7** (Subpar tempo consuming valuable deliveries).
6. **Case F (30 off 5, death overs)**: Contribution Score = **89.6** (Elite finish, high trajectory deviation).
7. **Case G (30 off 5, early overs)**: Contribution Score = **85.8** (Same explosive P2=96.4, but context and scaling calibrated for early overs).
8. **Case H (5* off 3, team already scoring at 12 RR)**: Contribution Score = **47.3** (Avoids over-crediting when platform was already dominant).
9. **Case I (5* off 3, team at 28/4 crisis)**: Contribution Score = **71.9** (Crisis collapse pressure recognized).
10. **Case J (0 balls faced, run out)**: Contribution Score = **47.0** (Evaluates gracefully without zero-division error, not NULL).

---

## 5. Mathematical Formulations

### Season Performance Quality (View A Average)
$$\text{average\_contribution\_score} = \frac{1}{N_{\text{batting}}} \sum_{i=1}^{N_{\text{batting}}} \text{contribution\_score}_i$$
*(DNB excluded from numerator and denominator)*

### Season Total Positive Contribution
$$\text{total\_positive\_raw\_contribution} = \sum_{i=1}^{N_{\text{batting}}} \max(0, C_{\text{raw}, i})$$

### Season Team Contribution Share
$$\text{season\_team\_contribution\_share} = \frac{\sum_{i \in \text{player}} \max(0, C_{\text{raw}, i})}{\sum_{j \in \text{team}} \max(0, C_{\text{raw}, j})} \times 100$$
*(Negative raw contribution does not receive positive share; DNB excluded from numerator and denominator)*

### Contribution Per Batting Opportunity
$$\text{contribution\_per\_batting\_opportunity} = \frac{\text{total\_positive\_raw\_contribution}}{\text{batting\_innings}}$$

---

## 6. Configurable Player Eligibility Filters

Player selection filters are strictly independent of the contribution scores:
- `season`: e.g., '2016', '2023', 'ALL'
- `minimum_runs`: e.g., 100, 200, 300, 400, 500
- `minimum_batting_innings`: optional
- `minimum_balls_faced`: optional
- `team`: specific franchise or 'ALL'

Changing the run threshold (e.g. from 300 to 400 runs) filters the displayed player list without changing any player's individual contribution scores, total contribution, or team share.

---

## 7. Contextual Categories

Preserved from Phase 5B with strict NULL retention when unobserved:
- `first_innings_contribution`: mean score when `innings == 1`
- `chase_contribution`: mean score when `innings == 2`
- `powerplay_contribution`: mean score when `entry_over < 6.0`
- `middle_over_contribution`: mean score when $6.0 \le \text{entry\_over} < 16.0$
- `death_over_contribution`: mean score when $\text{entry\_over} \ge 16.0$ or $\text{exit\_over} \ge 16.0$
- `high_pressure_contribution`: mean score when $\text{pillar1\_context\_score} \ge 60.0$

If a batter has no observations in a phase (e.g., an opener who never enters in middle overs, or a player who only batted in 1st innings), that category returns **NULL**, never zero.
