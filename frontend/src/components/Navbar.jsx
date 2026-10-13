import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  Calendar,
  Trophy,
  GitCompare,
  Layers,
  Calculator,
  BookOpen,
  Menu,
  X,
} from 'lucide-react';
import CricImpactLogo from './CricImpactLogo';
import CompetitionSelector from './CompetitionSelector';
import FormatSelector from './FormatSelector';
import { useCompetition } from '../context/CompetitionContext';

export default function Navbar() {
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const { activeMeta } = useCompetition();

  const isCurrent = (path) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard' || location.pathname === '/analytics';
    }
    if (path === '/players') {
      return location.pathname === '/players' || location.pathname.startsWith('/player/');
    }
    if (path === '/matches') {
      return location.pathname === '/matches' || location.pathname.startsWith('/match/');
    }
    if (path === '/seasons') {
      return location.pathname === '/seasons';
    }
    if (path === '/compare') {
      return location.pathname.startsWith('/compare');
    }
    if (path === '/matchups') {
      return location.pathname === '/matchups' || location.pathname === '/batters-vs-bowling-type';
    }
    return location.pathname.startsWith(path);
  };

  const navLinks = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/players', label: 'Players', icon: Users },
    { to: '/matches', label: 'Matches', icon: Calendar },
    { to: '/seasons', label: 'Leaderboards', icon: Trophy },
    { to: '/compare', label: 'Compare', icon: GitCompare },
    { to: '/matchups', label: 'Matchups', icon: Layers },
    { to: '/methodology', label: 'Methodology', icon: Calculator },
    { to: '/about', label: 'About', icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#080808]/95 backdrop-blur-md border-b border-[#2D2D2D] w-full">
      <div className="w-[94%] max-w-[1850px] mx-auto px-2 sm:px-4 lg:px-6">
        <div className="flex items-center justify-between min-h-[76px] sm:min-h-[82px] py-2 sm:py-2.5 gap-4">
          {/* 1. Left: Official CricImpact Logo (150–190px desktop) */}
          <div className="flex items-center shrink-0">
            <CricImpactLogo linkTo="/" size="navbar" priority />
          </div>

          {/* 2. Center: Centered Desktop Horizontal Navigation (14–15px) */}
          <nav
            aria-label="Primary Navigation"
            className="hidden lg:flex items-center justify-center space-x-1 font-mono flex-1 px-2"
          >
            {navLinks.map(({ to, label, icon: Icon }) => {
              const active = isCurrent(to);
              return (
                <Link
                  key={to}
                  to={to}
                  className={`px-3.5 py-2 rounded-lg text-[14px] lg:text-[14.5px] font-medium transition-all duration-150 flex items-center gap-2 ${
                    active
                      ? 'bg-[#161616] text-[#D4AF57] border border-[#D4AF57]/40 shadow-xs font-semibold'
                      : 'text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#161616] border border-transparent'
                  }`}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon className={`w-4 h-4 ${active ? 'text-[#D4AF57]' : 'text-[#858585]'}`} />
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>

          {/* 3. Right: Contextual Primary Action (Competition Selector & Format Selector) */}
          <div className="hidden sm:flex items-center gap-2.5 lg:gap-3.5 shrink-0">
            <CompetitionSelector variant="select" className="shrink-0" />
            <FormatSelector className="shrink-0" />
          </div>

          {/* Mobile selectors & menu toggle button */}
          <div className="flex lg:hidden items-center gap-2">
            <div className="sm:hidden flex items-center gap-1.5">
              <CompetitionSelector variant="select" />
              <FormatSelector />
            </div>
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="h-10 w-10 sm:h-11 sm:w-11 flex items-center justify-center rounded-lg text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#161616] border border-[#2D2D2D] transition-colors"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
            >
              {mobileMenuOpen ? <X className="w-5 h-5 text-[#D4AF57]" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div className="lg:hidden border-t border-[#2D2D2D] bg-[#080808] px-4 pt-3 pb-5 space-y-2 font-mono shadow-2xl">
          <div className="pb-2 mb-2 border-b border-[#222222] flex items-center justify-between text-[13px] text-[#858585]">
            <span>Active Tournament</span>
            <span className="text-[#D4AF57] font-semibold">{activeMeta?.name || 'Indian Premier League'}</span>
          </div>

          <div className="grid grid-cols-2 gap-2">
            {navLinks.map(({ to, label, icon: Icon }) => {
              const active = isCurrent(to);
              return (
                <Link
                  key={to}
                  to={to}
                  onClick={() => setMobileMenuOpen(false)}
                  className={`px-3.5 py-2.5 rounded-lg text-[13.5px] flex items-center gap-2 transition-colors ${
                    active
                      ? 'bg-[#161616] text-[#D4AF57] font-semibold border border-[#D4AF57]/40'
                      : 'text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#161616] border border-transparent'
                  }`}
                  aria-current={active ? 'page' : undefined}
                >
                  <Icon className={`w-4 h-4 ${active ? 'text-[#D4AF57]' : 'text-[#858585]'}`} />
                  <span className="truncate">{label}</span>
                </Link>
              );
            })}
          </div>

          <div className="pt-2.5 mt-2.5 border-t border-[#222222] flex items-center justify-between text-[13px] text-[#858585]">
            <Link
              to="/audit"
              onClick={() => setMobileMenuOpen(false)}
              className="hover:text-[#D4AF57] transition-colors"
            >
              Model Validation & Audit →
            </Link>
            <div className="flex items-center gap-2">
              <span className="text-[12px] text-[#858585]">Format:</span>
              <FormatSelector />
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
