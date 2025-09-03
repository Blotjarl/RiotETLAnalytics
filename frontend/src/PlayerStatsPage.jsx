import React, { useState, useEffect } from 'react';

// --- MOCK DATA FOR FRONTEND TESTING ---
// This simulates the data we will eventually get from our backend.
const mockPlayers = Array.from({ length: 100 }, (_, i) => ({
  rank: i + 1,
  puuid: `PUUID_PLAYER_${i + 1}`,
  summonerName: `ChallengerPlayer${i + 1}`,
  leaguePoints: 2000 - (i * 10),
}));
// --- END MOCK DATA ---

function PlayerStatsPage() {
  const [players, setPlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState(null);
  const [loading, setLoading] = useState(true);

  // Simulate fetching data when the component loads
  useEffect(() => {
    // In the future, we will replace this with an axios call to our API
    setPlayers(mockPlayers);
    setLoading(false);
  }, []);

  return (
    <div className="p-8 grid grid-cols-1 md:grid-cols-3 gap-8">
      {/* Column 1: Top 100 Player List */}
      <div className="md:col-span-1">
        <h2 className="text-3xl font-semibold mb-4">Top 100 Players</h2>
        <div className="bg-gray-800 rounded-lg p-4 h-[75vh] overflow-y-auto">
          {loading ? <p>Loading players...</p> : (
            <ul className="space-y-1">
              {players.map((player) => (
                <li 
                  key={player.puuid}
                  onClick={() => setSelectedPlayer(player)}
                  className="cursor-pointer p-3 rounded-md hover:bg-cyan-500 flex justify-between items-center text-left"
                >
                  <div className="flex items-center truncate">
                    <span className="font-bold w-10">{player.rank}.</span>
                    <div className="truncate">
                      <p className="font-semibold truncate" title={player.summonerName}>{player.summonerName}</p>
                      <p className="text-xs text-gray-400 truncate" title={player.puuid}>{player.puuid}</p>
                    </div>
                  </div>
                  <span className="font-bold text-gray-300 ml-2">{player.leaguePoints} LP</span>
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
            <div>
              <h3 className="text-4xl font-bold text-cyan-400 mb-6">{selectedPlayer.summonerName}</h3>
              <p className="text-center text-gray-300">Detailed stats will be displayed here once the backend is connected.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default PlayerStatsPage;
