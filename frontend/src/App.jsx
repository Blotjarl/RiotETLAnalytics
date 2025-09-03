import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link, NavLink } from 'react-router-dom';
import ChampionStatsPage from './ChampionStatsPage';
import PlayerStatsPage from './PlayerStatsPage';

function App() {
  const activeLinkStyle = {
    color: '#22d3ee', // Tailwind's cyan-400 color
    borderBottom: '2px solid #22d3ee'
  };

  return (
    <Router>
      <div className="bg-gray-900 text-white min-h-screen font-sans">
        <header className="text-center p-8 border-b border-gray-700">
          <h1 className="text-4xl font-bold">League of Legends - Challenger Stats</h1>
          <p className="text-gray-400 mt-2">Match Data Analytics Platform (2025)</p>
          
          {/* --- NAVIGATION MENU --- */}
          <nav className="flex justify-center gap-8 mt-6">
            <NavLink 
              to="/" 
              className="text-lg pb-1 border-b-2 border-transparent hover:text-cyan-400 transition-colors"
              style={({ isActive }) => isActive ? activeLinkStyle : undefined}
            >
              Champion Stats
            </NavLink>
            <NavLink 
              to="/players" 
              className="text-lg pb-1 border-b-2 border-transparent hover:text-cyan-400 transition-colors"
              style={({ isActive }) => isActive ? activeLinkStyle : undefined}
            >
              Player Stats
            </NavLink>
          </nav>
        </header>

        <main>
          <Routes>
            <Route path="/" element={<ChampionStatsPage />} />
            <Route path="/players" element={<PlayerStatsPage />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
