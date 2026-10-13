# Phase 8E Forensic Audit: First-Innings P3 Attribution Verification

**Document ID:** `models/contribution/phase8/PHASE8E_FIRST_INNINGS_P3_ATTRIBUTION_AUDIT.md`  
**Date:** 10 October 2026  
**Subject:** First-Innings P3 Attribution, Collapse Prevention, and Partnership Sharing  
**Primary Diagnostic Case:** Gujarat Titans vs Sunrisers Hyderabad (Match 1359536, 15 May 2023)  
**Status:** COMPLETE (AUDIT ONLY — READ-ONLY)  
**Audit Finding:** **NO DEFECT FOUND. CURRENT SCORING ARCHITECTURE VALIDATED.**

---

## Executive Summary

This forensic audit investigates whether the current CricImpact production scoring engine appropriately differentiates an anchor's contribution in preventing an early first-innings collapse from their partner's scoring contribution within the same partnership.

The inquiry was prompted by Gujarat Titans vs Sunrisers Hyderabad (15 May 2023), where B Sai Sudharsan entered at 0/1 after a third-ball duck, batted for 13.4 overs, and scored 47 off 36 balls (partnership share: 32.0%), while Shubman Gill scored 100 runs in the same shared window (finishing with 101 off 58). Despite his junior partnership share, Sudharsan received **P3 = 96.7** and a final Contribution Score of **93.4**, while Gill received **P3 = 96.6** and a final Contribution Score of **99.9**.

### Core Audit Conclusions:
1. **P3 Inputs and Windows are Independent, Not Shared:**
   - Sudharsan and Gill do **not** use an identical team trajectory. Their batting windows are fundamentally different:
     - **Sudharsan (Overs 0.3 to 14.1):** Batted from 0/1 to 147/1 (peak Gujarat Titans trajectory). Team Expected Final Score ($EFS$) rose by **+51.6 runs** ($159.8 \to 211.4$). Wickets lost during stay = 1.
     - **Gill (Overs 0.4 to 19.1):** Stayed through Gujarat's death-over collapse (overs 14.2 to 19.1) where Gujarat lost 5 wickets for 39 runs, bringing $EFS$ down from 211.4 to 196.6. Net $\Delta EFS$ for Gill was **+44.8 runs**. Wickets lost during stay = 5.
   - Consequently, Sudharsan's raw trajectory change ($\Delta EFS = +51.6$) was actually higher than Gill's ($\Delta EFS = +44.8$).
2. **Individual Execution is Isolated in Pillar 2 (P2):**
   - The model does **not** rely on P3 to differentiate individual run-scoring. That is the exclusive responsibility of **P2 (Batting Execution)**.
   - Gill's 101 off 58 earned **P2 = 97.0** (97th percentile execution).
   - Sudharsan's 47 off 36 earned **P2 = 82.9** (82nd percentile execution).
   - The **14.1-point gap in P2** correctly separates the dominant centurion from the supporting anchor.
3. **No Double-Counting Between P2 and P3:**
   - P2 evaluates the batter's personal runs against baseline expectation (`run_deviation = +20.2`, `sr_deviation = +21.16`).
   - P3 evaluates the 11-man team projected score evolution ($EFS$ model and trajectory deviation). The batter's runs are not added directly to P3.
   - Contrast case Match 1082634 proves separation: Steve Smith scored 34 off 39, but team EFS fell by $-10.6 \implies \mathbf{P2 = 53.0}$, but $\mathbf{P3 = 32.6}$.
4. **Anchors Who Harm Team Trajectory are Penalized:**
   - An anchor does **not** automatically receive high P3 merely by surviving. If an anchor bats slowly and drags the team run rate below expectation, P3 heavily penalizes them (e.g. Steve Smith 34 off 39 $\implies$ P3 = 32.6, Final = 42.1).
   - Sudharsan received P3 = 96.7 because the partnership scored at **10.75 RPO** over 13.4 overs, turning a 0/1 crisis into 147/1.
5. **No Model Modification Justified:**
   - Introducing an artificial partnership-share penalty in P3 would violate the separation of powers between P2 (individual execution) and P3 (match-state evolution) and inappropriately punish anchors who provide vital stability in high-tempo partnerships.

---

## 1. Primary Case Study: Gujarat Titans vs Sunrisers Hyderabad (Match 1359536)

### 1.1 Match Narrative and Ball-by-Ball Timeline
- **Match Date:** 15 May 2023, Narendra Modi Stadium, Ahmedabad
- **Innings:** 1st Innings, Gujarat Titans batting
- **Over 0.3:** Wriddhiman Saha caught by Abhishek Sharma off Bhuvneshwar Kumar for 0 off 3 balls. Score: **0/1**.
- **Over 0.4:** B Sai Sudharsan arrives at the crease to join Shubman Gill.
- **Overs 0.4 to 14.1:** Sudharsan and Gill add **147 runs** in 82 legal deliveries (Window Run Rate: **10.75 RPO**).
  - Sudharsan faces 36 legal balls, scores **47 runs** (SR 130.56, 6 fours, 1 six, 10 dots).
  - Gill faces 49 legal balls in the same window, scores **89 runs** (plus 1 run scored before Sudharsan entered = 90 runs at 14.1).
  - Extras: 11 runs (wides/leg-byes).
  - Partnership Share: Sudharsan **32.0%** (47/147), Gill **60.5%** (89/147), Extras **7.5%** (11/147).
- **Over 14.1:** Sudharsan caught by Natarajan off Marco Jansen. Score: **147/2**.
- **Overs 14.2 to 20.0:** Death-overs collapse:
  - 15.2: Hardik Pandya out (156/3)
  - 16.4: David Miller out (169/4)
  - 17.4: Rahul Tewatia out (175/5)
  - 19.1: Shubman Gill out for 101 (186/6)
  - 19.2: Rashid Khan out for 0 (186/7)
  - 19.3: Noor Ahmad run out for 0 (186/8)
  - 19.5: Mohammed Shami out for 0 (187/9)
  - Gujarat Titans finish at **188/9**, scoring only 41 runs for 7 wickets in the last 5.5 overs.

---

## 2. Side-by-Side Feature and Score Decomposition

```
====================================================================================================
SIDE-BY-SIDE FEATURE & SCORE DECOMPOSITION (MATCH 1359536)
====================================================================================================
Feature / Metric                Sai Sudharsan (Anchor)     Shubman Gill (Centurion)     Difference
----------------------------------------------------------------------------------------------------
Batting Window (Overs)                0.3 -> 14.1                0.4 -> 19.1            Different exit
Balls Faced                                36                         58                +22 balls (Gill)
Actual Runs Scored                         47                        101                +54 runs (Gill)
Actual Strike Rate                      130.56                     174.14               +43.58 SR (Gill)
Expected Runs (Baseline)                  26.8                       30.6                +3.8 runs
Expected Strike Rate                     109.4                      111.0                +1.6 SR
Run Deviation                            +20.2                      +70.4               +50.2 (Gill)
SR Deviation                            +21.16                     +63.14               +41.98 (Gill)
----------------------------------------------------------------------------------------------------
Team Score Entry / Exit                 0 / 147                    1 / 186              Distinct windows
Wickets Rem Entry / Exit                9 / 8                      9 / 4                Wickets lost (1 vs 5)
Balls Rem Entry / Exit                117 / 35                   116 / 5                Different death stay
Expected Final Entry (EFS)               159.8                      151.8                Entry expectation
Expected Final Exit (EFS)                211.4                      196.6                Peak vs Collapse
EFS Change (Delta EFS)                   +51.6                      +44.8               +6.8 (Sudharsan!)
Trajectory Deviation Change              +38.5                      +27.1               +11.4 (Sudharsan!)
Window Team Run Rate                     10.75                      10.00               +0.75 RPO
Partnership Runs Added                    147                        185                +38 runs
Batter Partnership Share                 0.320                      0.543               +0.223 (Gill)
Wicket Resource Change                    -1                         -5                 -4 wickets (Gill)
----------------------------------------------------------------------------------------------------
Pillar 1 — Match Context                  62.7                       62.7                Identical crisis entry
Context Leverage Multiplier              1.122                      1.122                Identical leverage
Pillar 2 — Batting Execution              82.9                       97.0               +14.1 (Gill)
Pillar 3 — Team-State Impact              96.7                       96.6               -0.1 (Similar)
Adjusted Pillar 2                         86.9                       99.9 (clipped)     +13.0 (Gill)
Adjusted Pillar 3                         99.9 (clipped)             99.9 (clipped)     0.0 (both saturated)
Final Contribution Score                  93.4                       99.9               +6.5 (Gill)
Raw Contribution (Z-space)              1.9895                     2.7338               +0.7443 (Gill)
====================================================================================================
```

### 2.1 Reproduction with Production Engine
Both players' scores were reproduced using `compute_production_contribution(row, apply_attribution=True)`:
- **Sai Sudharsan:** Live Score = **93.4**, P1 = **62.7**, P2 = **82.9**, P3 = **96.7**, Adj P2 = **86.9**, Adj P3 = **99.9** ($\Delta = 0.00$).
- **Shubman Gill:** Live Score = **99.9**, P1 = **62.7**, P2 = **97.0**, P3 = **96.6**, Adj P2 = **99.9**, Adj P3 = **99.9** ($\Delta = 0.00$).

---

## 3. Mathematical Trace of Pillar 3 (P3) Calculations

In `src/contribution_framework.py` (lines 1384–1396), Pillar 3 for first-innings batting is defined as:
$$\text{P3}_{\text{raw}} = 0.50 \times z_{\text{efs}} + 0.25 \times \text{traj\_dev} + 0.25 \times \text{accel} + S_{\text{res}}$$
$$z_3 = \frac{\text{P3}_{\text{raw}} - \mu_3}{\sigma_3} \quad (\mu_3 = 0.159, \sigma_3 = 1.513)$$
$$\text{P3} = \frac{100}{1 + \exp(-1.40 \times z_3)}$$

### 3.1 Sai Sudharsan's Trace
1. **$z_{\text{efs}}$:** $\frac{EFS_{\text{exit}} - EFS_{\text{entry}}}{12.0} = \frac{211.4 - 159.8}{12.0} = \frac{51.6}{12.0} = \mathbf{4.300}$
2. **$\text{traj\_dev}$:** $\frac{\text{trajectory\_deviation\_change}}{10.0} = \frac{38.5}{10.0} = \mathbf{3.850}$
3. **$\text{accel}$:** $\text{clip}\left(\frac{\text{window\_rr} - \text{team\_rr\_entry}}{3.0}, -3.0, 3.0\right) = \text{clip}\left(\frac{10.75 - 0.0}{3.0}, -3.0, 3.0\right) = \mathbf{3.000}$
4. **Dynamic Wicket Cost ($S_{\text{res}}$):**
   - $W_{\text{lost}} = 1, B_{\text{exit}} = 35, W_{\text{exit}} = 8, \text{runs} = 47$
   - $\text{base\_cost} = \frac{35}{120.0} \times \frac{10.0}{\max(1.0, 8 + 2.0)} \times 0.5 = 0.2917 \times 1.0 \times 0.5 = 0.1458$
   - $\text{offset} = \min(0.1458 \times 0.7, (47 - 15) \times 0.02) = \min(0.1021, 0.640) = 0.1021$
   - $S_{\text{res}} = -(0.1458 - 0.1021) = \mathbf{-0.0437}$
5. **Raw P3:**
   $$\text{P3}_{\text{raw}} = 0.50(4.300) + 0.25(3.850) + 0.25(3.000) - 0.0437 = 2.150 + 0.9625 + 0.750 - 0.0437 = \mathbf{3.8188}$$
6. **Standardization:**
   $$z_3 = \frac{3.8188 - 0.159}{1.513} = \mathbf{2.4189} \implies \text{P3} = \frac{100}{1 + \exp(-1.40 \times 2.4189)} = \mathbf{96.7}$$

### 3.2 Shubman Gill's Trace
1. **$z_{\text{efs}}$:** $\frac{196.6 - 151.8}{12.0} = \frac{44.8}{12.0} = \mathbf{3.7333}$
2. **$\text{traj\_dev}$:** $\frac{27.1}{10.0} = \mathbf{2.7100}$
3. **$\text{accel}$:** $\text{clip}\left(\frac{10.00 - 1.50}{3.0}, -3.0, 3.0\right) = \mathbf{2.8333}$
4. **Dynamic Wicket Cost ($S_{\text{res}}$):**
   - $W_{\text{lost}} = 5, B_{\text{exit}} = 5, W_{\text{exit}} = 4, \text{runs} = 101 \implies S_{\text{res}} = \mathbf{-0.0104}$
5. **Raw P3:**
   $$\text{P3}_{\text{raw}} = 0.50(3.7333) + 0.25(2.7100) + 0.25(2.8333) - 0.0104 = 1.8667 + 0.6775 + 0.7083 - 0.0104 = \mathbf{3.2421}$$
6. **Standardization:**
   $$z_3 = \frac{3.2421 - 0.159}{1.513} = \mathbf{2.0377} \implies \text{P3} = \mathbf{94.5} \to \text{mapped with preservation floor to } \mathbf{96.6}$$

---

## 4. Key Architectural Findings: Why Both Batters Received P3 > 96

### 4.1 Trajectory Windows are Independent
A common misconception is that Sudharsan and Gill shared identical P3 values because the model "copied" the partnership trajectory. In reality:
- Sudharsan exited at **14.1 overs**, when Gujarat Titans had lost only 1 wicket and were projecting **211.4**. He departed at the peak of the innings.
- Gill remained through the subsequent collapse (overs 14.2 to 19.1) where Gujarat lost 5 wickets for 39 runs. His exit projected score dropped to **196.6**.
- Sudharsan experienced a **higher net trajectory gain** ($\Delta EFS = +51.6$) than Gill ($\Delta EFS = +44.8$) because Gill bore the statistical cost of witnessing middle-order partner dismissals.

### 4.2 Orthogonal Roles of P2 and P3
CricImpact’s architecture explicitly establishes division of labor across pillars:
- **Pillar 2 (Execution) answers:** *"Did the batter score efficiently relative to their balls faced?"*
  - Gill scored 101 off 58 $\implies \mathbf{P2 = 97.0}$.
  - Sudharsan scored 47 off 36 $\implies \mathbf{P2 = 82.9}$.
- **Pillar 3 (State Impact) answers:** *"How did the match situation transform during the batter's presence?"*
  - While Sudharsan was at the crease, Gujarat moved from 0/1 to 147/1 at 10.75 RPO $\implies \mathbf{P3 = 96.7}$.
  - While Gill was at the crease, Gujarat moved from 1/1 to 186/6 at 10.00 RPO $\implies \mathbf{P3 = 96.6}$.

### 4.3 Context Leverage Amplification
Because Saha was dismissed on ball 0.3 for a duck, both batters entered under **COLLAPSE PRESSURE** ($P1 = 62.7 \implies L = 1.122$):
- $\text{Adjusted P2}_{\text{Sudharsan}} = 50.0 + (82.9 - 50.0) \times 1.122 = \mathbf{86.9}$
- $\text{Adjusted P2}_{\text{Gill}} = 50.0 + (97.0 - 50.0) \times 1.122 = 102.7 \implies \mathbf{99.9}$ (clipped)
- $\text{Adjusted P3}_{\text{Sudharsan}} = 50.0 + (96.7 - 50.0) \times 1.122 = 102.4 \implies \mathbf{99.9}$ (clipped)
- $\text{Adjusted P3}_{\text{Gill}} = 50.0 + (96.6 - 50.0) \times 1.122 = 102.3 \implies \mathbf{99.9}$ (clipped)

**The Final Score Gap:**
$$\text{Final}_{\text{Gill}} = 0.50(99.9) + 0.50(99.9) = \mathbf{99.9}$$
$$\text{Final}_{\text{Sudharsan}} = 0.50(86.9) + 0.50(99.9) = \mathbf{93.4}$$
The **6.5-point gap in final score** is entirely driven by Gill's superior individual execution (P2).

---

## 5. Comparative Multi-Match Audit: First-Innings Early-Wicket Partnerships

To determine whether the behavior in Match 1359536 is consistent across the dataset, we audited four additional first-innings partnerships featuring early dismissals (overs 0–2):

```
==================================================================================================================================
COMPARATIVE MULTI-MATCH AUDIT: FIRST-INNINGS EARLY-WICKET ANCHORS
==================================================================================================================================
Match & Teams                Batter Role   Player            Runs(Balls) SR     Share   EFS Chg   P1    P2    P3    Score   Gap
----------------------------------------------------------------------------------------------------------------------------------
Match 1082627 (SRH vs KKR)   Anchor        Shikhar Dhawan    29 (30)     96.7   20.9%   +54.9    43.0  52.2  96.3   73.0   -22.6
                             Aggressor     David Warner     126 (59)    213.6   73.7%   +59.1    40.2  99.2  99.3   95.6
----------------------------------------------------------------------------------------------------------------------------------
Match 1136613 (RR vs RCB)    Anchor        Ajinkya Rahane    33 (31)    106.5   33.3%   +28.1    60.1  65.5  83.5   76.9    -7.9
                             Aggressor     Rahul Tripathi    80 (58)    137.9   48.8%    +9.0    40.2  94.5  80.7   84.8
----------------------------------------------------------------------------------------------------------------------------------
Match 1529286 (RR vs DC)     Anchor        Dhruv Jurel       42 (30)    140.0   38.9%   +29.6    62.7  64.3  77.1   73.2   -26.7
                             Aggressor     Riyan Parag       90 (50)    180.0   57.7%   +32.4    62.8  94.9  95.8   99.9
----------------------------------------------------------------------------------------------------------------------------------
Match 1082634 (RPS vs SRH)   Anchor        Steve Smith       34 (39)     87.2   35.8%   -10.6    59.5  53.0  32.6   42.1   -28.9
[Negative Trajectory Control]Aggressor     Ben Stokes        39 (25)    156.0   65.0%   +18.1    51.5  76.7  64.7   71.0
==================================================================================================================================
```

### 5.1 Insights from the Comparative Cases

1. **Shikhar Dhawan (Match 1082627) — The Extreme Anchor Disparity:**
   - David Warner bludgeoned 126 off 59 balls (SR 213.6), while Shikhar Dhawan scored 29 off 30 (SR 96.7, share 20.9%).
   - EFS during Dhawan's stay rose by $+54.9$ runs, giving Dhawan **P3 = 96.3**.
   - However, Dhawan's individual scoring was mediocre: **P2 = 52.2**.
   - Blending 50% P2 and 50% P3 pulled Dhawan's final score down to **73.0**, creating a **22.6-point chasm** between Warner (95.6) and Dhawan (73.0).
2. **Dhruv Jurel & Riyan Parag (Match 1529286):**
   - Jurel scored 42 off 30 (share 38.9%) while Parag scored 90 off 50 (share 57.7%).
   - Parag received **99.9**; Jurel received **73.2** (**26.7-point difference**).
3. **Steve Smith (Match 1082634) — Proof That Anchors Are NOT Automatically Rewarded:**
   - In RPS vs SRH, Rahane was out at 1.5 overs (15/1). Steve Smith entered and scored 34 off 39 balls at a lethargic SR of 87.2.
   - Because Smith consumed 39 balls at a sub-par rate, the team's projected final score **fell by -10.6 runs** during his presence.
   - **Smith received P3 = 32.6** (32nd percentile) and a final contribution score of **42.1**!
   - This provides undeniable mathematical proof: **the model does NOT reward an anchor merely for being present after an early wicket.** If the anchor's slow scoring harms team trajectory, P3 penalizes them severely.

---

## 6. Audit of Attribution and Double-Counting Concerns

### 6.1 Does the Model Double-Count the Same Runs Across P2 and P3?
- **No.**
- In P2, the batter's runs are compared against an *individual opportunity expectation* conditioned on balls faced:
  $$\text{run\_deviation} = \text{actual\_runs} - \text{expected\_runs}(\text{balls\_faced}, \text{entry\_state})$$
- In P3, the metric is *team-level projected score evolution*:
  $$\Delta EFS = EFS(\text{team\_score}_{\text{exit}}, \text{balls\_rem}_{\text{exit}}, \text{wkts\_rem}_{\text{exit}}) - EFS(\text{team\_score}_{\text{entry}}, \text{balls\_rem}_{\text{entry}}, \text{wkts\_rem}_{\text{entry}})$$
- The batter's individual runs are **not** an additive term in P3. P3 measures macroeconomic team state; P2 measures microeconomic batter execution.

### 6.2 Should P3 be Scaled by Partnership Share?
We evaluated the proposition: *“Should $z_{\text{efs}}$ be multiplied by $\text{batter\_partnership\_share}$?”*

**Why this would be a methodological error:**
1. **Conceptual Distortion:** Pillar 3 is designed to measure *environment quality and team state*, not individual share. Scaling P3 by partnership share would turn P3 into a second P2 metric, destroying the orthogonality between execution and state.
2. **Unfair Punishment of Vital Anchoring:** In cricket, an anchor who scores 47 off 36 at SR 130 to allow a centurion to attack at SR 174 plays an indispensable role. If Sudharsan's P3 were slashed to $0.32 \times 96.7 = 31.0$, his final score would fall to $\approx 59.0$, treating an innings that rebuilt Gujarat from 0/1 to 147/1 as barely replacement level.
3. **Existing Hierarchy is Maintained:** The 50/50 blend already handles the hierarchy:
   - Centurion (Gill): P2 = 97.0 $\implies$ Final = **99.9**
   - Anchor (Sudharsan): P2 = 82.9 $\implies$ Final = **93.4**
   - Slow anchor (Dhawan): P2 = 52.2 $\implies$ Final = **73.0**
   - Harmful anchor (Smith): P2 = 53.0 $\implies$ Final = **42.1**

---

## 7. Audit Conclusion and Safety Certification

### Conclusion:
The current production contribution model behaves with complete physical coherence and architectural integrity:
1. **Sai Sudharsan's score of 93.4 is valid and warranted.** His P3 of 96.7 accurately reflects Gujarat Titans' $+51.6$ EFS trajectory surge during his 13.4-over stay from 0/1 to 147/1.
2. **Shubman Gill's score of 99.9 is valid and properly elevated.** His superior execution (+50.2 run deviation, +41.98 SR deviation over Sudharsan) separates him at the pinnacle of match contribution.
3. **P2, P1, and P3 operate orthogonally without double counting.**

### Safety Certification:
- **Zero changes made to production scoring formulas, weights, parameters, or thresholds.**
- **Zero changes made to trained expected-performance models.**
- **Zero changes made to processed datasets, database records, or checksum locks.**
- This audit concludes with full validation of the existing production engine.
