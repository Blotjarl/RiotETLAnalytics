import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [stats, setStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    axios.get('http://127.0.0.1:5000/api/champion-stats')
      .then(response => {
        setStats(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("There was an error fetching the data!", error);
        setError(error);
        setLoading(false);
      });
  }, []);

  return (
    <div className="bg-gray-900 text-white min-h-screen p-8">
      <header className="text-center mb-10">
        <h1 className="text-4xl font-bold">League of Legends - Challenger Stats</h1>
        <p className="text-gray-400">Match Data Analytics Platform (2025)</p>
      </header>
      <main>
        {loading && <p className="text-center">Loading data...</p>}
        {error && <p className="text-center text-red-500">Error fetching data. Is the backend server running?</p>}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map(champion => (
            <div key={champion.championName} className="bg-gray-800 p-4 rounded-lg shadow-lg">
              <h2 className="text-xl font-bold text-cyan-400">{champion.championName}</h2>
              <p>Win Rate: <span className="font-semibold">{parseFloat(champion.winRate).toFixed(2)}%</span></p>
              <p>Games Played: <span className="font-semibold">{champion.playCount}</span></p>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

export default App;