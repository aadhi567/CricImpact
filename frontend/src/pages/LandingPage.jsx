import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Trophy,
  Globe,
  ArrowRight,
  Compass,
  Zap,
  TrendingUp,
  Menu,
  X,
  Calculator,
  ChevronRight,
  Sparkles,
  Scale,
  Info,
} from 'lucide-react';
import { useCompetition } from '../context/CompetitionContext';
import { getMatchDetail } from '../services/api';
import CricImpactLogo from '../components/CricImpactLogo';

export default function LandingPage() {
  const navigate = useNavigate();
  const { setCompetition } = useCompetition();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [saiData, setSaiData] = useState(null);
  const [srkData, setSrkData] = useState(null);

  useEffect(() => {
    let isMounted = true;
    async function loadTelemetry() {
      try {
        const [sai, srk] = await Promise.all([
          getMatchDetail('1359536', 'B Sai Sudharsan'),
          getMatchDetail('1254065', 'M Shahrukh Khan'),
        ]);
        if (isMounted) {
          setSaiData(sai);
          setSrkData(srk);
        }
      } catch (err) {
        console.error('Failed to load canonical comparison telemetry:', err);
      }
    }
    loadTelemetry();
    return () => {
      isMounted = false;
    };
  }, []);

  const handleSelectCompetition = (compId) => {
    setCompetition(compId);
    navigate('/dashboard');
  };

  const scrollToSection = (id) => {
    setMobileMenuOpen(false);
    const element = document.getElementById(id);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="min-h-screen bg-[#080808] text-[#F2F2F2] font-ui selection:bg-[#D4AF57]/30 selection:text-[#F2F2F2] flex flex-col">
      {/* 1. Dedicated Landing Header (No Analytics Sidebar) */}
      <header className="sticky top-0 z-30 bg-[#080808]/90 backdrop-blur-md border-b border-[#2D2D2D] px-5 sm:px-8 lg:px-12 py-3 flex items-center justify-between">
        <CricImpactLogo linkTo="/" size="navbar" priority />

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-7 text-[13px] font-medium text-[#B8B8B8]">
          <Link to="/" className="text-[#F2F2F2] hover:text-[#D4AF57] transition-colors">
            Home
          </Link>
          <Link to="/dashboard" className="hover:text-[#F2F2F2] transition-colors">
            Explore Analytics
          </Link>
          <button
            type="button"
            onClick={() => scrollToSection('how-it-works')}
            className="hover:text-[#F2F2F2] transition-colors cursor-pointer"
          >
            How It Works
          </button>
          <Link to="/about" className="hover:text-[#F2F2F2] transition-colors">
            About
          </Link>
        </nav>

        {/* Primary CTA */}
        <div className="hidden md:flex items-center gap-3">
          <Link
            to="/dashboard"
            className="btn-gold text-[12px] py-1.5 px-4 shadow-sm"
          >
            <span>Open Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2 rounded-lg text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#161616] border border-[#2D2D2D] transition-colors"
          aria-label="Toggle Navigation Menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-[#101010] border-b border-[#2D2D2D] px-6 py-4 space-y-3 z-20">
          <Link
            to="/"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#F2F2F2] py-1.5"
          >
            Home
          </Link>
          <Link
            to="/dashboard"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5"
          >
            Explore Analytics
          </Link>
          <button
            type="button"
            onClick={() => scrollToSection('how-it-works')}
            className="block w-full text-left text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5"
          >
            How It Works
          </button>
          <Link
            to="/about"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5"
          >
            About
          </Link>
          <div className="pt-2 border-t border-[#222222]">
            <Link
              to="/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className="btn-gold w-full text-center py-2 text-[13px]"
            >
              Explore Analytics Workspace
            </Link>
          </div>
        </div>
      )}

      {/* 2. Hero Section */}
      <section className="relative pt-12 pb-16 sm:pt-20 sm:pb-24 px-5 sm:px-8 lg:px-12 max-w-6xl mx-auto w-full text-center flex flex-col items-center">
        {/* Subtle decorative glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[340px] sm:w-[500px] h-[260px] bg-[#D4AF57]/5 rounded-full blur-3xl pointer-events-none" />

        {/* Eyebrow Badge */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#161616] border border-[#2D2D2D] text-[#D4AF57] text-[11px] font-semibold uppercase tracking-wider mb-6 shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-[#D4AF57]" />
          <span>Contextual Batter Evaluation Framework</span>
        </div>

        {/* Main Headline */}
        <h1 className="font-heading text-[32px] sm:text-[44px] md:text-[52px] font-bold text-[#F2F2F2] tracking-tight leading-[1.15] max-w-4xl">
          Runs tell a story.{' '}
          <span className="text-[#D4AF57] block sm:inline">Context tells the truth.</span>
        </h1>

        {/* Supporting Description */}
        <p className="mt-5 text-[15px] sm:text-[17px] text-[#B8B8B8] max-w-2xl leading-relaxed font-normal">
          Discover how much a batter contributed to their team's performance by looking beyond runs and strike rate to the match situation, expectations, and impact.
        </p>

        {/* Call to Action Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center gap-3.5 w-full sm:w-auto">
          <Link
            to="/dashboard"
            className="btn-gold w-full sm:w-auto px-6 py-3 text-[14px] shadow-md"
          >
            <span>Explore Analytics</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <button
            type="button"
            onClick={() => scrollToSection('how-it-works')}
            className="btn-secondary w-full sm:w-auto px-6 py-3 text-[14px]"
          >
            <span>How It Works</span>
          </button>
        </div>

        {/* Contrast Visualizer Teaser: Beyond Runs and Strike Rate */}
        <div className="mt-14 w-full max-w-4xl bg-[#161616] border border-[#2D2D2D] rounded-xl p-5 sm:p-7 shadow-xl text-left">
          {/* Section Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-[#222222] gap-2">
            <div>
              <div className="flex items-center gap-2">
                <Scale className="w-4 h-4 text-[#D4AF57]" />
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold">
                  Beyond Runs and Strike Rate
                </span>
              </div>
              <h3 className="font-heading text-[18px] sm:text-[22px] font-bold text-[#F2F2F2] mt-0.5">
                Same Runs. Different Impact.
              </h3>
            </div>
            <span className="text-[11px] font-mono text-[#858585] bg-[#101010] px-2.5 py-1 rounded border border-[#2D2D2D] self-start sm:self-auto shrink-0">
              Verified IPL Telemetry
            </span>
          </div>

          <p className="text-[13px] sm:text-[14px] text-[#A3A3A3] mt-3 leading-relaxed">
            47 off 36 balls. Two very different match situations.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-5">
            {/* Example 1: B Sai Sudharsan */}
            <div className="bg-[#101010] p-5 rounded-xl border border-[#2D2D2D] hover:border-[#3D351E] transition-colors flex flex-col justify-between space-y-4">
              <div>
                {/* Header: Player Info & Impact Label */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <Link
                      to="/match/1359536/player/B%20Sai%20Sudharsan"
                      className="font-heading text-[16px] sm:text-[17px] font-bold text-[#F2F2F2] hover:text-[#D4AF57] transition-colors block"
                    >
                      {saiData?.player || 'B Sai Sudharsan'}
                    </Link>
                    <span className="text-[12px] text-[#858585] block mt-0.5">
                      {saiData?.team || 'Gujarat Titans'} • IPL {saiData?.season || '2023'}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded bg-[#1C180E] text-[#D4AF57] border border-[#3D351E] shrink-0 font-medium">
                    {saiData?.impact_label || 'High Match Impact'}
                  </span>
                </div>

                {/* Large final CricImpact score: Strongest element after player name */}
                <div className="mt-4 p-3.5 rounded-lg bg-[#141414] border border-[#222222] flex items-baseline justify-between">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-[#858585]">
                    CricImpact Score
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-mono text-[32px] sm:text-[36px] font-extrabold text-[#D4AF57] leading-none">
                      {saiData?.contribution_score !== undefined
                        ? saiData.contribution_score.toFixed(1)
                        : '93.4'}
                    </span>
                    <span className="text-[12px] font-mono text-[#858585]">/ 100</span>
                  </div>
                </div>

                {/* Concise Human-Readable Explanation (~15-20 words) */}
                <p className="mt-4 text-[13px] text-[#CCCCCC] leading-relaxed">
                  {saiData?.concise_summary ||
                    "Anchored a dominant 147-run stand after an early breakthrough, transforming Gujarat's innings into a match-winning total."}
                </p>
              </div>

              {/* View Match Breakdown Link */}
              <div className="pt-2 border-t border-[#1C1C1C]">
                <Link
                  to="/match/1359536/player/B%20Sai%20Sudharsan"
                  className="text-[12px] text-[#D4AF57] hover:text-[#E6C670] inline-flex items-center gap-1 font-medium transition-colors"
                >
                  <span>View match breakdown</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>

            {/* Example 2: M Shahrukh Khan */}
            <div className="bg-[#101010] p-5 rounded-xl border border-[#2D2D2D] hover:border-[#3D2818] transition-colors flex flex-col justify-between space-y-4">
              <div>
                {/* Header: Player Info & Impact Label */}
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <Link
                      to="/match/1254065/player/M%20Shahrukh%20Khan"
                      className="font-heading text-[16px] sm:text-[17px] font-bold text-[#F2F2F2] hover:text-[#D4AF57] transition-colors block"
                    >
                      {srkData?.player || 'M Shahrukh Khan'}
                    </Link>
                    <span className="text-[12px] text-[#858585] block mt-0.5">
                      {srkData?.team || 'Punjab Kings'} • IPL {srkData?.season || '2021'}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono uppercase tracking-wider px-2.5 py-1 rounded bg-[#211812] text-[#E5A869] border border-[#422A1D] shrink-0 font-medium">
                    {srkData?.impact_label || 'Crisis Stabilization'}
                  </span>
                </div>

                {/* Large final CricImpact score: Strongest element after player name */}
                <div className="mt-4 p-3.5 rounded-lg bg-[#141414] border border-[#222222] flex items-baseline justify-between">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-[#858585]">
                    CricImpact Score
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-mono text-[32px] sm:text-[36px] font-extrabold text-[#D4AF57] leading-none">
                      {srkData?.contribution_score !== undefined
                        ? srkData.contribution_score.toFixed(1)
                        : '53.6'}
                    </span>
                    <span className="text-[12px] font-mono text-[#858585]">/ 100</span>
                  </div>
                </div>

                {/* Concise Human-Readable Explanation (~15-20 words) */}
                <p className="mt-4 text-[13px] text-[#CCCCCC] leading-relaxed">
                  {srkData?.concise_summary ||
                    "Rescued Punjab from a 19/4 collapse, batting through 15 overs to push the total past 100 despite partners falling."}
                </p>
              </div>

              {/* View Match Breakdown Link */}
              <div className="pt-2 border-t border-[#1C1C1C]">
                <Link
                  to="/match/1254065/player/M%20Shahrukh%20Khan"
                  className="text-[12px] text-[#D4AF57] hover:text-[#E6C670] inline-flex items-center gap-1 font-medium transition-colors"
                >
                  <span>View match breakdown</span>
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </div>
          </div>

          {/* Short Takeaway Banner */}
          <div className="mt-5 p-3.5 sm:p-4 rounded-xl bg-[#101010] border border-[#262626] flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-[#161616] border border-[#2D2D2D] flex items-center justify-center shrink-0 text-[#D4AF57]">
              <Info className="w-3.5 h-3.5" />
            </div>
            <p className="text-[13px] text-[#B8B8B8] leading-relaxed">
              <strong className="text-[#D4AF57] font-semibold mr-1.5">Takeaway:</strong>
              Runs tell you what a batter scored. CricImpact evaluates how their innings mattered in context.
            </p>
          </div>
        </div>
      </section>

      {/* 3. Three Core Concepts Section */}
      <section className="py-14 sm:py-18 px-5 sm:px-8 lg:px-12 bg-[#0E0E0E] border-y border-[#202020]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center max-w-xl mx-auto mb-10">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-[#D4AF57]">
              The Analytical Framework
            </span>
            <h2 className="font-heading text-[24px] sm:text-[30px] font-bold text-[#F2F2F2] mt-1.5 tracking-tight">
              Three Pillars of Batter Equity
            </h2>
            <p className="text-[13px] text-[#858585] mt-2 leading-relaxed">
              Evaluating batting performance against situational baselines across every phase of the innings.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Concept 1 */}
            <div className="bg-[#161616] p-6 rounded-xl border border-[#2D2D2D] flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-[#1E190E] border border-[#3D351E] flex items-center justify-center text-[#D4AF57] mb-4">
                  <Compass className="w-5 h-5" />
                </div>
                <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2] tracking-tight">
                  1. Match Context
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-2 leading-relaxed">
                  Understand the situation a batter faced, including the innings phase (Powerplay, Middle, Death), match pressure, wickets down, and chase requirements.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#222222] text-[11px] font-mono text-[#858585]">
                Pillar 1: Base Context Pressure
              </div>
            </div>

            {/* Concept 2 */}
            <div className="bg-[#161616] p-6 rounded-xl border border-[#2D2D2D] flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-[#1E190E] border border-[#3D351E] flex items-center justify-center text-[#D4AF57] mb-4">
                  <TrendingUp className="w-5 h-5" />
                </div>
                <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2] tracking-tight">
                  2. Batting Performance
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-2 leading-relaxed">
                  Compare actual performance against what would reasonably be expected in that situation, benchmarking runs and strike rate against empirical baseline curves.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#222222] text-[11px] font-mono text-[#858585]">
                Pillar 2: Performance vs Expectation
              </div>
            </div>

            {/* Concept 3 */}
            <div className="bg-[#161616] p-6 rounded-xl border border-[#2D2D2D] flex flex-col justify-between">
              <div>
                <div className="w-10 h-10 rounded-lg bg-[#1E190E] border border-[#3D351E] flex items-center justify-center text-[#D4AF57] mb-4">
                  <Zap className="w-5 h-5" />
                </div>
                <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2] tracking-tight">
                  3. Team Impact
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-2 leading-relaxed">
                  Explore how a batter's performance contributed to the team's progress, measuring state transitions, match leverage, and clutch situational delivery.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#222222] text-[11px] font-mono text-[#858585]">
                Pillar 3: Match State Transition
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 4. Competition Selection Cards */}
      <section className="py-14 sm:py-20 px-5 sm:px-8 lg:px-12 max-w-5xl mx-auto w-full">
        <div className="text-center max-w-xl mx-auto mb-10">
          <span className="text-[11px] font-semibold uppercase tracking-widest text-[#D4AF57]">
            Available Datasets
          </span>
          <h2 className="font-heading text-[24px] sm:text-[30px] font-bold text-[#F2F2F2] mt-1.5 tracking-tight">
            Select Competition to Explore
          </h2>
          <p className="text-[13px] text-[#858585] mt-2 leading-relaxed">
            Choose from two isolated T20 tournaments with complete situational ball-by-ball analysis.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5 max-w-4xl mx-auto">
          {/* IPL Card */}
          <button
            type="button"
            onClick={() => handleSelectCompetition('ipl')}
            className="text-left bg-[#161616] hover:bg-[#1A1A1A] p-6 rounded-xl border border-[#2D2D2D] hover:border-[#D4AF57] transition-all group flex flex-col justify-between cursor-pointer"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#101010] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57] group-hover:scale-105 transition-transform">
                  <Trophy className="w-5 h-5" />
                </div>
                <span className="badge-gold">IPL</span>
              </div>
              <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] group-hover:text-[#D4AF57] transition-colors">
                Indian Premier League
              </h3>
              <p className="text-[13px] text-[#B8B8B8] mt-2 leading-relaxed">
                Complete historical ball-by-ball dataset covering 2008 to 2024 with 1,243 verified matches.
              </p>
            </div>
            <div className="mt-6 pt-3 border-t border-[#222222] flex items-center justify-between text-[12px] font-semibold text-[#D4AF57]">
              <span>Explore IPL Analytics</span>
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </button>

          {/* International T20I Card */}
          <button
            type="button"
            onClick={() => handleSelectCompetition('t20i')}
            className="text-left bg-[#161616] hover:bg-[#1A1A1A] p-6 rounded-xl border border-[#2D2D2D] hover:border-[#D4AF57] transition-all group flex flex-col justify-between cursor-pointer"
          >
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="w-10 h-10 rounded-lg bg-[#101010] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57] group-hover:scale-105 transition-transform">
                  <Globe className="w-5 h-5" />
                </div>
                <span className="badge-gold">T20I</span>
              </div>
              <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2] group-hover:text-[#D4AF57] transition-colors">
                International T20Is
              </h3>
              <p className="text-[13px] text-[#B8B8B8] mt-2 leading-relaxed">
                Global Men's International T20s from 2022 onwards, including ICC T20 World Cups, Asia Cups, and Bilateral series (2,264 matches).
              </p>
            </div>
            <div className="mt-6 pt-3 border-t border-[#222222] flex items-center justify-between text-[12px] font-semibold text-[#D4AF57]">
              <span>Explore T20I Analytics</span>
              <ChevronRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </div>
          </button>
        </div>
      </section>

      {/* 5. How It Works Section */}
      <section id="how-it-works" className="py-14 sm:py-20 px-5 sm:px-8 lg:px-12 bg-[#0E0E0E] border-t border-[#202020]">
        <div className="max-w-4xl mx-auto">
          <div className="text-center max-w-xl mx-auto mb-12">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-[#D4AF57]">
              Evaluation Pipeline
            </span>
            <h2 className="font-heading text-[24px] sm:text-[30px] font-bold text-[#F2F2F2] mt-1.5 tracking-tight">
              How the Contribution Score Works
            </h2>
            <p className="text-[13px] text-[#858585] mt-2 leading-relaxed">
              Every delivery in every innings is calibrated through a validated three-stage pipeline.
            </p>
          </div>

          <div className="space-y-4">
            {/* Step 1 */}
            <div className="bg-[#161616] p-5 sm:p-6 rounded-xl border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-[#1E190E] border border-[#3D351E] text-[#D4AF57] font-mono font-bold text-[13px] flex items-center justify-center shrink-0">
                1
              </div>
              <div className="flex-1">
                <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2]">
                  Understand the situation
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-1 leading-relaxed">
                  Identify the match conditions and the opportunity available to the batter: current run rate, required rate, wickets lost, pitch venue index, and phase of match (overs 1–6 powerplay, 7–15 middle, 16–20 death).
                </p>
              </div>
            </div>

            {/* Step 2 */}
            <div className="bg-[#161616] p-5 sm:p-6 rounded-xl border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-[#1E190E] border border-[#3D351E] text-[#D4AF57] font-mono font-bold text-[13px] flex items-center justify-center shrink-0">
                2
              </div>
              <div className="flex-1">
                <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2]">
                  Evaluate the performance
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-1 leading-relaxed">
                  Compare what happened with the expected performance for that situation. A batter who scores 35 runs when the situational expectation was 22 receives positive performance equity; a batter who consumes balls below par receives negative performance equity.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="bg-[#161616] p-5 sm:p-6 rounded-xl border border-[#2D2D2D] flex flex-col sm:flex-row sm:items-start gap-4">
              <div className="w-8 h-8 rounded-full bg-[#1E190E] border border-[#3D351E] text-[#D4AF57] font-mono font-bold text-[13px] flex items-center justify-center shrink-0">
                3
              </div>
              <div className="flex-1">
                <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2]">
                  Explore the contribution
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-1 leading-relaxed">
                  See the resulting contribution score bounded between 0.1 and 99.9 (where 50.0 represents situational par), alongside team contribution shares and match leverage shifts.
                </p>
              </div>
            </div>
          </div>

          <div className="mt-8 text-center">
            <Link
              to="/methodology"
              className="inline-flex items-center gap-2 text-[13px] font-semibold text-[#D4AF57] hover:text-[#E1C878] transition-colors"
            >
              <Calculator className="w-4 h-4" />
              <span>Read Full Mathematical Methodology & Formulas</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </section>

      {/* 6. Minimal Footer */}
      <footer className="mt-auto border-t border-[#2D2D2D] bg-[#080808] py-8 text-[12px] text-[#858585]">
        <div className="max-w-5xl mx-auto px-5 sm:px-8 lg:px-12 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-[#F2F2F2]">Cricket Contribution Analytics</span>
            <span>•</span>
            <span>Contextual Batter Evaluation</span>
          </div>

          <div className="flex items-center gap-5 text-[12px] font-medium text-[#B8B8B8]">
            <Link to="/about" className="hover:text-[#F2F2F2] transition-colors">
              About
            </Link>
            <Link to="/methodology" className="hover:text-[#F2F2F2] transition-colors">
              Methodology
            </Link>
            <Link to="/dashboard" className="text-[#D4AF57] hover:text-[#E1C878] transition-colors">
              Explore Analytics
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
