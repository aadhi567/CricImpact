
import React from 'react';
import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Analytics } from '@vercel/analytics/react';

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
      {/* Main navigation */}
      <Navbar />

      {/* Main content area */}
      <main className="flex-1 w-full max-w-[1680px] mx-auto px-3 sm:px-5 lg:px-6 py-3 sm:py-5 min-w-0">
        <Outlet />
      </main>

      {/* Application footer */}
      <Footer />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <CompetitionProvider>
        <Routes>
          {/* Landing page */}
          <Route path="/" element={<LandingPage />} />

          {/* Main application layout */}
          <Route element={<AppLayout />}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route
              path="/analytics"
              element={<Navigate to="/dashboard" replace />}
            />

            <Route path="/players" element={<Players />} />

            <Route path="/career" element={<CareerGraph />} />
            <Route path="/career/:playerId" element={<CareerGraph />} />
            <Route
              path="/career-graph"
              element={<Navigate to="/career" replace />}
            />

            <Route path="/ground-analysis" element={<GroundAnalysis />} />
            <Route
              path="/venues"
              element={<Navigate to="/ground-analysis" replace />}
            />

            <Route path="/matches" element={<Matches />} />
            <Route path="/matches/:matchId" element={<MatchOverview />} />
            <Route path="/match/:matchId" element={<MatchOverview />} />
            <Route
              path="/match/:matchId/player/:playerId"
              element={<MatchDetail />}
            />

            <Route path="/seasons" element={<Seasons />} />

            <Route path="/matchups" element={<BatterBowlingMatchup />} />
            <Route
              path="/batters-vs-bowling-type"
              element={<BatterBowlingMatchup />}
            />

            <Route path="/compare" element={<PlayerComparison />} />

            <Route path="/player/:playerId" element={<PlayerAnalysis />} />
            <Route
              path="/player/:playerId/:season"
              element={<PlayerAnalysis />}
            />
            <Route
              path="/player/:playerId/:season/*"
              element={<PlayerAnalysis />}
            />
            <Route
              path="/player/:playerId/*"
              element={<PlayerAnalysis />}
            />

            <Route path="/audit" element={<AuditInsights />} />
            <Route path="/about" element={<About />} />
            <Route path="/methodology" element={<Methodology />} />

            {/* Redirect unknown routes */}
            <Route
              path="*"
              element={<Navigate to="/dashboard" replace />}
            />
          </Route>
        </Routes>
      </CompetitionProvider>

      {/* Vercel Web Analytics: tracks page views */}
      <Analytics />
    </BrowserRouter>
  );
}
