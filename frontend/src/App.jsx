import React, { useState, useEffect } from 'react';
import axios from 'axios';

function App() {
  const [championStats, setChampionStats] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [etlStatus, setEtlStatus] = useState('');
  const [isEtlRunning, setIsEtlRunning] = useState(false);

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

  const handleRunEtl = () => {
    setIsEtlRunning(true);
    setEtlStatus('Starting data refresh...');

    axios.post('http://127.0.0.1:5000/api/run-etl')
      .then(response => {
        setEtlStatus('Refresh in progress. The bar below is an estimate. Please wait...');
        setTimeout(() => {
          setIsEtlRunning(false);
          setEtlStatus('Refresh complete! Reload the page (Ctrl+R) to see new data.');
        }, 360000); // 6 minutes
      })
      .catch(error => {
        setEtlStatus('Failed to start data refresh. Please try again.');
        setIsEtlRunning(false);
      });
  };

  return (
    <div className="bg-gray-900 text-white min-h-screen p-8 font-sans">
      <header className="text-center mb-10">
        <h1 className="text-4xl font-bold">League of Legends - Challenger Stats</h1>
        <p className="text-gray-400">Match Data Analytics Platform (2025)</p>

        <div className="mt-6 max-w-md mx-auto">
          <button 
            onClick={handleRunEtl}
            disabled={isEtlRunning}
            className="bg-cyan-500 hover:bg-cyan-600 text-white font-bold py-2 px-4 rounded w-full disabled:bg-gray-500 disabled:cursor-not-allowed transition-colors"
          >
            {isEtlRunning ? 'Refresh in Progress...' : 'Refresh Latest Match Data'}
          </button>
          {etlStatus && <p className="text-sm text-gray-400 mt-2 h-4">{etlStatus}</p>}

          {/* --- NEW LOADING BAR --- */}
          {isEtlRunning && (
            <div className="w-full bg-gray-700 rounded-full h-2.5 mt-2 overflow-hidden">
              <div className="bg-cyan-400 h-2.5 rounded-full animate-progress"></div>
            </div>
          )}
        </div>
      </header>

      <main>
        {/* ... (The rest of the JSX) ... */}
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
    </div>
  );
}

export default App;