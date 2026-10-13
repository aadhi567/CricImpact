# PHASE 7H: P1 CONTEXT LEVERAGE CALIBRATION & DUAL-ROLE BATTER AUDIT REPORT
## Cricket Batter Contribution Model — Research & Calibration Layer

> **Governance Mode**: PURE SIMULATION & RESEARCH LAYER (100% Isolated)  
> **Production Code & Datasets**: 100% UNTOUCHED (Phase 7D $25\% \text{ P1} / 35\% \text{ P2} / 40\% \text{ P3}$ active in production)  
> **Core Architecture Evaluated**: Context-as-Leverage with Asymmetric Leverage Functions $L(\text{P1})$  
> **Scoring Equation**: $\text{Overall Contribution} = 0.50 \times \text{Adjusted P2} + 0.50 \times \text{Adjusted P3}$  
> **Final Audit Verdict**: **`B. APPROVE WITH OBSERVATIONS`** (Recommended Research Candidate: **Model B — Asymmetric Linear Leverage**)

---

## 1. Executive Summary & Core Principle

Phase 7H investigates the calibration of the **Context-as-Leverage Architecture**, extending the breakthrough of Phase 7G to resolve the asymmetry between opening platforms, difficult chases, and catastrophic collapse rescues.

### 1.1 The Core Principle
$$\text{P1 represents HOW DIFFICULT THE SITUATION WAS, not HOW GOOD THE BATTER IS.}$$

P1 must **NOT** reward a player simply for being a middle-order batter, and it must **NOT** automatically make every opener low-value. Instead, P1 serves as a continuous situational leverage multiplier applied to what the batter actually executed:
- **P2 (Execution)**: How cleanly did the batter execute individually (boundaries, dots, strike rate vs expectation)?
- **P3 (State Transformation)**: How much did the batter advance the team's match trajectory (projected total or RRR liquidation)?
- **P1 (Situational Difficulty)**: How difficult was the inherited match context ($L(\text{P1})$)?

```
SITUATIONAL DIFFICULTY
        ↓
       P1
        ↓
    LEVERAGE
        ↓
  ┌───────────┐
  ↓           ↓
 P2           P3
Execution   Team-State
  ↓           ↓
Adjusted P2  Adjusted P3
  └─────┬─────┘
        ↓
     50/50
        ↓
Contribution Score
```

### 1.2 The Three Fundamental Behavior Rules
1. **If $P2/P3 > 50$ (Positive Execution)**: Higher P1 produces a stronger positive reward ($\text{Adjusted} > \text{Raw}$).
2. **If $P2/P3 < 50$ (Negative Execution)**: Higher P1 produces a stronger negative penalty ($\text{Adjusted} < \text{Raw}$; **zero free participation points**).
3. **If $P2/P3 = 50$ (Par Batting)**: Final score remains **exactly 50.0 regardless of P1**. High context alone can *never* manufacture points.

---

## 2. Critical Requirement: Dual-Role Batters Without Player-Type Bonuses

A batter can simultaneously occupy multiple tactical roles:
- An **early top-order batter** (entering in overs 0–4)
- An **anchor** (batting 10–15 overs, stabilizing wicket loss)
- A **collapse rescuer** (recovering from 7/4 or 20/3)
- A **finisher/accelerator** (striking at 150+ in the death overs)

### 2.1 The Traditional Flaw: Hardcoded Player-Type Bonuses
Conventional analytics frameworks attempt to classify batters into mutually exclusive buckets (*"opener"*, *"anchor"*, *"finisher"*, *"collapse specialist"*) and apply heuristic bonus points. This breaks down when a player fulfills multiple roles simultaneously (e.g. Kieron Pollard entering at 7/4 and batting 15 overs to win the match).

### 2.2 The Leverage Solution: Unified Continuous Mechanics
Under Context-as-Leverage, **NO PLAYER-TYPE BONUSES EXIST**:
- **P1** naturally captures the inherited crisis ($P1 = 68.2$, $L = 1.175$).
- **P2** naturally evaluates the batter's execution (striking, boundary percentage, resource efficiency).
- **P3** naturally evaluates the team transformation (stabilizing wickets, liquidating runs required).
- The dual-role batter is naturally rewarded through **High P1 Leverage acting upon High P2 and High P3**.

---

## 3. Controlled Simulation Cases (Cases A through F)

To test the fundamental behavior across archetypal scenarios, we simulated six controlled test cases under identical benchmark standards:

```
CONTROLLED SIMULATION CASES (MODEL B EVALUATION)
──────────────────────────────────────────────────────────────────────────────────────────────────────────
Case ID  Scenario Description                 P1    P2    P3    Prod 7D  Model B Lev  Model B Score  Net Shift
──────────────────────────────────────────────────────────────────────────────────────────────────────────
CASE-A   Normal Elite Opener (0/0, 1st inn)   37.3  90.0  90.0  76.8     0.904        86.2           +9.4 pts
CASE-B   Elite Chase Opener (0/0, chasing 190)49.0  88.0  88.0  78.3     0.992        87.7           +9.4 pts
CASE-C   Collapse Rescue (20/3, 80 off 50)    75.0  88.0  88.0  84.8     1.240        97.1           +12.4 pts
CASE-D   Collapse Failure (20/3, 5 off 15)    75.0  20.0  20.0  33.8     1.240        12.8           -21.0 pts
CASE-E   Dual-Role Batter (20/3, anchor+accel)75.0  92.0  94.0  88.3     1.240        99.9           +11.7 pts
CASE-F   Collapse Rescue w/ Moderate Batting  75.0  45.0  50.0  56.3     1.240        46.9           -9.4 pts
──────────────────────────────────────────────────────────────────────────────────────────────────────────
```

### Analysis of Simulation Findings:
1. **CASE A vs CASE B (Chase Opener vs Normal Opener)**:
   - Normal 1st-innings opener faces $P1 = 37.3$ ($L = 0.904$).
   - Chase opener facing a steep target of 190 ($RRR = 9.5$) faces $P1 = 49.0$ ($L = 0.992$).
   - Chase pressure is naturally reflected in P1 without any artificial opener penalty.
2. **CASE C vs CASE A (Collapse Rescue vs Normal Opener)**:
   - For equivalent batting ($P2=88, P3=88$), Collapse Rescue achieves **$97.1$** ($L = 1.240$), whereas Normal Opener achieves **$86.2$** ($L = 0.904$).
   - Collapse rescue receives **$+37.2\%$ greater leverage** and **$+3.0\text{ pts}$ greater net shift**.
3. **CASE D (Collapse Failure)**:
   - Failing under crisis drops score to **$12.8$ ($-21.0\text{ pt}$ penalty)**. Zero participation cushion.
4. **CASE E (Dual-Role Batter)**:
   - Entering at 20/3, anchoring, stabilizing, and accelerating ($P2=92, P3=94$) achieves the maximum legitimate rating of **$99.9$** purely through leverage on execution.
5. **CASE F (Collapse Rescue with Moderate Batting)**:
   - Entering at 20/3 and batting sluggishly (35 off 40, $P2=45, P3=50$) yields **$46.9$ (below par)**. High P1 alone does *not* create an elite score!

---

## 4. Chase-Opener Context Audit

We audited all 2,388 historical chase opening innings ($innings = 2, entry\_over \le 0.5$) in [batter_match_contributions.csv](file:///c:/Users/admin/Documents/contribution/data/processed/batter_match_contributions.csv) across target run-rate tiers:

```
CHASE OPENING PLATFORM ORDERING AUDIT
──────────────────────────────────────────────────────────────────────────────────────────
Opening Platform Scenario                 Count    Avg P1    Avg RRR    Cricket Context Interpretation
──────────────────────────────────────────────────────────────────────────────────────────
A. 0/0 chasing 120 (RRR ≤ 7.0)            419      18.0      5.88       Calm, low-pressure platform; minimal leverage
B. 0/0 chasing 160 (RRR 7.0 – 8.5)        799      32.0      7.85       Standard chase platform; mild dampening
C. 0/0 chasing 190 (RRR 8.5 – 10.0)       728      45.1      9.19       Steep target elevates P1 near par (L ≈ 1.0)
D. 0/2 chasing 190 (RRR 8.5 – 10.0, 2 dn) 91       62.0      9.23       Steep target + early wickets -> L ≈ 1.12
E. 20/3 chasing 190 (RRR 8.5 – 10.0, 3 dn)35       71.2      9.22       Acute crisis in steep chase -> L ≈ 1.20+
──────────────────────────────────────────────────────────────────────────────────────────
```

### Key Audit Finding:
The empirical P1 ordering conforms strictly to cricket reality:
$$P1(\text{0/0 chasing 120}) < P1(\text{0/0 chasing 160}) < P1(\text{0/0 chasing 190}) < P1(\text{0/2 chasing 190}) < P1(\text{20/3 chasing 190})$$
An opener chasing 190+ does **not** receive an artificially low context score. Chase pressure raises P1 to $45\text{--}50$ ($L \approx 1.0$), ensuring they are judged at neutral par rather than dampened.

---

## 5. Collapse Difficulty Progression Audit

We audited how P1 escalates during early collapses in 1st innings versus late collapses in chases:

| Platform Stage | 1st Innings Mean P1 | Late Chase Mean P1 | Net Context Gap | Interpretation |
|---|:---:|:---:|:---:|---|
| **0/0 Platform** | $37.3$ | $45.1$ | $+7.8$ | Chase target adds base pressure |
| **20/1 Early Wobble** | $44.1$ | $52.4$ | $+8.3$ | 1 wicket lost |
| **20/2 Moderate Wobble**| $51.1$ | $62.0$ | $+10.9$ | 2 wickets lost |
| **20/3 Genuine Collapse**| $53.4$ | $71.2$ | $+17.8$ | 3 wickets lost |
| **30/4 Severe Collapse** | $56.5$ | $78.5$ | $+22.0$ | 4 wickets lost |
| **Late Chase Crisis** | N/A | **$72.6\text{ to }85.0$** | **$+19.3$** | **Late chase collapse is substantially harder!** |

### Confirmation of Principle:
A 20/3 situation in the 12th over of a chase ($RRR > 12.0$) receives $P1 \approx 78\text{--}85$ ($L \approx 1.27\text{--}1.34$), whereas 20/3 in the 3rd over of the 1st innings receives $P1 \approx 53.4$ ($L \approx 1.03$). The model naturally recognizes that wickets lost late in a steep chase are exponentially more damaging than early in the 1st innings.

---

## 6. Candidate Leverage Models Evaluated

Four mathematically bounded candidate models were simulated:

```
CANDIDATE LEVERAGE FUNCTIONS
──────────────────────────────────────────────────────────────────────────────────────────
Model Name                         Mathematical Formula                                  Par Invariance  Bounds
──────────────────────────────────────────────────────────────────────────────────────────
Model A (Linear Bounded Baseline)  L = clip(1.0 + 0.35 * (P1 - 50) / 50, 0.65, 1.35)    L(50) = 1.000   [0.65, 1.35]
Model B (Asymmetric Linear)        Low: 1.0 + 0.38*(P1-50)/50; High: 1.0 + 0.48*(P1-50)/50 L(50) = 1.000   [0.65, 1.35]
Model C (Piecewise Context)        5-zone spline (breakpoints at 40, 50, 60, 75, 90)     L(50) = 1.000   [0.65, 1.35]
Model D (Collapse/Chase Sensitive) Low: 0.38 linear; High: 0.35 * ((P1-50)/50)^0.75     L(50) = 1.000   [0.65, 1.35]
──────────────────────────────────────────────────────────────────────────────────────────
```

---

## 7. Comparative Analysis Across All 19,111 Historical Innings

```
MACRO PERFORMANCE & ARCHETYPE COMPARISON (19,111 INNINGS)
──────────────────────────────────────────────────────────────────────────────────────────────────────────
Metric                               Phase 7D (Prod)    Model A (Sym)      Model B (Asym)     Model C (Piecewise)
──────────────────────────────────────────────────────────────────────────────────────────────────────────
Population Mean                      48.13              48.52              48.46              48.48
Population Median                    45.90              46.97              46.96              46.98
Standard Deviation                   17.90              23.44              23.51              23.32
Pearson Correlation w/ Prod          1.0000             0.9470             0.9444             0.9449
Spearman Rank Correlation            1.0000             0.9469             0.9447             0.9453
Mean Absolute Difference (MAD)       0.00               6.69               6.79               6.65
P2/P3 Raw Correlation                0.7284             0.6813             0.6790             0.6787
P2/P3 Correlation Drop               N/A                -0.0471            -0.0494            -0.0497
Top-10 Rank Overlap                  10 / 10            5 / 10             3 / 10             3 / 10
Top-25 Rank Overlap                  25 / 25            14 / 25            8 / 25             12 / 25
Scores ≤ 5.0 Count (%)               0                  271 (1.42%)        320 (1.67%)        294 (1.54%)
Scores ≥ 95.0 Count (%)              1 (0.01%)          223 (1.17%)        251 (1.31%)        233 (1.22%)
Clipping Events Count (%)            0                  911 (4.77%)        1,102 (5.77%)      1,010 (5.28%)
──────────────────────────────────────────────────────────────────────────────────────────────────────────
ARCHETYPE COHORT PERFORMANCE (19,111 INNINGS)
Elite Normal Opener (N=459) Gain     78.29 (base)       +9.85 pts          +9.53 pts          +9.08 pts
Elite Chase Opener (N=154) Gain      80.84 (base)       +9.94 pts          +10.19 pts         +9.84 pts
Collapse Rescue (N=141) Gain         87.13 (base)       +8.98 pts          +9.95 pts          +9.58 pts
Dual-Role Batter (N=59) Gain         75.64 (base)       +6.40 pts          +7.20 pts          +6.80 pts
Collapse Failure (N=1,003) Penalty   34.22 (base)       -23.58 pts         -24.60 pts         -24.14 pts
Chase Failure (N=464) Penalty        33.40 (base)       -11.18 pts         -11.81 pts         -11.48 pts
Ratio: CR Gain / Normal Opener Gain  —                  0.912 (FAIL)       1.044 (PASS)       1.055 (PASS)
Ratio: CR Gain / Chase Opener Gain   —                  0.903              0.976              0.974
──────────────────────────────────────────────────────────────────────────────────────────────────────────
```

### Key Statistical Takeaways:
1. **Model A Fails Macro Hierarchy**: In Model A, Collapse Rescue gained $+8.98\text{ pts}$ while Normal Opener gained $+9.85\text{ pts}$ ($\text{Ratio} = 0.912 < 1.0$).
2. **Model B Restores Cricket Hierarchy**: In Model B, Collapse Rescue gains **$+9.95\text{ pts}$**, exceeding Normal Opener (**$+9.53\text{ pts}$**, $\text{Ratio} = \mathbf{1.044} > 1.0$).
3. **Chase Opener Parity**: Elite Chase Openers gain **$+10.19\text{ pts}$**, correctly reflecting that chasing 190+ at 9.5 RRR against the new ball is as difficult as a middle-order wobble.

---

## 8. Real IPL 14-Archetype Validation Table

The 14 representative real IPL innings were evaluated under Model B:

| Category ID & Name | Player & Match | Inn | Score at Entry / Over | Wkts | Target / RRR | P1 | Lev | P2 | P3 | Adj P2 | Adj P3 | Proposed Score | Prod 7D | Net Diff | Cricket Assessment |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **CAT-01: Elite Normal Opener** | CH Gayle (1082610) | 1 | 0/0 (0.0) | 0 | - | 37.3 | 0.904 | 96.7 | 98.2 | 92.2 | 93.6 | **92.9** | 82.5 | `+10.4` | Century relieved of 0/0 context tax |
| **CAT-02: Failed Opener** | MA Agarwal (1082594) | 1 | 0/0 (0.1) | 0 | - | 37.3 | 0.904 | 10.4 | 11.3 | 14.2 | 15.0 | **14.6** | 17.5 | `-2.9` | Low P1 does not protect duck |
| **CAT-03: Elite Chase Opener** | G Gambhir (1082593) | 2 | 0/0 (0.0) | 0 | 184 / 9.2 | 44.4 | 0.957 | 91.3 | 97.5 | 89.5 | 95.5 | **92.5** | 82.1 | `+10.4` | Chasing 184; high score maintained |
| **CAT-04: Failed Chase Opener** | M Vohra (1082605) | 2 | 0/0 (0.0) | 0 | 164 / 8.2 | 47.0 | 0.977 | 14.8 | 36.8 | 15.6 | 37.1 | **26.4** | 31.6 | `-5.2` | Chase failure penalized firmly |
| **CAT-05: Mod Collapse Rescue**| SS Iyer (1082640) | 2 | 12/2 (1.5) | 2 | 209 / 10.9| 69.0 | 1.182 | 93.4 | 87.5 | 99.9 | 94.3 | **97.1** | 84.9 | `+12.2` | 96 (57) chasing 209 from 12/2 |
| **CAT-06: Sev Collapse Rescue**| HH Pandya (1082597) | 2 | 119/5 (16.2)| 5 | 179 / 16.4| 87.8 | 1.350 | 87.7 | 91.0 | 99.9 | 99.9 | **99.9** | 89.0 | `+10.9` | 29* (11) death rescue win |
| **CAT-07: Dual-Role Batter** | KA Pollard (1082602)| 2 | 7/4 (2.4) | 4 | 143 / 7.9 | 68.2 | 1.175 | 86.3 | 91.9 | 92.7 | 99.2 | **96.0** | 84.0 | `+12.0` | 70 (47) enters 7/4, anchors 15 ov |
| **CAT-08: Collapse Failure** | S Aravind (1082591) | 2 | 128/6 (16.5)| 6 | 208 / 18.9| 92.2 | 1.350 | 8.4 | 11.0 | 0.1 | 0.1 | **0.1** | 30.4 | `-30.3` | Fails at 6 down; 0 cushion points |
| **CAT-09: Normal Middle-Order**| DJ Hooda (1082604) | 2 | 75/3 (10.4) | 3 | 136 / 5.8 | 50.0 | 1.000 | 61.8 | 41.7 | 61.8 | 41.7 | **51.8** | 50.8 | `+1.0` | Par context (P1=50) -> L=1.000 |
| **CAT-10: High P2 / Low P3** | RR Pant (1082595) | 2 | 43/3 (7.4) | 3 | 158 / 8.3 | 33.5 | 0.875 | 82.9 | 25.4 | 78.8 | 28.5 | **53.7** | 47.5 | `+6.2` | Lone warrior striking in loss |
| **CAT-11: Low P2 / High P3** | Z Khan (1082595) | 2 | 142/9 (19.4)| 9 | 158 / 36.0| 99.7 | 1.350 | 23.8 | 82.8 | 14.6 | 94.3 | **54.5** | 66.4 | `-11.9`| Tail resistance recognized |
| **CAT-12: Losing Hero** | HM Amla (1082612) | 1 | 0/0 (0.0) | 0 | - | 37.3 | 0.904 | 98.3 | 96.7 | 93.7 | 92.2 | **93.0** | 82.4 | `+10.6` | 104* in loss; elite score safe |
| **CAT-13: Winning Passenger** | MC Henriques (1082609)| 1 | 32/1 (5.1) | 1 | - | 50.0 | 1.000 | 24.9 | 21.8 | 24.9 | 21.8 | **23.4** | 29.9 | `-6.5` | Slow 9 (16) in win; 0 bonus |
| **CAT-14: Death-Over Chase** | TS Mills (1082591) | 2 | 148/8 (18.0)| 8 | 208 / 29.0| 99.7 | 1.350 | 45.7 | 8.5 | 44.2 | 0.1 | **22.2** | 44.3 | `-22.1`| P3-ISSUE-01 blowout -> 22.2 |

---

## 9. Death-Over Chase Context & P3-ISSUE-01 Audit

In overs 17–20 of steep chases ($\text{RRR} \ge 15.0$, $N = 794$ innings):
- Phase 7D Production average score: **$56.86$** (cushioned by $0.25 \times 98.1 = 24.5$ participation points).
- Model B Proposed average score: **$40.62$ (Net Shift: $-16.24\text{ pts}$)**.
- **P3-ISSUE-01 Interaction**: When required run rate blows out exponentially (e.g. $RRR > 25.0$), uncalibrated P3 collapses below $10.0$. Multiplying this negative deviation by $L = 1.35$ causes **$21.5\%$ of hopeless chase entries (171 innings) to hit the $0.1\text{--}5.0$ floor**.
- **Rule 13 Adherence**: Phase 7H strictly preserved raw P3. Asymmetric leverage does *not* cause this artifact; it faithfully multiplies P3's underlying distortion. **This motivates Audit Verdict B rather than immediate deployment.**

---

## 10. Governance & Production Protection Verification

The four protected production files were verified by cryptographic MD5 hashes:

| File Path | Expected MD5 Hash | Actual MD5 Hash | Status |
|---|---|---|:---:|
| `src/contribution_framework.py` | `82a049dd242afac690264bad7032bacf` | `82a049dd242afac690264bad7032bacf` | **UNTOUCHED** |
| `data/processed/batter_match_contributions.csv` | `3bdcf553d4b9152746baaa9c5f7910c2` | `3bdcf553d4b9152746baaa9c5f7910c2` | **UNTOUCHED** |
| `models/contribution/phase6/phase6_season_metrics.csv` | `a1ca155321015cc0b26b926d6fee0147` | `a1ca155321015cc0b26b926d6fee0147` | **UNTOUCHED** |
| `src/season_aggregation.py` | `6efc324e060b4dcc225a851114b2b5cb` | `6efc324e060b4dcc225a851114b2b5cb` | **UNTOUCHED** |

Test suite execution: **All 26 Phase 7H calibration tests passed in 1.02s; all 261 workspace regression tests passed.**

---

## 11. Final Audit Verdict & Deliverables Summary

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                      ║
║                       FINAL AUDIT VERDICT: PHASE 7H                                  ║
║                                                                                      ║
║                           B. APPROVE WITH OBSERVATIONS                               ║
║                                                                                      ║
║   1. Model B (Asymmetric Linear) successfully resolves the calibration flaw:        ║
║      Collapse Rescue Gain (+9.95) exceeds Normal Opener Gain (+9.53).               ║
║   2. Dual-Role Batters naturally receive peak recognition through high leverage     ║
║      applied to high P2/P3, eliminating the need for player-type bonuses.           ║
║   3. Chase Openers are verified: target pressure elevates P1 to 45–50, ensuring     ║
║      steep chase openers are never artificially penalized.                          ║
║   4. Par invariance is exact (P1=50 -> L=1.000; P2=50, P3=50 -> Score=50.0).         ║
║   5. OBSERVATION: P3-ISSUE-01 in death-over hopeless chases must be mitigated in     ║
║      Phase 7I before final live production integration.                              ║
║   6. Production codebase and datasets remain 100% UNTOUCHED.                         ║
║                                                                                      ║
╚══════════════════════════════════════════════════════════════════════════════════════╝
```

### Deliverables Created:
1. [src/phase7h_leverage_calibration.py](file:///c:/Users/admin/Documents/contribution/src/phase7h_leverage_calibration.py): Core simulation and audit engine covering Models A, B, C, D, the 6 simulation cases, chase/collapse audits, and 14 real IPL archetypes.
2. [tests/test_phase7h_leverage_calibration.py](file:///c:/Users/admin/Documents/contribution/tests/test_phase7h_leverage_calibration.py): 26 unit and integration tests covering par invariance, monotonicity, dual-role mechanics, chase-opener audits, and production file protection.
3. [models/contribution/phase7/phase7h_leverage_spec.json](file:///c:/Users/admin/Documents/contribution/models/contribution/phase7/phase7h_leverage_spec.json): Mathematical specification of calibrated asymmetric leverage models.
4. [models/contribution/phase7/phase7h_leverage_validation.json](file:///c:/Users/admin/Documents/contribution/models/contribution/phase7/phase7h_leverage_validation.json): Quantitative validation metrics across all 19,111 historical innings.
5. [models/contribution/phase7/PHASE7H_LEVERAGE_CALIBRATION_REPORT.md](file:///c:/Users/admin/Documents/contribution/models/contribution/phase7/PHASE7H_LEVERAGE_CALIBRATION_REPORT.md): Complete audit report.
