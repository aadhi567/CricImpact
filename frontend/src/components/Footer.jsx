import React from 'react';
import { Link } from 'react-router-dom';
import { Mail } from 'lucide-react';
import CricImpactLogo from './CricImpactLogo';
import { useCompetition } from '../context/CompetitionContext';

/**
 * Reusable Footer component for CricImpact.
 * Matches the Gold & Onyx design system (Raw Carbon #080808 background, subtle borders, gold accents).
 * Remains in normal document flow (pinned to bottom of short viewports via flex-1 parent, rendered after content on long pages).
 */
export default function Footer() {
  const { activeMeta } = useCompetition();

  return (
    <footer className="border-t border-[#202020] bg-[#080808] text-[#858585] text-xs mt-auto font-ui w-full">
      <div className="w-full max-w-[1850px] mx-auto px-3 sm:px-4 lg:px-6 py-8 sm:py-12">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 lg:gap-12 pb-8 border-b border-[#1C1C1C]">
          {/* Brand & Description Column */}
          <div className="md:col-span-4 lg:col-span-4 space-y-3">
            <div className="flex items-center gap-3">
              <CricImpactLogo linkTo="/" size="sm" />
              <span className="font-semibold text-[15px] text-[#F2F2F2] tracking-tight">
                CricImpact
              </span>
            </div>
            <p className="text-[13px] font-medium text-[#D4AF57]">
              Cricket Contribution Analytics
            </p>
            <p className="text-[12.5px] text-[#858585] leading-relaxed max-w-sm">
              Contextual batter evaluation engine for T20 cricket. Quantifying player impact through situational equity and leverage rather than traditional box-score metrics.
            </p>
          </div>

          {/* Navigation Columns */}
          <div className="md:col-span-5 lg:col-span-5 grid grid-cols-2 sm:grid-cols-3 gap-6 text-[12.5px]">
            <div className="space-y-2.5">
              <span className="font-semibold text-[#F2F2F2] uppercase tracking-wider text-[11px] block">
                Workspaces
              </span>
              <ul className="space-y-2">
                <li>
                  <Link to="/dashboard" className="hover:text-[#D4AF57] transition-colors">
                    Dashboard
                  </Link>
                </li>
                <li>
                  <Link to="/seasons" className="hover:text-[#D4AF57] transition-colors">
                    Leaderboards
                  </Link>
                </li>
                <li>
                  <Link to="/players" className="hover:text-[#D4AF57] transition-colors">
                    Players Pool
                  </Link>
                </li>
                <li>
                  <Link to="/compare" className="hover:text-[#D4AF57] transition-colors">
                    Compare
                  </Link>
                </li>
              </ul>
            </div>

            <div className="space-y-2.5">
              <span className="font-semibold text-[#F2F2F2] uppercase tracking-wider text-[11px] block">
                Deep Dives
              </span>
              <ul className="space-y-2">
                <li>
                  <Link to="/career" className="hover:text-[#D4AF57] transition-colors">
                    Career Graph
                  </Link>
                </li>
                <li>
                  <Link to="/ground-analysis" className="hover:text-[#D4AF57] transition-colors">
                    Grounds
                  </Link>
                </li>
                <li>
                  <Link to="/matchups" className="hover:text-[#D4AF57] transition-colors">
                    Matchups
                  </Link>
                </li>
                <li>
                  <Link to="/matches" className="hover:text-[#D4AF57] transition-colors">
                    Match Logs
                  </Link>
                </li>
              </ul>
            </div>

            <div className="space-y-2.5">
              <span className="font-semibold text-[#F2F2F2] uppercase tracking-wider text-[11px] block">
                Research
              </span>
              <ul className="space-y-2">
                <li>
                  <Link to="/methodology" className="hover:text-[#D4AF57] transition-colors">
                    Methodology
                  </Link>
                </li>
                <li>
                  <Link to="/about" className="hover:text-[#D4AF57] transition-colors">
                    About
                  </Link>
                </li>
                <li>
                  <Link to="/audit" className="hover:text-[#D4AF57] transition-colors">
                    Audit Insights
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          {/* Developer & Contact Column */}
          <div className="md:col-span-3 lg:col-span-3 space-y-3">
            <span className="font-semibold text-[#F2F2F2] uppercase tracking-wider text-[11px] block">
              Developer & Contact
            </span>
            <div className="space-y-2.5 text-[12.5px]">
              <p className="text-[#B8B8B8]">
                Developed by{' '}
                <span className="text-[#F2F2F2] font-medium">Aadhithan B</span>
              </p>
              <div className="pt-0.5">
                <a
                  href="mailto:aadhithanb5@gmail.com"
                  className="inline-flex items-center gap-2 text-[#D4AF57] hover:text-[#E1C878] transition-colors py-1 focus:outline-none focus-visible:ring-1 focus-visible:ring-[#D4AF57] rounded"
                  aria-label="Contact developer via email at aadhithanb5@gmail.com"
                >
                  <Mail className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
                  <span className="underline decoration-[#D4AF57]/40 hover:decoration-[#E1C878] underline-offset-2 font-medium">
                    aadhithanb5@gmail.com
                  </span>
                </a>
              </div>
            </div>
          </div>
        </div>

        {/* Sub-footer Bar with Copyright and Engine Status */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-[12px] text-[#707070] text-center sm:text-left">
          <div>
            © 2026 CricImpact. All rights reserved.
          </div>
          <div className="flex flex-wrap items-center justify-center sm:justify-end gap-1.5 sm:gap-2 text-[11px] sm:text-[11.5px] font-mono text-[#858585]">
            <span className="break-words">Active Scoring Engine: Strategy 4 Hybrid (Single Source of Truth)</span>
            {activeMeta?.name && (
              <span className="hidden sm:inline-block px-1.5 py-0.5 rounded bg-[#161616] border border-[#262626] text-[#A8893D] text-[10.5px]">
                {activeMeta.name}
              </span>
            )}
          </div>
        </div>
      </div>
    </footer>
  );
}
