import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Home,
  LayoutDashboard,
  Users,
  TrendingUp,
  Calendar,
  Layers,
  GitCompare,
  ShieldCheck,
  Wind,
  Award,
  Trophy,
  BookOpen,
  Calculator,
  PanelLeftClose,
  PanelLeftOpen,
  X,
  BarChart3,
} from 'lucide-react';
import CompetitionSelector from './CompetitionSelector';
import { useCompetition } from '../context/CompetitionContext';

export default function Sidebar({
  isCollapsed = false,
  onToggleCollapse,
  mobileOpen = false,
  onCloseMobile,
}) {
  const location = useLocation();
  const { activeMeta } = useCompetition();

  // Navigation definition exactly matching Phase 7W requirements
  const navSections = [
    {
      title: 'MAIN MENU',
      items: [
        {
          to: '/',
          label: 'Home',
          tooltip: 'Return to landing overview',
          icon: Home,
          matcher: (path) => path === '/',
        },
        {
          to: '/dashboard',
          label: 'Dashboard',
          tooltip: 'Overall contribution overview',
          icon: LayoutDashboard,
          matcher: (path, hash) => (path === '/dashboard' || path === '/analytics') && !hash,
        },
        {
          to: '/players',
          label: 'Players',
          tooltip: 'Analyze individual players',
          icon: Users,
          matcher: (path) => path === '/players' || path.startsWith('/player/'),
        },
        {
          to: '/career',
          label: 'Career Graph',
          tooltip: 'Career batting & contribution graph',
          icon: TrendingUp,
          matcher: (path) => path.startsWith('/career'),
        },
        {
          to: '/matches',
          label: 'Matches',
          tooltip: 'Analyze every match',
          icon: Calendar,
          matcher: (path) => path.startsWith('/matches') || path.startsWith('/match/'),
        },
        {
          to: '/matchups',
          label: 'Matchups',
          tooltip: 'Batting vs pace and spin',
          icon: Layers,
          matcher: (path, _, search) =>
            (path === '/matchups' || path === '/batters-vs-bowling-type') &&
            !search.includes('pace') &&
            !search.includes('spin'),
        },
        {
          to: '/compare',
          label: 'Compare',
          tooltip: 'Compare players',
          icon: GitCompare,
          matcher: (path) => path.startsWith('/compare'),
        },
        {
          to: '/seasons',
          label: 'Seasons',
          tooltip: 'Season Top 10 contributors',
          icon: ShieldCheck,
          matcher: (path) => path === '/seasons' || path === '/audit',
        },
      ],
    },
    {
      title: 'ANALYTICS',
      items: [
        {
          to: '/matchups?tab=pace',
          label: 'Batters vs Pace/Spin',
          tooltip: 'Batters performance vs pace and spin',
          icon: Wind,
          matcher: (path, _, search) =>
            (path === '/matchups' || path === '/batters-vs-bowling-type') &&
            (search.includes('pace') || search.includes('spin')),
        },
        {
          to: '/players',
          label: 'Contribution Analysis',
          tooltip: 'Player contribution records',
          icon: Award,
          matcher: (path, hash) => (path === '/players' && !hash) || (path === '/dashboard' && hash === '#players-table'),
        },
        {
          to: '/seasons',
          label: 'Rankings',
          tooltip: 'Season Top 10 leaderboard',
          icon: Trophy,
          matcher: (path) => path === '/seasons',
        },
      ],
    },
    {
      title: 'LEARN',
      items: [
        {
          to: '/about',
          label: 'About',
          icon: BookOpen,
          matcher: (path) => path === '/about',
        },
        {
          to: '/methodology',
          label: 'Methodology',
          icon: Calculator,
          matcher: (path) => path === '/methodology',
        },
      ],
    },
  ];

  const checkActive = (item) => {
    return item.matcher(location.pathname, location.hash, location.search);
  };

  const renderNavContent = (isMobile = false) => {
    const collapsed = isMobile ? false : isCollapsed;

    return (
      <div className="flex flex-col h-full bg-[#080808]">
        {/* Brand Header Area */}
        {!collapsed ? (
          <div className="pt-4 pb-3.5 px-4 border-b border-[#2D2D2D] bg-[#080808]">
            <div className="flex items-center justify-between mb-2.5">
              <Link
                to="/dashboard"
                onClick={isMobile ? onCloseMobile : undefined}
                className="flex items-center gap-2 group"
                title="Cricket Contribution Analytics"
              >
                <div className="w-7 h-7 rounded-md bg-[#161616] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57] shrink-0 group-hover:border-[#D4AF57] transition-colors">
                  <BarChart3 className="w-4 h-4" />
                </div>
                <span className="text-[10.5px] font-['Inter',sans-serif] uppercase tracking-wider text-[#858585] font-medium">
                  Analytics Terminal
                </span>
              </Link>

              {isMobile ? (
                <button
                  type="button"
                  onClick={onCloseMobile}
                  className="p-1.5 rounded-md text-[#858585] hover:text-[#F2F2F2] hover:bg-[#161616] transition-colors"
                  aria-label="Close sidebar"
                >
                  <X className="w-4 h-4" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={onToggleCollapse}
                  className="p-1.5 rounded-md text-[#858585] hover:text-[#F2F2F2] hover:bg-[#161616] transition-colors cursor-pointer"
                  title="Collapse sidebar"
                  aria-label="Collapse sidebar"
                >
                  <PanelLeftClose className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Deliberate Two-Line Brand Title (Cinzel 14.5px / 700 / leading 1.15) */}
            <Link
              to="/dashboard"
              onClick={isMobile ? onCloseMobile : undefined}
              className="block group"
            >
              <div className="font-heading text-[14.5px] font-bold text-[#F2F2F2] tracking-wider leading-[1.18] whitespace-nowrap">
                CRICKET CONTRIBUTION
              </div>
              <div className="font-heading text-[14.5px] font-bold text-[#D4AF57] tracking-wider leading-[1.18] whitespace-nowrap">
                ANALYTICS
              </div>
              <div className="font-['Inter',sans-serif] text-[11px] text-[#858585] mt-1 font-normal leading-tight whitespace-nowrap">
                Contextual Batter Evaluation
              </div>
            </Link>

            {/* Quick Tournament Switcher */}
            <div className="mt-3 pt-2.5 border-t border-[#222222]">
              <div className="text-[10px] uppercase tracking-wider text-[#858585] font-semibold mb-1.5 flex items-center justify-between">
                <span>Tournament</span>
                <span className="text-[9px] text-[#D4AF57] font-bold">T20 ONLY</span>
              </div>
              <CompetitionSelector variant="pills" className="w-full justify-between" />
            </div>
          </div>
        ) : (
          <div className="py-3 flex flex-col items-center justify-center border-b border-[#2D2D2D] bg-[#080808] px-2 gap-1.5">
            <Link
              to="/dashboard"
              className="w-9 h-9 rounded-md bg-[#161616] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57] hover:border-[#D4AF57] transition-colors"
              title="Cricket Contribution Analytics — Contextual Batter Evaluation"
            >
              <BarChart3 className="w-4 h-4" />
            </Link>
            <span
              className="text-[9px] font-bold px-1 py-0.5 rounded bg-[#161616] text-[#D4AF57] border border-[#2D2D2D] tracking-wider"
              title={`Active: ${activeMeta?.name || 'IPL'}`}
            >
              {activeMeta?.badge || 'IPL'}
            </span>
          </div>
        )}

        {/* Collapsed expand toggle button */}
        {!isMobile && collapsed && (
          <div className="py-2 border-b border-[#2D2D2D] flex justify-center bg-[#080808]">
            <button
              type="button"
              onClick={onToggleCollapse}
              className="p-1.5 rounded-md text-[#858585] hover:text-[#F2F2F2] hover:bg-[#161616] transition-colors cursor-pointer"
              title="Expand sidebar"
              aria-label="Expand sidebar"
            >
              <PanelLeftOpen className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Navigation list */}
        <div className="flex-1 overflow-y-auto py-3 px-2.5 space-y-4">
          {navSections.map((section, sectionIdx) => (
            <div key={section.title} className={sectionIdx > 0 ? 'pt-1' : ''}>
              {!collapsed ? (
                <div className="px-3.5 pt-2 pb-1.5 text-[10.5px] font-['Inter',sans-serif] font-semibold text-[#858585] tracking-widest uppercase">
                  {section.title}
                </div>
              ) : (
                <div className="my-2 border-t border-[#222222] mx-1" />
              )}

              <div className="space-y-1">
                {section.items.map((item) => {
                  const Icon = item.icon;
                  const active = checkActive(item);

                  return (
                    <Link
                      key={item.label}
                      to={item.to}
                      onClick={isMobile ? onCloseMobile : undefined}
                      title={item.tooltip ? `${item.label} — ${item.tooltip}` : item.label}
                      className={`group relative flex items-center rounded-md text-[14px] font-['Inter',sans-serif] transition-colors duration-150 ${
                        collapsed
                          ? 'justify-center w-10 h-10 mx-auto'
                          : 'min-h-[42px] px-3.5 py-2.5 gap-3'
                      } ${
                        active
                          ? 'bg-[#161616] text-[#D4AF57] font-semibold'
                          : 'text-[#D0D0D0] hover:text-[#F2F2F2] hover:bg-[#161616] font-medium'
                      }`}
                    >
                      {/* Subtle Gold Vertical Active Indicator (2.5px wide on left) */}
                      {active && (
                        <span
                          className={`absolute left-0 bg-[#D4AF57] rounded-r-full ${
                            collapsed ? 'top-2 bottom-2 w-[3px]' : 'top-1.5 bottom-1.5 w-[3px]'
                          }`}
                          aria-hidden="true"
                        />
                      )}

                      <Icon
                        className={`w-[18px] h-[18px] shrink-0 transition-colors ${
                          active
                            ? 'text-[#D4AF57]'
                            : 'text-[#929292] group-hover:text-[#D4AF57]'
                        }`}
                      />
                      {!collapsed && (
                        <span className="whitespace-nowrap truncate tracking-normal">
                          {item.label}
                        </span>
                      )}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Sidebar footer status */}
        <div className="border-t border-[#2D2D2D] p-3.5 bg-[#080808]">
          {!collapsed ? (
            <div className="space-y-1">
              <div className="flex items-center gap-1.5 text-[11px] font-medium text-[#F2F2F2] font-['Inter',sans-serif]">
                <span className="w-1.5 h-1.5 rounded-full bg-[#5A9E60]" />
                <span>Phase 7 Validated Model</span>
              </div>
              <div className="text-[10.5px] font-normal text-[#858585] leading-tight font-['Inter',sans-serif]">
                Single Source of Truth: Python Backend
              </div>
            </div>
          ) : (
            <div className="flex justify-center" title="Phase 7 Validated Model • Single Source of Truth">
              <span className="w-2 h-2 rounded-full bg-[#5A9E60]" />
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      {/* 1. Desktop Permanent Sidebar (252px expanded / 68px collapsed) */}
      <aside
        className={`hidden md:block sticky top-0 h-screen overflow-hidden bg-[#080808] border-r border-[#2D2D2D] shrink-0 z-30 transition-all duration-200 ease-in-out ${
          isCollapsed ? 'w-[68px] min-w-[68px]' : 'w-[252px] min-w-[252px]'
        }`}
      >
        {renderNavContent(false)}
      </aside>

      {/* 2. Mobile Slide-out Drawer */}
      {mobileOpen && (
        <div className="md:hidden">
          {/* Backdrop overlay */}
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-xs z-40 transition-opacity"
            onClick={onCloseMobile}
            aria-hidden="true"
          />

          {/* Slide-out drawer */}
          <div className="fixed inset-y-0 left-0 w-[260px] max-w-[85vw] bg-[#080808] border-r border-[#2D2D2D] z-50 flex flex-col shadow-2xl animate-in slide-in-from-left duration-200">
            {renderNavContent(true)}
          </div>
        </div>
      )}
    </>
  );
}
