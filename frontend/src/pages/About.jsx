import React from 'react';
import { Link } from 'react-router-dom';
import {
  Compass,
  Zap,
  TrendingUp,
  Award,
  Calculator,
  Sparkles,
} from 'lucide-react';

export default function About() {
  return (
    <div className="w-full space-y-8 font-mono text-[#F2F2F2]">
      {/* Header */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div>
          <span className="px-2.5 py-0.5 rounded text-[11px] font-semibold bg-[#101010] text-[#D4AF57] border border-[#D4AF57]/40 tracking-wider">
            Cricket analytics guide
          </span>
          <h1 className="font-heading text-[30px] sm:text-[34px] lg:text-[36px] font-bold text-[#F2F2F2] mt-2.5 tracking-wider leading-tight">
            About the contribution model
          </h1>
          <p className="text-[15px] sm:text-[16px] text-[#B8B8B8] mt-2 max-w-3xl leading-relaxed font-normal">
            Why traditional cricket statistics — runs, batting averages, and strike rates — frequently mislead analysts, and how contextual equity measures what truly wins T20 matches.
          </p>
        </div>

        <div className="flex items-center gap-3 self-start md:self-auto shrink-0">
          <Link
            to="/methodology"
            className="px-4 py-2.5 rounded-lg bg-[#101010] text-[#F2F2F2] hover:bg-[#202020] border border-[#2D2D2D] text-[13px] sm:text-[13.5px] font-semibold transition-colors flex items-center gap-2"
          >
            <Calculator className="w-4 h-4 text-[#D4AF57]" />
            <span>Mathematical methodology</span>
          </Link>
          <Link
            to="/dashboard"
            className="px-4 py-2.5 rounded-lg bg-[#D4AF57] text-[#080808] hover:bg-[#E1C878] text-[13px] sm:text-[13.5px] font-bold shadow-xs transition-colors flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            <span>View season ratings</span>
          </Link>
        </div>
      </div>

      {/* The Core Problem in Modern Cricket Analytics */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-5">
        <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
          The flaw in traditional T20 batting stats
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 text-[14px] sm:text-[14.5px] text-[#B8B8B8] leading-relaxed">
          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2.5">
            <strong className="text-[#F2F2F2] block text-[15px] sm:text-[16px] font-semibold">Runs don't tell the situation</strong>
            <p className="font-normal text-[13.5px] sm:text-[14px] text-[#858585] leading-relaxed">
              Scoring 45 off 38 balls when chasing 120 is a match-winning anchor knock. Scoring 45 off 38 balls when chasing 215 loses the game for your team. Traditional box scores treat both as the exact same 45 runs.
            </p>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2.5">
            <strong className="text-[#F2F2F2] block text-[15px] sm:text-[16px] font-semibold">Strike rates can deceive</strong>
            <p className="font-normal text-[13.5px] sm:text-[14px] text-[#858585] leading-relaxed">
              A batter scoring 18 off 6 balls (SR 300) when the team is 190/3 in the final over is helpful. A batter hitting 18 off 6 when the team is 20/3 in the 3rd over and getting dismissed throws away the team's resource foundation.
            </p>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2.5">
            <strong className="text-[#F2F2F2] block text-[15px] sm:text-[16px] font-semibold">Context is everything</strong>
            <p className="font-normal text-[13.5px] sm:text-[14px] text-[#858585] leading-relaxed">
              Every delivery in a T20 match exists inside a state: balls remaining, wickets in hand, target pressure, and phase difficulty. Batters should be judged by how they change that match state relative to baseline expectation.
            </p>
          </div>
        </div>
      </div>

      {/* The 3 Core Cricket Questions */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-6">
        <div className="border-b border-[#2D2D2D] pb-3.5">
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
            The three questions the model answers
          </h2>
          <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
            Every innings is broken down into three straightforward, intuitive questions.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-[14px] sm:text-[14.5px] text-[#F2F2F2]">
          <div className="bg-[#101010] p-6 rounded-xl border border-[#2D2D2D] flex flex-col justify-between space-y-4">
            <div>
              <div className="w-9 h-9 rounded-lg bg-[#161616] border border-[#D4AF57]/40 flex items-center justify-center text-[#D4AF57] mb-3">
                <Compass className="w-5 h-5" />
              </div>
              <h3 className="font-heading text-[16px] sm:text-[17px] font-bold text-[#F2F2F2]">1. Match context (P1)</h3>
              <div className="text-[13px] italic text-[#D4AF57] font-medium mt-1">
                "What situation did the batter inherit?"
              </div>
              <p className="text-[#858585] mt-2.5 leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
                Evaluates the difficulty of the task: whether entering against a swinging new ball in the powerplay, facing a 12 RPO death-over mountain, or stepping into a 4-wicket collapse.
              </p>
            </div>
            <div className="pt-3 border-t border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#858585]">
              Sets the <strong className="text-[#D4AF57]">context leverage multiplier</strong> to scale execution rewards.
            </div>
          </div>

          <div className="bg-[#101010] p-6 rounded-xl border border-[#2D2D2D] flex flex-col justify-between space-y-4">
            <div>
              <div className="w-9 h-9 rounded-lg bg-[#161616] border border-[#D4AF57]/40 flex items-center justify-center text-[#D4AF57] mb-3">
                <Zap className="w-5 h-5" />
              </div>
              <h3 className="font-heading text-[16px] sm:text-[17px] font-bold text-[#F2F2F2]">2. Batting execution (P2)</h3>
              <div className="text-[13px] italic text-[#D4AF57] font-medium mt-1">
                "What did the batter personally do?"
              </div>
              <p className="text-[#858585] mt-2.5 leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
                Compares actual runs and strike rate against what an average T20 batter would produce in that specific scenario. Rewards run volume and boundaries while penalizing wasted deliveries.
              </p>
            </div>
            <div className="pt-3 border-t border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#858585]">
              Constitutes <strong className="text-[#D4AF57]">50% of the final score</strong>.
            </div>
          </div>

          <div className="bg-[#101010] p-6 rounded-xl border border-[#2D2D2D] flex flex-col justify-between space-y-4">
            <div>
              <div className="w-9 h-9 rounded-lg bg-[#161616] border border-[#2A4D30] flex items-center justify-center text-[#5A9E60] mb-3">
                <TrendingUp className="w-5 h-5" />
              </div>
              <h3 className="font-heading text-[16px] sm:text-[17px] font-bold text-[#F2F2F2]">3. Team-state impact (P3)</h3>
              <div className="text-[13px] italic text-[#5A9E60] font-medium mt-1">
                "Did the team's winning chances improve or decline?"
              </div>
              <p className="text-[#858585] mt-2.5 leading-relaxed text-[13.5px] sm:text-[14px] font-normal">
                Tracks the change in projected score (EFS in 1st innings) or required run rate (in chases) from the ball the batter walked in to the ball they walked off.
              </p>
            </div>
            <div className="pt-3 border-t border-[#2D2D2D] text-[12px] sm:text-[12.5px] text-[#858585]">
              Constitutes <strong className="text-[#5A9E60]">50% of the final score</strong>.
            </div>
          </div>
        </div>
      </div>

      {/* Understanding the Ratings You See */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-6">
        <div className="border-b border-[#2D2D2D] pb-3.5">
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide">
            Understanding the ratings you see
          </h2>
          <p className="text-[13.5px] sm:text-[14px] text-[#858585] mt-1 font-normal">
            The model produces several distinct metrics. They answer completely different questions, so they should not be interpreted as the same thing.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-[14px] sm:text-[14.5px] text-[#F2F2F2]">
          {/* Contribution Score */}
          <div className="bg-[#101010] p-5 sm:p-6 rounded-xl border border-[#2D2D2D] space-y-3 flex flex-col justify-between">
            <div>
              <div className="text-[12px] font-semibold text-[#D4AF57] tracking-wider uppercase">
                Single inning rating
              </div>
              <h3 className="font-heading text-[17px] sm:text-[18px] font-bold text-[#F2F2F2] mt-1">
                Contribution Score
              </h3>
              <div className="text-[13px] italic font-medium text-[#D4AF57] mt-1">
                "How much did this batter contribute in this particular batting opportunity?"
              </div>
              <p className="text-[#B8B8B8] mt-2.5 leading-relaxed text-[14px] sm:text-[14.5px] font-normal">
                The overall score for one batting opportunity. It combines Match Context (P1), Batting Execution (P2), Team-State Impact (P3), and Context Leverage.
              </p>
              <div className="mt-3.5 p-3 rounded-lg bg-[#161616] border border-[#2D2D2D] text-[12.5px] sm:text-[13px] text-[#858585] space-y-1.5 font-mono">
                <div>• <strong className="text-[#F2F2F2]">Around 50:</strong> Roughly par contribution</div>
                <div>• <strong className="text-[#5A9E60]">Above 50:</strong> Above-par contribution</div>
                <div>• <strong className="text-[#C25454]">Below 50:</strong> Below-par contribution</div>
              </div>
            </div>
            <p className="text-[12px] sm:text-[12.5px] text-[#858585] pt-3 border-t border-[#2D2D2D]">
              A high Contribution Score does not simply mean the batter scored many runs. The situation in which those runs were scored also matters.
            </p>
          </div>

          {/* Positive Contribution */}
          <div className="bg-[#101010] p-5 sm:p-6 rounded-xl border border-[#2D2D2D] space-y-3 flex flex-col justify-between">
            <div>
              <div className="text-[12px] font-semibold text-[#5A9E60] tracking-wider uppercase">
                Season volume accumulator
              </div>
              <h3 className="font-heading text-[17px] sm:text-[18px] font-bold text-[#F2F2F2] mt-1">
                Positive Contribution
              </h3>
              <div className="text-[13px] italic font-medium text-[#5A9E60] mt-1">
                "How much positive value did this batter provide?"
              </div>
              <p className="text-[#B8B8B8] mt-2.5 leading-relaxed text-[14px] sm:text-[14.5px] font-normal">
                Positive Contribution represents the positive portion of the player's underlying raw contribution. If the underlying contribution is positive, that value adds to the player's total. If negative, it contributes <strong className="text-[#F2F2F2]">0</strong>.
              </p>
              <div className="mt-3.5 p-3 rounded-lg bg-[#271414] border border-[#4D2626] text-[12px] sm:text-[12.5px] text-[#C25454] leading-relaxed">
                <strong>Important:</strong> Positive Contribution is <strong>NOT</strong> runs scored. A player with 500 positive contribution has not scored 500 runs. It is a model-based measure of positive batting contribution.
              </div>
            </div>
            <p className="text-[12px] sm:text-[12.5px] text-[#858585] pt-3 border-t border-[#2D2D2D]">
              Used primarily when aggregating season-level production and team-level volume.
            </p>
          </div>

          {/* Team Contribution Share */}
          <div className="bg-[#101010] p-5 sm:p-6 rounded-xl border border-[#2D2D2D] space-y-3 flex flex-col justify-between">
            <div>
              <div className="text-[12px] font-semibold text-[#D4AF57] tracking-wider uppercase">
                Team attribution share
              </div>
              <h3 className="font-heading text-[17px] sm:text-[18px] font-bold text-[#F2F2F2] mt-1">
                Team Contribution Share
              </h3>
              <div className="text-[13px] italic font-medium text-[#D4AF57] mt-1">
                "What share of the team's positive batting contribution came from this player?"
              </div>
              <p className="text-[#B8B8B8] mt-2.5 leading-relaxed text-[14px] sm:text-[14.5px] font-normal">
                Compares a player's positive contribution with the total positive contribution produced by the team's entire batting lineup.
              </p>
              <div className="mt-3.5 p-3 rounded-lg bg-[#161616] border border-[#2D2D2D] text-[12.5px] sm:text-[13px] text-[#858585] space-y-1 font-mono">
                <div>Player Positive Contrib: 80</div>
                <div>Team Total Positive: 400</div>
                <div className="text-[#D4AF57] font-bold">Team Share = (80 / 400) × 100 = 20%</div>
              </div>
            </div>
            <p className="text-[12px] sm:text-[12.5px] text-[#858585] pt-3 border-t border-[#2D2D2D]">
              It does <strong>NOT</strong> mean 20% of team runs, 20% of team wins, or 20% batting average. It is specifically a <strong>share of positive model contribution</strong>.
            </p>
          </div>

          {/* Raw Contribution (C_RAW) */}
          <div className="bg-[#101010] p-5 sm:p-6 rounded-xl border border-[#2D2D2D] space-y-3 flex flex-col justify-between">
            <div>
              <div className="text-[12px] font-semibold text-[#858585] tracking-wider uppercase">
                Underlying statistical engine
              </div>
              <h3 className="font-heading text-[17px] sm:text-[18px] font-bold text-[#F2F2F2] mt-1">
                Raw Contribution (C_RAW)
              </h3>
              <div className="text-[13px] italic font-medium text-[#858585] mt-1">
                "What was the player's underlying contribution before the final score presentation?"
              </div>
              <p className="text-[#B8B8B8] mt-2.5 leading-relaxed text-[14px] sm:text-[14.5px] font-normal">
                C_RAW is the underlying standardized value produced directly by the mathematical framework in z-space. It can be positive (above-par value added) or negative (below-par equity lost).
              </p>
              <div className="mt-3.5 p-3 rounded-lg bg-[#161616] border border-[#2D2D2D] text-[12.5px] sm:text-[13px] text-[#858585] space-y-1.5 font-mono">
                <div>• <strong className="text-[#5A9E60]">Positive C_RAW:</strong> Positive underlying contribution</div>
                <div>• <strong className="text-[#C25454]">Negative C_RAW:</strong> Negative underlying contribution</div>
              </div>
            </div>
            <p className="text-[12px] sm:text-[12.5px] text-[#858585] pt-3 border-t border-[#2D2D2D]">
              Positive Contribution is derived by taking <code className="font-mono text-[#D4AF57]">max(0, C_RAW)</code>.
            </p>
          </div>
        </div>

        {/* How These Metrics Relate (Hierarchy Banner) */}
        <div className="p-5 sm:p-6 bg-[#101010] rounded-xl border border-[#2D2D2D] space-y-3.5 text-[14px]">
          <div className="flex items-center gap-2.5">
            <span className="font-heading font-bold text-[#F2F2F2] tracking-wide text-[16px] sm:text-[17px]">
              How these metrics relate
            </span>
            <span className="text-[#858585] text-[13px] font-normal">— Three distinct levels</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5">
            <div className="bg-[#161616] p-4 rounded-lg border border-[#2D2D2D]">
              <span className="text-[12px] font-semibold text-[#D4AF57] tracking-wider uppercase block">Level 1: Opportunity</span>
              <div className="font-semibold text-[#F2F2F2] mt-1 text-[14px] sm:text-[15px]">Contribution Score</div>
              <p className="text-[12.5px] sm:text-[13px] text-[#858585] mt-1.5 leading-relaxed font-normal">How good was this particular batting opportunity?</p>
            </div>

            <div className="bg-[#161616] p-4 rounded-lg border border-[#2D2D2D]">
              <span className="text-[12px] font-semibold text-[#5A9E60] tracking-wider uppercase block">Level 2: Season Volume</span>
              <div className="font-semibold text-[#F2F2F2] mt-1 text-[14px] sm:text-[15px]">Positive Contribution</div>
              <p className="text-[12.5px] sm:text-[13px] text-[#858585] mt-1.5 leading-relaxed font-normal">How much positive underlying contribution did the player produce?</p>
            </div>

            <div className="bg-[#161616] p-4 rounded-lg border border-[#2D2D2D]">
              <span className="text-[12px] font-semibold text-[#B8B8B8] tracking-wider uppercase block">Level 3: Team Context</span>
              <div className="font-semibold text-[#F2F2F2] mt-1 text-[14px] sm:text-[15px]">Team Contribution Share</div>
              <p className="text-[12.5px] sm:text-[13px] text-[#858585] mt-1.5 leading-relaxed font-normal">How much of the team's total positive contribution came from this player?</p>
            </div>
          </div>

          <div className="text-[12.5px] sm:text-[13px] text-[#858585] pt-1.5">
            <strong>Key takeaway:</strong> They are related, but they are <strong className="text-[#F2F2F2]">not interchangeable</strong>.
          </div>
        </div>
      </div>

      {/* Real Player Case Study in Plain English */}
      <div className="bg-[#161616] rounded-xl p-6 sm:p-8 border border-[#2D2D2D] space-y-5">
        <div className="border-b border-[#2D2D2D] pb-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <h2 className="font-heading text-[21px] sm:text-[23px] font-bold text-[#F2F2F2] tracking-wide flex items-center gap-2.5">
            <Award className="w-5 h-5 text-[#D4AF57]" />
            Real player intuition: the 62 off 47 balls dilemma
          </h2>
          <span className="text-[12px] text-[#858585] bg-[#101010] px-3 py-1 rounded border border-[#2D2D2D] font-mono self-start sm:self-auto">
            Match #1082602 (Kohli vs. MI)
          </span>
        </div>

        <p className="text-[14px] sm:text-[15px] text-[#B8B8B8] leading-relaxed font-normal">
          Consider Virat Kohli's 62 off 47 balls (SR 131.9) against Mumbai Indians. A traditional scorecard sees a fine half-century. But why did the Contribution Model rate it <strong className="text-[#D4AF57] font-semibold font-mono">55.5</strong> (solid above-par, but not an elite 80+)?
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 text-[14px]">
          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2.5">
            <strong className="text-[#5A9E60] block font-semibold text-[15px]">The positive side: personal excellence</strong>
            <p className="text-[#858585] font-normal leading-relaxed text-[13.5px] sm:text-[14px]">
              Kohli entered in the first over and scored 32.3 runs more than situational baseline expectation. His individual batting execution scored an elite <strong className="text-[#F2F2F2] font-mono">P2 = 81.4</strong>. He anchored the top order and struck 5 boundaries and 2 sixes.
            </p>
          </div>

          <div className="bg-[#101010] p-5 rounded-lg border border-[#2D2D2D] space-y-2.5">
            <strong className="text-[#C25454] block font-semibold text-[15px]">The contextual reality: team stagnation</strong>
            <p className="text-[#858585] font-normal leading-relaxed text-[13.5px] sm:text-[14px]">
              Across the 15.3 overs he occupied the crease, Mumbai's bowlers successfully tied down the run rate (7.1 RPO). The team's projected final total fell from 169.7 to 158.6 (a loss of -11.0 runs in projection), resulting in a <strong className="text-[#F2F2F2] font-mono">P3 = 30.4</strong>.
            </p>
          </div>
        </div>

        <div className="p-5 bg-[#101010] rounded-lg border border-[#2D2D2D] text-[14px] text-[#F2F2F2] space-y-1.5">
          <strong className="text-[#D4AF57] block text-[15px] sm:text-[16px] font-semibold">The 50/50 synthesis:</strong>
          <p className="text-[#B8B8B8] text-[14px] sm:text-[14.5px] font-normal leading-relaxed">
            By balancing personal execution (79.1 adjusted) with team-state trajectory (31.8 adjusted), the model produced a final score of <strong className="text-[#D4AF57] font-semibold font-mono">55.5</strong>. It rewards his personal brilliance while recognizing that the match equity did not shift decisively into RCB's favor.
          </p>
        </div>
      </div>

      {/* Benchmark Reference */}
      <div className="bg-[#101010] rounded-xl p-5 sm:p-6 border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-center justify-between gap-4 text-xs sm:text-[13px]">
        <div className="flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-[#161616] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57] font-bold font-mono text-[15px]">
            50.0
          </div>
          <div>
            <div className="font-semibold text-[#F2F2F2] text-[14px]">Par benchmark = 50.0</div>
            <div className="text-[#858585] text-[13px]">A score of 50.0 represents exactly meeting situational T20 expectations.</div>
          </div>
        </div>
        <div className="flex items-center gap-4 text-[12px] sm:text-[12.5px] text-[#858585] font-medium font-mono">
          <span className="text-[#5A9E60]">&gt; 65.0: Match-winning</span>
          <span className="text-[#D4AF57]">&gt; 52.0: Above-par</span>
          <span className="text-[#858585]">&lt; 48.0: Below-par</span>
          <span className="text-[#C25454]">&lt; 35.0: Detrimental</span>
        </div>
      </div>
    </div>
  );
}
