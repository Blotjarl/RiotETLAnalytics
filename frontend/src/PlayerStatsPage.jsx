import React, { useState, useEffect } from 'react';
import { supabase } from './supabaseClient';

function PlayerStatsPage() {
  const [players, setPlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Fetch the apex leaderboard from Supabase when the component loads
  useEffect(() => {
    setLoading(true);
    supabase
      .from('players')
      .select('*')
      .order('leaderboardrank', { ascending: true })
      .then(({ data, error }) => {
        if (error) {
          console.error("There was an error fetching the player data!", error);
          setError(error);
        } else {
          setPlayers(data);
        }
        setLoading(false);
      });
  }, []); // The empty array ensures this effect runs only once

  return (
    <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-8">
      {/* Column 1: Apex Leaderboard (Challenger/Grandmaster/Master) */}
      <div className="md:col-span-1">
        <h2 className="text-3xl font-semibold mb-4">Apex Leaderboard</h2>
        <div className="bg-gray-800 rounded-lg p-4 h-[75vh] overflow-y-auto">
          {loading && <p className="text-center p-4">Loading players...</p>}
          {error && <p className="text-center p-4 text-red-500">Error fetching player data.</p>}

          {!loading && !error && (
            <ul className="space-y-1">
              {players.map((player) => (
                <li
                  key={player.puuid}
                  onClick={() => setSelectedPlayer(player)}
                  className={`cursor-pointer p-3 rounded-md hover:bg-cyan-600 transition-colors flex justify-between items-center text-left ${selectedPlayer?.puuid === player.puuid ? 'bg-cyan-500' : ''}`}
                >
                  <div>
                    <span className="font-bold text-lg">#{player.leaderboardrank}</span>
                    <span className="text-xs text-gray-400 ml-2">{player.tier}</span>
                  </div>
                  <span className="font-semibold text-gray-300 ml-4">{player.leaguepoints} LP</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* Column 2: Player Stats Display */}
      <div className="md:col-span-2">
        <h2 className="text-3xl font-semibold mb-4">Specific Stats</h2>
        <div className="bg-gray-800 rounded-lg p-6 min-h-[75vh] flex items-center justify-center">
          {!selectedPlayer ? (
            <p className="text-gray-400">Select a player from the list to see their stats.</p>
          ) : (
            <div className="text-center w-full max-w-md">
              <h3 className="text-4xl font-bold text-cyan-400 mb-2">
                Rank #{selectedPlayer.leaderboardrank}
              </h3>
              <p className="text-gray-400 mb-8">{selectedPlayer.tier} &middot; {selectedPlayer.leaguepoints} LP</p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 text-2xl">
                <div className="bg-gray-700 p-6 rounded-lg shadow-lg">
                  <p className="text-gray-400 text-sm font-bold uppercase tracking-wider">Wins</p>
                  <p className="font-bold text-green-400 mt-2 text-4xl">{selectedPlayer.wins}</p>
                </div>
                <div className="bg-gray-700 p-6 rounded-lg shadow-lg">
                  <p className="text-gray-400 text-sm font-bold uppercase tracking-wider">Losses</p>
                  <p className="font-bold text-red-400 mt-2 text-4xl">{selectedPlayer.losses}</p>
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlayerStatsPage;
