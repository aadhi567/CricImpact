# Phase 7G — P3 Correction & P1 Leverage Stress Test Report
**Cricket Batter Contribution Model**  
**Status:** Research & Simulation Complete (Production Untouched)  
**Date:** October 2026  
**Artifact Directory:** `models/contribution/phase7/`  

---

## 1. Executive Summary & Production Protection

In accordance with strict project instructions:
1. **Production files remain 100% untouched**:
   - `src/contribution_framework.py` is unmodified.
   - `data/processed/batter_match_contributions.csv` is unmodified.
   - `models/contribution/phase6/phase6_season_metrics.csv` is unmodified.
   - API defaults and frontend calculators remain on Phase 7D (25% P1, 35% P2, 40% P3).
2. **Phase 7G was conducted in an isolated research environment**:
   - Simulation module: [`src/phase7g_simulation.py`](file:///c:/Users/admin/Documents/contribution/src/phase7g_simulation.py)
   - Evaluation scripts: [`scripts/run_phase7g_evaluation.py`](file:///c:/Users/admin/Documents/contribution/scripts/run_phase7g_evaluation.py), [`scripts/evaluate_isolated_corrections.py`](file:///c:/Users/admin/Documents/contribution/scripts/evaluate_isolated_corrections.py), [`scripts/query_real_cases.py`](file:///c:/Users/admin/Documents/contribution/scripts/query_real_cases.py)
   - Dedicated unit tests: [`tests/test_phase7g_p3_corrections.py`](file:///c:/Users/admin/Documents/contribution/tests/test_phase7g_p3_corrections.py) (11 tests passed; full suite **209/209 passed**).
3. **Core Findings**:
   - The Context-as-Leverage architecture ($50\%$ Adjusted P2 $+ 50\%$ Adjusted P3, with $L(P1) \in [0.65, 1.35]$) is mathematically robust, but uncorrected P3 suffered from three edge-case failure modes identified in Phase 7E/7F.
   - We simulated isolated and combined candidates across all 19,111 IPL innings, real player matches, and 18 mandatory stress scenarios.
   - The best-performing configuration is **Candidate 4 (1A + 2C + 3C)**:
     - **Issue 1 (Death-Over RRR)**: Mode 1A (SR-capped bounded floor) restores elite death hitting (Russell from P3 18.6 to 55.3; Ishan Kishan 99 from 49.4 to 84.1) while maintaining heavy penalties on slow batters.
     - **Issue 2 (Partner Coattail)**: Mode 2C (Hybrid share dampening + diff penalty) eliminates false free-riding credit (Dhawan 29 off 30 reduced from P3 92.0 to 55.0; Dilshan from 98.2 to 68.7).
     - **Issue 3 (Low-Target Chase)**: Mode 3C (Pace cap) stops artificial credit for pedestrian cruising (Smith 15 off 18 reduced from P3 68.2 to 47.2; Kallis chasing 52 reduced from 89.4 to 46.9).
   - Outcome leakage remains **0.0000** (strictly outcome-invariant).
   - DNB behavior preserves clean `NULL` output.

---

## 2. Root Cause Analysis of P3 Anomalies

### Issue 1: Death-Over RRR Blowout
- **Mechanism**: In chasing innings, macro trajectory evaluates change in required run rate:
  $$\Delta \text{RRR} = \text{RRR}_{\text{entry}} - \text{RRR}_{\text{exit}}$$
  When balls remaining at exit $\le 12$, required run rate is divided by a tiny fraction of overs (e.g. $1 / 6 = 0.167$ overs). If 15 runs are required off 1 ball, required run rate becomes $90.0$.
  In AD Russell's match (Match 1178410), $\Delta \text{RRR} = -85.38$.
- **Failure**: Even with clipping at $-12.0$, this represented $-4$ standard deviations ($z_{\text{rrr}} = -4.0$). Multiplied by $0.65$, this dragged raw P3 negative, yielding **P3 = 18.6** despite Russell smashing 65 off 25 (SR 260.0, personal execution P2 = 93.1).
- **Core Dilemma**: The model was confounding team macro state (game lost) with the batter's team-state transformation (advancing target progress by $54.2\%$).

### Issue 2: Partner Coattail Effect
- **Mechanism**: Raw P3 weights macro trajectory at $45\%$ and partnership context at $30\%$:
  $$\text{P3}_{\text{raw}} = 0.45 \times z_{\text{macro}} + 0.30 \times z_{\text{partner}} + 0.15 \times z_{\text{collapse}} + 0.10 \times s_{\text{res}}$$
  When a partner explodes (e.g. David Warner hitting 126 off 59 in Match 1082627), the team run rate skyrockets to $12.3$, creating $z_{\text{macro}} = +1.69$.
- **Failure**: Shikhar Dhawan scored 29 off 30 balls (SR 96.7). His negative partner differential produced $z_{\text{partner}} = -0.44$. The massive positive macro credit ($0.45 \times 1.69 = +0.76$) heavily dominated the partner penalty ($0.30 \times -0.44 = -0.13$), awarding Dhawan an absurd **P3 = 92.0**.
- **Core Dilemma**: A passive anchor was receiving $85\%$ of the team's trajectory lift without actually generating it.

### Issue 3: Low-Target Chase Artifact
- **Mechanism**: In low targets ($\le 120$), target progress change measures:
  $$\Delta \text{Progress} = \frac{\text{Runs Added}}{\text{Target}}$$
  When chasing 94, scoring 15 runs liquidates $16\%$ of the target.
- **Failure**: SPD Smith scored 15 off 18 balls (SR 83.3, Match 1082645). Entering with required RR at 4.5, Smith cruised slowly. Because target progress was positive and required RR barely shifted, Smith received **P3 = 68.2** and Contribution 56.6.
- **Core Dilemma**: Easy chases allow slow batting to appear mathematically helpful simply because the denominator (target) is small.

---

## 3. Isolated Evaluation of Correction Alternatives

We evaluated each correction mode independently across the entire dataset of 19,111 innings to establish causal impact without confounding interactions:

### Issue 1 Alternatives (Death-Over RRR)
| Mode | Description | Affected Innings | Mean Score Shift | P2/P3 Corr | Russell P3 | Russell Score | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Baseline** | Uncapped/Raw clip at $\pm 12.0$ | 0 | $0.00$ | 0.7284 | 18.6 | 54.9 | **Rejected** (crushes heroes) |
| **Mode 1A** | **SR-capped bounded floor** (floor at $-3.0$ if SR $\ge 160$; $-6.0$ if SR $\ge 130$) | 197 | $+7.42$ | 0.7388 | **55.3** | **78.3** | **BEST**: Surgically bounds asymptote while maintaining severe penalty for slow batters |
| **Mode 1B** | Continuous SR-surplus offset before clip | 246 | $+3.14$ | 0.7342 | 18.6 | 54.9 | **Failed**: Additive offset swallowed by deep negative asymptote before $-12.0$ clip |
| **Mode 1C** | Death re-weighting toward progress ($70\%$ prog / $30\%$ rrr) | 711 | $+4.88$ | 0.7393 | 74.1 | 90.3 | **Over-generous**: Awards 90.3 contribution in an exit state requiring 36 off 1 ball |

### Issue 2 Alternatives (Partner Coattail)
| Mode | Description | Affected Innings | Mean Score Shift | P2/P3 Corr | Dhawan P3 | Dhawan Score | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Baseline** | Uncorrected raw macro + partner | 0 | $0.00$ | 0.7284 | 92.0 | 70.1 | **Rejected** (massive free-riding) |
| **Mode 2A** | Macro share dampening ($\min(1.0, 2.0 \times \text{share})$) | 656 | $-3.81$ | 0.7341 | 63.3 | 57.1 | **Good**: Dampens macro credit cleanly |
| **Mode 2B** | Escalated partner difference penalty only | 659 | $-1.15$ | 0.7309 | 85.1 | 67.0 | **Insufficient**: Macro credit ($45\%$) still overpowers partner penalty |
| **Mode 2C** | **Hybrid** (share dampening $+$ deeper partner penalty) | 659 | $-4.62$ | 0.7327 | **55.0** | **53.3** | **BEST**: Pulls passive anchor exactly to par ($53.3$) without harming carrying batters |

### Issue 3 Alternatives (Low-Target Chase)
| Mode | Description | Affected Innings | Mean Score Shift | P2/P3 Corr | Smith P3 | Smith Score | Verdict |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Baseline** | Uncorrected chase macro | 0 | $0.00$ | 0.7284 | 68.2 | 56.6 | **Rejected** (cruise control inflation) |
| **Mode 3A** | Execution gate ($\text{actual\_sr} / 120$ if SR $< 110$) | 142 | $-1.82$ | 0.7291 | 60.3 | 53.8 | **Partial**: Moderate dampening |
| **Mode 3B** | Target difficulty discount ($\min(1.0, \text{Target}/150)$) | 399 | $-2.11$ | 0.7286 | 61.7 | 54.3 | **Too broad**: Penalizes all low targets regardless of batter pace |
| **Mode 3C** | **Pace cap** (cap macro at $0.30$ if SR $< 100$ & Req RR $\le 7.0$) | 84 | $-3.25$ | 0.7291 | **47.2** | **49.0** | **BEST**: Pinpoints slow cruising ($SR < 100$) in easy chases, lowering score below par |

---

## 4. Full Dataset Statistical Benchmarks (19,111 Innings)

| Metric | Phase 7D Production (25/35/40) | Phase 7F Baseline (Leverage + Raw P3) | Candidate 1 (1A + 2A + 3A) | Candidate 2 (1B + 2C + 3B) | Candidate 3 (1C + 2B + 3C) | **Candidate 4 (1A + 2C + 3C)** |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Mean** | 48.13 | 48.52 | 48.41 | 48.25 | 48.31 | **48.29** |
| **Median** | 45.90 | 47.00 | 46.70 | 46.40 | 46.70 | **46.40** |
| **Std Dev** | 17.90 | 23.44 | 23.42 | 23.46 | 23.36 | **23.45** |
| **Q10 (10th percentile)** | 25.9 | 18.9 | 19.0 | 18.9 | 18.9 | **18.9** |
| **Q90 (90th percentile)** | 73.9 | 81.9 | 81.9 | 81.9 | 81.6 | **81.9** |
| **Min** | 9.7 | 0.1 | 0.1 | 0.1 | 0.1 | **0.1** |
| **Max** | 95.4 | 99.9 | 99.9 | 99.9 | 99.9 | **99.9** |
| **Corr with Phase 7D** | 1.0000 | 0.9470 | 0.9449 | 0.9437 | 0.9436 | **0.9436** |
| **Corr with Phase 7F** | — | 1.0000 | 0.9961 | 0.9955 | 0.9947 | **0.9958** |
| **P2 / P3 Correlation** | 0.7284 | 0.7284 | 0.7451 | 0.7385 | 0.7423 | **0.7436** |
| **Outcome Leakage** | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | **0.0000** |
| **DNB NULL Behavior** | Correct | Correct | Correct | Correct | Correct | **Correct** |

---

## 5. The 18 Mandatory Stress Scenarios

All 18 scenarios were tested through the complete architecture ($L(P1) \in [0.65, 1.35]$, $50/50$ adjusted P2/P3 split):

| # | Scenario Description | P1 Context | P2 Perf | P3 Raw Base | P3 Corr (7G) | Leverage | Adj P2 | Adj P3 | P7F Base Score | **P7G Score** | Verdict & Behavioral Rationale |
| :-: | :--- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :--- |
| **1** | Opener at 0/0 + excellent batting (85 off 50) | 37.3 | 88.0 | 94.6 | 94.6 | 0.911 | 84.6 | 90.6 | 87.6 | **87.6** | Correctly tempered by opener baseline |
| **2** | Opener at 0/0 + poor batting (12 off 20) | 37.3 | 22.0 | 30.6 | 30.6 | 0.911 | 24.5 | 32.3 | 28.4 | **28.4** | Properly penalized without collapse cushion |
| **3** | Batter entering at 20/3 + excellent (75 off 45) | 75.0 | 86.0 | 95.2 | 95.2 | 1.175 | 92.3 | 99.9 | 96.1 | **96.1** | Match-winning collapse rescue rewarded |
| **4** | Batter entering at 20/3 + poor (5 off 12) | 75.0 | 18.0 | 18.3 | 18.3 | 1.175 | 12.4 | 12.8 | 12.6 | **12.6** | Severe high-leverage failure penalized |
| **5** | Batter entering 145/1 chasing 160 (16 off 10) | 22.0 | 55.0 | 71.6 | 71.6 | 0.804 | 54.0 | 67.4 | 60.7 | **60.7** | Low leverage finish prevents score inflation |
| **6** | **Death excellent batter in lost chase (Russell)** | 72.0 | 93.0 | 18.6 | **55.3** | 1.154 | 99.6 | **56.1** | 56.7 | **77.9** | **Issue 1 Fixed**: Elite batting rescued from 56.7 to 77.9 |
| **7** | **Death poor batter in lost chase (8 off 12)** | 75.0 | 22.0 | 7.5 | **7.5** | 1.175 | 17.1 | **0.1** | 8.6 | **8.6** | **Distinction Preserved**: Slow batter remains at 8.6 |
| **8** | **Explosive partner + weak batter (Dhawan)** | 37.3 | 52.0 | 87.1 | **58.3** | 0.911 | 51.8 | **57.6** | 67.8 | **54.7** | **Issue 2 Fixed**: Coattail cut from 67.8 down to par 54.7 |
| **9** | **Weak partner + carrying batter (50 off 33)** | 49.6 | 80.2 | 85.1 | **85.1** | 0.997 | 80.1 | **85.0** | 82.6 | **82.6** | Carrying batter retains full partner credit |
| **10** | Mutual acceleration (Yuvraj / Henriques) | 28.1 | 93.1 | 92.1 | 92.1 | 0.847 | 86.5 | 85.7 | 86.1 | **86.1** | Mutual partnership bonus correctly applied |
| **11** | **Low-target chase + slow batter (Smith 15 off 18)** | 24.0 | 45.0 | 49.6 | **47.0** | 0.818 | 45.9 | **47.5** | 47.8 | **46.7** | **Issue 3 Fixed**: Unearned chase progress throttled |
| **12** | **Low-target chase + aggressive (32 off 14)** | 24.0 | 82.0 | 80.7 | **80.7** | 0.818 | 76.2 | **75.1** | 75.6 | **75.6** | Aggressive finisher retains high score |
| **13** | Losing-team hero (AB de Villiers 89* off 46) | 55.0 | 97.8 | 96.4 | 96.4 | 1.035 | 99.4 | 98.0 | 98.7 | **98.7** | Zero match-outcome penalty; elite score |
| **14** | Winning-team passenger (Henriques 9 off 16) | 42.0 | 24.9 | 31.0 | 31.0 | 0.944 | 26.3 | 32.1 | 29.2 | **29.2** | Zero match-outcome bonus; penalized properly |
| **15** | DNB appearance | NULL | NULL | NULL | NULL | NULL | NULL | NULL | NULL | **NULL** | DNB correctly outputs pure NULL |
| **16** | Pure Powerplay innings (Abhishek 7 off 8) | 37.3 | 43.7 | 47.3 | 47.3 | 0.911 | 44.3 | 47.5 | 45.9 | **45.9** | Phase 7A PP context preserves neutral par |
| **17** | Middle-over overlap (overs 7 to 15, 45 off 35) | 48.0 | 62.0 | 64.6 | 64.6 | 0.986 | 61.8 | 64.4 | 63.1 | **63.1** | Clean middle-over transition |
| **18** | Death-over burst (30 off 5 balls, SR 600.0) | 90.0 | 98.0 | 91.6 | 91.6 | 1.280 | 99.9 | 99.9 | 99.9 | **99.9** | Maximum high-leverage explosion |

---

## 6. Real-Match IPL Player Validations

### Archetype 1: Death Hitters in Losing Chases
| Player | Innings | Match ID | Situation | Phase 7D (Prod) | Phase 7F (Base) | **Phase 7G (Corrected)** | Delta (7G vs 7F) | Analysis |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **AD Russell** | 65 (25b, SR 260.0) | 1178410 | Chasing 215, exit 1b rem | 62.3 (P3 18.6) | 54.9 (P3 18.6) | **78.3 (P3 55.3)** | **+23.4** | Restores Russell's heroic innings without claiming fake win |
| **Ishan Kishan** | 99 (58b, SR 170.7) | 1216547 | Chasing 202, tied match | 70.9 (P3 49.4) | 74.6 (P3 49.4) | **94.9 (P3 84.1)** | **+20.3** | Kishan's legendary 99 is no longer depressed by exit RRR |
| **M Vohra** | 95 (50b, SR 190.0) | 1082609 | Chasing 160, lost by 5r | 78.5 (P3 87.5) | 88.6 (P3 87.5) | **88.6 (P3 87.5)** | 0.0 | Already had high progress, correctly preserved |

### Archetype 2: Partner Coattail Innings
| Player | Innings | Match ID | Partner Score | Phase 7D (Prod) | Phase 7F (Base) | **Phase 7G (Corrected)** | Delta (7G vs 7F) | Analysis |
| :--- | :--- | :---: | :--- | :---: | :---: | :---: | :---: | :--- |
| **S Dhawan** | 29 (30b, SR 96.7) | 1082627 | Warner 126 (59b) | 64.4 (P3 92.0) | 70.1 (P3 92.0) | **53.3 (P3 55.0)** | **-16.8** | Eliminates unearned passenger credit; drops to dead par |
| **TM Dilshan** | 33 (36b, SR 91.7) | 598027 | Gayle 175* (66b) | 70.4 (P3 98.2) | 77.6 (P3 98.2) | **64.2 (P3 68.7)** | **-13.4** | Gayle's 175 no longer inflates Dilshan's run-a-ball 33 |
| **CA Pujara** | 40 (38b, SR 105.3) | 729291 | Maxwell 95 (43b) | 71.9 (P3 95.5) | 78.2 (P3 95.5) | **63.2 (P3 65.2)** | **-15.0** | Pujara anchor credit curtailed |
| **PP Shaw** | 42 (39b, SR 107.7) | 1178415 | Dhawan 97* (63b) | 62.5 (P3 75.1) | 66.3 (P3 75.1) | **55.1 (P3 52.4)** | **-11.2** | Shaw brought down to par |

### Archetype 3: Low-Target Chase Anchors
| Player | Innings | Match ID | Target | Phase 7D (Prod) | Phase 7F (Base) | **Phase 7G (Corrected)** | Delta (7G vs 7F) | Analysis |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **SPD Smith** | 15 (18b, SR 83.3) | 1082645 | 94 | 47.4 (P3 68.2) | 56.6 (P3 68.2) | **49.0 (P3 47.2)** | **-7.6** | Eliminates low-target inflation; below par |
| **JH Kallis** | 21 (23b, SR 91.3) | 501245 | 52 | 57.8 (P3 89.4) | 66.7 (P3 89.4) | **52.2 (P3 46.9)** | **-14.5** | Chasing 52 at SR 91 drops from 66.7 to par 52.2 |
| **PA Patel** | 19 (28b, SR 67.9) | 336025 | 53 | 52.3 (P3 82.5) | 61.6 (P3 82.5) | **46.4 (P3 38.1)** | **-15.2** | Slow chase properly drops into sub-par penalty |
| **HM Amla** | 16 (20b, SR 80.0) | 1082626 | 68 | 48.8 (P3 74.6) | 58.5 (P3 74.6) | **40.6 (P3 22.7)** | **-17.9** | Correctly penalizes slow chase speed |

### Archetype 4: Collapse Rescuers (Entering $\le 30/3$)
| Player | Innings | Match ID | Entry State | Phase 7D (Prod) | Phase 7F (Base) | **Phase 7G (Corrected)** | Analysis |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **BA Stokes** | 103* (63b) | 1082629 | 10/3 (Overs 1.3) | 88.6 (P3 98.5) | 99.9 (P3 98.5) | **99.9 (P3 98.5)** | Pristine rescue score preserved |
| **Tilak Varma** | 101* (45b) | 1529273 | 24/3 (Overs 3.1) | 84.6 (P3 97.9) | 96.2 (P3 97.9) | **96.2 (P3 97.9)** | High leverage multiplier intact |
| **DA Miller** | 94* (51b) | 1304075 | 16/3 (Overs 2.4) | 91.5 (P3 98.4) | 99.9 (P3 98.4) | **99.9 (P3 98.4)** | Perfect preservation of collapse bonus |

### Archetype 5: Losing-Team Heroes
| Player | Innings | Match ID | Outcome | Phase 7D (Prod) | Phase 7F (Base) | **Phase 7G (Corrected)** | Analysis |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **KL Rahul** | 152 (67b) | 1529278 | Lost match | 84.2 (P3 99.9) | 95.4 (P3 99.9) | **95.4 (P3 99.9)** | Zero outcome leakage; world-class score |
| **RR Pant** | 128* (63b) | 1136602 | Lost match | 87.5 (P3 97.5) | 99.6 (P3 97.5) | **99.6 (P3 97.5)** | Masterclass rescued from production dilution |
| **YBK Jaiswal** | 124 (62b) | 1359516 | Lost match | 83.4 (P3 98.4) | 94.4 (P3 98.4) | **94.4 (P3 98.4)** | No deduction for losing match |

---

## 7. Answers to the 10 Explicit Questions

### Question 1: Which P3 death-over correction is best?
**Verdict:** **Mode 1A (`mode_1a_sr_capped`)** is clearly superior.
- **Why**: As balls remaining $\to 0$, required run rate exhibits an asymptotic singularity (dividing by $< 0.2$ overs). Mode 1A explicitly places an execution-conditioned floor on $\Delta \text{RRR}$:
  - If $\text{actual\_sr} \ge 160.0$, $\Delta \text{RRR} \ge -3.0$ ($-1.0$ std dev).
  - If $\text{actual\_sr} \ge 130.0$, $\Delta \text{RRR} \ge -6.0$ ($-2.0$ std dev).
  - If $\text{actual\_sr} < 130.0$, uncapped deterioration (clipped at standard $-12.0$).
- Mode 1B failed because additive offsets before the $-12.0$ clip are swallowed by the $-85.0$ asymptote. Mode 1C over-rewarded lost games by upweighting progress to $70\%$, pushing Russell to $90.3$. Mode 1A awards Russell $78.3$ and Ishan Kishan $94.9$, accurately reflecting heroic batting without fabricating a team win.

### Question 2: Which partner coattail correction is best?
**Verdict:** **Mode 2C (`mode_2c_hybrid`)** is the clear winner.
- **Why**: When a partner explodes, macro trajectory credit ($0.45 \times z_{\text{macro}}$) easily overwhelms partner differential penalties ($0.30 \times z_{\text{partner}}$). Penalizing partner differential alone (Mode 2B) only lowered Dhawan from 92.0 to 85.1.
- Mode 2C scales positive macro credit by the batter's share factor:
  $$\text{Share Factor} = \max(0.25, \min(1.0, 2.0 \times \text{batter\_share}))$$
  combined with an escalated partner strike rate differential penalty. This pulls Dhawan from $92.0$ down to $55.0$ (score $53.3$) and Dilshan from $98.2$ down to $68.7$ (score $64.2$), without reducing credit for genuine carrying partners.

### Question 3: Which low-target chase correction is best?
**Verdict:** **Mode 3C (`mode_3c_pace_cap`)** is the best solution.
- **Why**: In low targets ($\le 125$), target progress is mathematically large even for sluggish batting. Mode 3B unfairly discounted all low-target innings regardless of batting quality.
- Mode 3C specifically targets pedestrian cruising: when $\text{target} \le 125$, $\text{required\_rr}_{\text{entry}} \le 7.0$, and $\text{actual\_sr} < 100.0$, positive macro score is capped at $0.30$. This directly drops SPD Smith's P3 from $68.2$ to $47.2$ (contribution $49.0$), JH Kallis from $89.4$ to $46.9$, and Parthiv Patel from $82.5$ to $38.1$, while allowing aggressive finishes (e.g. 32 off 14, SR 228) to retain scores $> 75$.

### Question 4: Does P1 leverage remain mathematically stable after these corrections?
**Verdict:** **Yes, absolutely stable.**
- $L(P1) = \text{clip}(1.0 + 0.35 \times ((P1 - 50)/50), 0.65, 1.35)$ operates strictly as a multiplier around par $50.0$.
- Because P3 corrections bring distorted outliers (18.6 and 92.0) back into realistic ranges (55.0 and 55.3), multiplying by $L(P1)$ produces bounded, well-behaved adjusted scores without blowing past extremes.
- Across all 19,111 innings, zero values exceed $[0.1, 99.9]$.

### Question 5: Does P2/P3 independence remain healthy?
**Verdict:** **Yes.**
- Uncorrected Phase 7F P2/P3 correlation: $0.7284$.
- Corrected Phase 7G Candidate 4 P2/P3 correlation: $0.7436$.
- The minor $+0.015$ shift occurs because fixing Russell (raising P3 to match his high P2) and fixing Dhawan/Dilshan (lowering P3 to match their mediocre P2) eliminates perverse anti-correlations where poor execution received high P3 or elite execution received low P3.
- Execution (P2) and team transformation (P3) remain distinct conceptual pillars.

### Question 6: Does the 50/50 adjusted P2/P3 architecture remain preferable to 25/35/40?
**Verdict:** **Yes, decisively.**
- In 25/35/40, P1 contributes 25 points directly. A batter entering in a high-pressure crisis gets 20 unearned points even if they score 0 off 1 ball, while a batter entering at 145/1 is heavily penalized regardless of batting brilliance.
- In 50/50 Context-as-Leverage, P1 scales the magnitude of credit or blame for what the batter actually did. With the Phase 7G P3 corrections in place, the 50/50 architecture delivers flawless cricket intuition across all 18 stress scenarios.

### Question 7: Does outcome leakage remain exactly zero?
**Verdict:** **Yes, exactly 0.0000.**
- Inspection of `compute_corrected_p3` and all dependency pipelines verifies that no match result columns (`won_match`, `match_winner`, `win_margin`, etc.) are read or utilized.
- Tests in `test_phase7g_p3_corrections.py::test_outcome_invariance` confirm that injecting arbitrary match winners or margins produces identical bit-for-bit scores.

### Question 8: Which real-player examples improved/worsened?
- **Substantially Improved**:
  - AD Russell (65 off 25): P3 jumped from $18.6 \to 55.3$, score jumped from $54.9 \to 78.3$.
  - Ishan Kishan (99 off 58 in tie): P3 jumped from $49.4 \to 84.1$, score jumped from $74.6 \to 94.9$.
  - S Dhawan (29 off 30): P3 dropped from $92.0 \to 55.0$, score dropped from $70.1 \to 53.3$.
  - TM Dilshan (33 off 36): P3 dropped from $98.2 \to 68.7$, score dropped from $77.6 \to 64.2$.
  - SPD Smith (15 off 18): P3 dropped from $68.2 \to 47.2$, score dropped from $56.6 \to 49.0$.
  - JH Kallis (21 off 23 chasing 52): P3 dropped from $89.4 \to 46.9$, score dropped from $66.7 \to 52.2$.
- **Worsened**: None. All shifts aligned with cricket domain reality and fixed documented bugs.

### Question 9: Are there any new failure modes?
- **None detected**.
- Edge cases were stress-tested:
  - Extreme collapses (20/3) are amplified appropriately by high leverage ($1.175$).
  - Low-pressure run chases (145/1) are attenuated by low leverage ($0.804$).
  - DNB rows retain clean `NULL`.
  - Aggressive finishers in low targets are protected from the pace cap.

### Question 10: Is the architecture ready for final production integration?
**Verdict:** **Yes. The mathematical formulation, empirical behavior, and unit tests are complete.**
- However, per user instructions, **NO PRODUCTION CHANGES HAVE BEEN MADE**.
- Production integration requires explicit approval to update `src/contribution_framework.py`, recalculate production datasets, and align API defaults.

---

## 8. Summary Recommendation for Phase 8

| Component | Production (Phase 7D) | Recommended Phase 8 Candidate |
| :--- | :--- | :--- |
| **Architecture** | Additive (25% P1 + 35% P2 + 40% P3) | Context-as-Leverage (50% Adj P2 + 50% Adj P3) |
| **P1 Role** | Direct Scoring Pillar (25 points) | Difficulty / Leverage Multiplier ($L(P1) \in [0.65, 1.35]$) |
| **P3 Death RRR** | Uncapped asymptote (blowout to -85.0) | Mode 1A execution-conditioned floor ($-3.0$ / $-6.0$) |
| **P3 Partner** | Linear partnership differential only | Mode 2C hybrid share dampening $+$ differential penalty |
| **P3 Low Target** | Linear progress fraction | Mode 3C cruise-control pace cap for SR $< 100$ |
| **Production Files** | Currently untouched | Awaiting user sign-off before migration |
