import React from 'react';
import { Compass, Zap, TrendingUp, GitFork, CheckCircle, Info, Scale } from 'lucide-react';

export default function ContributionExplanation({
  pillars = {},
  signals = [],
  verdict,
  score,
  _raw,
  diagnostic,
  leverage,
  p1_leverage,
  adjusted_p2,
  adjusted_p3,
}) {
  const p1Pillar = pillars.pillar1_context || {};
  const p2Pillar = pillars.pillar2_performance || {};
  const p3Pillar = pillars.pillar3_state || {};
  const p4Pillar = pillars.pillar4_cf || {};

  const p1Score = p1Pillar.score;
  const p1IsNull = p1Score === null || p1Score === undefined;

  // Leverage calculation
  const levVal =
    leverage?.value ??
    p1_leverage ??
    p1Pillar.leverage ??
    (!p1IsNull ? Math.max(0.65, Math.min(1.35, 1.0 + 0.35 * ((Number(p1Score) - 50.0) / 50.0))) : 1.0);

  // Raw & Adjusted P2
  const rawP2 = p2Pillar.raw_score ?? p2Pillar.score;
  const p2IsNull = rawP2 === null || rawP2 === undefined;
  const adjP2 =
    adjusted_p2 ??
    p2Pillar.adjusted_score ??
    (!p2IsNull ? Math.max(0.1, Math.min(99.9, 50.0 + (Number(rawP2) - 50.0) * levVal)) : null);

  // Raw & Adjusted P3
  const rawP3 = p3Pillar.raw_score ?? p3Pillar.score;
  const p3IsNull = rawP3 === null || rawP3 === undefined;
  const adjP3 =
    adjusted_p3 ??
    p3Pillar.adjusted_score ??
    (!p3IsNull ? Math.max(0.1, Math.min(99.9, 50.0 + (Number(rawP3) - 50.0) * levVal)) : null);

  // P4 Counterfactual Diagnostic
  const p4Score = p4Pillar.score;
  const p4IsNull = p4Score === null || p4Score === undefined;
  const diagData = diagnostic || p4Pillar.diagnostic || {};
  const altScenario =
    diagData.alternative_scenario ||
    p4Pillar.description ||
    'Optimal aggression & strike rotation balance under match conditions';
  const effGain = diagData.efficiency_gain || 'Tactical boundary equity';
  const diagImpact =
    diagData.diagnostic_impact ||
    'Identifies what the batter could have done differently without penalizing or modifying the Contribution Score.';

  return (
    <div className="space-y-6">
      {/* Mathematical Architecture Formula Banner */}
      <div className="bg-[#161616] rounded-xl p-5 sm:p-6 border border-[#2D2D2D] shadow-xs space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[#2D2D2D] pb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-[#1F1C14] text-[#D4AF57] border border-[#A8893D]/40">
                Phase 7 architecture
              </span>
              <span className="text-[12px] text-[#858585] font-mono">
                Context-as-leverage (50% Adj P2 + 50% Adj P3)
              </span>
            </div>
            <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] mt-1.5 tracking-tight">
              Contribution Score = 50% × Adjusted P2 + 50% × Adjusted P3
            </h3>
            <p className="text-[13px] font-normal text-[#858585] mt-1 leading-relaxed max-w-3xl">
              P1 does not directly add points to the Contribution Score. It establishes situational leverage to scale execution rewards and collapse accountability relative to the match context.
            </p>
          </div>
          <div className="flex items-center gap-2 self-start md:self-auto">
            <div className="px-3 py-1.5 rounded-lg bg-[#101010] border border-[#2D2D2D] text-[11px] text-[#858585]">
              <strong className="font-semibold text-[#F2F2F2]">Par Invariance:</strong> Par execution (50.0) stays 50.0 at any leverage
            </div>
          </div>
        </div>

        {/* 4-Step Pipeline Flow Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5 text-[13px]">
          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
            <div>
              <span className="font-semibold text-[#858585] block text-[11px]">
                Step 1: P1 context
              </span>
              <span className="text-[#F2F2F2] text-[14px] font-bold mt-1 block tabular-nums font-mono">
                {p1IsNull ? '—' : Number(p1Score).toFixed(1)} / 100
              </span>
            </div>
            <span className="text-[11px] text-[#858585] mt-1">Situation difficulty inherited</span>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
            <div>
              <span className="font-semibold text-[#858585] block text-[11px]">
                Step 2: Leverage multiplier
              </span>
              <span className="text-[#D4AF57] text-[14px] font-mono font-bold mt-1 block tabular-nums">
                L(P1) = {Number(levVal).toFixed(3)}×
              </span>
            </div>
            <span className="text-[11px] text-[#858585] mt-1">
              Bounds [0.65×, 1.35×] • {levVal > 1.0 ? 'Amplifies deviations' : levVal < 1.0 ? 'Dampens deviations' : 'Neutral par'}
            </span>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] flex flex-col justify-between">
            <div>
              <span className="font-semibold text-[#858585] block text-[11px]">
                Step 3: Adjusted P2 & P3
              </span>
              <span className="text-[#F2F2F2] text-[13px] font-medium mt-1 block tabular-nums font-mono">
                P2: {adjP2 !== null ? Number(adjP2).toFixed(1) : '—'} • P3: {adjP3 !== null ? Number(adjP3).toFixed(1) : '—'}
              </span>
            </div>
            <span className="text-[11px] text-[#858585] mt-1">Adjusted = 50 + (Raw - 50) × L</span>
          </div>

          <div className="bg-[#152718] p-3 rounded-lg border border-[#2A4D30] flex flex-col justify-between">
            <div>
              <span className="font-semibold text-[#5A9E60] block text-[11px]">
                Step 4: Final 50/50 score
              </span>
              <span className="text-[#5A9E60] text-[14px] font-bold mt-1 block tabular-nums font-mono">
                Score: {score !== null && score !== undefined ? Number(score).toFixed(1) : '—'}
              </span>
            </div>
            <span className="text-[11px] text-[#5A9E60] mt-1">50% Adj P2 + 50% Adj P3</span>
          </div>
        </div>
      </div>

      {/* P1 Context / Leverage Controller Card */}
      <div className="bg-[#161616] rounded-xl p-5 border border-[#2D2D2D] shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            <Compass className="w-5 h-5 text-[#D4AF57]" />
            <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
              P1 — Context and leverage controller
            </h3>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-[#101010] text-[#858585] border border-[#2D2D2D]">
              Leverage signal • 0 direct points
            </span>
          </div>
          <div className="text-[12px] text-[#858585] font-mono">
            Multiplier: <strong className="text-[#D4AF57] font-bold">{Number(levVal).toFixed(3)}×</strong> (Bounds: 0.65 to 1.35)
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-[13px] mt-3">
          <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
            <span className="text-[11px] font-semibold text-[#858585] block mb-1">
              Context difficulty (P1)
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-[28px] font-bold text-[#F2F2F2] tabular-nums font-mono leading-none">
                {p1IsNull ? '—' : Number(p1Score).toFixed(1)}
              </span>
              <span className="text-[#858585] font-mono text-[13px]">/ 100</span>
            </div>
            <p className="text-[12px] text-[#858585] mt-2 leading-relaxed">
              {p1Pillar.description || 'Evaluates situational difficulty, match leverage, entry point, phase demands, and collapse pressure.'}
            </p>
          </div>

          <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
            <span className="text-[11px] font-semibold text-[#858585] block mb-1">
              Leverage formula
            </span>
            <div className="font-mono text-[12px] text-[#D4AF57] font-semibold bg-[#080808] px-2.5 py-1.5 rounded border border-[#2D2D2D]">
              L(P1) = 1.0 + 0.35 × ((P1 - 50) / 50)
            </div>
            <p className="text-[12px] text-[#858585] mt-2 leading-relaxed">
              P1 &lt; 50 scales down deviations (easier context); P1 &gt; 50 scales up deviations (clutch context). Par (50.0) produces exactly 1.000×.
            </p>
          </div>

          <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D]">
            <span className="text-[11px] font-semibold text-[#858585] block mb-1">
              Situational interpretation
            </span>
            <div className="text-[13px] text-[#F2F2F2] mt-1">
              {Number(p1Score) < 45 ? (
                <span className="text-[#858585] font-normal">
                  Comfortable situation (L = {Number(levVal).toFixed(3)}×): Moderately dampens deviation so unearned bonus is avoided.
                </span>
              ) : Number(p1Score) > 55 ? (
                <span className="text-[#D4AF57] font-medium">
                  Demanding situation (L = {Number(levVal).toFixed(3)}×): Amplifies performance rewards and accountability under pressure.
                </span>
              ) : (
                <span className="text-[#5A9E60] font-medium">
                  Standard situation (L ≈ 1.000×): Direct 1:1 reflection of batter execution and state impact.
                </span>
              )}
            </div>
            <p className="text-[11px] text-[#858585] mt-2">
              Note: P1 scales impact; it never directly adds score points.
            </p>
          </div>
        </div>
      </div>

      {/* Model Signals & Verdict Banner */}
      <div className="bg-[#161616] rounded-xl p-5 border border-[#2D2D2D] shadow-xs">
        <div className="flex items-center gap-2 mb-3">
          <Info className="w-4 h-4 text-[#D4AF57]" />
          <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
            Situational signals and cricket explanation
          </h3>
        </div>

        {verdict && (
          <div className="p-3.5 rounded-lg bg-[#101010] border border-[#2D2D2D] text-[13px] text-[#F2F2F2] mb-4 leading-relaxed">
            <span className="font-semibold text-[#D4AF57] mr-1.5">Model Assessment:</span>
            {verdict}
          </div>
        )}

        <div className="space-y-2">
          <h4 className="text-[11px] font-semibold text-[#858585]">
            Active innings signals:
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            {signals.map((sig, idx) => (
              <div
                key={idx}
                className="flex items-start gap-2 bg-[#101010] rounded-lg p-2.5 border border-[#2D2D2D] text-[13px] text-[#B8B8B8]"
              >
                <CheckCircle className="w-3.5 h-3.5 text-[#5A9E60] shrink-0 mt-0.5" />
                <span>{sig}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Core Scoring Pillars Grid (P2 50% + P3 50%) */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
              Core scoring pillars (50% Adjusted P2 + 50% Adjusted P3)
            </h3>
            <p className="text-[12px] font-normal text-[#858585]">
              P2 (Execution) and P3 (Team-State Impact) each carry 50% weight in the final Contribution Score.
            </p>
          </div>
          <span className="text-[11px] font-semibold text-[#5A9E60] bg-[#152718] px-2.5 py-1 rounded border border-[#2A4D30]">
            P2 (50%) + P3 (50%) = 100%
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Pillar 2: Batter Performance / Execution */}
          <div className="rounded-xl p-5 border border-[#2D2D2D] bg-[#161616] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full border bg-[#1F1C14] text-[#D4AF57] border-[#A8893D]/40">
                  P2 • 50% of final score
                </span>
                <Zap className="w-4 h-4 text-[#D4AF57]" />
              </div>

              <h4 className="font-heading text-[15px] font-bold text-[#F2F2F2] mt-1">
                Pillar 2 — Batting Execution
              </h4>
              <div className="text-[12px] italic text-[#858585] mt-1 font-normal">
                "{p2Pillar.question || 'What did the batter actually do?'}"
              </div>

              <p className="text-[13px] font-normal text-[#858585] mt-2.5 leading-relaxed">
                {p2Pillar.description || 'Evaluates scoring output, strike rate, boundaries, and pace relative to the expected situational baseline.'}
              </p>
            </div>

            <div className="mt-5 pt-3 border-t border-[#2D2D2D] space-y-2">
              <div className="flex items-center justify-between text-[12px] text-[#858585]">
                <span>Raw execution score (P2):</span>
                <span className="font-mono font-semibold text-[#F2F2F2] tabular-nums">
                  {p2IsNull ? '—' : Number(rawP2).toFixed(1)} / 100
                </span>
              </div>
              <div className="flex items-center justify-between text-[12px] text-[#858585]">
                <span>Context leverage applied:</span>
                <span className="font-mono font-semibold text-[#D4AF57]">
                  × {Number(levVal).toFixed(3)}
                </span>
              </div>
              <div className="flex items-baseline justify-between pt-1 border-t border-[#2D2D2D]">
                <span className="text-[12px] font-semibold text-[#D4AF57]">Adjusted P2 (50% weight):</span>
                <div className="text-right">
                  <span className="text-[28px] font-bold text-[#F2F2F2] tabular-nums font-mono leading-none">
                    {adjP2 !== null ? Number(adjP2).toFixed(1) : '—'}
                  </span>
                  <span className="text-[12px] text-[#858585] font-mono"> / 100</span>
                </div>
              </div>
            </div>
          </div>

          {/* Pillar 3: Team-State Impact */}
          <div className="rounded-xl p-5 border border-[#2D2D2D] bg-[#161616] shadow-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full border bg-[#152718] text-[#5A9E60] border-[#2A4D30]">
                  P3 • 50% of final score
                </span>
                <TrendingUp className="w-4 h-4 text-[#5A9E60]" />
              </div>

              <h4 className="font-heading text-[15px] font-bold text-[#F2F2F2] mt-1">
                Pillar 3 — Team-State Impact
              </h4>
              <div className="text-[12px] italic text-[#858585] mt-1 font-normal">
                "{p3Pillar.question || "How did the batter change the team's position while at the crease?"}"
              </div>

              <p className="text-[13px] font-normal text-[#858585] mt-2.5 leading-relaxed">
                {p3Pillar.description || "Measures exact entry-to-exit trajectory shift, partnership carrying share, and collapse stabilization."}
              </p>
            </div>

            <div className="mt-5 pt-3 border-t border-[#2D2D2D] space-y-2">
              <div className="flex items-center justify-between text-[12px] text-[#858585]">
                <span>Raw state impact (P3):</span>
                <span className="font-mono font-semibold text-[#F2F2F2] tabular-nums">
                  {p3IsNull ? '—' : Number(rawP3).toFixed(1)} / 100
                </span>
              </div>
              <div className="flex items-center justify-between text-[12px] text-[#858585]">
                <span>Context leverage applied:</span>
                <span className="font-mono font-semibold text-[#D4AF57]">
                  × {Number(levVal).toFixed(3)}
                </span>
              </div>
              <div className="flex items-baseline justify-between pt-1 border-t border-[#2D2D2D]">
                <span className="text-[12px] font-semibold text-[#5A9E60]">Adjusted P3 (50% weight):</span>
                <div className="text-right">
                  <span className="text-[28px] font-bold text-[#F2F2F2] tabular-nums font-mono leading-none">
                    {adjP3 !== null ? Number(adjP3).toFixed(1) : '—'}
                  </span>
                  <span className="text-[12px] text-[#858585] font-mono"> / 100</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Synthesis Summary Bar */}
      <div className="bg-[#101010] rounded-xl p-4 border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-[13px]">
        <div className="flex items-center gap-2">
          <Scale className="w-4 h-4 text-[#5A9E60]" />
          <span className="font-semibold text-[#F2F2F2]">Score synthesis:</span>
          <span className="text-[#858585] font-mono tabular-nums">
            0.50 × ({adjP2 !== null ? Number(adjP2).toFixed(1) : '—'}) + 0.50 × ({adjP3 !== null ? Number(adjP3).toFixed(1) : '—'})
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[#858585]">Final contribution score:</span>
          <span className="text-[18px] font-bold text-[#D4AF57] font-mono tabular-nums">
            {score !== null && score !== undefined ? Number(score).toFixed(1) : '—'}
          </span>
        </div>
      </div>

      {/* Separate P4 Counterfactual Diagnostic Section */}
      <div className="bg-[#101010] rounded-xl p-5 border border-[#2D2D2D] shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <GitFork className="w-4 h-4 text-[#858585]" />
            <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] tracking-tight">
              P4 counterfactual diagnostic
            </h3>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-[#161616] text-[#858585] border border-[#2D2D2D]">
              Weight: 0% • Diagnostic only
            </span>
          </div>
          <span className="text-[12px] text-[#858585]">
            Does NOT modify Contribution Score
          </span>
        </div>

        <p className="text-[13px] font-normal text-[#858585] leading-relaxed mb-4">
          Explains what the batter could reasonably have done differently given match conditions. Decoupled from the 0–100 Contribution Score so diagnostic exploration never inflates or penalizes performance.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[13px]">
          <div className="bg-[#161616] p-3 rounded-lg border border-[#2D2D2D]">
            <span className="text-[11px] font-semibold text-[#858585] block mb-1">
              Alternative scenario
            </span>
            <p className="text-[#F2F2F2]">{altScenario}</p>
          </div>

          <div className="bg-[#161616] p-3 rounded-lg border border-[#2D2D2D]">
            <span className="text-[11px] font-semibold text-[#858585] block mb-1">
              Efficiency gain
            </span>
            <p className="text-[#F2F2F2]">{effGain}</p>
          </div>

          <div className="bg-[#161616] p-3 rounded-lg border border-[#2D2D2D]">
            <span className="text-[11px] font-semibold text-[#858585] block mb-1">
              Diagnostic context
            </span>
            <p className="text-[#F2F2F2]">{diagImpact}</p>
          </div>
        </div>

        {!p4IsNull && (
          <div className="mt-3 pt-3 border-t border-[#2D2D2D] flex items-center justify-between text-[12px] text-[#858585]">
            <span>Diagnostic scenario value (informational):</span>
            <span className="font-mono font-semibold text-[#F2F2F2] tabular-nums">
              {Number(p4Score).toFixed(1)} / 100
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
