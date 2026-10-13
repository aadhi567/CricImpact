import React, { useState } from 'react';
import {
  Anchor,
  TrendingUp,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  Clock,
  Zap,
  Target,
  BarChart3,
  Layers,
} from 'lucide-react';

export default function AnchorInningsAnalysis({ data, playerName, p3Score }) {
  const [selectedOver, setSelectedOver] = useState(
    data?.timeline_overs && data.timeline_overs.length > 0 ? data.timeline_overs[0].over : 0
  );
  const [showMatchups, setShowMatchups] = useState(false);

  if (!data) return null;

  const {
    why_p3_high = [],
    anchor_profile = {},
    partnership_dynamics = {},
    p3_components = [],
    timeline_overs = [],
    final_takeaway = {},
  } = data;

  const getLabelBadge = (label) => {
    switch (label?.toLowerCase()) {
      case 'supported':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase font-mono bg-[#152718] text-[#5A9E60] border border-[#2A4D30]">
            <CheckCircle2 className="w-3 h-3" /> Supported
          </span>
        );
      case 'mixed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase font-mono bg-[#2A2312] text-[#D4AF57] border border-[#4D3F1E]">
            <AlertCircle className="w-3 h-3" /> Mixed
          </span>
        );
      case 'inconclusive':
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase font-mono bg-[#1F1F1F] text-[#A0A0A0] border border-[#333333]">
            <HelpCircle className="w-3 h-3" /> Inconclusive
          </span>
        );
    }
  };

  const getImpactBadge = (direction) => {
    switch (direction?.toLowerCase()) {
      case 'positive':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-[#152718] text-[#5A9E60] border border-[#2A4D30]">
            + Positive
          </span>
        );
      case 'negative':
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-[#2A1414] text-[#C25454] border border-[#4D2626]">
            - Negative
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center px-2 py-0.5 rounded text-[11px] font-bold font-mono bg-[#1E1E1E] text-[#B8B8B8] border border-[#333333]">
            • Neutral
          </span>
        );
    }
  };

  const currentTimelineOver = timeline_overs.find((o) => o.over === selectedOver) || timeline_overs[0];

  return (
    <div className="bg-[#161616] rounded-xl p-6 sm:p-7 border border-[#2D2D2D] shadow-xs space-y-6">
      {/* SECTION HEADER */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#2D2D2D] pb-4">
        <div>
          <div className="flex items-center gap-2 text-[11px] font-semibold text-[#D4AF57] tracking-wider mb-1 font-mono uppercase">
            <Anchor className="w-4 h-4 text-[#D4AF57]" />
            <span>Forensic Match Analysis</span>
          </div>
          <h2 className="font-heading text-[20px] font-bold text-[#F2F2F2] tracking-tight">
            Anchor Innings & Partnership Attribution
          </h2>
          <p className="text-[12px] text-[#858585] mt-0.5 font-mono">
            Concise, evidence-backed evaluation of {playerName}'s team-state impact (P3 = {p3Score ?? '96.7'}).
          </p>
        </div>
        <div className="px-3 py-1.5 rounded-lg bg-[#101010] border border-[#3D351E] flex items-center gap-2 self-start sm:self-auto">
          <span className="text-[11px] text-[#858585] font-mono">P3 Score:</span>
          <span className="text-[15px] font-bold text-[#D4AF57] font-mono tabular-nums">{p3Score ?? '96.7'}</span>
        </div>
      </div>

      {/* 1. MAIN SECTION: WHY IS P3 HIGH? (PLACED NEAR TOP) */}
      <div className="bg-[#101010] rounded-xl p-5 border border-[#3D351E] space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-heading text-[15px] font-bold text-[#F2F2F2] flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[#D4AF57]" />
            Why is P3 high? (Observed Evidence)
          </h3>
          <span className="text-[11px] text-[#858585] font-mono">6 Evidence Findings</span>
        </div>
        <div className="divide-y divide-[#222222]">
          {why_p3_high.map((item, idx) => (
            <div key={idx} className="py-2.5 first:pt-1 last:pb-1 flex flex-col sm:flex-row sm:items-start justify-between gap-2">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="text-[#D4AF57] text-[13px] font-bold">•</span>
                  <span className="font-bold text-[#F2F2F2] text-[13px]">{item.heading}:</span>
                  <span className="text-[13px] text-[#B8B8B8] font-mono">{item.metric}</span>
                </div>
                <p className="text-[12px] text-[#858585] pl-3.5 leading-snug">
                  {item.significance}
                </p>
              </div>
              <div className="pl-3.5 sm:pl-0 shrink-0">
                {getLabelBadge(item.evidence_label)}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 2. ANCHOR BATTING PROFILE */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-heading text-[15px] font-bold text-[#F2F2F2] flex items-center gap-2">
            <Target className="w-4 h-4 text-[#D4AF57]" />
            Anchor Batting Profile
          </h3>
          <span className="text-[11px] text-[#858585] font-mono">Execution Metrics</span>
        </div>

        {/* Compact Metric Tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] space-y-0.5">
            <span className="text-[10px] font-semibold text-[#858585] uppercase tracking-wider font-mono block">Runs & Balls</span>
            <span className="text-[16px] font-bold text-[#F2F2F2] font-mono tabular-nums">
              {anchor_profile.runs} <span className="text-[11px] text-[#858585] font-normal">({anchor_profile.balls}b)</span>
            </span>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] space-y-0.5">
            <span className="text-[10px] font-semibold text-[#858585] uppercase tracking-wider font-mono block">Strike Rate</span>
            <span className="text-[16px] font-bold text-[#D4AF57] font-mono tabular-nums">
              {anchor_profile.strike_rate}
            </span>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] space-y-0.5">
            <span className="text-[10px] font-semibold text-[#858585] uppercase tracking-wider font-mono block">Dot Balls</span>
            <span className="text-[16px] font-bold text-[#F2F2F2] font-mono tabular-nums">
              {anchor_profile.dot_balls} <span className="text-[11px] text-[#858585] font-normal">({anchor_profile.dot_percentage}%)</span>
            </span>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] space-y-0.5">
            <span className="text-[10px] font-semibold text-[#858585] uppercase tracking-wider font-mono block">Max Dot Streak</span>
            <span className="text-[16px] font-bold text-[#5A9E60] font-mono tabular-nums">
              {anchor_profile.longest_dot_streak} <span className="text-[11px] text-[#858585] font-normal">balls</span>
            </span>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] space-y-0.5">
            <span className="text-[10px] font-semibold text-[#858585] uppercase tracking-wider font-mono block">Running Runs</span>
            <span className="text-[16px] font-bold text-[#F2F2F2] font-mono tabular-nums">
              {anchor_profile.singles}s <span className="text-[11px] text-[#858585] font-normal">({anchor_profile.twos}x2, {anchor_profile.threes}x3)</span>
            </span>
          </div>

          <div className="bg-[#101010] p-3 rounded-lg border border-[#2D2D2D] space-y-0.5">
            <span className="text-[10px] font-semibold text-[#858585] uppercase tracking-wider font-mono block">Boundaries</span>
            <span className="text-[16px] font-bold text-[#F2F2F2] font-mono tabular-nums">
              {anchor_profile.fours}x4 • {anchor_profile.sixes}x6
            </span>
          </div>
        </div>

        {/* Phase Breakdown Bar */}
        {anchor_profile.phase_breakdown && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-[#101010] rounded-lg border border-[#2D2D2D] flex items-center justify-between">
              <div>
                <span className="text-[11px] text-[#858585] font-mono">Powerplay (Overs 0–5):</span>
                <span className="ml-2 font-bold text-[#F2F2F2] font-mono">
                  {anchor_profile.phase_breakdown.powerplay?.runs} off {anchor_profile.phase_breakdown.powerplay?.balls}b
                </span>
              </div>
              <span className="text-[11px] font-mono text-[#D4AF57] font-semibold">
                SR {anchor_profile.phase_breakdown.powerplay?.strike_rate} ({anchor_profile.phase_breakdown.powerplay?.boundaries}x4)
              </span>
            </div>

            <div className="p-3 bg-[#101010] rounded-lg border border-[#2D2D2D] flex items-center justify-between">
              <div>
                <span className="text-[11px] text-[#858585] font-mono">Middle Overs (Overs 6–14):</span>
                <span className="ml-2 font-bold text-[#F2F2F2] font-mono">
                  {anchor_profile.phase_breakdown.middle_overs?.runs} off {anchor_profile.phase_breakdown.middle_overs?.balls}b
                </span>
              </div>
              <span className="text-[11px] font-mono text-[#5A9E60] font-semibold">
                SR {anchor_profile.phase_breakdown.middle_overs?.strike_rate} ({anchor_profile.phase_breakdown.middle_overs?.dots} dots)
              </span>
            </div>
          </div>
        )}

        {/* 3-5 Pattern Bullets */}
        <div className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D] space-y-1.5">
          <span className="text-[11px] font-bold text-[#858585] uppercase tracking-wider font-mono block">Key Batting Patterns:</span>
          {anchor_profile.pattern_bullets?.map((bullet, idx) => (
            <div key={idx} className="flex items-start gap-2 text-[12px] text-[#B8B8B8]">
              <span className="text-[#D4AF57] font-bold">•</span>
              <span>{bullet}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 3. PARTNERSHIP DYNAMICS */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-heading text-[15px] font-bold text-[#F2F2F2] flex items-center gap-2">
            <Zap className="w-4 h-4 text-[#D4AF57]" />
            Partnership Dynamics (Side-by-Side)
          </h3>
          <span className="text-[11px] text-[#858585] font-mono">Tandem Interaction</span>
        </div>

        {/* Side by Side Batter vs Partner Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Batter Card */}
          <div className="bg-[#101010] rounded-lg p-4 border border-[#2D2D2D] space-y-2.5">
            <div className="flex justify-between items-baseline border-b border-[#2D2D2D] pb-2">
              <span className="font-bold text-[#F2F2F2] text-[14px]">{partnership_dynamics.batter?.name}</span>
              <span className="text-[11px] font-mono text-[#D4AF57] px-2 py-0.5 rounded bg-[#1C1A14] border border-[#3D351E]">
                Anchor (32.0% share)
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#1E1E1E]">
                <span className="text-[#858585]">Runs / Balls:</span>
                <span className="font-mono text-[#F2F2F2] font-semibold">{partnership_dynamics.batter?.runs} ({partnership_dynamics.batter?.balls}b)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1E1E1E]">
                <span className="text-[#858585]">Strike Rate:</span>
                <span className="font-mono text-[#F2F2F2] font-semibold">{partnership_dynamics.batter?.strike_rate}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1E1E1E]">
                <span className="text-[#858585]">Balls PP / Mid:</span>
                <span className="font-mono text-[#F2F2F2] font-semibold">{partnership_dynamics.batter?.pp_balls} / {partnership_dynamics.batter?.mid_balls}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1E1E1E]">
                <span className="text-[#858585]">Strike Rotation:</span>
                <span className="font-mono text-[#F2F2F2] font-semibold">{partnership_dynamics.batter?.rotation_pct}%</span>
              </div>
            </div>
          </div>

          {/* Partner Card */}
          <div className="bg-[#101010] rounded-lg p-4 border border-[#2D2D2D] space-y-2.5">
            <div className="flex justify-between items-baseline border-b border-[#2D2D2D] pb-2">
              <span className="font-bold text-[#F2F2F2] text-[14px]">{partnership_dynamics.partner?.name}</span>
              <span className="text-[11px] font-mono text-[#5A9E60] px-2 py-0.5 rounded bg-[#152718] border border-[#2A4D30]">
                Aggressor (60.5% share)
              </span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[#1E1E1E]">
                <span className="text-[#858585]">Runs / Balls:</span>
                <span className="font-mono text-[#F2F2F2] font-semibold">{partnership_dynamics.partner?.runs} ({partnership_dynamics.partner?.balls}b)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1E1E1E]">
                <span className="text-[#858585]">Strike Rate:</span>
                <span className="font-mono text-[#F2F2F2] font-semibold">{partnership_dynamics.partner?.strike_rate}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1E1E1E]">
                <span className="text-[#858585]">Balls PP / Mid:</span>
                <span className="font-mono text-[#F2F2F2] font-semibold">{partnership_dynamics.partner?.pp_balls} / {partnership_dynamics.partner?.mid_balls}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[#1E1E1E]">
                <span className="text-[#858585]">Strike Rotation:</span>
                <span className="font-mono text-[#F2F2F2] font-semibold">{partnership_dynamics.partner?.rotation_pct}%</span>
              </div>
            </div>
          </div>
        </div>

        {/* Progressive Disclosure: Bowler Matchups */}
        <div className="bg-[#101010] rounded-lg border border-[#2D2D2D] overflow-hidden">
          <button
            onClick={() => setShowMatchups(!showMatchups)}
            className="w-full p-3 flex items-center justify-between text-left hover:bg-[#151515] transition-colors cursor-pointer text-xs"
          >
            <span className="font-semibold text-[#D4AF57] flex items-center gap-2">
              <BarChart3 className="w-3.5 h-3.5" />
              Comparative Bowler Matchups ({partnership_dynamics.bowler_matchups?.length || 0} Bowlers Faced)
            </span>
            <div className="flex items-center gap-1.5 text-[#858585]">
              <span>{showMatchups ? 'Hide matchups' : 'Show matchups'}</span>
              {showMatchups ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </div>
          </button>

          {showMatchups && (
            <div className="p-3 pt-0 border-t border-[#222222] overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="text-[11px] font-mono text-[#858585] border-b border-[#222222]">
                    <th className="py-2 pr-3">Bowler</th>
                    <th className="py-2 px-3">Style</th>
                    <th className="py-2 px-3 text-right">{playerName} (R/B)</th>
                    <th className="py-2 px-3 text-right">{playerName} SR</th>
                    <th className="py-2 px-3 text-right">{partnership_dynamics.partner?.name} (R/B)</th>
                    <th className="py-2 pl-3 text-right">{partnership_dynamics.partner?.name} SR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#1C1C1C] font-mono">
                  {partnership_dynamics.bowler_matchups?.map((b, idx) => (
                    <tr key={idx} className="hover:bg-[#141414]">
                      <td className="py-1.5 pr-3 font-sans font-medium text-[#F2F2F2]">{b.bowler}</td>
                      <td className="py-1.5 px-3 text-[#858585]">{b.style}</td>
                      <td className="py-1.5 px-3 text-right text-[#F2F2F2]">{b.batter_runs} ({b.batter_balls}b)</td>
                      <td className="py-1.5 px-3 text-right font-bold text-[#D4AF57]">{b.batter_sr}</td>
                      <td className="py-1.5 px-3 text-right text-[#F2F2F2]">{b.partner_runs} ({b.partner_balls}b)</td>
                      <td className="py-1.5 pl-3 text-right font-bold text-[#5A9E60]">{b.partner_sr}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Short Findings Bullets */}
        <div className="bg-[#101010] p-4 rounded-lg border border-[#2D2D2D] space-y-2 text-xs">
          <div className="flex items-start gap-2">
            <span className="text-[#D4AF57] font-bold">•</span>
            <div>
              <strong className="text-[#F2F2F2]">Partnership Support:</strong>{' '}
              <span className="text-[#B8B8B8]">{partnership_dynamics.findings?.partnership_support}</span>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-[#D4AF57] font-bold">•</span>
            <div>
              <strong className="text-[#F2F2F2]">Pressure Transfer:</strong>{' '}
              <span className="text-[#B8B8B8]">{partnership_dynamics.findings?.pressure_transfer}</span>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="text-[#D4AF57] font-bold">•</span>
            <div>
              <strong className="text-[#F2F2F2]">Alternative Explanations:</strong>{' '}
              <span className="text-[#B8B8B8]">{partnership_dynamics.findings?.alternative_explanations}</span>
            </div>
          </div>
          <div className="flex items-start gap-2 pt-1 border-t border-[#1E1E1E]">
            <span className="text-[#5A9E60] font-bold">•</span>
            <div>
              <strong className="text-[#F2F2F2]">Confidence Assessment:</strong>{' '}
              <span className="text-[#5A9E60] font-semibold">{partnership_dynamics.findings?.confidence}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 4. P3 COMPONENT BREAKDOWN */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-heading text-[15px] font-bold text-[#F2F2F2] flex items-center gap-2">
            <Layers className="w-4 h-4 text-[#D4AF57]" />
            P3 Component Breakdown (Inputs & Direction)
          </h3>
          <span className="text-[11px] text-[#858585] font-mono">Mathematical Inputs</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {p3_components.map((c, idx) => (
            <div key={idx} className="bg-[#101010] p-3.5 rounded-lg border border-[#2D2D2D] flex flex-col justify-between space-y-2">
              <div className="flex justify-between items-start gap-2">
                <div>
                  <span className="text-[12px] font-bold text-[#F2F2F2] block">{c.metric_name}</span>
                  <span className="text-[13px] font-mono font-bold text-[#D4AF57] mt-0.5 block">{c.observed_value}</span>
                </div>
                {getImpactBadge(c.direction)}
              </div>
              <p className="text-[11px] text-[#858585] leading-snug pt-1 border-t border-[#1C1C1C]">
                {c.explanation}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* 5. INNINGS TIMELINE (VISUAL OVER-BY-OVER PROGRESSION) */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-heading text-[15px] font-bold text-[#F2F2F2] flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#D4AF57]" />
            Innings Timeline (Over-by-Over Progression)
          </h3>
          <span className="text-[11px] text-[#858585] font-mono">Click an over to inspect</span>
        </div>

        {/* Timeline Over Pills */}
        <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
          {timeline_overs.map((o) => {
            const isSelected = o.over === selectedOver;
            return (
              <button
                key={o.over}
                onClick={() => setSelectedOver(o.over)}
                className={`px-3 py-2 rounded-lg border text-left shrink-0 transition-all cursor-pointer font-mono ${
                  isSelected
                    ? 'bg-[#1C1A14] border-[#D4AF57] text-[#D4AF57] shadow-xs'
                    : 'bg-[#101010] border-[#2D2D2D] text-[#858585] hover:border-[#3D351E] hover:text-[#F2F2F2]'
                }`}
              >
                <div className="text-[10px] uppercase font-bold">{o.over_label}</div>
                <div className="text-[14px] font-bold text-[#F2F2F2] mt-0.5">{o.runs}r</div>
                <div className="text-[10px] text-[#858585]">{o.team_score}</div>
              </button>
            );
          })}
        </div>

        {/* Selected Over Detail Card */}
        {currentTimelineOver && (
          <div className="bg-[#101010] p-4 rounded-lg border border-[#3D351E] space-y-2.5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#222222] pb-2">
              <div className="flex items-center gap-3">
                <span className="font-bold text-[#F2F2F2] text-[14px]">{currentTimelineOver.over_label}</span>
                <span className="text-[12px] text-[#858585] font-mono">Bowler: <strong className="text-[#F2F2F2]">{currentTimelineOver.bowler}</strong></span>
              </div>
              <div className="flex items-center gap-4 text-xs font-mono text-[#B8B8B8]">
                <span>Over Runs: <strong className="text-[#D4AF57]">{currentTimelineOver.runs}</strong></span>
                <span>Team: <strong className="text-[#F2F2F2]">{currentTimelineOver.team_score}</strong></span>
                <span>RR: <strong className="text-[#5A9E60]">{currentTimelineOver.team_rr}</strong></span>
              </div>
            </div>

            {/* Event bullets for the selected over */}
            <div className="space-y-1.5 pt-1">
              <span className="text-[10px] font-mono text-[#858585] uppercase tracking-wider block">Observed Events:</span>
              {currentTimelineOver.bullets?.map((b, idx) => (
                <div key={idx} className="flex items-start gap-2 text-xs text-[#B8B8B8]">
                  <span className="text-[#D4AF57] font-bold">•</span>
                  <span>{b}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 6. FINAL TAKEAWAY (COMPACT SUMMARY) */}
      <div className="bg-[#101010] p-5 rounded-xl border border-[#2D2D2D] space-y-4">
        <h3 className="font-heading text-[15px] font-bold text-[#F2F2F2] flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-[#D4AF57]" />
          Final Analytical Takeaway
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          {/* Why P3 is high */}
          <div className="space-y-1.5">
            <span className="font-bold text-[#D4AF57] text-[12px] block">Why P3 is High:</span>
            {final_takeaway.why_p3_high_bullets?.map((bullet, idx) => (
              <div key={idx} className="flex items-start gap-2 text-[#B8B8B8]">
                <span className="text-[#D4AF57] font-bold">•</span>
                <span>{bullet}</span>
              </div>
            ))}
          </div>

          {/* Partnership Effect & Attribution Caveat */}
          <div className="space-y-2.5">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="font-bold text-[#F2F2F2] text-[12px]">Partnership Effect:</span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase font-mono bg-[#152718] text-[#5A9E60] border border-[#2A4D30]">
                  {final_takeaway.partnership_effect?.label || 'Support Provided'}
                </span>
              </div>
              <p className="text-[#B8B8B8] leading-snug">
                {final_takeaway.partnership_effect?.summary}
              </p>
            </div>

            <div className="pt-2 border-t border-[#1E1E1E]">
              <span className="font-bold text-[#858585] text-[11px] block mb-0.5">Attribution Caveat:</span>
              <p className="text-[#858585] italic leading-snug">
                {final_takeaway.attribution_caveat}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
