import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import { CompetitionProvider } from './context/CompetitionContext';
import LandingPage from './pages/LandingPage';
import Dashboard from './pages/Dashboard';
import PlayerAnalysis from './pages/PlayerAnalysis';
import MatchDetail from './pages/MatchDetail';
import AuditInsights from './pages/AuditInsights';
import PlayerComparison from './pages/PlayerComparison';
import About from './pages/About';
import Methodology from './pages/Methodology';
import BatterBowlingMatchup from './pages/BatterBowlingMatchup';
import Matches from './pages/Matches';
import MatchOverview from './pages/MatchOverview';
import Seasons from './pages/Seasons';
import Players from './pages/Players';
import CareerGraph from './pages/CareerGraph';
import GroundAnalysis from './pages/GroundAnalysis';

function AppLayout() {
  return (
    <div className="min-h-screen bg-[#080808] text-[#F2F2F2] flex flex-col font-ui selection:bg-[#D4AF57]/30 selection:text-[#F2F2F2]">
      {/* Official Top Horizontal Navbar with Logo, Centered Navigation, and Competition Selector */}
      <Navbar />

      {/* Main Content Area - Expanded to 94% Viewport Width */}
      <main className="flex-1 w-[94%] max-w-[1850px] mx-auto px-2 sm:px-4 lg:px-6 py-6 sm:py-8">
        <Outlet />
      </main>

      {/* Reusable Application Footer */}
      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <CompetitionProvider>
        <Routes>
          {/* Landing Page */}
          <Route path="/" element={<LandingPage />} />

          {/* Analytics Workspace Layout (Horizontal Navbar) */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/analytics" element={<Navigate to="/dashboard" replace />} />
            <Route path="/players" element={<Players />} />
            <Route path="/career" element={<CareerGraph />} />
            <Route path="/career/:playerId" element={<CareerGraph />} />
            <Route path="/career-graph" element={<Navigate to="/career" replace />} />
            <Route path="/ground-analysis" element={<GroundAnalysis />} />
            <Route path="/venues" element={<Navigate to="/ground-analysis" replace />} />
            <Route path="/matches" element={<Matches />} />
            <Route path="/matches/:matchId" element={<MatchOverview />} />
            <Route path="/match/:matchId" element={<MatchOverview />} />
            <Route path="/match/:matchId/player/:playerId" element={<MatchDetail />} />
            <Route path="/seasons" element={<Seasons />} />
            <Route path="/matchups" element={<BatterBowlingMatchup />} />
            <Route path="/batters-vs-bowling-type" element={<BatterBowlingMatchup />} />
            <Route path="/compare" element={<PlayerComparison />} />
            <Route path="/player/:playerId" element={<PlayerAnalysis />} />
            <Route path="/player/:playerId/:season" element={<PlayerAnalysis />} />
            <Route path="/audit" element={<AuditInsights />} />
            <Route path="/about" element={<About />} />
            <Route path="/methodology" element={<Methodology />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Route>
        </Routes>
      </CompetitionProvider>
    </BrowserRouter>
  );
}
