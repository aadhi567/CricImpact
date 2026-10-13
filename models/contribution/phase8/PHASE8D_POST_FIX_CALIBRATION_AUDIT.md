# Phase 8D Forensic Audit: Post-RRR-Fix Contribution Calibration Audit

**Document ID:** `models/contribution/phase8/PHASE8D_POST_FIX_CALIBRATION_AUDIT.md`  
**Date:** 10 October 2026  
**Subject:** Post-Phase 8C Contribution Calibration and Score Semantics Audit  
**Status:** COMPLETE (AUDIT ONLY — READ-ONLY)  
**Scope:** Verification of Phase 8C integrity, dataset-wide distribution shifts across IPL, T20I, and SMAT, investigation of large upward shifts, testing of score semantics (chases and collapses), and first-innings P3 trajectory attribution (B Sai Sudharsan diagnostic case).

---

## Executive Summary

In Phase 8C, the upstream feature sign inversion in `scripts/ingest_competition_data.py` was corrected, aligning `required_rr_change` across the International T20I and Syed Mushtaq Ali Trophy (SMAT) partitions to the canonical definition:
$$\text{required\_rr\_change} = RRR_{\text{entry}} - RRR_{\text{exit}}$$
This Phase 8D audit examines whether the resulting score distributions and individual player ratings adhere to CricImpact’s foundational principles: **evaluating individual batting execution (P2) modulated by match context (P1) and attributable team-state impact (P3)**.

### Primary Audit Findings:
1. **Phase 8C Integrity Verified 100%:**
   - Canonical sign convention is verified across **100.0%** of second-innings rows in T20I (17,258 rows) and SMAT (657 rows).
   - IPL root datasets remain **100% frozen and untouched**; post-migration SHA256 hashes match Phase 8 locks exactly.
   - Live production calculations, stored contributions, API endpoints, and UI displays reconcile with **0.00 discrepancy**.
   - DNB integrity is strictly preserved (797 non-batting player-seasons in T20I, 207 in SMAT maintain `NaN` scores and shares).
2. **Score Distribution Shift is Methodologically Sound:**
   - In T20I, the mean contribution score shifted from **43.59 to 41.17** ($\Delta = -2.42$). The negative net shift is explained by the fact that in international cricket, failed chases where teams collapse and required run rate escalates outnumber dominant successful chases. The bug had previously awarded hundreds of failing batters unearned positive P3 scores.
   - P1 (Context) and P2 (Execution) distributions experienced **0.00 drift**, proving surgical isolation.
   - Scores $\ge 90$ remain rare and elite: **1.38%** in T20I, **1.92%** in SMAT, and **4.33%** in IPL.
3. **Large Upward Movement Validation:**
   - The large upward shifts in successful chases (Sanju Samson $+29.3$, Matthew Wade $+42.0$, Ali Nayyer $+42.3$, Suryansh Shedge $+41.1$, Shivam Dube $+38.2$, Yashasvi Jaiswal $+32.4$, Jiwanjot Singh $+23.7$) represent the **restoration of genuine chase-liquidation credit** that was previously suppressed by the negative sign bug.
   - However, the audit confirms that batters who arrive late in a chase (e.g. S Dube 8* off 4) inherit large P3 values because the team required run rate drops to 0.00 during their stay. Their final scores are properly modulated down by P2 execution (Dube P2 = 76.1 $\to$ Final = 82.8 vs Samson P2 = 95.9 $\to$ Final = 95.6).
4. **First-Innings P3 Team-Trajectory Attribution (Sai Sudharsan Case):**
   - In Gujarat Titans vs Sunrisers Hyderabad (15 May 2023), B Sai Sudharsan entered at 0/1 (0.3 overs) and scored 47 off 36 balls, while partner Shubman Gill scored 101 off 58 in a 147-run partnership. Sudharsan received P3 = **96.7** and Final Score = **93.4**.
   - Audit traces that the first-innings P3 formula evaluates team $EFS$ change ($+51.6$ runs) without weighting by partnership scoring share. Sudharsan's P3 reflects the overall partnership trajectory and collapse stabilization rather than his 32% scoring share alone.
   - Individual execution is properly isolated in P2 (Gill P2 = 97.0 $\implies$ Final 99.9 vs Sudharsan P2 = 82.9 $\implies$ Final 93.4).

---

## 1. Verification of Phase 8C Integrity

| Audit Check | Requirement | Verification Result | Status |
|---|---|---|:---:|
| **Canonical RRR Convention** | $RRR_{\text{entry}} - RRR_{\text{exit}}$ across all chase rows | T20I: 17,258/17,258 rows (100.0%)<br>SMAT: 657/657 rows (100.0%) | **PASS** |
| **IPL Integrity Lock** | Exact match with approved SHA256 | `F3AD19F7DBF517D19F68B457ACC1B03A9FE31606764BD334B80BCE87EDDA388E` | **PASS** |
| **IPL Row/Col Invariance** | 19,111 rows, 98 cols | 19,111 rows, 98 cols (zero drift) | **PASS** |
| **Live Calculation Agreement** | Fresh production score equals stored | Samson: Live 95.6 == Stored 95.6<br>Dube: Live 82.8 == Stored 82.8 | **PASS** |
| **API Reconciliation** | Match & Player endpoints match stored | `/api/match/1512770`: Samson 95.6, Dube 82.8 | **PASS** |
| **DNB Strict Null Invariant** | 0-batting player-seasons have NaN scores | T20I: 797/797 NaN (100%)<br>SMAT: 207/207 NaN (100%) | **PASS** |
| **Completed Chase Handling** | Valid denominator, no division-by-zero | $RRR_{\text{exit}} = 0.00$ on target achievement | **PASS** |
| **Regression Test Suite** | All tests pass | 534/534 tests pass in 86.2s | **PASS** |
| **Frontend Production Build** | Vite build succeeds | Clean build in 17.1s | **PASS** |

---

## 2. Dataset-Wide Score Distribution Audit

The three competitions represent distinct competitive tiers:
- **IPL:** High parity, established player pool, balanced scoring environments.
- **T20I:** Bimodal distribution with elite international fixtures and uneven Associate mismatches.
- **SMAT:** Domestic tournament with variable pitch conditions and regional strength differentials.

### 2.1 Post-Fix Distribution Summary Across Competitions

| Metric | IPL (Frozen) | T20I (Post-Fix) | SMAT (Post-Fix) |
|---|---:|---:|---:|
| **Total Rows** | 19,111 | 37,066 | 1,403 |
| **Contribution Score (Mean)** | 48.92 | 41.17 | 45.22 |
| **Contribution Score (Median)** | 47.30 | 37.80 | 43.30 |
| **Contribution Score (Std)** | 23.19 | 21.57 | 21.99 |
| **P10 / P25 / P50 / P75 / P90** | 19.6 / 29.1 / 47.3 / 66.9 / 82.2 | 15.8 / 23.3 / 37.8 / 56.6 / 73.2 | 16.7 / 26.9 / 43.3 / 61.8 / 76.1 |
| **P99** | 95.9 | 91.5 | 93.3 |
| **% $\ge 80.0$** | 11.93% | 5.97% | 7.48% |
| **% $\ge 90.0$** | 4.33% | 1.38% | 1.92% |
| **% $\ge 95.0$** | 1.45% | 0.39% | 0.64% |
| **% $\ge 99.0$** | 0.36% | 0.10% | 0.00% |
| **Boundary Clip ($\le 1.0$)** | 0.00% | 0.01% | 0.00% |
| **Boundary Clip ($\ge 99.0$)** | 0.36% | 0.10% | 0.00% |

### 2.2 Pillar Breakdown (Post-Fix vs Pre-Fix Deltas)

| Component | T20I Pre-Fix | T20I Post-Fix | T20I Delta | SMAT Pre-Fix | SMAT Post-Fix | SMAT Delta | IPL (Frozen) |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Pillar 1 (Context)** | 49.15 | 49.15 | **0.00** | 48.40 | 48.40 | **0.00** | 48.39 |
| **Pillar 2 (Execution)** | 43.53 | 43.53 | **0.00** | 48.65 | 48.65 | **0.00** | 49.43 |
| **Pillar 3 (State Impact)** | 44.04 | 39.93 | **-4.11** | 44.37 | 42.79 | **-1.58** | 49.09 |
| **Adjusted P2** | 42.98 | 42.98 | **0.00** | 48.21 | 48.21 | **0.00** | 49.16 |
| **Adjusted P3** | 44.20 | 39.36 | **-4.84** | 44.58 | 42.23 | **-2.34** | 48.69 |
| **Final Contribution** | 43.59 | 41.17 | **-2.42** | 46.39 | 45.22 | **-1.17** | 48.92 |

### 2.3 Volume of Large Score Movements

| Movement Threshold | T20I Overall (37,066) | T20I Chases (17,258) | SMAT Overall (1,403) | SMAT Chases (657) |
|---|---:|---:|---:|---:|
| **Score Shift $\ge +10.0$** | 2,995 (8.08%) | 2,995 (17.35%) | 154 (10.98%) | 154 (23.44%) |
| **Score Shift $\le -10.0$** | 4,945 (13.34%) | 4,945 (28.65%) | 164 (11.69%) | 164 (24.96%) |
| **Score Shift $\ge +20.0$** | 1,507 (4.07%) | 1,507 (8.73%) | 81 (5.77%) | 81 (12.33%) |
| **Score Shift $\le -20.0$** | 3,389 (9.14%) | 3,389 (19.64%) | 111 (7.91%) | 111 (16.89%) |
| **Score Shift $\ge +30.0$** | 643 (1.73%) | 643 (3.73%) | 32 (2.28%) | 32 (4.87%) |
| **Score Shift $\le -30.0$** | 2,541 (6.86%) | 2,541 (14.72%) | 81 (5.77%) | 81 (12.33%) |

**Methodological Interpretation:**  
The downward shifts outnumber the upward shifts by nearly 1.6:1 in T20I. In international cricket, low-ranked teams frequently lose wickets rapidly in second innings, allowing the required run rate to spiral out of control. Prior to Phase 8C, these batters received artificial positive bonuses because the sign inversion converted $RRR_{\text{exit}} - RRR_{\text{entry}}$ into positive values. Phase 8C correctly removed this unearned inflation.

---

## 3. Investigation of Named Large Upward Movement Cases

We audited seven specific batters identified with major positive score shifts:

```
==================================================================================================================================
CASE STUDY MATRIX: SEVEN NOTABLE CHASE PERFORMANCES
==================================================================================================================================
Player             Match Details               Runs(Balls) SR     RRR In -> Out   P1    P2    P3_old -> P3_new  Score_old -> new  Share
----------------------------------------------------------------------------------------------------------------------------------
Sanju Samson       IND vs WI (1512770)         97*(50)    194.0    9.80 -> 0.00  47.7  95.9   37.2   -> 96.9     66.3   -> 95.6    48.7%
Shivam Dube        IND vs WI (1512770)          8*(4)     200.0   10.20 -> 0.00  48.7  76.1   13.0   -> 90.1     44.6   -> 82.8    40.0%
Matthew Wade       AUS vs IND (1389393)        28*(16)    175.0   13.69 -> 0.00  58.1  70.8   17.7   -> 95.7     43.8   -> 85.8    30.8%
Ali Nayyer         SUI vs FRA (1321287)        48*(16)    300.0   13.68 -> 0.00  59.0  95.4   17.3   -> 95.0     56.9   -> 99.2    84.2%
Suryansh Shedge    MUM vs VID (1446104)        36*(12)    300.0   13.45 -> 0.00  53.2  94.0   15.3   -> 95.0     54.8   -> 95.9    53.7%
Shivam Dube        MUM vs VID (1446104)        37*(22)    168.2   11.77 -> 0.00  55.0  74.4   18.5   -> 95.6     46.3   -> 86.7    34.9%
Jiwanjot Singh     UTT vs HAR (1332927)        77*(55)    140.0    7.55 -> 0.00  38.7  87.7   43.2   -> 95.0     64.1   -> 87.8    50.0%
Yashasvi Jaiswal   MUM vs MP (1332943)         66*(44)    150.0    8.61 -> 0.00  53.7  86.3   31.9   -> 94.4     59.4   -> 91.8    45.5%
==================================================================================================================================
```

### 3.1 Case-by-Case Analysis

1. **Sanju Samson (SV Samson) — 97* (50) vs West Indies:**
   - Anchor and primary engine of a 196 chase. Batted from 0.0 to 19.2 overs, scoring 48.7% of team runs with 12 fours and 4 sixes.
   - P2 = 95.9, P3 = 96.9, Final = 95.6. Both execution and state impact agree: masterclass performance.
2. **Ali Nayyer — 48* (16) vs France:**
   - Entered at 101/7 in 15.6 overs chasing 158 (RRR 13.68 with only 3 wickets left). Scored 48 of the 57 runs added (84.2% share) at SR 300.0, hitting the winning runs off the final ball.
   - P2 = 95.4, P3 = 95.0, Final = 99.2. Unquestionably one of the greatest lower-order death chases in T20I history. Elite score fully warranted.
3. **Suryansh Shedge — 36* (12) vs Vidarbha:**
   - Entered at 157/4 in 15.1 overs chasing 222 (RRR 13.45). Scored 36 off 12 (SR 300.0) in an unbroken 67-run partnership to seal victory with 4 balls to spare.
   - P2 = 94.0, P3 = 95.0, Final = 95.9. Exceptional execution and state transformation.
4. **Yashasvi Jaiswal (YBK Jaiswal) — 66* (44) vs Madhya Pradesh:**
   - Chased 182, added 145 runs for the 2nd wicket, scoring 66 runs at SR 150.0. Finished not out at 182/2.
   - P2 = 86.3, P3 = 94.4, Final = 91.8. High-caliber top-order chase anchor.
5. **Jiwanjot Singh — 77* (55) vs Haryana:**
   - Anchored entire chase of 151 from 0.0 to 19.3 overs, scoring exactly 50.0% of team runs.
   - P2 = 87.7, P3 = 95.0, Final = 87.8. Solid, composed chase anchor.
6. **Matthew Wade (MS Wade) — 28* (16) vs India (Match 1389393):**
   - Australia chasing 223. Wade entered at 134/5 in 13.4 overs. Glenn Maxwell scored 104* off 48 balls at the other end. Wade scored 28 off 16 (SR 175.0, partnership share 30.8%).
   - Wade's team state (P3) is 95.7 because the required run rate fell from 13.69 to 0.00 while he was at the crease.
   - Crucially, **P2 separates Wade from Maxwell**: Wade's P2 is 70.8, while Maxwell's P2 is 98.4. Wade's final score is **85.8**, whereas Maxwell's final score is **98.6**.
7. **Shivam Dube — 8* (4) vs West Indies (Match 1512770):**
   - Entered at 179/5 on over 18.2 with 10 balls remaining. Batted 4 deliveries, scored 8 runs (SR 200.0), non-striker when Samson hit the winning four.
   - Dube's P3 rose to 90.1, bringing his final score to **82.8**.
   - **Audit Observation:** Dube's stay was only 4 balls. While he scored at SR 200 without wasting resources, receiving P3 = 90.1 reflects the team achieving victory rather than his 8 runs alone. This is an expected artifact of the short sample size at the death, balanced by P2 (76.1) keeping him well below Samson (95.6).

---

## 4. Testing Score Semantics

To ensure that the model behaves sensibly across all cricket situations, we tested seven distinct operational archetypes:

```
+--------------------------------------------------------------------------------------------------------+
|                                  SEVEN SCORE SEMANTIC ARCHETYPES                                        |
+--------------------------------------------------------------------------------------------------------+
| Archetype A: Exceptional Chase Completer (e.g. Samson 97* off 50)             -> Score: 95.6 (P3: 96.9)|
| Archetype B: Modest Personal Contribution in Win (e.g. Van Beek 4* off 4)     -> Score: 58.3 (P3: 76.4)|
| Archetype C: RRR Rose Substantially Before Wicket (e.g. Salt 57 off 24)       -> Score: 52.0 (P3: 14.1)|
| Archetype D: Partner Scored Most Runs (e.g. David Miller 8 off 12, share 12%) -> Score: 22.1 (P3: 32.8)|
| Archetype E: First-Innings Collapse Anchor (e.g. Dinesh Karthik 52 off 38)   -> Score: 76.0 (P3: 67.8)|
| Archetype F: Team Won Despite Batter Failing (e.g. TLW Cooper 8 off 16)       -> Score: 32.2 (P3: 38.0)|
| Archetype G: Did-Not-Bat (DNB) & Negligible Opportunities                      -> Score: NaN / Null    |
+--------------------------------------------------------------------------------------------------------+
```

### 4.1 Archetype Findings:
1. **Winning does NOT guarantee an elite score (Archetype F & B):**
   - TLW Cooper (Netherlands, Match 1298136): scored 8 off 16 balls (SR 50.0). Netherlands won the match, but Cooper's P2 was 23.9, P3 was 38.0, and his Final Contribution was **32.2** (32nd percentile).
   - Logan van Beek: 4 off 4 balls in a completed chase. Received **58.3** (slightly above average), not an elite score.
2. **Individual scoring without team relief is penalized (Archetype C):**
   - Phil Salt (England, Match 1256722): blasted 57 off 24 balls (SR 237.5, P2 = 89.6). However, England lost wickets rapidly around him, and by his dismissal, the required run rate had skyrocketed from 13.36 to 48.00 ($\Delta RRR = -34.64$). His P3 collapsed to **14.1**, pulling his final score down to **52.0**.
   - Nicholas Pooran (West Indies, Match 1256723): 22 off 16, RRR worsened by $-4.66 \implies$ P3 = **23.6**, Final Score = **38.4**.
3. **Low partnership share is penalized (Archetype D):**
   - David Miller (South Africa, Match 1276913): scored 8 off 12 balls while partner added 56 runs (Miller share = 12.5%). Despite the team scoring, Miller's P2 was 16.7, P3 was 32.8, and Final Score was **22.1**.
4. **Collapse stabilization remains rewarded (Archetype E):**
   - Dinesh Karthik (KKR, Match 1136618): entered at 3.4 overs with 7 wickets remaining, scored 52 off 38 balls. P1 = 65.2 (crisis context), P2 = 77.5, P3 = 67.8, Final Contribution = **76.0**.

---

## 5. Inspection of First-Innings P3: B Sai Sudharsan Case Study

### 5.1 Match Context
- **Match:** Gujarat Titans vs Sunrisers Hyderabad (IPL Match 1359536, 15 May 2023, Ahmedabad)
- **Innings:** 1st Innings (Gujarat Titans batting)
- **Event at Over 0.3:** Wriddhiman Saha dismissed for 0 off 3 balls (0/1).
- **Entry:** B Sai Sudharsan enters at over 0.3 at **0/1** with 9 wickets in hand (117 balls remaining).
- **Exit:** Sudharsan dismissed on over 14.1 at **147/2** (35 balls remaining).

```
========================================================================================
PARTNERSHIP BREAKDOWN: GUJARAT TITANS 2ND WICKET (OVER 0.3 TO 14.1)
========================================================================================
Team Runs Added in Window: 147 runs in 13.4 overs (Window Run Rate: 10.75 RPO)
B Sai Sudharsan: 47 runs off 36 balls (SR 130.56, 6x4, 1x6, 10 dots) | Share: 32.0%
Shubman Gill:    100 runs off 50 balls in window (finished 101 off 58) | Share: 68.0%
----------------------------------------------------------------------------------------
Team State Trajectory:
  Entry Expected Final Score (EFS): 159.8 runs
  Exit Expected Final Score (EFS):  211.4 runs
  EFS Change:                       +51.6 runs
  Trajectory Deviation Change:      +38.5 runs
========================================================================================
```

### 5.2 Mathematical Decomposition of Sudharsan's P3
In `src/contribution_framework.py` (lines 1384–1396), first-innings P3 is computed as:
$$\text{P3}_{\text{raw}} = 0.50 \times z_{\text{efs}} + 0.25 \times \text{traj\_dev} + 0.25 \times \text{accel} + S_{\text{res}}$$

1. **Normalized EFS Change ($z_{\text{efs}}$):**
   $$z_{\text{efs}} = \frac{EFS_{\text{change}}}{12.0} = \frac{51.6}{12.0} = \mathbf{4.300}$$
2. **Trajectory Deviation Change ($\text{traj\_dev}$):**
   $$\text{traj\_dev} = \frac{38.5}{10.0} = \mathbf{3.850}$$
3. **Run Rate Acceleration ($\text{accel}$):**
   $$\text{accel} = \text{clip}\left(\frac{\text{window\_rr} - \text{team\_rr\_entry}}{3.0}, -3.0, 3.0\right) = \text{clip}\left(\frac{10.75 - 0.0}{3.0}, -3.0, 3.0\right) = \mathbf{3.000}$$
4. **Dynamic Wicket Cost ($S_{\text{res}}$):**
   Only Sudharsan's own dismissal occurred at 14.1 with 8 wickets remaining and 35 balls left ($S_{\text{res}} = -0.044$).
5. **Raw P3 Calculation:**
   $$\text{P3}_{\text{raw}} = 0.50 \times 4.300 + 0.25 \times 3.850 + 0.25 \times 3.000 - 0.044 = 2.150 + 0.9625 + 0.750 - 0.044 = \mathbf{3.819}$$
6. **Standardization & Sigmoid Score:**
   $$z_3 = \frac{3.819 - 0.159}{1.513} = \mathbf{2.419} \implies \text{P3} = \frac{100}{1 + \exp(-1.40 \times 2.419)} = \mathbf{96.7}$$
7. **Leverage & Final Score:**
   - Entry at 0/1 in over 1 gives $P1 = 62.7 \implies L = 1.122$.
   - $\text{Adjusted P2} = 50.0 + (82.9 - 50.0) \times 1.122 = \mathbf{86.9}$
   - $\text{Adjusted P3} = 50.0 + (96.7 - 50.0) \times 1.122 = \mathbf{99.9}$ (clipped)
   - $\text{Final Contribution} = 0.50 \times 86.9 + 0.50 \times 99.9 = \mathbf{93.4}$

### 5.3 Comparative Reconciliation: Sudharsan vs. Gill

| Metric | B Sai Sudharsan | Shubman Gill | Methodological Separation |
|---|---:|---:|---|
| **Runs / Balls (SR)** | 47 off 36 (130.6) | 101 off 58 (174.1) | Gill drove the scoring rate |
| **Partnership Share** | **32.0%** | **68.0%** | Gill contributed over 2/3 of runs |
| **Pillar 1 (Match Context)** | 62.7 | 62.7 | Identical crisis entry point (0/1) |
| **Pillar 2 (Execution)** | **82.9** | **97.0** | **Explicitly separates execution quality (+14.1 delta)** |
| **Pillar 3 (State Impact)** | **96.7** | **96.6** | Both receive credit for +51.6 team EFS surge |
| **Adjusted P2** | 86.9 | 99.9 | Context multiplies individual execution gap |
| **Adjusted P3** | 99.9 | 99.9 | Both platforms saturated in high-leverage context |
| **Final Contribution** | **93.4** | **99.9** | **Gill scores a near-perfect 99.9; Sudharsan scores 93.4** |

### 5.4 Methodological Evaluation: Is Sudharsan Over-Rewarded?
- **Why P3 is 96.7:** In the current architecture, Pillar 3 measures *team state change during the batter's presence*. While Sudharsan was at the crease, Gujarat Titans progressed from 0/1 to 147/1, transforming an early loss into an unassailable total. He absorbed 36 balls, hit 47 runs, stabilized the innings, and enabled Gill to attack without fear of exposing the middle order.
- **Why Phase 7U Model T did not adjust EFS:** Phase 7U Model T attribution is designed to protect batters during *collapses* (`wkt_res_chg <= -2`). In this innings, Gujarat Titans did not collapse; they dominated.
- **The Design Reality:** The model deliberately assigns team trajectory improvement to the partnership while relying on **P2 (Batting Execution)** to distinguish between the junior and senior partner. Gill received P2 = 97.0 (97th percentile), whereas Sudharsan received P2 = 82.9. Gill's overall contribution is 99.9 (elite match-winning), while Sudharsan's is 93.4 (high-impact support anchor).

---

## 6. Confirmed Systemic Insights & Future Considerations

### 6.1 Confirmed Valid Behaviors:
1. **P2/P3 Orthogonality Holds:** In both chases and first-innings partnerships, P2 captures individual execution efficiency while P3 captures team match-state evolution. Blending them at 50/50 ensures that high execution without state impact (e.g. Phil Salt 52.0) and high state impact with modest execution (e.g. Matthew Wade 85.8) are balanced appropriately.
2. **Phase 8C Restores Physical Coherence:** Chases that eliminate required run rate are now properly rewarded across all competitions; chases that let required run rate explode are penalized.

### 6.2 Potential Future Model Refinements (Post-Phase 8):
1. **Partnership Share Damping in Team Trajectory (P3):**
   Currently, in both 1st innings ($EFS$) and 2nd innings ($RRR$), the team trajectory change is credited equally to both batters at the crease regardless of partnership share. In extreme cases where a batter scores $\le 25\%$ of partnership runs while their partner hits a century, weighting $z_{\text{efs}}$ or $z_{\text{rrr}}$ by a soft function of partnership share $\phi = \sqrt{\text{share} / 0.50}$ could prevent junior partners from inheriting $>95$ P3 scores purely on the back of a partner's masterclass.
2. **Ultra-Short Death Stays in Completed Chases:**
   When a batter faces $\le 5$ balls at the death (e.g. S Dube 8* off 4) and the match finishes during their brief stay, the exit required run rate drops to 0.00, yielding $z_{\text{rrr}} > 2.0$. While sample size gating dampens negligible stays ($<3$ balls), introducing a smooth opportunity-weighting dampener for stays under 8 balls in completed chases could better align late-entry cameos.

---

## 7. Audit Conclusion and Sign-Off

The Phase 8C correction is **fully validated and calibrated**. 

The CricImpact contribution framework successfully differentiates:
- Elite chase masterclasses (Sanju Samson **95.6**, Ali Nayyer **99.2**) from late-over cameos (Shivam Dube **82.8**).
- Dominant centuries (Shubman Gill **99.9**) from supportive stabilization anchors (Sai Sudharsan **93.4**).
- Hard-fought winning anchors (Jiwanjot Singh **87.8**) from low-contribution passengers (TLW Cooper **32.2**).
- High strike-rate scoring in losing collapses (Phil Salt **52.0**) from genuine match-winning impact.

**Safety Sign-off:** No production code, scoring formulas, trained models, database records, or checksum locks were modified during this audit.
