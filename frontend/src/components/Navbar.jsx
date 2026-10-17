import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  MapPin,
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

  // Close mobile drawer on Escape key press
  useEffect(() => {
    if (!mobileMenuOpen) return;
    function handleKeyDown(e) {
      if (e.key === 'Escape') {
        setMobileMenuOpen(false);
      }
    }
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [mobileMenuOpen]);

  // Auto-close mobile drawer if viewport expands to desktop (>= 1280px)
  useEffect(() => {
    if (!mobileMenuOpen) return;
    function handleResize() {
      if (window.innerWidth >= 1280) {
        setMobileMenuOpen(false);
      }
    }
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [mobileMenuOpen]);

  const isCurrent = (path) => {
    if (path === '/dashboard') {
      return location.pathname === '/dashboard' || location.pathname === '/analytics';
    }
    if (path === '/players') {
      return location.pathname === '/players' || location.pathname.startsWith('/player/');
    }
    if (path === '/career') {
      return location.pathname === '/career' || location.pathname.startsWith('/career');
    }
    if (path === '/ground-analysis') {
      return location.pathname === '/ground-analysis' || location.pathname.startsWith('/venues');
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
    { to: '/dashboard', label: 'Dashboard' },
    { to: '/players', label: 'Players' },
    { to: '/career', label: 'Career Graph' },
    { to: '/ground-analysis', label: 'Grounds', icon: MapPin },
    { to: '/matches', label: 'Matches' },
    { to: '/seasons', label: 'Leaderboards' },
    { to: '/compare', label: 'Compare' },
    { to: '/matchups', label: 'Matchups' },
    { to: '/methodology', label: 'Methodology' },
    { to: '/about', label: 'About' },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#080808]/95 backdrop-blur-md border-b border-[#2D2D2D] w-full">
      <div className="w-[96%] 2xl:w-[94%] max-w-[1850px] mx-auto px-2 sm:px-3 xl:px-4 2xl:px-6">
        <div className="flex items-center min-h-[58px] sm:min-h-[64px] 2xl:min-h-[70px] py-1.5 gap-2 xl:gap-2.5 2xl:gap-4">
          {/* 1. Left: Official CricImpact Logo on extreme left */}
          <div className="flex items-center shrink-0">
            <CricImpactLogo linkTo="/" size="navbar" priority />
          </div>

          {/* 2. Desktop Navigation: Left-aligned with intelligent compact spacing on intermediate desktop */}
          <nav
            aria-label="Primary Navigation"
            className="hidden xl:flex items-center gap-0.5 xl:gap-1 2xl:gap-1.5 ml-1.5 xl:ml-2.5 2xl:ml-5 font-sans min-w-0"
          >
            {navLinks.map(({ to, label, icon: Icon }) => {
              const active = isCurrent(to);
              return (
                <Link
                  key={to}
                  to={to}
                  className={`px-1.5 xl:px-2 2xl:px-3 py-1 2xl:py-1.5 rounded-lg text-[12px] xl:text-[12.5px] 2xl:text-[13.5px] font-medium transition-all duration-150 flex items-center gap-1 xl:gap-1.5 whitespace-nowrap shrink-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF57] ${
                    active
                      ? 'bg-[#141414] text-[#D4AF57] border border-[#D4AF57]/40 font-semibold shadow-xs'
                      : 'text-[#A3A3A3] hover:text-[#F2F2F2] hover:bg-[#141414]/70 border border-transparent'
                  }`}
                  aria-current={active ? 'page' : undefined}
                >
                  {Icon && <Icon className="w-3 h-3 2xl:w-3.5 2xl:h-3.5 text-[#D4AF57] shrink-0" />}
                  <span>{label}</span>
                </Link>
              );
            })}
          </nav>

          {/* 3. Far Right: Competition & Format Selectors (Desktop) */}
          <div className="hidden xl:flex items-center gap-1.5 xl:gap-2 2xl:gap-3 shrink-0 ml-auto">
            <CompetitionSelector variant="select" className="shrink-0" />
            <FormatSelector className="shrink-0" />
          </div>

          {/* 4. Responsive Controls (< xl) */}
          <div className="flex xl:hidden items-center gap-1.5 sm:gap-2 ml-auto shrink-0">
            <CompetitionSelector variant="select" className="shrink-0" />
            <div className="hidden sm:flex items-center shrink-0">
              <FormatSelector className="shrink-0" />
            </div>
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="h-9 w-9 sm:h-10 sm:w-10 flex items-center justify-center rounded-lg text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#161616] border border-[#2D2D2D] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF57] cursor-pointer shrink-0"
              aria-label="Toggle navigation menu"
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-nav-drawer"
            >
              {mobileMenuOpen ? <X className="w-5 h-5 text-[#D4AF57]" /> : <Menu className="w-5 h-5" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div
          id="mobile-nav-drawer"
          className="xl:hidden border-t border-[#2D2D2D] bg-[#080808]/98 backdrop-blur-md px-4 pt-3 pb-5 space-y-2.5 font-sans shadow-2xl"
        >
          <div className="pb-2 mb-1 border-b border-[#222222] flex items-center justify-between text-[12.5px] text-[#858585]">
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
                  className={`px-3 py-2 sm:py-2.5 rounded-lg text-[13px] sm:text-[13.5px] flex items-center gap-2 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF57] ${
                    active
                      ? 'bg-[#141414] text-[#D4AF57] font-semibold border border-[#D4AF57]/40 shadow-xs'
                      : 'text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#141414] border border-transparent'
                  }`}
                  aria-current={active ? 'page' : undefined}
                >
                  {Icon && <Icon className="w-4 h-4 text-[#D4AF57] shrink-0" />}
                  <span className="truncate">{label}</span>
                </Link>
              );
            })}
          </div>

          <div className="pt-2.5 mt-2 border-t border-[#222222] flex items-center justify-between text-[12.5px] text-[#858585]">
            <Link
              to="/audit"
              onClick={() => setMobileMenuOpen(false)}
              className="hover:text-[#D4AF57] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-[#D4AF57]"
            >
              Model Validation & Audit →
            </Link>
            <div className="flex sm:hidden items-center gap-2">
              <span className="text-[12px] text-[#858585]">Format:</span>
              <FormatSelector />
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
