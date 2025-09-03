import React, { useState, useEffect } from 'react';
import axios from 'axios';

function ChampionStatsPage() {
  const [championStats, setChampionStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // The state for the refresh button is no longer needed

  const fetchData = () => {
    setLoading(true);
    axios.get('http://127.0.0.1:5000/api/champion-stats')
      .then(response => {
        setChampionStats(response.data);
        setLoading(false);
      })
      .catch(error => {
        console.error("There was an error fetching the data!", error);
        setError(error);
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchData();
  }, []);

  // The handleRunEtl function is no longer needed

  return (
    // The outer div and the <header> element have been removed.
    // The component now starts directly with the <main> content.
    <main className="p-8">
      {loading && <p className="text-center">Loading data...</p>}
      {error && <p className="text-center text-red-500">Error fetching data.</p>}
      
      <section>
        <h2 className="text-3xl font-semibold mb-6 border-l-4 border-cyan-400 pl-4">Champion Stats</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {championStats.map(champion => (
            <div key={champion.championName} className="bg-gray-800 p-4 rounded-lg shadow-lg">
              <h3 className="text-xl font-bold text-cyan-400">{champion.championName}</h3>
              <p>Win Rate: <span className="font-semibold">{parseFloat(champion.winRate).toFixed(2)}%</span></p>
              <p>Games Played: <span className="font-semibold">{champion.playCount}</span></p>
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

export default ChampionStatsPage;
