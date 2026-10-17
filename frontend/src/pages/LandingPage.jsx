import React, { useState, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
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
  Users,
  MapPin,
  ShieldCheck,
  Layers,
  Activity,
  BarChart3,
  Calendar,
} from 'lucide-react';
import { useCompetition } from '../context/CompetitionContext';
import { getMatchDetail } from '../services/api';
import CricImpactLogo from '../components/CricImpactLogo';
import Footer from '../components/Footer';

export default function LandingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setCompetition } = useCompetition();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [saiData, setSaiData] = useState(null);
  const [srkData, setSrkData] = useState(null);

  // Automatically scroll to anchor when navigating from inner routes (e.g. /#features or /#how-it-works)
  useEffect(() => {
    if (location.hash) {
      const id = location.hash.replace('#', '');
      const timer = setTimeout(() => {
        const element = document.getElementById(id);
        if (element) {
          element.scrollIntoView({ behavior: 'smooth' });
        }
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [location.hash]);

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
        console.warn('Live telemetry unavailable, using verified fallback data:', err?.message || err);
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
      {/* 1. Dedicated Landing Header */}
      <header className="sticky top-0 z-30 bg-[#080808]/90 backdrop-blur-md border-b border-[#2D2D2D] px-5 sm:px-8 lg:px-12 py-3.5 flex items-center justify-between">
        <CricImpactLogo linkTo="/" size="navbar" priority />

        {/* Desktop Navigation */}
        <nav className="hidden lg:flex items-center gap-6 text-[13px] font-medium text-[#B8B8B8]">
          <Link to="/" className="text-[#F2F2F2] hover:text-[#D4AF57] transition-colors">
            Home
          </Link>
          <Link to="/dashboard" className="hover:text-[#F2F2F2] transition-colors">
            Explore Analytics
          </Link>
          <Link to="/career" className="hover:text-[#F2F2F2] transition-colors">
            Career Graph
          </Link>
          <Link to="/compare" className="hover:text-[#F2F2F2] transition-colors">
            Player Comparison
          </Link>
          <Link to="/ground-analysis" className="hover:text-[#F2F2F2] transition-colors">
            Ground Analysis
          </Link>
          <button
            type="button"
            onClick={() => scrollToSection('features')}
            className="hover:text-[#F2F2F2] transition-colors cursor-pointer"
          >
            Features
          </button>
          <Link to="/about" className="hover:text-[#F2F2F2] transition-colors">
            About
          </Link>
          <Link to="/methodology" className="hover:text-[#F2F2F2] transition-colors">
            Methodology
          </Link>
        </nav>

        {/* Primary CTA */}
        <div className="hidden lg:flex items-center gap-3">
          <Link
            to="/dashboard"
            className="btn-gold text-[12.5px] py-1.5 px-4 shadow-sm inline-flex items-center gap-1.5"
          >
            <span>Open Workspace</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {/* Mobile Hamburger Toggle */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="lg:hidden p-2 rounded-lg text-[#B8B8B8] hover:text-[#F2F2F2] hover:bg-[#161616] border border-[#2D2D2D] transition-colors cursor-pointer"
          aria-label="Toggle Navigation Menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </header>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="lg:hidden bg-[#101010] border-b border-[#2D2D2D] px-6 py-4 space-y-2.5 z-20">
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
          <Link
            to="/career"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5"
          >
            Career Graph
          </Link>
          <Link
            to="/compare"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5"
          >
            Player Comparison
          </Link>
          <Link
            to="/ground-analysis"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5"
          >
            Ground Analysis
          </Link>
          <button
            type="button"
            onClick={() => scrollToSection('features')}
            className="block w-full text-left text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5 cursor-pointer"
          >
            Features
          </button>
          <Link
            to="/about"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5"
          >
            About
          </Link>
          <Link
            to="/methodology"
            onClick={() => setMobileMenuOpen(false)}
            className="block text-[14px] font-medium text-[#B8B8B8] hover:text-[#F2F2F2] py-1.5"
          >
            Methodology
          </Link>
          <div className="pt-2 border-t border-[#222222] flex flex-col gap-2">
            <Link
              to="/dashboard"
              onClick={() => setMobileMenuOpen(false)}
              className="btn-gold w-full text-center py-2 text-[13px]"
            >
              Explore Analytics Workspace
            </Link>
            <Link
              to="/compare"
              onClick={() => setMobileMenuOpen(false)}
              className="btn-secondary w-full text-center py-2 text-[13px]"
            >
              Compare Players
            </Link>
          </div>
        </div>
      )}

      {/* 2. Hero Section */}
      <section className="relative pt-12 pb-16 sm:pt-20 sm:pb-24 px-5 sm:px-8 lg:px-12 max-w-6xl mx-auto w-full text-center flex flex-col items-center">
        {/* Subtle decorative glow */}
        <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[340px] sm:w-[500px] h-[260px] bg-[#D4AF57]/5 rounded-full blur-3xl pointer-events-none" />

        {/* Eyebrow Badge */}
        <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#161616] border border-[#2D2D2D] text-[#D4AF57] text-[11px] font-semibold uppercase tracking-wider mb-6 shadow-xs">
          <Sparkles className="w-3.5 h-3.5 text-[#D4AF57]" />
          <span>Contextual Batter Evaluation Framework</span>
        </div>

        {/* Main Headline */}
        <h1 className="font-heading text-[32px] sm:text-[46px] md:text-[54px] font-bold text-[#F2F2F2] tracking-tight leading-[1.15] max-w-4xl">
          Measure the Impact.{' '}
          <span className="text-[#D4AF57] block sm:inline">Understand the Game.</span>
        </h1>

        {/* Supporting Description */}
        <p className="mt-5 text-[15px] sm:text-[17px] text-[#B8B8B8] max-w-3xl leading-relaxed font-normal">
          CricImpact goes beyond traditional scorecards to evaluate batting contribution in match context. Explore player careers, compare performances and discover ground-level insights across IPL and international T20 cricket.
        </p>

        {/* Call to Action Buttons */}
        <div className="mt-8 flex flex-col sm:flex-row items-center gap-3.5 w-full sm:w-auto">
          <Link
            to="/dashboard"
            className="btn-gold w-full sm:w-auto px-7 py-3 text-[14px] shadow-md flex items-center justify-center gap-2"
          >
            <span>Explore Analytics</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <Link
            to="/compare"
            className="btn-secondary w-full sm:w-auto px-7 py-3 text-[14px] flex items-center justify-center gap-2"
          >
            <span>Compare Players</span>
            <Users className="w-4 h-4 text-[#D4AF57]" />
          </Link>
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
            47 runs off 36 balls. Two very different match situations, evaluated through situational context and team leverage.
          </p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-5">
            {/* Example 1: B Sai Sudharsan */}
            <div className="bg-[#101010] p-5 rounded-xl border border-[#2D2D2D] hover:border-[#3D351E] transition-colors flex flex-col justify-between space-y-4">
              <div>
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

                <p className="mt-4 text-[13px] text-[#CCCCCC] leading-relaxed">
                  {saiData?.concise_summary ||
                    "Anchored a dominant 147-run stand after an early breakthrough, transforming Gujarat's innings into a match-winning total."}
                </p>
              </div>

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

                <div className="mt-4 p-3.5 rounded-lg bg-[#141414] border border-[#222222] flex items-baseline justify-between">
                  <span className="text-[11px] font-mono uppercase tracking-wider text-[#858585]">
                    CricImpact Score
                  </span>
                  <div className="flex items-baseline gap-1">
                    <span className="font-mono text-[32px] sm:text-[36px] font-extrabold text-[#D4AF57] leading-none">
                      {srkData?.contribution_score !== undefined
                        ? srkData.contribution_score.toFixed(1)
                        : '63.7'}
                    </span>
                    <span className="text-[12px] font-mono text-[#858585]">/ 100</span>
                  </div>
                </div>

                <p className="mt-4 text-[13px] text-[#CCCCCC] leading-relaxed">
                  {srkData?.concise_summary ||
                    "Rescued Punjab from a 19/4 collapse, batting through 15 overs to push the total past 100 despite partners falling."}
                </p>
              </div>

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

          {/* Takeaway Banner */}
          <div className="mt-5 p-3.5 sm:p-4 rounded-xl bg-[#101010] border border-[#262626] flex items-center gap-3">
            <div className="w-7 h-7 rounded-lg bg-[#161616] border border-[#2D2D2D] flex items-center justify-center shrink-0 text-[#D4AF57]">
              <Info className="w-3.5 h-3.5" />
            </div>
            <p className="text-[13px] text-[#B8B8B8] leading-relaxed">
              <strong className="text-[#D4AF57] font-semibold mr-1.5">Takeaway:</strong>
              Runs indicate raw output. CricImpact evaluates how each innings altered match equity relative to expectations.
            </p>
          </div>
        </div>
      </section>

      {/* 3. Four Feature Sections */}
      <div id="features" className="space-y-16 sm:space-y-24 py-12 sm:py-16">
        {/* Feature A: Cricket Contribution Analytics */}
        <section className="px-5 sm:px-8 lg:px-12 max-w-6xl mx-auto w-full">
          <div className="bg-[#121212] border border-[#2D2D2D] rounded-2xl p-6 sm:p-9 shadow-xl space-y-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#222222] pb-6">
              <div>
                <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold mb-1">
                  <Activity className="w-4 h-4" />
                  <span>CORE ANALYTICAL ENGINE</span>
                </div>
                <h2 className="font-heading text-[24px] sm:text-[30px] font-bold text-[#F2F2F2] tracking-tight">
                  Cricket Contribution Analytics
                </h2>
                <p className="text-[14px] sm:text-[15px] text-[#A3A3A3] mt-2 max-w-2xl leading-relaxed">
                  CricImpact evaluates batting performance relative to expected baseline curves and match situations, rather than simply rewarding high run totals or strike rates without context.
                </p>
              </div>
              <Link
                to="/methodology"
                className="btn-secondary text-[12.5px] py-2 px-4 self-start md:self-auto shrink-0 inline-flex items-center gap-1.5"
              >
                <span>Read Full Methodology</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              {/* Pillar 1 */}
              <div className="bg-[#161616] p-5 sm:p-6 rounded-xl border border-[#262626] flex flex-col justify-between">
                <div>
                  <div className="w-10 h-10 rounded-lg bg-[#1E190E] border border-[#3D351E] flex items-center justify-center text-[#D4AF57] mb-4">
                    <Compass className="w-5 h-5" />
                  </div>
                  <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2]">
                    1. Match Context (P1)
                  </h3>
                  <div className="text-[12px] italic text-[#D4AF57] font-medium mt-0.5">
                    "What situation did the batter inherit?"
                  </div>
                  <p className="text-[13px] text-[#A3A3A3] mt-2.5 leading-relaxed">
                    Evaluates situational leverage and pressure: entry phase (Powerplay, Middle, Death), wickets lost, required run rate, and pitch conditions.
                  </p>
                </div>
                <div className="mt-5 pt-3 border-t border-[#222222] text-[11px] font-mono text-[#858585]">
                  Scales leverage multiplier [0.65, 1.35]
                </div>
              </div>

              {/* Pillar 2 */}
              <div className="bg-[#161616] p-5 sm:p-6 rounded-xl border border-[#262626] flex flex-col justify-between">
                <div>
                  <div className="w-10 h-10 rounded-lg bg-[#1E190E] border border-[#3D351E] flex items-center justify-center text-[#D4AF57] mb-4">
                    <Zap className="w-5 h-5" />
                  </div>
                  <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2]">
                    2. Batting Execution (P2)
                  </h3>
                  <div className="text-[12px] italic text-[#D4AF57] font-medium mt-0.5">
                    "What did the batter personally produce?"
                  </div>
                  <p className="text-[13px] text-[#A3A3A3] mt-2.5 leading-relaxed">
                    Benchmarks individual runs and strike rate against empirical baseline curves calibrated for that exact phase and wicket state.
                  </p>
                </div>
                <div className="mt-5 pt-3 border-t border-[#222222] text-[11px] font-mono text-[#858585]">
                  50% Weight of Final Evaluation
                </div>
              </div>

              {/* Pillar 3 */}
              <div className="bg-[#161616] p-5 sm:p-6 rounded-xl border border-[#262626] flex flex-col justify-between">
                <div>
                  <div className="w-10 h-10 rounded-lg bg-[#152718] border border-[#2A4D30] flex items-center justify-center text-[#5A9E60] mb-4">
                    <TrendingUp className="w-5 h-5" />
                  </div>
                  <h3 className="font-heading text-[16px] font-bold text-[#F2F2F2]">
                    3. Team-State Impact (P3)
                  </h3>
                  <div className="text-[12px] italic text-[#5A9E60] font-medium mt-0.5">
                    "Did winning chances improve or decline?"
                  </div>
                  <p className="text-[13px] text-[#A3A3A3] mt-2.5 leading-relaxed">
                    Tracks the change in projected score (1st innings) or required rate (chases) from the delivery the batter arrived to the delivery they departed.
                  </p>
                </div>
                <div className="mt-5 pt-3 border-t border-[#222222] text-[11px] font-mono text-[#858585]">
                  50% Weight of Final Evaluation
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Feature B: Career Graph */}
        <section className="px-5 sm:px-8 lg:px-12 max-w-6xl mx-auto w-full">
          <div className="bg-[#121212] border border-[#2D2D2D] rounded-2xl p-6 sm:p-9 shadow-xl space-y-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#222222] pb-6">
              <div>
                <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold mb-1">
                  <TrendingUp className="w-4 h-4" />
                  <span>LONGITUDINAL VISUALIZATION</span>
                </div>
                <h2 className="font-heading text-[24px] sm:text-[30px] font-bold text-[#F2F2F2] tracking-tight">
                  Career Graph & Seasonal Performance
                </h2>
                <p className="text-[14px] sm:text-[15px] text-[#A3A3A3] mt-2 max-w-2xl leading-relaxed">
                  Explore how a batter's impact evolves across seasons. Showcase seasonal trajectories across runs, strike rates, Strategy 4 contribution ratings, positive contribution frequency, and ball efficiency.
                </p>
              </div>
              <Link
                to="/career"
                className="btn-gold text-[12.5px] py-2 px-4.5 self-start md:self-auto shrink-0 inline-flex items-center gap-2 shadow-sm"
              >
                <span>Explore Career Graphs</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold">
                  Volume & Rate
                </span>
                <h4 className="font-heading text-[16px] font-bold text-[#F2F2F2]">Runs & Strike Rate</h4>
                <p className="text-[12.5px] text-[#858585] leading-relaxed">
                  Seasonal total runs, balls faced, and strike rate trends compared against league baselines across tournaments.
                </p>
              </div>

              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold">
                  Contextual Quality
                </span>
                <h4 className="font-heading text-[16px] font-bold text-[#F2F2F2]">Average Contribution</h4>
                <p className="text-[12.5px] text-[#858585] leading-relaxed">
                  Seasonal Strategy 4 contribution ratings benchmarked against the 50.0 par baseline to measure situational value added.
                </p>
              </div>

              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#5A9E60] font-semibold">
                  Reliability Rate
                </span>
                <h4 className="font-heading text-[16px] font-bold text-[#F2F2F2]">Positive Contribution Rate</h4>
                <p className="text-[12.5px] text-[#858585] leading-relaxed">
                  Percentage of innings where the batter produced positive underlying contribution, measuring consistency of match equity.
                </p>
              </div>

              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2">
                <span className="text-[11px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold">
                  Discipline & Splits
                </span>
                <h4 className="font-heading text-[16px] font-bold text-[#F2F2F2]">Dot-Balls & Bowling Splits</h4>
                <p className="text-[12.5px] text-[#858585] leading-relaxed">
                  Dot-ball percentages, boundary percentages, and career progression trends against pace versus spin bowling.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Feature C: Player Comparison */}
        <section className="px-5 sm:px-8 lg:px-12 max-w-6xl mx-auto w-full">
          <div className="bg-[#121212] border border-[#2D2D2D] rounded-2xl p-6 sm:p-9 shadow-xl space-y-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#222222] pb-6">
              <div>
                <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold mb-1">
                  <Users className="w-4 h-4" />
                  <span>HEAD-TO-HEAD BENCHMARKING</span>
                </div>
                <h2 className="font-heading text-[24px] sm:text-[30px] font-bold text-[#F2F2F2] tracking-tight">
                  Player Comparison
                </h2>
                <p className="text-[14px] sm:text-[15px] text-[#A3A3A3] mt-2 max-w-2xl leading-relaxed">
                  Compare up to five batters head-to-head within any season using metrics supported by the existing application: contribution ratings, situational splits, phase performance, and team shares.
                </p>
              </div>
              <Link
                to="/compare"
                className="btn-gold text-[12.5px] py-2 px-4.5 self-start md:self-auto shrink-0 inline-flex items-center gap-2 shadow-sm"
              >
                <span>Launch Player Comparison</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2.5">
                <div className="flex items-center gap-2 text-[#D4AF57]">
                  <BarChart3 className="w-4 h-4" />
                  <span className="font-heading text-[15px] font-bold text-[#F2F2F2]">
                    Contribution vs Par (50.0)
                  </span>
                </div>
                <p className="text-[13px] text-[#A3A3A3] leading-relaxed">
                  Direct side-by-side comparison of overall Contribution Scores, Positive Contribution volume, and team contribution shares.
                </p>
              </div>

              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2.5">
                <div className="flex items-center gap-2 text-[#D4AF57]">
                  <Layers className="w-4 h-4" />
                  <span className="font-heading text-[15px] font-bold text-[#F2F2F2]">
                    Three-Pillar Breakdown
                  </span>
                </div>
                <p className="text-[13px] text-[#A3A3A3] leading-relaxed">
                  Inspect the underlying pillars side-by-side: Match Context (P1), Individual Execution (P2), and Team-State Trajectory (P3).
                </p>
              </div>

              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2.5">
                <div className="flex items-center gap-2 text-[#D4AF57]">
                  <Compass className="w-4 h-4" />
                  <span className="font-heading text-[15px] font-bold text-[#F2F2F2]">
                    Phase & Situation Splits
                  </span>
                </div>
                <p className="text-[13px] text-[#A3A3A3] leading-relaxed">
                  Evaluate batters across 1st innings vs Chasing, Powerplay (0–6), Middle Overs (6–16), Death (16–20), and high-pressure situations.
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Feature D: Ground & Venue Analysis */}
        <section className="px-5 sm:px-8 lg:px-12 max-w-6xl mx-auto w-full">
          <div className="bg-[#121212] border border-[#2D2D2D] rounded-2xl p-6 sm:p-9 shadow-xl space-y-8">
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b border-[#222222] pb-6">
              <div>
                <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-[#D4AF57] font-semibold mb-1">
                  <MapPin className="w-4 h-4" />
                  <span>VENUE-LEVEL CONTEXT</span>
                </div>
                <h2 className="font-heading text-[24px] sm:text-[30px] font-bold text-[#F2F2F2] tracking-tight">
                  Ground & Venue Analysis
                </h2>
                <p className="text-[14px] sm:text-[15px] text-[#A3A3A3] mt-2 max-w-2xl leading-relaxed">
                  Pitches and stadium dimensions directly influence match context. Explore ground-level statistics, first vs second innings scoring patterns, pace versus spin characteristics, and historical match logs.
                </p>
              </div>
              <Link
                to="/ground-analysis"
                className="btn-gold text-[12.5px] py-2 px-4.5 self-start md:self-auto shrink-0 inline-flex items-center gap-2 shadow-sm"
              >
                <span>Explore Ground Analysis</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2.5">
                <div className="flex items-center gap-2 text-[#D4AF57]">
                  <Scale className="w-4 h-4" />
                  <span className="font-heading text-[15px] font-bold text-[#F2F2F2]">
                    1st vs 2nd Innings Baselines
                  </span>
                </div>
                <p className="text-[13px] text-[#A3A3A3] leading-relaxed">
                  Average first and second innings scores, defend versus chase win percentages, and rolling 5-year versus all-time venue trends.
                </p>
              </div>

              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2.5">
                <div className="flex items-center gap-2 text-[#D4AF57]">
                  <Zap className="w-4 h-4" />
                  <span className="font-heading text-[15px] font-bold text-[#F2F2F2]">
                    Phase Tempo & Bowling Splits
                  </span>
                </div>
                <p className="text-[13px] text-[#A3A3A3] leading-relaxed">
                  Powerplay, middle, and death-over run rates, alongside bowling discipline profiles (pace vs spin wickets, averages, and economies).
                </p>
              </div>

              <div className="bg-[#161616] p-5 rounded-xl border border-[#262626] space-y-2.5">
                <div className="flex items-center gap-2 text-[#D4AF57]">
                  <Calendar className="w-4 h-4" />
                  <span className="font-heading text-[15px] font-bold text-[#F2F2F2]">
                    Match History & Conditions
                  </span>
                </div>
                <p className="text-[13px] text-[#A3A3A3] leading-relaxed">
                  Chronological match outcomes at each ground with condition disclosures for standard fixtures, DLS rain-shortened matches, and reduced overs.
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>

      {/* 4. Historical Cricket Data Coverage Section */}
      <section className="py-14 sm:py-20 px-5 sm:px-8 lg:px-12 bg-[#0E0E0E] border-t border-[#202020]">
        <div className="max-w-5xl mx-auto space-y-10">
          <div className="text-center max-w-2xl mx-auto">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-[#D4AF57]">
              DATASET SCOPE & INTEGRITY
            </span>
            <h2 className="font-heading text-[24px] sm:text-[32px] font-bold text-[#F2F2F2] mt-1.5 tracking-tight">
              Historical Cricket Data Coverage
            </h2>
            <p className="text-[14px] sm:text-[15px] text-[#A3A3A3] mt-3 leading-relaxed">
              Explore historical cricket data across multiple seasons and tournament editions. Coverage varies by competition, season and source-data availability.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* IPL Card */}
            <div className="bg-[#161616] p-6 rounded-xl border border-[#2D2D2D] hover:border-[#D4AF57]/60 transition-colors flex flex-col justify-between space-y-5">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-[#101010] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57]">
                    <Trophy className="w-5 h-5" />
                  </div>
                  <span className="badge-gold">IPL</span>
                </div>
                <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2]">
                  Indian Premier League
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-2.5 leading-relaxed">
                  Extensive historical league coverage across multiple seasons, featuring complete situational ball-by-ball analysis and player season leaderboards.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleSelectCompetition('ipl')}
                className="w-full btn-secondary text-[12.5px] py-2 px-3 flex items-center justify-between cursor-pointer"
              >
                <span>Explore IPL Analytics</span>
                <ChevronRight className="w-4 h-4 text-[#D4AF57]" />
              </button>
            </div>

            {/* International T20Is Card */}
            <div className="bg-[#161616] p-6 rounded-xl border border-[#2D2D2D] hover:border-[#D4AF57]/60 transition-colors flex flex-col justify-between space-y-5">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-[#101010] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57]">
                    <Globe className="w-5 h-5" />
                  </div>
                  <span className="badge-gold">T20I</span>
                </div>
                <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2]">
                  International Men's T20Is
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-2.5 leading-relaxed">
                  International bilateral series and multi-nation tournaments across international cricket boards with situational evaluations against diverse global oppositions.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleSelectCompetition('t20i')}
                className="w-full btn-secondary text-[12.5px] py-2 px-3 flex items-center justify-between cursor-pointer"
              >
                <span>Explore T20I Analytics</span>
                <ChevronRight className="w-4 h-4 text-[#D4AF57]" />
              </button>
            </div>

            {/* ICC T20 World Cup Historical Editions Card */}
            <div className="bg-[#161616] p-6 rounded-xl border border-[#2D2D2D] hover:border-[#D4AF57]/60 transition-colors flex flex-col justify-between space-y-5">
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-lg bg-[#101010] border border-[#2D2D2D] flex items-center justify-center text-[#D4AF57]">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                  <span className="badge-gold">WORLD CUP</span>
                </div>
                <h3 className="font-heading text-[17px] font-bold text-[#F2F2F2]">
                  ICC Men's T20 World Cups
                </h3>
                <p className="text-[13px] text-[#B8B8B8] mt-2.5 leading-relaxed">
                  Official ICC Men's T20 World Cup historical tournament editions, enabling tournament-specific filtering to evaluate high-pressure world championship performances.
                </p>
              </div>
              <button
                type="button"
                onClick={() => handleSelectCompetition('t20i')}
                className="w-full btn-secondary text-[12.5px] py-2 px-3 flex items-center justify-between cursor-pointer"
              >
                <span>Explore World Cup Editions</span>
                <ChevronRight className="w-4 h-4 text-[#D4AF57]" />
              </button>
            </div>
          </div>

          {/* Cautious Integrity Note */}
          <div className="p-4 sm:p-5 rounded-xl bg-[#121212] border border-[#262626] flex items-start gap-3.5">
            <div className="w-7 h-7 rounded-lg bg-[#161616] border border-[#2D2D2D] flex items-center justify-center shrink-0 text-[#D4AF57] mt-0.5">
              <Info className="w-3.5 h-3.5" />
            </div>
            <div className="text-[12.5px] sm:text-[13px] text-[#858585] leading-relaxed space-y-1">
              <span className="text-[#D4AF57] font-semibold block">Coverage Transparency & Data Standards:</span>
              <span>
                CricImpact calculates contextual contribution strictly from verified ball-by-ball delivery telemetry. Records require delivery-level match events (runs, wickets, balls remaining, extras, and match situations) to generate valid contextual baselines. Matches with incomplete delivery logs are excluded to prevent skewed historical ratings.
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 5. How It Works Pipeline Section */}
      <section id="how-it-works" className="py-14 sm:py-20 px-5 sm:px-8 lg:px-12 bg-[#080808] border-t border-[#202020]">
        <div className="max-w-4xl mx-auto">
          <div className="text-center max-w-xl mx-auto mb-12">
            <span className="text-[11px] font-semibold uppercase tracking-widest text-[#D4AF57]">
              EVALUATION PIPELINE
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
            <div className="bg-[#121212] p-5 sm:p-6 rounded-xl border border-[#262626] flex flex-col sm:flex-row sm:items-start gap-4">
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
            <div className="bg-[#121212] p-5 sm:p-6 rounded-xl border border-[#262626] flex flex-col sm:flex-row sm:items-start gap-4">
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
            <div className="bg-[#121212] p-5 sm:p-6 rounded-xl border border-[#262626] flex flex-col sm:flex-row sm:items-start gap-4">
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

      {/* 6. Final Call to Action Banner */}
      <section className="py-14 sm:py-20 px-5 sm:px-8 lg:px-12 bg-[#0E0E0E] border-t border-[#202020]">
        <div className="max-w-4xl mx-auto bg-gradient-to-b from-[#181818] to-[#121212] border border-[#3D351E]/60 rounded-2xl p-8 sm:p-12 text-center space-y-6 shadow-2xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#1E190E] border border-[#3D351E] text-[#D4AF57] text-[11px] font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Launch CricImpact</span>
          </div>

          <h2 className="font-heading text-[26px] sm:text-[34px] font-bold text-[#F2F2F2] tracking-tight">
            Ready to Explore Contextual Cricket Analytics?
          </h2>

          <p className="text-[14px] sm:text-[16px] text-[#B8B8B8] max-w-xl mx-auto leading-relaxed">
            Dive into season leaderboards, analyze player match contributions, and uncover insights across IPL and international T20 cricket.
          </p>

          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3.5 w-full sm:w-auto">
            <Link
              to="/dashboard"
              className="btn-gold w-full sm:w-auto px-7 py-3 text-[14px] shadow-md flex items-center justify-center gap-2"
            >
              <span>Explore Analytics</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
            <Link
              to="/compare"
              className="btn-secondary w-full sm:w-auto px-7 py-3 text-[14px] flex items-center justify-center gap-2"
            >
              <span>Compare Players</span>
              <Users className="w-4 h-4 text-[#D4AF57]" />
            </Link>
          </div>
        </div>
      </section>

      {/* 7. Comprehensive Reusable Footer */}
      <Footer />
    </div>
  );
}
