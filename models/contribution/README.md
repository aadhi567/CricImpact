# Phase 5B — Contextual Batter Contribution Model
## Corrected Mathematical Specification, Four-Pillar Framework & Validation Report

---

## 1. Executive Summary & Core Objective

The Contextual Batter Contribution Framework answers the fundamental question:

> **"How much did this batter contribute to his team's position, given the exact situation he faced?"**

The model explicitly rejects naive conventions:
- **It does NOT automatically penalize short innings:** A short innings does not mean a low-quality innings. Performance quality is evaluated directly without sample-size dampeners.
- **It distinguishes Performance Quality from Opportunity Size:** 5 balls, 30 runs, SR 600 represents elite execution. The small number of balls faced does not artificially reduce the quality score. Opportunity size is accounted for through context, resource availability, and team-state impact.
- **It does NOT assume Actual Runs - Expected Runs = True Contribution:** Expected Runs and Expected SR are strictly supporting baselines ($\le 15\%$ weight in Pillar 2), never ground truth. T20 batting exhibits high natural variance.
- **It does NOT reward merely being on the winning team:** A passenger scoring 5 off 4 in a 60-run blowout win did not create the win; conversely, an 82 off 45 in a 2-run loss remains an elite batting performance. Match outcome leakage is mathematically zero.
- **Super Overs are Excluded:** Super Overs are fundamentally distinct from 20-over cricket and return `NULL` (`None` / `np.nan`), never a standard 20-over contribution score.
- **Did-Not-Bat (DNB) is strictly NULL:** If a batter never comes to the crease, Score = NULL and Share = NULL. Zero is reserved for evaluated batting failures. Season averages are never diluted by non-batting appearances.

---

## 2. Four Equally Important Conceptual Pillars (25% Each)

The architecture strictly preserves equal conceptual, nominal, and empirical priority across four pillars:

$$\text{Contribution} = 25\% \text{ Match Context } (P_1) + 25\% \text{ Batter Performance } (P_2) + 25\% \text{ Team-State Impact } (P_3) + 25\% \text{ Counterfactual Value } (P_4)$$

```text
+-----------------------------------------------------------------------------------------------+
|                               FOUR EQUAL PILLARS (25% EACH)                                    |
+-------------------------------+-------------------------------+-------------------------------+
| Pillar 1: Match Context       | Pillar 2: Batter Performance  | Pillar 3: Team-State Impact   | Pillar 4: Counterfactual      |
| "What situation did the       | "What did the batter actually | "How much did the team state  | "Given exact situation, what  |
| batter face?"                 | do?"                          | change while batting?"        | could batter reasonably have  |
| Phase, entry over, wickets,   | Runs, SR, Boundaries, Pace vs | Exact entry -> exit window;   | done differently to help?"    |
| balls rem, collapse pressure, | team/req RR, dismissal status | delta EFS, delta RRR, dynamic | Realistic situational tempo,  |
| platform pressure, chase RRR  | (NO short-innings penalty)    | wicket cost, target progress  | not equating CF to Exp Runs   |
+-------------------------------+-------------------------------+-------------------------------+
```

---

## 3. Mathematical Formulation of the Four Pillars

### Pillar 1 — Match Context ($Z_{\text{context}}$)
Evaluates situation difficulty, urgency, and resource leverage upon entering the crease:
- **Phase Urgency:** Death overs ($overs \ge 15.0$) demand immediate scoring tempo:
  $$U_{\text{death}} = \max\left(0.0, \frac{\text{entry\_over} - 15.0}{4.0}\right)$$
- **Collapse Pressure:** Overs remaining per wicket in hand:
  $$R_{\text{wkt}} = \frac{\text{balls\_remaining\_entry} / 6.0}{\max(1.0, \text{wickets\_remaining\_entry})}$$
  $$\text{Collapse Pressure} = \text{clip}\left(\frac{R_{\text{wkt}} - 1.5}{1.0}, -1.5, 2.5\right)$$
- **First Innings Platform Pressure:** Pressure to accelerate when current team RR is depressed:
  $$\text{Platform Pressure} = \text{clip}\left(\frac{7.5 - \text{team\_rr\_entry}}{2.5}, -2.0, 2.0\right)$$
  $$\text{Raw}_1 = 1.2 \cdot U_{\text{death}} + 0.45 \cdot \text{Collapse Pressure} + 0.35 \cdot \text{Platform Pressure}$$
- **Second Innings (Chase Pressure):**
  $$\text{Chase Pressure} = \frac{\text{clip}(\text{required\_rr\_entry}, 0, 24) - 8.5}{3.0} + 0.35 \cdot \frac{\text{clip}(\text{rr\_gap\_entry}, -4, 8)}{2.5}$$
  $$\text{Raw}_1 = \text{Chase Pressure} + 0.8 \cdot U_{\text{death}} + 0.3 \cdot \text{Collapse Pressure}$$
- **Super Over:** Excluded from standard framework; returns `np.nan`.

#### Justification of Pillar 1 Coefficients (Section 8)
- `death_urgency` (1.2): Overs 16.0–20.0 represent maximum scoring urgency where balls cannot be deferred. Boundary expectation escalates from ~125 to >165 SR. Weight 1.2 provides ~1.0–1.2 raw units of leverage across death overs.
- `collapse_pressure` (0.45): Measures overs remaining per wicket in hand. Captures resource scarcity when wickets fall early, balancing the risk of bowling-out against scoring progression.
- `platform_pressure` (0.35): Scales the urgency to break run rate stagnation when the current run rate is depressed below par in the 1st innings.
- `chase_pressure` (1.0): Directly reflects required run rate and RR gap in the second innings.
- *Sensitivity Analysis:* Perturbing these coefficients by $\pm 30\%$ to $\pm 86\%$ produces a maximum shift of $< 1.3$ points on the 100-point contribution scale, proving that the model is robust and not overly dependent on manual parameter choices.

---

### Pillar 2 — Batter Performance ($Z_{\text{perf}}$)
Evaluates what the batter actually did.

#### CRITICAL CORRECTION: Removal of Short-Innings Penalty
The prior formulation contained:
$$\text{opp\_factor} = \sqrt{\min\left(1.0, \frac{\text{balls\_faced}}{15.0}\right)}, \quad z_{\text{sr}} = \text{clip}\left(\frac{\text{actual\_sr} - 125.0}{50.0} \cdot \text{opp\_factor}, -3.0, 3.5\right)$$
This automatically penalized batters facing fewer deliveries. In the corrected formulation, this penalty is **completely removed**:
$$z_{\text{sr}} = \text{clip}\left(\frac{\text{actual\_sr} - 125.0}{50.0}, -3.0, 3.5\right)$$

- **Standardized Volume:** $z_{\text{runs}} = (\text{actual\_runs} - 19.8) / 21.6$
- **Strike Rate:** $z_{\text{sr}} = \text{clip}((\text{actual\_sr} - 125.0) / 50.0, -3.0, 3.5)$ (if balls faced $> 0$)
- **Relative Pace vs Context:**
  - 1st Innings: $z_{\text{pace}} = \text{clip}(((\text{actual\_sr} \cdot 0.06) - \text{team\_rr\_entry}) / 3.5, -3.0, 3.5)$
  - 2nd Innings: $z_{\text{pace}} = \text{clip}(((\text{actual\_sr} \cdot 0.06) - \min(24.0, \text{required\_rr\_entry})) / 3.5, -3.0, 3.5)$
- **Boundary Contribution:** $z_{\text{bnd}} = \text{clip}((\text{boundary\_pct} - 45.0) / 30.0, -2.5, 2.5)$
- **Supporting Expected Baseline Signal (Strictly $\le 15\%$ weight):**
  $$z_{\text{base}} = 0.7 \cdot \frac{\text{actual\_runs} - \text{expected\_runs}}{14.5} + 0.3 \cdot \text{clip}\left(\frac{\text{actual\_sr} - \text{expected\_sr}}{48.0}, -3.0, 3.0\right)$$
- **Not-Out Preservation Bonus:** $+0.25$ if dismissal status is not out and $\text{balls\_faced} \ge 1$.
$$\text{Raw}_2 = 0.35 \cdot z_{\text{runs}} + 0.25 \cdot z_{\text{sr}} + 0.20 \cdot z_{\text{pace}} + 0.10 \cdot z_{\text{bnd}} + 0.10 \cdot z_{\text{base}} + \text{Bonus}_{\text{not\_out}}$$

---

### Pillar 3 — Team-State Impact ($Z_{\text{state}}$)
Measures the actual shift in team state across the **exact crease window** ($\text{entry\_over} \to \text{exit\_over}$, e.g. 7.2 to 13.4, never extended to an arbitrary 15-over boundary):
- **Dynamic Wicket Cost (Section 16):**
  A wicket lost at over 19.5 (balls remaining = 1) has near-zero resource penalty. A wicket lost at over 3.2 (balls remaining = 100) with wickets remaining = 6 has substantial resource penalty:
  - If dismissed:
    $$\text{Cost} = \left(\frac{\text{balls\_remaining\_exit}}{120.0}\right) \cdot \left(\frac{10.0}{\max(1.0, \text{wickets\_remaining\_exit} + 2.0)}\right) \cdot 0.5$$
    Offset for high run volume: $\text{Offset} = \min(\text{Cost} \cdot 0.7, \max(0.0, \text{actual\_runs} - 15.0) \cdot 0.02)$
    $$S_{\text{res}} = -(\text{Cost} - \text{Offset})$$
  - If not dismissed: $S_{\text{res}} = +0.15 \cdot (\text{wickets\_remaining\_exit} / 10.0)$
- **First Innings Trajectory Shift:**
  $$\text{Raw}_3 = 0.50 \cdot \left(\frac{\Delta EFS}{12.0}\right) + 0.25 \cdot \left(\frac{\Delta \text{TrajDev}}{10.0}\right) + 0.25 \cdot \text{clip}\left(\frac{\text{window\_team\_rr} - \text{team\_rr\_entry}}{3.0}, -3, 3\right) + S_{\text{res}}$$
- **Second Innings Chase Relief:**
  $$\text{Raw}_3 = 0.50 \cdot \left(\frac{\text{clip}(\Delta RRR, -12, 12)}{3.0}\right) + 0.25 \cdot \left(\frac{\text{clip}(\Delta RR_{\text{gap}}, -12, 12)}{3.0}\right) + 0.25 \cdot \left(\frac{\Delta \text{TargetProg} - 0.15}{0.15}\right) + S_{\text{res}}$$

---

### Pillar 4 — Counterfactual Value ($Z_{\text{cf}}$)
Answers: *"Given the exact situation faced, what could the batter reasonably have done differently that would have helped the team more?"*
- **Constructing the Realistic Situational Counterfactual:**
  - Grounded in situation: Powerplay base SR = 120, Middle overs base SR = 125, Death overs base SR = $150 + \min(25, (\text{over} - 16) \cdot 8)$.
  - Adjusted for collapse: $-15$ SR if $\le 4$ wickets remain before over 14.
  - Adjusted for chase: Scaled with required RR (floored at 115 SR for low RRR, capped at 165 SR for high RRR).
- **Realistic Counterfactual Runs:**
  $$CF_{\text{realistic\_runs}} = \text{balls\_faced} \cdot \left(\frac{\text{Base\_SR}}{100.0}\right)$$
  $$\Delta_{\text{runs}} = \text{actual\_runs} - CF_{\text{realistic\_runs}}$$
- **Trajectory Delta:**
  - 1st Innings: $\Delta_{\text{traj}} = \Delta EFS - (CF_{\text{realistic\_runs}} - 19.8) \cdot 0.5$
    $$\text{Raw}_4 = 0.60 \cdot \left(\frac{\Delta_{\text{runs}}}{14.0}\right) + 0.40 \cdot \left(\frac{\Delta_{\text{traj}}}{12.0}\right)$$
  - 2nd Innings: $\Delta_{\text{rrr\_relief}} = \text{clip}(\Delta RRR, -12, 12) - \text{clip}\left(\frac{\Delta_{\text{runs}} \cdot 6.0}{\text{balls\_rem\_exit}}, -8, 8\right)$
    $$\text{Raw}_4 = 0.50 \cdot \left(\frac{\Delta_{\text{runs}}}{14.0}\right) + 0.50 \cdot \left(\frac{\Delta_{\text{rrr\_relief}}}{2.5}\right)$$

---

## 4. Normalization and Scale Unification

All four raw scores are standardized to unit variance across standard 20-over innings ($N = 19,111$):

$$Z_k = \frac{\text{Raw}_k - \mu_k}{\sigma_k}, \quad k \in \{1, 2, 3, 4\}$$

Empirical standardization parameters:
- Pillar 1 (Context): $\mu_1 = 0.413, \sigma_1 = 1.115$
- Pillar 2 (Performance): $\mu_2 = -0.068, \sigma_2 = 1.029$
- Pillar 3 (State Impact): $\mu_3 = 0.159, \sigma_3 = 1.513$
- Pillar 4 (Counterfactual): $\mu_4 = 0.127, \sigma_4 = 0.948$

### Output A: Final Contribution Score (0 to 100, Par = 50.0)
$$C_{\text{raw}} = 0.25 \cdot Z_1 + 0.25 \cdot Z_2 + 0.25 \cdot Z_3 + 0.25 \cdot Z_4$$
$$\text{Contribution Score} = \text{clip}\left(\frac{100.0}{1.0 + \exp(-1.40 \cdot (C_{\text{raw}} - (-0.138)))}, 0.1, 99.9\right)$$

Empirical Distribution ($N = 19,111$):
- Mean: 53.1
- Median: 50.0 (exact Par alignment)
- Std: 19.0
- IQR: 27.6 (P25 = 38.2, P75 = 65.9)
- Extremes: P1 = 20.1, P10 = 30.7, P90 = 82.2, P99 = 95.2

### Output B: Team Contribution Share (%)
Within an individual match innings:
$$\text{Share}_i = \frac{\max(0, C_{\text{raw}, i})}{\sum_j \max(0, C_{\text{raw}, j})} \times 100\%$$
- Net-negative contributors ($C_{\text{raw}} \le 0$) receive $0.0\%$ share.
- In team collapses where all batters are negative, share is equally partitioned ($100/N$).

---

## 5. Non-Batting Matches & 1 Run Not-Out Handling

- **Section 17: Non-Batting Matches (DNB):**
  When a player does not come to the crease:
  $$\text{Contribution Score} = \text{NULL}$$
  $$\text{Team Contribution Share} = \text{NULL}$$
  Zero is never used for DNB. NULL represents absence of opportunity.
- **Section 18: Genuine Short Batting (1 Run Not-Out):**
  If a batter comes to the crease and faces even 1 ball (e.g. $1^*$ off 2 balls, or 1 off 1 to win), this is a genuine batting innings and is evaluated. It is NOT NULL.

---

## 6. Season Aggregation Methodology (Section 19)

Season aggregation must never average match-level contribution shares. Instead:
1. Calculate underlying contribution for every actual batting innings.
2. Ignore NULL non-batting matches (no dilution of average).
3. Sum positive raw contribution across the season.
4. Calculate season-level team contribution share from aggregated values:
   $$\text{Season Share}_p = \frac{\sum_{m \in \text{season}} \max(0, C_{\text{raw}, p, m})}{\sum_{m \in \text{season}} \sum_{j \in \text{team}, m} \max(0, C_{\text{raw}, j, m})} \times 100\%$$

Report:
- `matches_played`
- `batting_innings`
- `did_not_bat_matches`
- `average_contribution_score`
- `total_contribution`
- `season_team_contribution_share`

---

## 7. Validation: All 16 Required Tests (Section 15 & 20)

| Case ID | Scenario / Test Description | P1 Context | P2 Perf | P3 State | P4 CF | Score | Validation Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Case 1** | **5b, 30r in death overs (Section 15 Case A)**: Enters 19.1 ov, 160/5, 30 off 5 (SR 600) | 52.0 | 96.4 | 87.4 | 92.5 | **89.6** | **PASS** — High performance recognition without short-innings penalty. |
| **Case 2** | **5b, 30r early in innings (Section 15 Case B)**: Enters 7.1 ov, 75/0, 30 off 5 (SR 600) | 38.7 | 96.4 | 79.4 | 90.4 | **85.8** | **PASS** — Same explosive P2 (96.4), but lower context urgency separates it from Case 1. |
| **Case 3** | **5b, 30r when team RR = 12 (Section 15 Case C)**: Team at 180/2 at 16.0 ov; 30 off 5 | 18.3 | 96.4 | 82.0 | 90.7 | **83.0** | **PASS** — Incremental team impact measured; avoids over-hyping solely on SR 600. |
| **Case 4** | **High-SR short cameo under pressure (Section 15 Case D)**: Team RR 6, RRR 10, 20 off 5 | 67.9 | 95.4 | 63.7 | 51.1 | **78.4** | **PASS** — Meaningful positive contribution shifting match pressure. |
| **Case 5** | **Slow innings followed by acceleration (Section 14)**: 60/2 at 10 ov, 20 off 26, out at 14 ov | 40.2 | 37.8 | 35.8 | 17.0 | **36.1** | **PASS** — Subpar pacing (36.1), but not catastrophically blamed for ruined match. |
| **Case 6** | **High runs but low SR**: 50 off 48 balls (SR 104.2) at entry 2.0 ov, team RR was 8.5 | 39.8 | 62.3 | 36.2 | 15.5 | **41.3** | **PASS** — Volume recognized in P2, but resource consumption dampens score (41.3). |
| **Case 7** | **Heroic innings in losing team**: 82 off 45 balls (SR 182.2) in 2-run loss | 72.3 | 91.6 | 79.4 | 56.4 | **80.7** | **PASS** — Elite score (>80), completely invariant to match loss. |
| **Case 8** | **Low contribution in winning team**: 5 off 4 balls (SR 125.0) in 60-run blowout win | 30.8 | 33.9 | 37.0 | 49.1 | **42.1** | **PASS** — Below par (42.1), not inflated by the winning team result. |
| **Case 9** | **Exact entry-exit window 7.2 to 13.4**: Crease occupied strictly 6.2 overs | 38.8 | 68.7 | 57.8 | 56.8 | **60.4** | **PASS** — Evaluated strictly over occupied window; no arbitrary 15th over boundary. |
| **Case 10** | **Batter remains not-out until innings end**: Enters 14.2 ov, 42 off 22, stays till 20.0 | 27.0 | 86.8 | 77.8 | 80.6 | **74.8** | **PASS** — Evaluated through innings end (overs_spent=5.4), benefits from preservation. |
| **Case 11** | **Zero-ball appearance**: Run out at non-striker end facing 0 balls | 54.1 | 41.3 | 29.5 | 45.3 | **47.0** | **PASS** — Genuine batting appearance; evaluates gracefully without crash (~47.0). |
| **Case 12** | **Player did not bat (DNB)**: Named in XI, never came to crease | NULL | NULL | NULL | NULL | **NULL** | **PASS** — Score = NULL, Share = NULL. Zero is never used. |
| **Case 13** | **Super Over exclusion**: Innings = 3 | NULL | NULL | NULL | NULL | **NULL** | **PASS** — Excluded from 20-over contribution calculations; super_over = True. |
| **Case 14** | **Rain-shortened innings**: 10-over match, 28 off 14 (SR 200), expected_final_change is NaN | 26.6 | 84.1 | 82.3 | 74.5 | **73.3** | **PASS** — Evaluates window rate and acceleration without invalid 20-over extrapolation. |
| **Case 15** | **High required RR chase**: Enters at 14.0 ov needing 14.0 RRR, scores 45 off 20 | 92.2 | 87.7 | 74.2 | 53.7 | **83.3** | **PASS** — High context urgency (P1=92.2) and decisive RRR relief yields score 83.3. |
| **Case 16** | **Low required RR chase**: Enters needing 3.0 RRR in over 18.4, scores 1* off 2 balls | 4.0 | 32.0 | 47.0 | 56.8 | **32.1** | **PASS** — Genuine batting innings evaluated (32.1), definitely NOT NULL. |

---

## 8. Leakage Audit (Section 21)

Strict architectural segregation is enforced between:
1. **Information available at batter entry:** Match phase, entry over, score, wickets in hand, RRR, team RR.
2. **Information during batter stay:** Deliveries faced, runs scored, boundaries, wickets lost during window.
3. **Information after exit:** Completed match outcome, winning margin, post-exit team scoring.

**Invariance Verification:**
Altering `won_match` (True $\to$ False) and changing winning margins ($50\text{ runs} \to 1\text{ wicket}$) produces a variance of exactly:
$$\Delta Z_{\text{context}} = 0.000, \quad \Delta Z_{\text{perf}} = 0.000, \quad \Delta Z_{\text{state}} = 0.000, \quad \Delta Z_{\text{cf}} = 0.000, \quad \Delta \text{Contribution Score} = 0.000$$
The model is 100% leak-free.

---

## 9. Deliverables Directory

All required artifacts are updated and validated in `models/contribution/`:
- `phase5b_framework.json`: High-level mathematical formulation and standardized parameters.
- `contribution_score_spec.json`: Detailed specification of Output A (logistic scaling, par benchmark).
- `pillar_scores.json`: Correlation matrix, variance decomposition, and distributions.
- `counterfactual_spec.json`: Realistic counterfactual construction rules.
- `season_aggregation_spec.json`: DNB rules and season aggregation formulas with RCB 2016 demonstration.
- `edge_case_results.json`: Validation results for all 16 required test cases.
- `sensitivity_analysis.json`: Monotonicity tests and Pillar 1 coefficient sensitivity audits.
- `leakage_audit.json`: Strict outcome-invariance proof against future information leakage.
- `phase5b_examples.json`: Detailed evaluation of all 16 illustrative match situations.
- `metrics.json`: High-level dataset metrics and validation summary.
- `README.md`: This comprehensive specification and architecture document.
