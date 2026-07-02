import React, { useState, useEffect } from 'react';
import { supabase } from './supabaseClient';

const TIERS = ['CHALLENGER', 'GRANDMASTER', 'MASTER'];

function ChampionStatsPage() {
  const [tier, setTier] = useState('CHALLENGER');
  const [championStats, setChampionStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    setLoading(true);
    supabase
      .from('champion_stats_by_tier')
      .select('*')
      .eq('tier', tier)
      .order('playcount', { ascending: false })
      .then(({ data, error }) => {
        if (error) {
          console.error("There was an error fetching the data!", error);
          setError(error);
        } else {
          setChampionStats(data);
        }
        setLoading(false);
      });
  }, [tier]);

  return (
    <main className="p-8">
      <div className="flex items-center justify-between mb-6 border-l-4 border-cyan-400 pl-4">
        <h2 className="text-3xl font-semibold">Champion Stats</h2>
        <select
          value={tier}
          onChange={(e) => setTier(e.target.value)}
          className="bg-gray-800 text-white rounded-md px-3 py-2"
        >
          {TIERS.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>

      {loading && <p className="text-center">Loading data...</p>}
      {error && <p className="text-center text-red-500">Error fetching data.</p>}

      {!loading && !error && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {championStats.map(champion => (
            <div key={champion.championname} className="bg-gray-800 p-4 rounded-lg shadow-lg">
              <h3 className="text-xl font-bold text-cyan-400">{champion.championname}</h3>
              <p>Win Rate: <span className="font-semibold">{champion.winrate}%</span></p>
              <p>Games Played: <span className="font-semibold">{champion.playcount}</span></p>
            </div>
          ))}
        </div>
      )}
    </main>
  );
}

export default ChampionStatsPage;
